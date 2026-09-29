"""
Views REST de mensajería multicanal y WhatsApp Business (Meta Cloud API).

Mensajería:
  /api/messaging/channels/                          CRUD canales
  /api/messaging/conversations/                     listar (filtros: status, channel, agent, mine, unassigned)
  /api/messaging/conversations/stats/               contadores para la bandeja
  /api/messaging/conversations/start/               iniciar conversación WhatsApp con plantilla
  /api/messaging/conversations/{id}/                detalle
  /api/messaging/conversations/{id}/messages/       GET listar / POST enviar texto
  /api/messaging/conversations/{id}/send-template/  enviar plantilla (fuera de la ventana de 24 h)
  /api/messaging/conversations/{id}/assign/         asignar agente
  /api/messaging/conversations/{id}/take/           el agente toma la conversación
  /api/messaging/conversations/{id}/close/          cerrar
  /api/messaging/conversations/{id}/reopen/         reabrir
  /api/messaging/messages/{id}/media/               descargar adjunto
  /api/messaging/messages/{id}/retry/               reintentar envío fallido

WhatsApp (solo admin):
  /api/messaging/whatsapp/providers/                CRUD proveedores (Apps de Meta)
  /api/messaging/whatsapp/providers/{id}/test/      validar token
  /api/messaging/whatsapp/providers/{id}/regenerate-verify-token/
  /api/messaging/whatsapp/providers/{id}/phone-numbers/?waba_id=
  /api/messaging/whatsapp/lines/                    CRUD líneas (números)
  /api/messaging/whatsapp/lines/{id}/test/          verificar número en Meta
  /api/messaging/whatsapp/lines/{id}/subscribe/     suscribir app a la WABA (webhooks)
  /api/messaging/whatsapp/lines/{id}/sync-templates/
  /api/messaging/whatsapp/lines/{id}/send-test/     enviar plantilla de prueba
  /api/messaging/whatsapp/templates/                listar / crear / borrar plantillas

Webhook público:
  /api/messaging/webhooks/meta/<app_id>/            GET verificación, POST eventos
"""
import hashlib
import hmac
import json
import logging
import mimetypes
import os
import re

from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminOrSupervisorOrReadOnly, IsAdminUser
from .models import Channel, Conversation, Message, WhatsAppLine, WhatsAppProvider, WhatsAppTemplate
from .realtime import push
from .serializers import (
    ChannelSerializer, ConversationDetailSerializer, ConversationSerializer, MessageSerializer,
    WhatsAppLineSerializer, WhatsAppProviderSerializer, WhatsAppTemplateSerializer,
)
from .whatsapp import (
    WindowClosedError, create_outbound, process_webhook_payload,
    render_template_preview, send_outbound,
)
from .whatsapp_service import WhatsAppAPIError, WhatsAppCloudClient, client_for_line, normalize_wa_number

logger = logging.getLogger(__name__)


def _is_supervisor(user):
    return user.is_superuser or getattr(user, 'role', None) in ('admin', 'supervisor')


def _agent_for(user):
    from apps.agents.models import Agent
    return Agent.objects.filter(user=user).first()


def _api_error(e: WhatsAppAPIError, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(e.to_dict(), status=http_status)


# ══════════════════════════════════════════════════════════════════════════════
# Canales
# ══════════════════════════════════════════════════════════════════════════════

class ChannelViewSet(viewsets.ModelViewSet):
    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['channel_type', 'is_active']
    search_fields = ['name', 'identifier']
    ordering = ['channel_type', 'name']


# ══════════════════════════════════════════════════════════════════════════════
# Conversaciones
# ══════════════════════════════════════════════════════════════════════════════

class ConversationViewSet(viewsets.ModelViewSet):
    """
    Agentes: ven sus conversaciones y las sin asignar.
    Admin/supervisor: ven todas.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'channel', 'agent', 'campaign']
    search_fields = ['contact_identifier', 'contact_name', 'contact__first_name', 'contact__last_name']
    ordering_fields = ['started_at', 'closed_at', 'last_message_at']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = Conversation.objects.select_related(
            'channel__whatsapp_line', 'agent__user', 'contact', 'campaign', 'disposition'
        ).prefetch_related('tags')
        user = self.request.user
        if not _is_supervisor(user):
            agent = _agent_for(user)
            if not agent:
                return qs.none()
            qs = qs.filter(Q(agent=agent) | Q(agent__isnull=True))

        params = self.request.query_params
        if params.get('mine') in ('1', 'true'):
            agent = _agent_for(user)
            qs = qs.filter(agent=agent) if agent else qs.none()
        if params.get('unassigned') in ('1', 'true'):
            qs = qs.filter(agent__isnull=True)
        if params.get('active') in ('1', 'true'):
            qs = qs.exclude(status='closed')
        if params.get('line'):
            qs = qs.filter(channel__whatsapp_line__id=params['line'])
        if params.get('channel_type'):
            qs = qs.filter(channel__channel_type=params['channel_type'])
        # Orden por defecto: actividad más reciente
        if not params.get('ordering'):
            from django.db.models import F
            qs = qs.order_by(F('last_message_at').desc(nulls_last=True), '-started_at')
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer

    def _check_can_act(self, conv):
        """Agente solo actúa sobre sus conversaciones o sin asignar."""
        user = self.request.user
        if _is_supervisor(user):
            return None
        agent = _agent_for(user)
        if not agent or (conv.agent_id and conv.agent_id != agent.id):
            return Response({'error': 'Esta conversación está asignada a otro agente.'},
                            status=status.HTTP_403_FORBIDDEN)
        return None

    # ── Contadores ───────────────────────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = self.get_queryset()
        agent = _agent_for(request.user)
        unread = Message.objects.filter(conversation__in=qs.exclude(status='closed'),
                                        direction='inbound', is_read=False).count()
        return Response({
            'open': qs.filter(status='open').count(),
            'waiting': qs.filter(status='waiting').count(),
            'unassigned': qs.filter(agent__isnull=True).exclude(status='closed').count(),
            'mine': qs.filter(agent=agent).exclude(status='closed').count() if agent else 0,
            'closed_today': qs.filter(status='closed', closed_at__date=timezone.localdate()).count(),
            'unread': unread,
        })

    # ── Iniciar conversación saliente ────────────────────────────────────────
    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        Body: {line_id, to, template_id, body_params: [], header_params: [], contact_id?}
        WhatsApp exige plantilla aprobada para iniciar una conversación.
        """
        data = request.data
        try:
            line = WhatsAppLine.objects.select_related('channel', 'provider').get(
                pk=data.get('line_id'), is_active=True)
        except WhatsAppLine.DoesNotExist:
            return Response({'error': 'Línea de WhatsApp no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        to = normalize_wa_number(data.get('to', ''))
        if len(to) < 8:
            return Response({'to': ['Número inválido. Usa formato internacional, ej: 573001234567']},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            tpl = WhatsAppTemplate.objects.get(pk=data.get('template_id'), line=line)
        except WhatsAppTemplate.DoesNotExist:
            return Response({'template_id': ['Plantilla no encontrada para esta línea']},
                            status=status.HTTP_400_BAD_REQUEST)
        if tpl.status and tpl.status.upper() != 'APPROVED':
            return Response({'error': f'La plantilla está en estado {tpl.status}; solo se pueden usar aprobadas.'},
                            status=status.HTTP_400_BAD_REQUEST)

        conv = Conversation.objects.filter(channel=line.channel, contact_identifier=to) \
            .exclude(status='closed').first()
        if not conv:
            from apps.contacts.models import Contact
            contact = Contact.objects.filter(pk=data.get('contact_id')).first() if data.get('contact_id') else None
            conv = Conversation.objects.create(
                channel=line.channel, contact_identifier=to, contact=contact,
                agent=_agent_for(request.user),  # quien inicia la conversación la atiende
                campaign=line.default_campaign, status='open',
            )
        denied = self._check_can_act(conv)
        if denied:
            return denied

        msg = self._send_template(conv, tpl, data)
        return Response({
            'conversation': ConversationSerializer(conv, context={'request': request}).data,
            'message': MessageSerializer(msg).data,
        }, status=status.HTTP_201_CREATED if msg.status != 'failed' else status.HTTP_400_BAD_REQUEST)

    def _send_template(self, conv, tpl, data):
        body_params = [str(p) for p in (data.get('body_params') or [])]
        header_params = [str(p) for p in (data.get('header_params') or [])]
        return create_outbound(
            conv,
            body=render_template_preview(tpl, body_params, header_params),
            sender=self.request.user,
            message_type='template',
            metadata={
                'template_name': tpl.name, 'language': tpl.language,
                'body_params': body_params, 'header_params': header_params,
            },
        )

    # ── Mensajes ─────────────────────────────────────────────────────────────
    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        conv = self.get_object()

        if request.method == 'GET':
            qs = conv.messages.select_related('sender').order_by('sent_at')
            unread = list(qs.filter(direction='inbound', is_read=False).values_list('external_id', flat=True))
            if unread:
                qs.filter(direction='inbound', is_read=False).update(is_read=True)
                self._mark_read_on_whatsapp(conv, [u for u in unread if u])
            return Response(MessageSerializer(qs, many=True).data)

        denied = self._check_can_act(conv)
        if denied:
            return denied
        body = (request.data.get('body') or '').strip()
        if not body:
            return Response({'body': ['El mensaje no puede estar vacío.']}, status=status.HTTP_400_BAD_REQUEST)
        if len(body) > 4096:
            return Response({'body': ['Máximo 4096 caracteres.']}, status=status.HTTP_400_BAD_REQUEST)

        # Si el agente escribe en una conversación sin asignar, la toma
        if not conv.agent_id and not _is_supervisor(request.user):
            conv.agent = _agent_for(request.user)
            conv.assigned_at = timezone.now()
            conv.save(update_fields=['agent', 'assigned_at'])

        try:
            msg = create_outbound(conv, body=body, sender=request.user)
        except WindowClosedError as e:
            return Response({'error': str(e), 'code': 'window_closed', 'requires_template': True},
                            status=status.HTTP_400_BAD_REQUEST)
        except WhatsAppAPIError as e:
            return _api_error(e)
        http = status.HTTP_201_CREATED if msg.status != 'failed' else status.HTTP_502_BAD_GATEWAY
        return Response(MessageSerializer(msg).data, status=http)

    def _mark_read_on_whatsapp(self, conv, external_ids):
        """Confirma lectura en WhatsApp (doble check azul) del último mensaje."""
        line = getattr(conv.channel, 'whatsapp_line', None)
        if not line or not external_ids:
            return
        try:
            client_for_line(line).mark_read(line.phone_number_id, external_ids[-1])
        except Exception as e:
            logger.debug(f"[WhatsApp] mark_read falló: {e}")

    @action(detail=True, methods=['post'], url_path='send-template')
    def send_template(self, request, pk=None):
        conv = self.get_object()
        denied = self._check_can_act(conv)
        if denied:
            return denied
        line = getattr(conv.channel, 'whatsapp_line', None)
        if not line:
            return Response({'error': 'La conversación no es de WhatsApp'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tpl = WhatsAppTemplate.objects.get(pk=request.data.get('template_id'), line=line)
        except WhatsAppTemplate.DoesNotExist:
            return Response({'template_id': ['Plantilla no encontrada']}, status=status.HTTP_400_BAD_REQUEST)
        msg = self._send_template(conv, tpl, request.data)
        http = status.HTTP_201_CREATED if msg.status != 'failed' else status.HTTP_502_BAD_GATEWAY
        return Response(MessageSerializer(msg).data, status=http)

    # ── Estado / asignación ──────────────────────────────────────────────────
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        from apps.agents.models import Agent
        if not _is_supervisor(request.user):
            return Response({'error': 'Solo supervisores pueden reasignar'}, status=status.HTTP_403_FORBIDDEN)
        conv = self.get_object()
        previous_agent_id = conv.agent_id
        agent_id = request.data.get('agent_id')
        if agent_id in (None, '', 0):
            conv.agent = None
            conv.status = 'waiting'
        else:
            agent = Agent.objects.filter(pk=agent_id).select_related('user').first()
            if not agent:
                return Response({'error': 'Agente no encontrado'}, status=status.HTTP_404_NOT_FOUND)
            conv.agent = agent
            conv.status = 'open'
            conv.assigned_at = conv.assigned_at or timezone.now()
        conv.save(update_fields=['agent', 'status', 'assigned_at'])
        push(conv, 'conversation.assigned', also_agents=[previous_agent_id],
             also_unassigned=previous_agent_id is None)
        return Response(ConversationSerializer(conv, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def take(self, request, pk=None):
        conv = self.get_object()
        agent = _agent_for(request.user)
        if not agent:
            return Response({'error': 'Tu usuario no tiene perfil de agente'}, status=status.HTTP_400_BAD_REQUEST)
        if conv.agent_id and conv.agent_id != agent.id and not _is_supervisor(request.user):
            return Response({'error': 'Ya está asignada a otro agente'}, status=status.HTTP_409_CONFLICT)
        previous_agent_id = conv.agent_id
        conv.agent = agent
        conv.status = 'open'
        conv.assigned_at = conv.assigned_at or timezone.now()
        conv.save(update_fields=['agent', 'status', 'assigned_at'])
        push(conv, 'conversation.assigned', also_agents=[previous_agent_id],
             also_unassigned=previous_agent_id is None)
        return Response(ConversationSerializer(conv, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        conv = self.get_object()
        denied = self._check_can_act(conv)
        if denied:
            return denied
        if conv.status == 'closed':
            return Response({'error': 'La conversación ya está cerrada'}, status=status.HTTP_400_BAD_REQUEST)

        # Tipificación (calificaciones de la campaña) + etiquetas + notas
        from apps.campaigns.models import CampaignDisposition
        from .models import ConversationTag
        data = request.data
        disposition_id = data.get('disposition_id')
        campaign_dispositions = CampaignDisposition.objects.filter(campaign_id=conv.campaign_id) \
            if conv.campaign_id else CampaignDisposition.objects.none()
        if disposition_id:
            disposition = campaign_dispositions.filter(pk=disposition_id).first()
            if not disposition:
                return Response({'disposition_id': ['La tipificación no pertenece a la campaña de la conversación.']},
                                status=status.HTTP_400_BAD_REQUEST)
            conv.disposition = disposition
        elif campaign_dispositions.exists() and not data.get('skip_disposition'):
            return Response({'error': 'Selecciona una tipificación para cerrar la conversación.',
                             'code': 'disposition_required'}, status=status.HTTP_400_BAD_REQUEST)

        conv.close_notes = str(data.get('notes', '') or '')[:2000]
        conv.status = 'closed'
        conv.closed_at = timezone.now()
        conv.closed_reason = 'agent'
        conv.save(update_fields=['status', 'closed_at', 'closed_reason', 'disposition', 'close_notes'])
        if 'tag_ids' in data:
            conv.tags.set(ConversationTag.objects.filter(pk__in=data.get('tag_ids') or [], is_active=True))

        # Calificación con "requiere rellamada" → programar callback (si hay contacto)
        if conv.disposition_id and conv.disposition.requires_callback and conv.contact_id:
            try:
                from apps.contacts.models import Contact
                Contact.objects.filter(pk=conv.contact_id).update(status='callback')
            except Exception:
                pass

        push(conv, 'conversation.closed')
        return Response(ConversationSerializer(conv, context={'request': request}).data)

    @action(detail=True, methods=['get'], url_path='close-options')
    def close_options(self, request, pk=None):
        """Tipificaciones de la campaña de la conversación y etiquetas activas."""
        from apps.campaigns.models import CampaignDisposition
        from .models import ConversationTag
        conv = self.get_object()
        dispositions = CampaignDisposition.objects.filter(campaign_id=conv.campaign_id) \
            .values('id', 'code', 'name', 'is_success', 'requires_callback') if conv.campaign_id else []
        return Response({
            'dispositions': list(dispositions),
            'disposition_required': bool(conv.campaign_id and len(dispositions)),
            'tags': list(ConversationTag.objects.filter(is_active=True).values('id', 'name', 'color')),
            'current_tags': list(conv.tags.values_list('id', flat=True)),
        })

    @action(detail=True, methods=['post'])
    def tags(self, request, pk=None):
        """Reemplaza las etiquetas de la conversación. Body: {tag_ids: []}"""
        from .models import ConversationTag
        conv = self.get_object()
        denied = self._check_can_act(conv)
        if denied:
            return denied
        conv.tags.set(ConversationTag.objects.filter(pk__in=request.data.get('tag_ids') or [], is_active=True))
        return Response(ConversationSerializer(conv, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='attachments')
    def attachments(self, request, pk=None):
        """
        Enviar un archivo (multipart: file, caption). Límites de WhatsApp:
        imagen 5 MB (jpg/png), audio y video 16 MB, documento 100 MB.
        """
        import uuid
        from django.conf import settings as dj_settings
        conv = self.get_object()
        denied = self._check_can_act(conv)
        if denied:
            return denied
        upload = request.FILES.get('file')
        if not upload:
            return Response({'file': ['Adjunta un archivo.']}, status=status.HTTP_400_BAD_REQUEST)

        mime = upload.content_type or mimetypes.guess_type(upload.name)[0] or 'application/octet-stream'
        if mime in ('image/jpeg', 'image/png'):
            mtype, limit = 'image', 5
        elif mime.startswith('image/'):
            mtype, limit = 'document', 100  # WhatsApp solo acepta jpg/png como imagen
        elif mime.startswith('audio/'):
            mtype, limit = 'audio', 16
        elif mime in ('video/mp4', 'video/3gpp'):
            mtype, limit = 'video', 16
        else:
            mtype, limit = 'document', 100
        if conv.channel.channel_type == 'email':
            limit = 20
        if upload.size > limit * 1024 * 1024:
            return Response({'file': [f'El archivo supera el límite de {limit} MB para este tipo.']},
                            status=status.HTTP_400_BAD_REQUEST)

        safe = ''.join(ch for ch in upload.name if ch.isalnum() or ch in '._-')[:120] or 'archivo'
        directory = os.path.join(str(dj_settings.MEDIA_ROOT), 'outbound')
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"{uuid.uuid4().hex}_{safe}")
        with open(path, 'wb') as fh:
            for chunk in upload.chunks():
                fh.write(chunk)

        if not conv.agent_id and not _is_supervisor(request.user):
            agent = _agent_for(request.user)
            if agent:
                conv.agent = agent
                conv.assigned_at = timezone.now()
                conv.save(update_fields=['agent', 'assigned_at'])
        caption = (request.data.get('caption') or '').strip()[:1024]
        try:
            msg = create_outbound(conv, body=caption, sender=request.user, message_type=mtype,
                                  metadata={'local_path': path, 'mime_type': mime,
                                            'filename': upload.name, 'size': upload.size})
        except WindowClosedError as e:
            os.remove(path)
            return Response({'error': str(e), 'code': 'window_closed', 'requires_template': True},
                            status=status.HTTP_400_BAD_REQUEST)
        http = status.HTTP_201_CREATED if msg.status != 'failed' else status.HTTP_502_BAD_GATEWAY
        return Response(MessageSerializer(msg).data, status=http)

    @action(detail=False, methods=['post'], url_path='start-email')
    def start_email(self, request):
        """Nuevo correo saliente. Body: {account_id, to, subject, body}"""
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_email
        from .models import EmailAccount
        data = request.data
        account = EmailAccount.objects.select_related('channel').filter(pk=data.get('account_id'), is_active=True).first()
        if not account:
            return Response({'error': 'Cuenta de email no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        to = (data.get('to') or '').strip().lower()
        try:
            validate_email(to)
        except ValidationError:
            return Response({'to': ['Email inválido']}, status=status.HTTP_400_BAD_REQUEST)
        subject = (data.get('subject') or '').strip()[:300]
        body = (data.get('body') or '').strip()
        if not subject or not body:
            return Response({'error': 'Asunto y mensaje son obligatorios'}, status=status.HTTP_400_BAD_REQUEST)
        from apps.contacts.models import Contact
        conv = Conversation.objects.create(
            channel=account.channel, contact_identifier=to, subject=subject,
            contact=Contact.objects.filter(email__iexact=to).first(),
            agent=_agent_for(request.user), assigned_at=timezone.now(),
            campaign=account.default_campaign, status='open',
        )
        msg = create_outbound(conv, body=body, sender=request.user, metadata={'subject': subject})
        return Response({
            'conversation': ConversationSerializer(conv, context={'request': request}).data,
            'message': MessageSerializer(msg).data,
        }, status=status.HTTP_201_CREATED if msg.status != 'failed' else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        conv = self.get_object()
        denied = self._check_can_act(conv)
        if denied:
            return denied
        conv.status = 'open' if conv.agent_id else 'waiting'
        conv.closed_at = None
        conv.closed_reason = ''
        conv.save(update_fields=['status', 'closed_at', 'closed_reason'])
        push(conv, 'conversation.reopened')
        return Response(ConversationSerializer(conv, context={'request': request}).data)


class MessageViewSet(viewsets.GenericViewSet):
    """Acciones sobre mensajes individuales (adjuntos, reintento)."""
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        qs = Message.objects.select_related('conversation__channel__whatsapp_line__provider')
        user = self.request.user
        if not _is_supervisor(user):
            agent = _agent_for(user)
            if not agent:
                return qs.none()
            qs = qs.filter(Q(conversation__agent=agent) | Q(conversation__agent__isnull=True))
        return qs

    @action(detail=True, methods=['get'])
    def media(self, request, pk=None):
        msg = self.get_object()
        meta = msg.metadata or {}
        path = meta.get('local_path')
        if not path or not os.path.exists(path):
            if meta.get('media_id'):
                return Response({'error': 'El archivo aún se está descargando, intenta en unos segundos.'},
                                status=status.HTTP_404_NOT_FOUND)
            return Response({'error': 'El mensaje no tiene adjunto'}, status=status.HTTP_404_NOT_FOUND)
        content_type = meta.get('mime_type') or mimetypes.guess_type(path)[0] or 'application/octet-stream'
        resp = FileResponse(open(path, 'rb'), content_type=content_type)
        resp['Content-Disposition'] = f'inline; filename="{meta.get("filename") or os.path.basename(path)}"'
        return resp

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        msg = self.get_object()
        if msg.direction != 'outbound' or msg.status != 'failed':
            return Response({'error': 'Solo se reintentan mensajes salientes fallidos'},
                            status=status.HTTP_400_BAD_REQUEST)
        msg.status = 'pending'
        msg.save(update_fields=['status'])
        send_outbound(msg)
        return Response(MessageSerializer(msg).data)


# ══════════════════════════════════════════════════════════════════════════════
# WhatsApp: proveedores, líneas y plantillas (solo administradores)
# ══════════════════════════════════════════════════════════════════════════════

class WhatsAppProviderViewSet(viewsets.ModelViewSet):
    queryset = WhatsAppProvider.objects.all()
    serializer_class = WhatsAppProviderSerializer
    permission_classes = [IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        provider = self.get_object()
        if provider.lines.exists():
            return Response({'error': 'Elimina primero las líneas de este proveedor.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Valida el token consultando la identidad del Usuario del Sistema."""
        provider = self.get_object()
        try:
            me = WhatsAppCloudClient.for_provider(provider).me()
        except WhatsAppAPIError as e:
            provider.last_error = e.message
            provider.save(update_fields=['last_error'])
            return _api_error(e)
        provider.last_error = ''
        provider.save(update_fields=['last_error'])
        return Response({'success': True, 'identity': me,
                         'message': f"Token válido — {me.get('name', 'usuario del sistema')}"})

    @action(detail=True, methods=['post'], url_path='regenerate-verify-token')
    def regenerate_verify_token(self, request, pk=None):
        from .models import _generate_verify_token
        provider = self.get_object()
        provider.verify_token = _generate_verify_token()
        provider.webhook_verified = False
        provider.save(update_fields=['verify_token', 'webhook_verified'])
        return Response(self.get_serializer(provider).data)

    @action(detail=True, methods=['get'], url_path='phone-numbers')
    def phone_numbers(self, request, pk=None):
        """Lista los números de una WABA para autocompletar el formulario de línea."""
        provider = self.get_object()
        waba_id = (request.query_params.get('waba_id') or '').strip()
        if not waba_id:
            return Response({'error': 'waba_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            numbers = WhatsAppCloudClient.for_provider(provider).list_phone_numbers(waba_id)
        except WhatsAppAPIError as e:
            return _api_error(e)
        return Response(numbers)

    @action(detail=False, methods=['get'], url_path='webhook-info')
    def webhook_info(self, request):
        """
        Webhook de ESTA instalación (cada servidor tiene el suyo):
          {base_url}/api/messaging/webhooks/meta/{APP_ID}/
        base_url sale de PUBLIC_BASE_URL (.env) o, si no existe, del host con el que se abrió la web.
        """
        from .serializers import build_webhook_url, webhook_base_diagnostics
        info = webhook_base_diagnostics(request)
        info['path_template'] = '/api/messaging/webhooks/meta/{APP_ID}/'
        info['url_template'] = build_webhook_url(request, '{APP_ID}')
        info['providers'] = [{
            'id': p.id, 'name': p.name, 'app_id': p.app_id,
            'webhook_url': build_webhook_url(request, p.app_id),
            'verify_token': p.verify_token, 'webhook_verified': p.webhook_verified,
            'last_webhook_at': p.last_webhook_at,
        } for p in WhatsAppProvider.objects.order_by('name')]
        return Response(info)

    @action(detail=True, methods=['post'], url_path='check-webhook')
    def check_webhook(self, request, pk=None):
        """
        Simula la verificación de Meta llamando a la URL pública del webhook con HTTPS estricto.
        La prueba sale desde este servidor: confirma DNS, certificado y proxy, aunque no
        garantiza que el firewall acepte tráfico entrante desde Internet.
        """
        import secrets
        import requests
        from .serializers import build_webhook_url
        provider = self.get_object()
        url = build_webhook_url(request, provider.app_id)
        if not url.startswith('https://'):
            return Response({'ok': False, 'stage': 'https',
                             'message': 'La URL no usa HTTPS. Meta la rechazará.', 'url': url})
        challenge = secrets.token_hex(8)
        params = {'hub.mode': 'subscribe', 'hub.verify_token': provider.verify_token, 'hub.challenge': challenge}
        try:
            resp = requests.get(url, params=params, timeout=10, verify=True, allow_redirects=False)
        except requests.exceptions.SSLError as e:
            return Response({'ok': False, 'stage': 'ssl', 'url': url,
                             'message': 'El certificado SSL no es válido (autofirmado, vencido o de otro dominio). '
                                        'Meta no entregará mensajes.', 'detail': str(e)[:300]})
        except requests.exceptions.ConnectionError as e:
            return Response({'ok': False, 'stage': 'connection', 'url': url,
                             'message': 'No se pudo conectar a la URL (DNS, puerto 443 o firewall).', 'detail': str(e)[:300]})
        except requests.exceptions.Timeout:
            return Response({'ok': False, 'stage': 'timeout', 'url': url, 'message': 'La URL no respondió en 10 s.'})
        if resp.status_code == 200 and resp.text.strip() == challenge:
            return Response({'ok': True, 'stage': 'done', 'url': url,
                             'message': 'La URL responde correctamente con HTTPS válido. Ya puedes verificarla en Meta.'})
        return Response({'ok': False, 'stage': 'response', 'url': url,
                         'message': f'La URL respondió HTTP {resp.status_code} en lugar del desafío esperado. '
                                    'Revisa que el dominio apunte a este servidor y que nginx enrute /api/.',
                         'detail': resp.text[:200]})


class WhatsAppLineViewSet(viewsets.ModelViewSet):
    queryset = WhatsAppLine.objects.select_related('provider', 'channel', 'default_campaign')
    serializer_class = WhatsAppLineSerializer
    permission_classes = [IsAdminUser]

    def get_permissions(self):
        # Agentes/supervisores necesitan listar líneas para iniciar conversaciones
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        if not _is_supervisor(self.request.user):
            qs = qs.filter(is_active=True, status='connected')
        return qs

    def destroy(self, request, *args, **kwargs):
        line = self.get_object()
        if line.channel.conversations.exists():
            line.is_active = False
            line.status = 'disabled'
            line.save(update_fields=['is_active', 'status'])
            line.channel.is_active = False
            line.channel.save(update_fields=['is_active'])
            return Response({'status': 'disabled',
                             'reason': 'La línea tiene conversaciones; se deshabilitó para conservar el historial.'})
        channel = line.channel
        line.delete()
        channel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Consulta el número en Meta y actualiza nombre verificado, calidad y estado."""
        line = self.get_object()
        try:
            info = client_for_line(line).get_phone_number(line.phone_number_id)
        except WhatsAppAPIError as e:
            line.status = 'error'
            line.status_detail = e.message
            line.save(update_fields=['status', 'status_detail'])
            return _api_error(e)
        line.display_phone_number = info.get('display_phone_number', '')
        line.verified_name = info.get('verified_name', '')
        line.quality_rating = info.get('quality_rating', '')
        line.messaging_limit = info.get('messaging_limit_tier', '') or ''
        line.status = 'connected'
        line.status_detail = ''
        line.save()
        line.channel.identifier = line.display_phone_number or line.phone_number_id
        line.channel.save(update_fields=['identifier'])
        return Response({'success': True, 'phone': info, 'line': self.get_serializer(line).data})

    @action(detail=True, methods=['post'])
    def subscribe(self, request, pk=None):
        """Suscribe la app a la WABA para que Meta envíe los webhooks de esta cuenta."""
        line = self.get_object()
        try:
            client_for_line(line).subscribe_app(line.waba_id)
        except WhatsAppAPIError as e:
            return _api_error(e)
        line.webhook_subscribed = True
        line.save(update_fields=['webhook_subscribed'])
        return Response({'success': True, 'message': 'App suscrita a los eventos de la cuenta de WhatsApp Business.'})

    @action(detail=True, methods=['post'], url_path='sync-templates')
    def sync_templates(self, request, pk=None):
        from .tasks import sync_line_templates
        line = self.get_object()
        try:
            result = sync_line_templates(line)
        except WhatsAppAPIError as e:
            return _api_error(e)
        return Response({'success': True, **result})

    @action(detail=True, methods=['post'], url_path='send-test')
    def send_test(self, request, pk=None):
        """Envía una plantilla de prueba (por defecto hello_world / en_US)."""
        line = self.get_object()
        to = normalize_wa_number(request.data.get('to', ''))
        if len(to) < 8:
            return Response({'to': ['Número inválido']}, status=status.HTTP_400_BAD_REQUEST)
        name = request.data.get('template_name') or 'hello_world'
        language = request.data.get('language') or 'en_US'
        try:
            resp = client_for_line(line).send_template(line.phone_number_id, to, name, language)
        except WhatsAppAPIError as e:
            return _api_error(e)
        return Response({'success': True, 'response': resp})


class WhatsAppTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = WhatsAppTemplateSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['line', 'status', 'category', 'language']
    search_fields = ['name']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_permissions(self):
        # Cualquier usuario autenticado puede listar plantillas (para enviarlas)
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        qs = WhatsAppTemplate.objects.select_related('line')
        if not _is_supervisor(self.request.user):
            qs = qs.filter(status__iexact='APPROVED', line__is_active=True)
        return qs

    def create(self, request, *args, **kwargs):
        """
        Crea la plantilla en Meta (queda PENDING hasta aprobación).
        Body: {line, name, language, category, header_text?, body_text, footer_text?, body_examples?[]}
        """
        data = request.data
        try:
            line = WhatsAppLine.objects.select_related('provider').get(pk=data.get('line'))
        except WhatsAppLine.DoesNotExist:
            return Response({'line': ['Línea no encontrada']}, status=status.HTTP_400_BAD_REQUEST)

        name = (data.get('name') or '').strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{1,512}', name):
            return Response({'name': ['Solo minúsculas, números y guion bajo (ej: confirmacion_cita).']},
                            status=status.HTTP_400_BAD_REQUEST)
        category = (data.get('category') or 'UTILITY').upper()
        if category not in ('MARKETING', 'UTILITY', 'AUTHENTICATION'):
            return Response({'category': ['MARKETING, UTILITY o AUTHENTICATION']}, status=status.HTTP_400_BAD_REQUEST)
        body_text = (data.get('body_text') or '').strip()
        if not body_text:
            return Response({'body_text': ['El cuerpo es obligatorio']}, status=status.HTTP_400_BAD_REQUEST)
        language = data.get('language') or 'es'

        components = []
        header_text = (data.get('header_text') or '').strip()
        if header_text:
            components.append({'type': 'HEADER', 'format': 'TEXT', 'text': header_text})
        body = {'type': 'BODY', 'text': body_text}
        n_params = len(set(re.findall(r'\{\{(\d+)\}\}', body_text)))
        if n_params:
            examples = [str(x) for x in (data.get('body_examples') or [])]
            examples += [f'ejemplo{i + 1}' for i in range(len(examples), n_params)]
            body['example'] = {'body_text': [examples[:n_params]]}
        components.append(body)
        footer = (data.get('footer_text') or '').strip()
        if footer:
            components.append({'type': 'FOOTER', 'text': footer})

        try:
            resp = client_for_line(line).create_template(line.waba_id, name, language, category, components)
        except WhatsAppAPIError as e:
            return _api_error(e)

        tpl, _ = WhatsAppTemplate.objects.update_or_create(
            line=line, name=name, language=language,
            defaults={'meta_id': resp.get('id', ''), 'category': resp.get('category', category),
                      'status': resp.get('status', 'PENDING'), 'components': components},
        )
        return Response(self.get_serializer(tpl).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        tpl = self.get_object()
        try:
            client_for_line(tpl.line).delete_template(tpl.line.waba_id, tpl.name)
        except WhatsAppAPIError as e:
            # Si ya no existe en Meta, borrar igualmente en local
            if e.status != 404 and e.code not in (100,):
                return _api_error(e)
        tpl.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ══════════════════════════════════════════════════════════════════════════════
# Webhook público de Meta
# ══════════════════════════════════════════════════════════════════════════════

class MetaWebhookView(APIView):
    """
    Callback URL a configurar en Meta for Developers → WhatsApp → Configuración:
        https://<dominio>/api/messaging/webhooks/meta/<APP_ID>/
    Suscribir el campo "messages".
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []  # Meta envía ráfagas: no aplicar rate limit anónimo

    def get(self, request, app_id):
        mode = request.query_params.get('hub.mode')
        token = request.query_params.get('hub.verify_token', '')
        challenge = request.query_params.get('hub.challenge', '')
        provider = WhatsAppProvider.objects.filter(app_id=app_id, is_active=True).first()
        if mode == 'subscribe' and provider and hmac.compare_digest(token, provider.verify_token):
            provider.webhook_verified = True
            provider.webhook_verified_at = timezone.now()
            provider.save(update_fields=['webhook_verified', 'webhook_verified_at'])
            logger.info(f"[WhatsApp] Webhook verificado para app {app_id}")
            return HttpResponse(challenge, content_type='text/plain')
        logger.warning(f"[WhatsApp] Verificación de webhook rechazada para app {app_id}")
        return HttpResponse('Forbidden', status=403)

    def post(self, request, app_id):
        provider = WhatsAppProvider.objects.filter(app_id=app_id, is_active=True).first()
        if not provider:
            return HttpResponse(status=404)

        raw = request.body
        if provider.app_secret:
            signature = request.headers.get('X-Hub-Signature-256', '')
            expected = 'sha256=' + hmac.new(provider.app_secret.encode(), raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                logger.warning(f"[WhatsApp] Firma inválida en webhook de app {app_id}")
                return HttpResponse('Invalid signature', status=403)

        try:
            payload = json.loads(raw.decode('utf-8') or '{}')
        except ValueError:
            return HttpResponse('Bad request', status=400)

        provider.last_webhook_at = timezone.now()
        provider.save(update_fields=['last_webhook_at'])

        try:
            if payload.get('object') in ('page', 'instagram'):
                from .meta_pages import process_page_webhook
                process_page_webhook(provider, payload)
            else:
                process_webhook_payload(provider, payload)
        except Exception:
            # Responder 200 igualmente: si devolvemos error Meta reintenta en bucle
            logger.exception("[WhatsApp] Error procesando webhook")
        return HttpResponse('EVENT_RECEIVED', status=200)
