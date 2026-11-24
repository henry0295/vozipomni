from django.db import transaction
from django.db.models import Max
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsAdminOrSupervisor

from .connectors import get_connector
from .engine import simulate
from .models import AIProvider, BotFlow, BotFlowVersion, BotSession, Connector
from .schema import NODE_TYPES, validate_definition
from .serializers import (
    AIProviderSerializer, BotFlowSerializer, BotFlowVersionSerializer, BotSessionSerializer,
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
        return Response({'node_types': sorted(NODE_TYPES), 'connectors': connectors, 'ai_providers': ai_providers,
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
