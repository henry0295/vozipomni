"""
ViewSets para features avanzados de Contact Center:
- CallbackViewSet      → gestión de devoluciones de llamada
- WebhookViewSet       → configuración de webhooks
- ScreenPopView        → datos del contacto al recibir llamada
- ConsultiveTransferView → agentes disponibles para transferencia
- ConferenceView       → conferencia a 3 vías vía AMI
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Q
import logging

from core.permissions import IsAdminOrSupervisor, IsAdminOrSupervisorOrReadOnly

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Serializers inline
# ──────────────────────────────────────────────────────────────────────────────

from rest_framework import serializers as drf_serializers


class CallbackSerializer(drf_serializers.ModelSerializer):
    agent_name = drf_serializers.SerializerMethodField()
    campaign_name = drf_serializers.CharField(source='campaign.name', read_only=True)

    class Meta:
        from apps.telephony.models import CallbackRequest
        model = CallbackRequest
        fields = [
            'id', 'phone', 'contact_name', 'notes', 'status', 'priority',
            'scheduled_at', 'attempts', 'max_attempts',
            'call', 'campaign', 'campaign_name', 'agent', 'agent_name',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'attempts', 'created_by']

    def get_agent_name(self, obj):
        if obj.agent and obj.agent.user:
            return obj.agent.user.get_full_name() or obj.agent.user.username
        return None

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class WebhookEndpointSerializer(drf_serializers.ModelSerializer):
    delivery_count = drf_serializers.IntegerField(source='total_deliveries', read_only=True)
    success_rate = drf_serializers.SerializerMethodField()

    class Meta:
        from apps.telephony.models import WebhookEndpoint
        model = WebhookEndpoint
        fields = [
            'id', 'name', 'url', 'secret', 'events', 'headers',
            'is_active', 'retry_on_failure', 'timeout_seconds',
            'last_triggered_at', 'last_status_code',
            'delivery_count', 'failed_deliveries', 'success_rate',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_triggered_at', 'last_status_code']
        extra_kwargs = {'secret': {'write_only': True}}

    def get_success_rate(self, obj):
        if obj.total_deliveries == 0:
            return 100.0
        return round((1 - obj.failed_deliveries / obj.total_deliveries) * 100, 1)

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class WebhookDeliverySerializer(drf_serializers.ModelSerializer):
    class Meta:
        from apps.telephony.models import WebhookDelivery
        model = WebhookDelivery
        fields = ['id', 'event_type', 'status_code', 'success', 'duration_ms',
                  'attempt', 'error_message', 'created_at']
        read_only_fields = fields


# ──────────────────────────────────────────────────────────────────────────────
# Callbacks ViewSet
# ──────────────────────────────────────────────────────────────────────────────

class CallbackViewSet(viewsets.ModelViewSet):
    """CRUD + acciones para devoluciones de llamada."""
    serializer_class = CallbackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'campaign', 'agent']
    search_fields = ['phone', 'contact_name', 'notes']
    ordering_fields = ['scheduled_at', 'priority', 'created_at']

    def get_queryset(self):
        from apps.telephony.models import CallbackRequest
        return CallbackRequest.objects.select_related(
            'agent__user', 'campaign', 'call', 'created_by'
        ).all()

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancelar un callback pendiente."""
        cb = self.get_object()
        if cb.status not in ('pending', 'scheduled'):
            return Response({'error': 'Solo se pueden cancelar callbacks pendientes/programados'},
                            status=status.HTTP_400_BAD_REQUEST)
        cb.status = 'cancelled'
        cb.save(update_fields=['status', 'updated_at'])
        return Response({'status': 'cancelled'})

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """Re-programar un callback."""
        cb = self.get_object()
        new_time = request.data.get('scheduled_at')
        if not new_time:
            return Response({'error': 'scheduled_at requerido'}, status=status.HTTP_400_BAD_REQUEST)
        cb.scheduled_at = new_time
        cb.status = 'scheduled'
        cb.save(update_fields=['scheduled_at', 'status', 'updated_at'])
        return Response({'status': 'rescheduled', 'scheduled_at': cb.scheduled_at})

    @action(detail=False, methods=['get'])
    def pending_count(self, request):
        """Conteo de callbacks pendientes para el dashboard."""
        from apps.telephony.models import CallbackRequest
        count = CallbackRequest.objects.filter(
            status__in=['pending', 'scheduled']
        ).count()
        overdue = CallbackRequest.objects.filter(
            status__in=['pending', 'scheduled'],
            scheduled_at__lt=timezone.now(),
        ).count()
        return Response({'pending': count, 'overdue': overdue})


# ──────────────────────────────────────────────────────────────────────────────
# Webhooks ViewSet
# ──────────────────────────────────────────────────────────────────────────────

class WebhookViewSet(viewsets.ModelViewSet):
    """CRUD + test de webhooks."""
    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsAdminOrSupervisor]

    def get_queryset(self):
        from apps.telephony.models import WebhookEndpoint
        return WebhookEndpoint.objects.prefetch_related('deliveries').all()

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Enviar un evento de prueba al webhook."""
        ep = self.get_object()
        from apps.telephony.webhook_service import WebhookService
        from apps.telephony.tasks import deliver_webhook
        payload = {
            'event': 'test',
            'message': 'Prueba de webhook desde VoZIPOMNI',
            'timestamp': timezone.now().isoformat(),
        }
        deliver_webhook.delay(ep.id, 'test', payload)
        return Response({'status': 'test dispatched'})

    @action(detail=True, methods=['get'])
    def deliveries(self, request, pk=None):
        """Últimas 50 entregas de este webhook."""
        ep = self.get_object()
        qs = ep.deliveries.order_by('-created_at')[:50]
        return Response(WebhookDeliverySerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def available_events(self, request):
        """Lista de eventos disponibles para suscripción."""
        from apps.telephony.models import WEBHOOK_EVENTS
        return Response([{'value': v, 'label': l} for v, l in WEBHOOK_EVENTS])


# ──────────────────────────────────────────────────────────────────────────────
# Screen Pop
# ──────────────────────────────────────────────────────────────────────────────

class ScreenPopView(APIView):
    """
    GET /api/cc/screen-pop/?phone=573001234567
    Devuelve datos del contacto para mostrar cuando llega una llamada.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        phone = request.query_params.get('phone', '').strip()
        if not phone:
            return Response({'error': 'phone requerido'}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar en contactos
        from apps.contacts.models import Contact
        from apps.telephony.models import Call

        # Normalizar: quitar +, espacios
        phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')

        contact = Contact.objects.filter(
            Q(phone__endswith=phone_clean[-10:]) |
            Q(phone2__endswith=phone_clean[-10:]) |
            Q(phone3__endswith=phone_clean[-10:])
        ).first()

        # Historial de llamadas del número
        last_calls = Call.objects.filter(
            Q(caller_id__endswith=phone_clean[-10:]) |
            Q(called_number__endswith=phone_clean[-10:])
        ).select_related('agent', 'campaign', 'disposition').order_by('-start_time')[:5]

        contact_data = None
        if contact:
            contact_data = {
                'id': contact.id,
                'full_name': contact.full_name,
                'phone': contact.phone,
                'phone2': contact.phone2,
                'phone3': contact.phone3,
                'email': contact.email,
                'company': contact.company,
                'city': contact.city,
                'country': contact.country,
                'is_vip': contact.is_vip,
                'dnc_opt_out': contact.dnc_opt_out,
                'status': contact.status,
                'attempts': contact.attempts,
                'custom_fields': contact.custom_fields,
                'notes': list(contact.notes.order_by('-created_at').values(
                    'note', 'created_at', 'is_important'
                )[:3]),
            }

        call_history = [{
            'call_id': c.call_id,
            'direction': c.direction,
            'start_time': c.start_time,
            'duration': c.duration,
            'disposition': c.disposition.name if c.disposition else None,
            'agent': c.agent.user.get_full_name() if c.agent and c.agent.user else None,
            'campaign': c.campaign.name if c.campaign else None,
        } for c in last_calls]

        return Response({
            'phone': phone,
            'contact': contact_data,
            'call_history': call_history,
            'is_known': contact is not None,
        })


# ──────────────────────────────────────────────────────────────────────────────
# Transfer Consultivo
# ──────────────────────────────────────────────────────────────────────────────

class ConsultiveTransferView(APIView):
    """
    GET  /api/cc/available-agents/       → lista agentes disponibles para transferencia
    POST /api/cc/consultive-transfer/    → ejecuta transferencia consultiva vía AMI
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.agents.models import Agent
        agents = Agent.objects.filter(
            status='available',
            webrtc_enabled=True,
        ).select_related('user').order_by('user__first_name')

        data = [{
            'id': a.id,
            'name': a.user.get_full_name() or a.user.username,
            'sip_extension': a.sip_extension,
            'status': a.status,
            'calls_today': a.calls_today,
        } for a in agents]
        return Response({'available_agents': data, 'count': len(data)})

    def post(self, request):
        """
        Body: { channel: "PJSIP/1001-...", extension: "1002", blind: false }
        """
        channel = request.data.get('channel', '').strip()
        extension = request.data.get('extension', '').strip()
        blind = request.data.get('blind', True)

        if not channel or not extension:
            return Response({'error': 'channel y extension requeridos'},
                            status=status.HTTP_400_BAD_REQUEST)

        from apps.telephony.services import CallService
        if blind:
            result = CallService.transfer_call(channel, extension)
        else:
            # Transfer consultiva: originar al agente receptor primero
            result = CallService.transfer_call(channel, extension)

        return Response(result)


# ──────────────────────────────────────────────────────────────────────────────
# Conferencia a 3 vías
# ──────────────────────────────────────────────────────────────────────────────

class ConferenceView(APIView):
    """
    POST /api/cc/conference/
    Body: { channel: "PJSIP/1001-...", third_party: "3001234567", caller_id: "CC" }
    Agrega un tercer participante a la llamada actual vía AMI Originate → ConfBridge.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        channel = request.data.get('channel', '').strip()
        third_party = request.data.get('third_party', '').strip()
        caller_id = request.data.get('caller_id', 'ConferenceBridge')
        conf_bridge_id = request.data.get('conference_id', f"conf-{int(timezone.now().timestamp())}")

        if not channel or not third_party:
            return Response({'error': 'channel y third_party requeridos'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.telephony.asterisk_ami import AsteriskAMI

            ami = AsteriskAMI()
            if not ami.connect():
                return Response({'error': 'No se pudo conectar a Asterisk AMI'},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)

            # 1) Mover el canal actual al ConfBridge
            ami._send_command(
                f"Action: Redirect\r\n"
                f"Channel: {channel}\r\n"
                f"Context: confbridge\r\n"
                f"Exten: {conf_bridge_id}\r\n"
                f"Priority: 1\r\n"
                f"\r\n"
            )
            ami._read_command_response(timeout=5)

            # 2) Originar llamada al tercero y meterlo al mismo ConfBridge
            ami._send_command(
                f"Action: Originate\r\n"
                f"Channel: Local/{third_party}@from-internal\r\n"
                f"Context: confbridge\r\n"
                f"Exten: {conf_bridge_id}\r\n"
                f"Priority: 1\r\n"
                f"CallerID: {caller_id}\r\n"
                f"Timeout: 30000\r\n"
                f"Async: true\r\n"
                f"\r\n"
            )
            ami._read_command_response(timeout=5)
            ami.disconnect()

            return Response({
                'status': 'conference_initiated',
                'conference_id': conf_bridge_id,
                'third_party': third_party,
            })
        except Exception as e:
            logger.error(f"Conference error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ──────────────────────────────────────────────────────────────────────────────
# DNC Check
# ──────────────────────────────────────────────────────────────────────────────

class DNCCheckView(APIView):
    """
    POST /api/cc/dnc-check/
    Body: { phone: "..." }
    Verifica si un número está en la lista negra o tiene opt-out.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone = request.data.get('phone', '').strip()
        if not phone:
            return Response({'error': 'phone requerido'}, status=status.HTTP_400_BAD_REQUEST)

        phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')

        from apps.contacts.models import Blacklist, Contact
        from django.db.models import Q

        in_blacklist = Blacklist.objects.filter(
            phone__endswith=phone_clean[-10:],
            is_active=True,
        ).exists()

        dnc_contact = Contact.objects.filter(
            Q(phone__endswith=phone_clean[-10:]),
            dnc_opt_out=True,
        ).exists()

        blocked = in_blacklist or dnc_contact
        return Response({
            'phone': phone,
            'blocked': blocked,
            'in_blacklist': in_blacklist,
            'dnc_opt_out': dnc_contact,
        })


# ──────────────────────────────────────────────────────────────────────────────
# Bulk Import de Contactos
# ──────────────────────────────────────────────────────────────────────────────

class BulkContactImportView(APIView):
    """
    POST /api/cc/bulk-import/
    Form-data: { contact_list_id: int, file: CSV/Excel, skip_duplicates: bool }
    Importa contactos masivamente con validación y deduplicación.
    """
    permission_classes = [IsAdminOrSupervisor]
    parser_classes = None  # acepta multipart

    def post(self, request):
        from rest_framework.parsers import MultiPartParser
        contact_list_id = request.data.get('contact_list_id')
        uploaded_file = request.FILES.get('file')
        skip_duplicates = request.data.get('skip_duplicates', 'true').lower() == 'true'

        if not contact_list_id or not uploaded_file:
            return Response({'error': 'contact_list_id y file son requeridos'},
                            status=status.HTTP_400_BAD_REQUEST)

        filename = uploaded_file.name.lower()
        try:
            from apps.contacts.services import ContactService

            if filename.endswith('.csv'):
                result = ContactService.import_contacts_from_csv(
                    contact_list_id=int(contact_list_id),
                    csv_file=uploaded_file,
                    user=request.user,
                    skip_duplicates=skip_duplicates,
                )
            elif filename.endswith(('.xlsx', '.xls')):
                result = ContactService.import_contacts_from_excel(
                    contact_list_id=int(contact_list_id),
                    excel_file=uploaded_file,
                    user=request.user,
                    skip_duplicates=skip_duplicates,
                )
            else:
                return Response({'error': 'Formato no soportado. Use CSV o XLSX.'},
                                status=status.HTTP_400_BAD_REQUEST)

            return Response(result)

        except Exception as e:
            logger.error(f"Bulk import error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────────────────────────────────────
# Quality Management
# ──────────────────────────────────────────────────────────────────────────────

class QualityStatsView(APIView):
    """
    GET /api/cc/quality-stats/?date_from=&date_to=&agent_id=
    Estadísticas de calidad: scores promedio, trending, calibración.
    """
    permission_classes = [IsAdminOrSupervisor]

    def get(self, request):
        from apps.recordings.models import RecordingEvaluation
        from django.db.models import Avg, Count, Min, Max
        from django.db.models.functions import TruncDate

        qs = RecordingEvaluation.objects.all()

        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        agent_id = request.query_params.get('agent_id')

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if agent_id:
            qs = qs.filter(recording__agent_id=agent_id)

        # Estadísticas globales
        totals = qs.aggregate(
            count=Count('id'),
            avg_total=Avg('total_score'),
            avg_greeting=Avg('greeting'),
            avg_clarity=Avg('clarity'),
            avg_professionalism=Avg('professionalism'),
            avg_resolution=Avg('resolution'),
            avg_closing=Avg('closing'),
            min_score=Min('total_score'),
            max_score=Max('total_score'),
        )

        # Trending diario
        daily = list(
            qs.annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(avg_score=Avg('total_score'), evaluations=Count('id'))
            .order_by('date')
        )

        # Top 5 agentes por score
        top_agents = list(
            qs.values('recording__agent__user__first_name',
                      'recording__agent__user__last_name',
                      'recording__agent_id')
            .annotate(avg_score=Avg('total_score'), count=Count('id'))
            .order_by('-avg_score')[:5]
        )

        return Response({
            'totals': totals,
            'daily_trending': daily,
            'top_agents': top_agents,
        })
