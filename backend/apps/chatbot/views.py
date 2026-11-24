from django.db import transaction
from django.db.models import Max
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsAdminOrSupervisor

from .connectors import get_connector
from .engine import simulate
from .models import AIProvider, BotFlow, BotFlowVersion, BotSession, Connector, KnowledgeArticle, KnowledgeBase, KnowledgeQuery
from .schema import NODE_TYPES, validate_definition
from .serializers import (
    AIProviderSerializer, BotFlowSerializer, KnowledgeArticleSerializer, KnowledgeBaseSerializer, KnowledgeQuerySerializer, BotFlowVersionSerializer, BotSessionSerializer,
    ConnectorLogSerializer, ConnectorSerializer,
)
from .templates import FLOW_TEMPLATES


class IsAdminForWrites(IsAdminOrSupervisor):
    """Lectura: admin y supervisor. Conectores (credenciales): solo admin escribe."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return getattr(request.user, 'role', None) == 'admin' or request.user.is_superuser


def _connector_ids():
    return set(Connector.objects.filter(is_active=True).values_list('id', flat=True))


def _ai_ids():
    return set(AIProvider.objects.filter(is_active=True).values_list('id', flat=True))


class AIProviderViewSet(viewsets.ModelViewSet):
    queryset = AIProvider.objects.all()
    serializer_class = AIProviderSerializer
    permission_classes = [IsAdminForWrites]

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        from .ai import AIError, test_provider
        try:
            return Response(test_provider(self.get_object()))
        except AIError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def classify(self, request, pk=None):
        """Prueba un mensaje contra intenciones: {text, intents, fields}."""
        from .ai import AIError, classify
        text = str(request.data.get('text') or '')[:2000]
        intents = request.data.get('intents') or []
        if not text or not isinstance(intents, list) or not intents:
            return Response({'error': 'text e intents son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(classify(self.get_object(), text, intents, request.data.get('fields') or [],
                                     purpose='test'))
        except AIError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def usage(self, request, pk=None):
        rows = self.get_object().usage.all()[:100]
        return Response([{'created_at': r.created_at, 'purpose': r.purpose, 'status': r.status,
                          'tokens': r.prompt_tokens + r.completion_tokens, 'duration_ms': r.duration_ms,
                          'result': r.result, 'error': r.error} for r in rows])


class ConnectorViewSet(viewsets.ModelViewSet):
    queryset = Connector.objects.all()
    serializer_class = ConnectorSerializer
    permission_classes = [IsAdminForWrites]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Prueba la conexión (GLPI: inicia y cierra sesión)."""
        res = get_connector(self.get_object()).execute('__test__', {}, source='test')
        return Response({'status': res.status, 'data': res.data, 'error': res.error,
                         'duration_ms': res.duration_ms},
                        status=status.HTTP_200_OK if res.status != 'error' else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='run')
    def run_action(self, request, pk=None):
        """Ejecuta una acción con parámetros de prueba (solo administradores)."""
        if getattr(request.user, 'role', None) != 'admin' and not request.user.is_superuser:
            return Response({'error': 'Solo administradores'}, status=status.HTTP_403_FORBIDDEN)
        act = request.data.get('action')
        params = request.data.get('params') or {}
        if not act or not isinstance(params, dict):
            return Response({'error': 'action y params son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
        res = get_connector(self.get_object()).execute(act, params, source='test')
        return Response({'status': res.status, 'data': res.data, 'error': res.error,
                         'duration_ms': res.duration_ms})

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        qs = self.get_object().logs.all()[:100]
        return Response(ConnectorLogSerializer(qs, many=True).data)


class BotFlowViewSet(viewsets.ModelViewSet):
    queryset = BotFlow.objects.prefetch_related('channels').select_related('published_version')
    serializer_class = BotFlowSerializer
    permission_classes = [IsAdminOrSupervisor]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def catalog(self, request):
        """Tipos de bloque, conectores activos con sus acciones y plantillas de flujo."""
        connectors = [{'id': c.id, 'name': c.name, 'type': c.connector_type,
                       'actions': ConnectorSerializer(c).data['actions']}
                      for c in Connector.objects.filter(is_active=True)]
        ai_providers = [{'id': p.id, 'name': p.name, 'model': p.model}
                        for p in AIProvider.objects.filter(is_active=True)]
        kbs = [{'id': k.id, 'name': k.name} for k in KnowledgeBase.objects.filter(is_active=True)]
        return Response({'node_types': sorted(NODE_TYPES), 'connectors': connectors, 'ai_providers': ai_providers,
                         'knowledge_bases': kbs,
                         'templates': [{'key': k, 'name': t['name'], 'description': t['description']}
                                       for k, t in FLOW_TEMPLATES.items()]})

    @action(detail=False, methods=['post'], url_path='from-template')
    def from_template(self, request):
        key = request.data.get('template')
        tpl = FLOW_TEMPLATES.get(key)
        if not tpl:
            return Response({'error': 'Plantilla desconocida'}, status=status.HTTP_400_BAD_REQUEST)
        flow = BotFlow.objects.create(name=request.data.get('name') or tpl['name'],
                                      description=tpl['description'], draft=tpl['definition'](request.data),
                                      created_by=request.user)
        return Response(BotFlowSerializer(flow).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        flow = self.get_object()
        definition = request.data.get('definition') or flow.draft
        errors = validate_definition(definition, connectors_ids=_connector_ids(), ai_ids=_ai_ids())
        return Response({'valid': not errors, 'errors': errors})

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Valida el borrador y crea una versión inmutable que pasa a ser la publicada."""
        flow = self.get_object()
        errors = validate_definition(flow.draft, connectors_ids=_connector_ids(), ai_ids=_ai_ids())
        if errors:
            return Response({'valid': False, 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            number = (flow.versions.aggregate(m=Max('number'))['m'] or 0) + 1
            version = BotFlowVersion.objects.create(flow=flow, number=number, definition=flow.draft,
                                                    notes=(request.data.get('notes') or '')[:300],
                                                    created_by=request.user)
            flow.published_version = version
            flow.save(update_fields=['published_version', 'updated_at'])
        return Response({'valid': True, 'version': number, 'flow': BotFlowSerializer(flow).data})

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        return Response(BotFlowVersionSerializer(self.get_object().versions.all()[:50], many=True).data)

    @action(detail=True, methods=['post'], url_path=r'versions/(?P<number>[0-9]+)/restore')
    def restore(self, request, pk=None, number=None):
        """Copia una versión anterior al borrador (no la publica)."""
        flow = self.get_object()
        version = flow.versions.filter(number=number).first()
        if not version:
            return Response({'error': 'Versión no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        flow.draft = version.definition
        flow.save(update_fields=['draft', 'updated_at'])
        return Response(BotFlowSerializer(flow).data)

    @action(detail=True, methods=['post'])
    def simulate(self, request, pk=None):
        """
        Body: {"definition"?: {...}, "inputs": ["hola", {"text": "Soporte", "reply_id": "opt:a"}],
               "variables"?: {...}, "live"?: false}
        live=true ejecuta los conectores de verdad (solo administradores).
        """
        flow = self.get_object()
        definition = request.data.get('definition') or flow.draft
        # El simulador acepta borradores incompletos: solo exige un bloque de inicio
        starts = {n.get('id') for n in (definition or {}).get('nodes', [])}
        if not isinstance(definition, dict) or definition.get('start') not in starts:
            return Response({'valid': False, 'errors': ['Marque un bloque como inicio']},
                            status=status.HTTP_400_BAD_REQUEST)
        live = bool(request.data.get('live')) and (
            getattr(request.user, 'role', None) == 'admin' or request.user.is_superuser)
        inputs = request.data.get('inputs') or []
        if not isinstance(inputs, list) or len(inputs) > 50:
            return Response({'error': 'inputs debe ser una lista (máx. 50)'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(simulate(definition, inputs, request.data.get('variables') or {}, live=live))

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        qs = BotSession.objects.filter(flow=self.get_object()).select_related(
            'conversation', 'conversation__channel', 'version')[:100]
        return Response(BotSessionSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Sesiones por estado y bloques donde más se quedan los clientes."""
        from collections import Counter
        flow = self.get_object()
        sessions = BotSession.objects.filter(flow=flow)
        by_status = Counter(sessions.values_list('status', flat=True))
        dropoff = Counter(sessions.filter(status__in=['timeout']).values_list('current_node', flat=True))
        return Response({'by_status': by_status, 'dropoff_nodes': dropoff.most_common(10),
                         'total': sum(by_status.values())})


# ══════════════════════════════════════════════════════════════════════════════
# Base de conocimiento
# ══════════════════════════════════════════════════════════════════════════════

KB_UPLOAD_EXT = ('.pdf', '.docx', '.xlsx', '.txt', '.md', '.csv')
KB_UPLOAD_MAX = 20 * 1024 * 1024


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeBase.objects.all()
    serializer_class = KnowledgeBaseSerializer
    permission_classes = [IsAdminOrSupervisor]

    @action(detail=True, methods=['post'], url_path='upload')
    def upload(self, request, pk=None):
        """Carga un documento (PDF, Word, Excel, TXT) como artículo. Se lee en el servidor."""
        import os
        import uuid
        from django.conf import settings
        from .knowledge import import_file

        kb = self.get_object()
        f = request.FILES.get('file')
        if not f:
            return Response({'error': 'Falta el archivo'}, status=status.HTTP_400_BAD_REQUEST)
        name = os.path.basename(f.name)
        if not name.lower().endswith(KB_UPLOAD_EXT):
            return Response({'error': 'Formatos permitidos: PDF, Word (.docx), Excel (.xlsx), TXT, MD, CSV'},
                            status=status.HTTP_400_BAD_REQUEST)
        if f.size > KB_UPLOAD_MAX:
            return Response({'error': 'Máximo 20 MB'}, status=status.HTTP_400_BAD_REQUEST)
        directory = os.path.join(str(settings.MEDIA_ROOT), 'knowledge')
        os.makedirs(directory, exist_ok=True)
        safe = ''.join(ch for ch in name if ch.isalnum() or ch in '._-')[:120] or 'documento'
        path = os.path.join(directory, f'{uuid.uuid4().hex[:12]}_{safe}')
        with open(path, 'wb') as out:
            for chunk in f.chunks():
                out.write(chunk)
        try:
            article = import_file(kb, path, name, request.user)
        except Exception as e:
            return Response({'error': str(e)[:300]}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            try:
                os.remove(path)  # el texto ya quedó en el artículo
            except OSError:
                pass
        return Response(KnowledgeArticleSerializer(article).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='sync-glpi')
    def sync_glpi(self, request, pk=None):
        from .knowledge import sync_glpi
        try:
            return Response(sync_glpi(self.get_object()))
        except Exception as e:
            return Response({'error': str(e)[:300]}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def unanswered(self, request, pk=None):
        """Preguntas que la base no supo responder (para completar artículos)."""
        qs = self.get_object().queries.filter(found=False)[:200]
        return Response(KnowledgeQuerySerializer(qs, many=True).data)


class KnowledgeArticleViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeArticleSerializer
    permission_classes = [IsAdminOrSupervisor]

    def get_queryset(self):
        qs = KnowledgeArticle.objects.all()
        kb = self.request.query_params.get('knowledge_base')
        if kb:
            qs = qs.filter(knowledge_base_id=kb)
        q = (self.request.query_params.get('search') or '').strip()
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q) | Q(keywords__icontains=q))
        return qs

    def perform_create(self, serializer):
        from .knowledge import index_article
        index_article(serializer.save(created_by=self.request.user))

    def perform_update(self, serializer):
        from .knowledge import index_article
        index_article(serializer.save())


class KnowledgeAssistView(viewsets.ViewSet):
    """
    Para asesores (cualquier rol excepto analista sin conversación):
      GET  /chatbot/knowledge/search/?q=…&kb=1,2     → fragmentos relevantes
      POST /chatbot/knowledge/suggest/ {conversation_id}  → respuesta sugerida a partir de la conversación
    """
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def search(self, request):
        from .knowledge import search
        q = (request.query_params.get('q') or '').strip()[:500]
        kb_ids = [int(x) for x in (request.query_params.get('kb') or '').split(',') if x.isdigit()] or None
        if len(q) < 3:
            return Response([])
        hits = search(q, kb_ids, limit=8)
        return Response(hits)

    @action(detail=False, methods=['post'])
    def suggest(self, request):
        from apps.messaging.models import Conversation
        from .knowledge import answer

        conv = Conversation.objects.filter(pk=request.data.get('conversation_id')).select_related('agent__user').first()
        if not conv:
            return Response({'error': 'Conversación no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        role = getattr(request.user, 'role', None)
        if role == 'agent' and (not conv.agent_id or conv.agent.user_id != request.user.id):
            return Response({'error': 'La conversación no es suya'}, status=status.HTTP_403_FORBIDDEN)
        last = list(conv.messages.filter(direction='inbound').exclude(body='').order_by('-sent_at')
                    .values_list('body', flat=True)[:3])
        question = (request.data.get('question') or ' '.join(reversed(last))).strip()[:1500]
        if not question:
            return Response({'error': 'No hay mensajes del cliente para analizar'}, status=status.HTTP_400_BAD_REQUEST)
        provider = AIProvider.objects.filter(pk=request.data.get('provider_id'), is_active=True).first() \
            if request.data.get('provider_id') else AIProvider.objects.filter(is_active=True).order_by('id').first()
        kb_ids = [int(x) for x in request.data.get('kb_ids') or [] if str(x).isdigit()] or None
        status_, result = answer(question, kb_ids, provider, source='agent', conversation_id=conv.id,
                                 tone='cordial y profesional, para que un asesor lo envíe al cliente')
        return Response({'status': status_, 'question': question, 'used_ai': bool(provider), **result})