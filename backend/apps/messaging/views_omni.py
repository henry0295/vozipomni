"""
API de funciones omnicanal:

  /api/messaging/tags/                          etiquetas de conversación
  /api/messaging/quick-replies/                 respuestas rápidas (?campaign=&channel_type=&for_agent=1)
  /api/messaging/whatsapp/broadcasts/           envíos masivos (+ start, pause, resume, cancel, recipients, preview)
  /api/messaging/email/accounts/                cuentas de email (+ test, poll)
  /api/messaging/webchat/widgets/               widgets de chat web (+ regenerate-key)
  /api/messaging/meta/pages/                    páginas Messenger / Instagram (+ test, subscribe, discover)
  /api/messaging/metrics/                       métricas de atención de chats

Público (widget de chat web, sin autenticación, con límite por IP):
  /api/messaging/webchat/public/<key>/config/          GET
  /api/messaging/webchat/public/<key>/session/         POST {name, email, page_url}
  /api/messaging/webchat/public/<key>/messages/        GET ?token=&after=  ·  POST {token, body}
  /api/messaging/webchat/public/<key>/media/<id>/      GET ?token=
"""
import json
import logging
import os
import uuid
from datetime import datetime, timedelta

from django.core import signing
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.db.models.functions import TruncDate
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from core.permissions import (
    IsAdminOrSupervisor, IsAdminOrSupervisorOrReadOnly, IsAdminSupervisorOrAnalyst, IsAdminUser,
)
from .models import (
    Conversation, ConversationTag, EmailAccount, Message, MetaPage, QuickReply,
    WebChatWidget, WhatsAppBroadcast, WhatsAppProvider,
)
from .serializers_omni import (
    ConversationTagSerializer, EmailAccountSerializer, MetaPageSerializer, QuickReplySerializer,
    WebChatWidgetSerializer, WhatsAppBroadcastSerializer,
)
from .whatsapp_service import WhatsAppAPIError

logger = logging.getLogger(__name__)


def _seconds(td):
    return round(td.total_seconds()) if td else None


# ══════════════════════════════════════════════════════════════════════════════
# Etiquetas y respuestas rápidas
# ══════════════════════════════════════════════════════════════════════════════

class ConversationTagViewSet(viewsets.ModelViewSet):
    queryset = ConversationTag.objects.all()
    serializer_class = ConversationTagSerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    pagination_class = None


class QuickReplyViewSet(viewsets.ModelViewSet):
    serializer_class = QuickReplySerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'shortcut', 'body']
    pagination_class = None

    def get_queryset(self):
        qs = QuickReply.objects.select_related('campaign')
        p = self.request.query_params
        campaign = p.get('campaign')
        if p.get('for_agent') in ('1', 'true'):
            # Para el chat: globales + las de la campaña de la conversación, solo activas
            qs = qs.filter(is_active=True).filter(Q(campaign__isnull=True) | Q(campaign_id=campaign or 0))
            ctype = p.get('channel_type')
            if ctype:
                qs = qs.filter(Q(channel_type='') | Q(channel_type=ctype))
            return qs
        if campaign == 'global':
            qs = qs.filter(campaign__isnull=True)
        elif campaign:
            qs = qs.filter(campaign_id=campaign)
        if p.get('channel_type'):
            qs = qs.filter(channel_type=p['channel_type'])
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ══════════════════════════════════════════════════════════════════════════════
# Envíos masivos
# ══════════════════════════════════════════════════════════════════════════════

class WhatsAppBroadcastViewSet(viewsets.ModelViewSet):
    serializer_class = WhatsAppBroadcastSerializer
    permission_classes = [IsAdminOrSupervisor]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'line']
    search_fields = ['name']

    def get_queryset(self):
        return WhatsAppBroadcast.objects.select_related('line', 'template', 'contact_list', 'created_by')

    def perform_create(self, serializer):
        b = serializer.save(created_by=self.request.user, status='draft')
        if b.scheduled_at and b.scheduled_at > timezone.now():
            b.status = 'scheduled'
            b.save(update_fields=['status'])

    def perform_update(self, serializer):
        b = serializer.save()
        if b.status in ('draft', 'scheduled'):
            b.status = 'scheduled' if b.scheduled_at and b.scheduled_at > timezone.now() else 'draft'
            b.save(update_fields=['status'])

    def destroy(self, request, *args, **kwargs):
        b = self.get_object()
        if b.status == 'running':
            return Response({'error': 'Pausa o cancela el envío antes de eliminarlo.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    def preview(self, request):
        """Cuántos contactos de la lista recibirían el envío. Body: {contact_list, require_opt_in}."""
        from apps.contacts.models import Contact
        list_id = request.data.get('contact_list')
        require = request.data.get('require_opt_in', True) not in (False, 'false', '0', 0)
        qs = Contact.objects.filter(contact_list_id=list_id)
        total = qs.count()
        usable = qs.filter(dnc_opt_out=False).exclude(status='blacklisted')
        opted = usable.filter(whatsapp_opt_in=True).count()
        return Response({
            'total': total,
            'eligible': opted if require else usable.count(),
            'opted_in': opted,
            'dnc': total - usable.count(),
        })

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        from .broadcasts import start_broadcast
        from .tasks import process_broadcast_batch
        b = self.get_object()
        try:
            info = start_broadcast(b)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if info['total'] == 0:
            b.status = 'completed'
            b.finished_at = timezone.now()
            b.save(update_fields=['status', 'finished_at'])
            return Response({'error': 'Ningún contacto cumple las condiciones (opt-in, DNC, teléfono válido).',
                             **info}, status=status.HTTP_400_BAD_REQUEST)
        process_broadcast_batch.delay(b.id)
        return Response(self.get_serializer(b).data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        b = self.get_object()
        if b.status != 'running':
            return Response({'error': 'Solo se pausan envíos en curso.'}, status=status.HTTP_400_BAD_REQUEST)
        b.status = 'paused'
        b.save(update_fields=['status'])
        return Response(self.get_serializer(b).data)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        from .tasks import process_broadcast_batch
        b = self.get_object()
        if b.status != 'paused':
            return Response({'error': 'Solo se reanudan envíos pausados.'}, status=status.HTTP_400_BAD_REQUEST)
        b.status = 'running'
        b.last_error = ''
        b.save(update_fields=['status', 'last_error'])
        process_broadcast_batch.delay(b.id)
        return Response(self.get_serializer(b).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        b = self.get_object()
        if b.status in ('completed', 'cancelled'):
            return Response({'error': 'El envío ya terminó.'}, status=status.HTTP_400_BAD_REQUEST)
        b.status = 'cancelled'
        b.finished_at = timezone.now()
        b.save(update_fields=['status', 'finished_at'])
        return Response(self.get_serializer(b).data)

    @action(detail=True, methods=['get'])
    def recipients(self, request, pk=None):
        b = self.get_object()
        qs = b.recipients.select_related('contact').order_by('id')
        st = request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        page = self.paginate_queryset(qs)
        rows = [{
            'id': r.id, 'phone': r.phone, 'status': r.status, 'error': r.error,
            'sent_at': r.sent_at, 'contact_name': r.contact.full_name if r.contact else '',
            'conversation_id': r.message.conversation_id if r.message_id else None,
        } for r in (page if page is not None else qs[:500])]
        if page is not None:
            return self.get_paginated_response(rows)
        return Response(rows)


# ══════════════════════════════════════════════════════════════════════════════
# Canales: email, chat web, Messenger / Instagram
# ══════════════════════════════════════════════════════════════════════════════

class _ChannelConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]

    def get_permissions(self):
        # Supervisores pueden ver la configuración (para la bandeja), no modificarla
        if self.action in ('list', 'retrieve'):
            return [IsAdminOrSupervisor()]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        channel = obj.channel
        if channel.conversations.exists():
            obj.is_active = False
            obj.save(update_fields=['is_active'])
            channel.is_active = False
            channel.save(update_fields=['is_active'])
            return Response({'status': 'disabled',
                             'reason': 'El canal tiene conversaciones; se deshabilitó para conservar el historial.'})
        obj.delete()
        channel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailAccountViewSet(_ChannelConfigViewSet):
    serializer_class = EmailAccountSerializer
    queryset = EmailAccount.objects.select_related('channel', 'default_campaign', 'time_condition')

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        from .email_channel import test_account
        result = test_account(self.get_object())
        ok = result['imap'] and result['smtp']
        return Response(result, status=status.HTTP_200_OK if ok else status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def poll(self, request, pk=None):
        from .email_channel import poll_account
        account = self.get_object()
        try:
            n = poll_account(account)
        except Exception as e:
            account.last_error = str(e)[:500]
            account.save(update_fields=['last_error'])
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'new_messages': n})


class WebChatWidgetViewSet(_ChannelConfigViewSet):
    serializer_class = WebChatWidgetSerializer
    queryset = WebChatWidget.objects.select_related('channel', 'default_campaign', 'time_condition')

    @action(detail=True, methods=['post'], url_path='regenerate-key')
    def regenerate_key(self, request, pk=None):
        from .models import _generate_widget_key
        w = self.get_object()
        w.widget_key = _generate_widget_key()
        w.save(update_fields=['widget_key'])
        return Response(self.get_serializer(w).data)


class MetaPageViewSet(_ChannelConfigViewSet):
    serializer_class = MetaPageSerializer
    queryset = MetaPage.objects.select_related('channel', 'provider', 'default_campaign', 'time_condition')

    @action(detail=False, methods=['get'])
    def discover(self, request):
        """Páginas accesibles con el token del proveedor. ?provider=<id>"""
        from .meta_pages import list_pages
        provider = WhatsAppProvider.objects.filter(pk=request.query_params.get('provider')).first()
        if not provider:
            return Response({'error': 'Proveedor no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        try:
            pages = list_pages(provider)
        except WhatsAppAPIError as e:
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)
        configured = set(MetaPage.objects.values_list('platform', 'page_id'))
        for p in pages:
            p['configured_messenger'] = ('messenger', p['page_id']) in configured
            p['configured_instagram'] = ('instagram', p['page_id']) in configured
        return Response(pages)

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        from .meta_pages import test_page
        page = self.get_object()
        try:
            info = test_page(page)
        except WhatsAppAPIError as e:
            page.last_error = e.message
            page.save(update_fields=['last_error'])
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)
        page.last_error = ''
        page.save(update_fields=['last_error'])
        return Response({'success': True, 'info': info})

    @action(detail=True, methods=['post'])
    def subscribe(self, request, pk=None):
        from .meta_pages import subscribe_page
        page = self.get_object()
        try:
            subscribe_page(page)
        except WhatsAppAPIError as e:
            page.last_error = e.message
            page.save(update_fields=['last_error'])
            return Response(e.to_dict(), status=status.HTTP_400_BAD_REQUEST)
        return Response({'success': True, 'message': 'Página suscrita a los eventos de mensajes.'})


# ══════════════════════════════════════════════════════════════════════════════
# Métricas de chat
# ══════════════════════════════════════════════════════════════════════════════

def _date_range(params):
    now = timezone.localtime()
    try:
        start = timezone.make_aware(datetime.strptime(params.get('date_from', ''), '%Y-%m-%d'))
    except ValueError:
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        end = timezone.make_aware(datetime.strptime(params.get('date_to', ''), '%Y-%m-%d')) \
            .replace(hour=23, minute=59, second=59)
    except ValueError:
        end = now
    return start, end


def conversation_metrics_qs(params):
    start, end = _date_range(params)
    qs = Conversation.objects.filter(started_at__gte=start, started_at__lte=end).exclude(closed_reason='broadcast',
                                                                                        last_inbound_at__isnull=True)
    if params.get('channel_type'):
        qs = qs.filter(channel__channel_type=params['channel_type'])
    if params.get('channel'):
        qs = qs.filter(channel_id=params['channel'])
    if params.get('campaign'):
        qs = qs.filter(campaign_id=params['campaign'])
    if params.get('agent'):
        qs = qs.filter(agent_id=params['agent'])
    return qs, start, end


FRT = ExpressionWrapper(F('first_response_at') - F('started_at'), output_field=DurationField())
AHT = ExpressionWrapper(F('closed_at') - F('started_at'), output_field=DurationField())
ASA = ExpressionWrapper(F('assigned_at') - F('started_at'), output_field=DurationField())


class ChatMetricsView(APIView):
    """
    GET /api/messaging/metrics/?date_from=YYYY-MM-DD&date_to=&channel_type=&channel=&campaign=&agent=&sla_minutes=5
    """
    permission_classes = [IsAuthenticated, IsAdminSupervisorOrAnalyst]

    def get(self, request):
        p = request.query_params
        qs, start, end = conversation_metrics_qs(p)
        try:
            sla_minutes = max(1, int(p.get('sla_minutes', 5)))
        except ValueError:
            sla_minutes = 5

        agg = qs.aggregate(
            total=Count('id'),
            closed=Count('id', filter=Q(status='closed')),
            unassigned=Count('id', filter=Q(agent__isnull=True) & ~Q(status='closed')),
            responded=Count('id', filter=Q(first_response_at__isnull=False)),
            avg_frt=Avg(FRT, filter=Q(first_response_at__isnull=False)),
            avg_aht=Avg(AHT, filter=Q(status='closed', closed_at__isnull=False)),
            avg_asa=Avg(ASA, filter=Q(assigned_at__isnull=False)),
        )
        within_sla = qs.filter(first_response_at__isnull=False).annotate(frt=FRT) \
            .filter(frt__lte=timedelta(minutes=sla_minutes)).count()
        msgs = Message.objects.filter(conversation__in=qs)
        msg_agg = msgs.aggregate(
            inbound=Count('id', filter=Q(direction='inbound')),
            outbound=Count('id', filter=Q(direction='outbound')),
        )

        # Por agente
        sent_by_user = dict(
            msgs.filter(direction='outbound', sender__isnull=False)
            .values_list('sender').annotate(n=Count('id'))
        )
        by_agent = []
        for row in qs.exclude(agent__isnull=True).values(
                'agent', 'agent__agent_id', 'agent__user_id', 'agent__user__first_name',
                'agent__user__last_name', 'agent__user__username').annotate(
                conversations=Count('id'),
                closed=Count('id', filter=Q(status='closed')),
                avg_frt=Avg(FRT, filter=Q(first_response_at__isnull=False)),
                avg_aht=Avg(AHT, filter=Q(status='closed', closed_at__isnull=False)),
        ).order_by('-conversations'):
            name = f"{row['agent__user__first_name'] or ''} {row['agent__user__last_name'] or ''}".strip()
            by_agent.append({
                'agent_id': row['agent'],
                'name': name or row['agent__user__username'] or row['agent__agent_id'],
                'conversations': row['conversations'],
                'closed': row['closed'],
                'avg_first_response': _seconds(row['avg_frt']),
                'avg_handle_time': _seconds(row['avg_aht']),
                'messages_sent': sent_by_user.get(row['agent__user_id'], 0),
            })

        by_channel = [
            {'channel_type': r['channel__channel_type'], 'conversations': r['n']}
            for r in qs.values('channel__channel_type').annotate(n=Count('id')).order_by('-n')
        ]
        by_disposition = [
            {'disposition': r['disposition__name'], 'is_success': r['disposition__is_success'], 'count': r['n']}
            for r in qs.exclude(disposition__isnull=True)
            .values('disposition__name', 'disposition__is_success').annotate(n=Count('id')).order_by('-n')
        ]
        by_tag = [
            {'tag': r['tags__name'], 'color': r['tags__color'], 'count': r['n']}
            for r in qs.exclude(tags__isnull=True).values('tags__name', 'tags__color')
            .annotate(n=Count('id')).order_by('-n')
        ]
        daily = [
            {'date': r['d'].isoformat(), 'conversations': r['n'], 'closed': r['c'],
             'avg_first_response': _seconds(r['frt'])}
            for r in qs.annotate(d=TruncDate('started_at')).values('d').annotate(
                n=Count('id'), c=Count('id', filter=Q(status='closed')),
                frt=Avg(FRT, filter=Q(first_response_at__isnull=False)),
            ).order_by('d')
        ]

        responded = agg['responded'] or 0
        return Response({
            'period': {'start': start.isoformat(), 'end': end.isoformat()},
            'total_conversations': agg['total'],
            'closed_conversations': agg['closed'],
            'open_conversations': agg['total'] - agg['closed'],
            'unassigned': agg['unassigned'],
            'avg_first_response': _seconds(agg['avg_frt']),
            'avg_handle_time': _seconds(agg['avg_aht']),
            'avg_time_to_assign': _seconds(agg['avg_asa']),
            'sla_minutes': sla_minutes,
            'sla_pct': round(within_sla / responded * 100, 1) if responded else None,
            'messages_inbound': msg_agg['inbound'],
            'messages_outbound': msg_agg['outbound'],
            'by_agent': by_agent,
            'by_channel': by_channel,
            'by_disposition': by_disposition,
            'by_tag': by_tag,
            'daily': daily,
        })


# ══════════════════════════════════════════════════════════════════════════════
# Chat web — API pública del widget
# ══════════════════════════════════════════════════════════════════════════════

TOKEN_SALT = 'messaging.webchat'
TOKEN_MAX_AGE = 60 * 60 * 24 * 30  # 30 días


class WebChatThrottle(AnonRateThrottle):
    scope = 'webchat'


class _PublicWebChatView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [WebChatThrottle]

    widget = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.widget = WebChatWidget.objects.select_related('channel').filter(
            widget_key=kwargs.get('key'), is_active=True).first()

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        origin = request.headers.get('Origin')
        if origin and self.widget and self.widget.origin_allowed(origin):
            response['Access-Control-Allow-Origin'] = origin
            response['Vary'] = 'Origin'
        return response

    def _guard(self, request):
        if not self.widget:
            return Response({'error': 'Widget no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        origin = request.headers.get('Origin')
        if origin and not self.widget.origin_allowed(origin):
            return Response({'error': 'Origen no autorizado'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def _body(self, request):
        # El widget envía text/plain (petición "simple", sin preflight CORS)
        try:
            return json.loads((request.body or b'{}').decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            return {}

    def _visitor(self, token):
        try:
            data = signing.loads(token or '', salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
        except signing.BadSignature:
            return None
        if data.get('w') != self.widget.id:
            return None
        return data


def _public_message(m: Message):
    meta = m.metadata or {}
    return {
        'id': m.id,
        'direction': m.direction,
        'type': m.message_type,
        'body': m.body,
        'sent_at': m.sent_at.isoformat(),
        'agent': (m.sender.first_name or m.sender.username) if (m.sender_id and m.direction == 'outbound') else None,
        'has_media': bool(meta.get('local_path')),
        'filename': meta.get('filename'),
    }


class WebChatConfigView(_PublicWebChatView):
    def get(self, request, key):
        denied = self._guard(request)
        if denied:
            return denied
        from .routing import is_open_now
        w = self.widget
        online = is_open_now(w)
        return Response({
            'title': w.title, 'subtitle': w.subtitle, 'color': w.primary_color, 'position': w.position,
            'require_name': w.require_name, 'require_email': w.require_email, 'intro_text': w.intro_text,
            'online': online, 'offline_text': w.after_hours_message if not online else '',
        })


class WebChatSessionView(_PublicWebChatView):
    def post(self, request, key):
        denied = self._guard(request)
        if denied:
            return denied
        data = self._body(request)
        name = str(data.get('name', '')).strip()[:100]
        email_addr = str(data.get('email', '')).strip()[:200]
        if self.widget.require_name and not name:
            return Response({'name': ['Escribe tu nombre.']}, status=status.HTTP_400_BAD_REQUEST)
        if email_addr:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(email_addr)
            except ValidationError:
                return Response({'email': ['Email inválido.']}, status=status.HTTP_400_BAD_REQUEST)
        elif self.widget.require_email:
            return Response({'email': ['Escribe tu email.']}, status=status.HTTP_400_BAD_REQUEST)
        visitor = f"wc_{uuid.uuid4().hex[:16]}"
        token = signing.dumps({'w': self.widget.id, 'v': visitor, 'n': name, 'e': email_addr,
                               'u': str(data.get('page_url', ''))[:300]}, salt=TOKEN_SALT)
        return Response({'token': token, 'visitor_id': visitor, 'name': name})


class WebChatMessagesView(_PublicWebChatView):
    def get(self, request, key):
        denied = self._guard(request)
        if denied:
            return denied
        visitor = self._visitor(request.query_params.get('token'))
        if not visitor:
            return Response({'error': 'Sesión inválida'}, status=status.HTTP_401_UNAUTHORIZED)
        conv = Conversation.objects.filter(channel=self.widget.channel, contact_identifier=visitor['v']) \
            .order_by('-started_at').first()
        if not conv:
            return Response({'messages': [], 'status': None})
        try:
            after = int(request.query_params.get('after', 0) or 0)
        except ValueError:
            after = 0
        msgs = list(conv.messages.select_related('sender').filter(id__gt=after).order_by('id')[:200])
        # Lo que el visitante ya vio queda como "entregado"
        delivered = [m.id for m in msgs if m.direction == 'outbound' and m.status == 'sent']
        if delivered:
            Message.objects.filter(id__in=delivered).update(status='delivered')
        return Response({
            'messages': [_public_message(m) for m in msgs],
            'status': conv.status,
            'agent': (conv.agent.user.first_name if conv.agent_id and conv.agent.user_id else None),
        })

    def post(self, request, key):
        denied = self._guard(request)
        if denied:
            return denied
        data = self._body(request)
        visitor = self._visitor(data.get('token'))
        if not visitor:
            return Response({'error': 'Sesión inválida'}, status=status.HTTP_401_UNAUTHORIZED)
        body = str(data.get('body', '')).strip()
        if not body:
            return Response({'body': ['Mensaje vacío.']}, status=status.HTTP_400_BAD_REQUEST)
        if len(body) > 2000:
            return Response({'body': ['Máximo 2000 caracteres.']}, status=status.HTTP_400_BAD_REQUEST)

        from apps.contacts.models import Contact
        from .routing import ingest_inbound
        contact = Contact.objects.filter(email__iexact=visitor['e']).first() if visitor.get('e') else None
        result = ingest_inbound(
            self.widget.channel, visitor['v'], message_type='text', body=body,
            name=visitor.get('n', ''), contact=contact, config=self.widget,
            conv_metadata={'visitor_email': visitor.get('e', ''), 'page_url': visitor.get('u', ''),
                           'user_agent': request.headers.get('User-Agent', '')[:200],
                           'ip': request.META.get('REMOTE_ADDR', '')},
        )
        conv, message, _ = result
        return Response({'message': _public_message(message), 'status': conv.status},
                        status=status.HTTP_201_CREATED)


class WebChatMediaView(_PublicWebChatView):
    def get(self, request, key, message_id):
        denied = self._guard(request)
        if denied:
            return denied
        visitor = self._visitor(request.query_params.get('token'))
        if not visitor:
            return JsonResponse({'error': 'Sesión inválida'}, status=401)
        m = Message.objects.filter(id=message_id, conversation__channel=self.widget.channel,
                                   conversation__contact_identifier=visitor['v']).first()
        path = (m.metadata or {}).get('local_path') if m else None
        if not path or not os.path.exists(path):
            return JsonResponse({'error': 'Archivo no encontrado'}, status=404)
        resp = FileResponse(open(path, 'rb'), content_type=(m.metadata or {}).get('mime_type')
                            or 'application/octet-stream')
        resp['Content-Disposition'] = f'inline; filename="{(m.metadata or {}).get("filename") or "archivo"}"'
        return resp
