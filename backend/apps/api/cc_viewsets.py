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
from rest_framework.permissions import IsAuthenticated, BasePermission, SAFE_METHODS
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.db.models import Q
import logging
import time

from core.permissions import (
    IsAdminOrSupervisor, IsAdminOrSupervisorOrReadOnly, IsAdminSupervisorOrAnalyst,
)
from core.validators import (
    validate_ami_channel, validate_dial_extension, validate_dial_number, sanitize_caller_id,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Serializers inline
# ──────────────────────────────────────────────────────────────────────────────

from rest_framework import serializers as drf_serializers

from apps.contacts.models import Contact


class CallbackSerializer(drf_serializers.ModelSerializer):
    agent_name = drf_serializers.SerializerMethodField()
    campaign_name = drf_serializers.CharField(source='campaign.name', read_only=True)
    # contact: id del contacto en lectura; contact_id: para asignarlo al crear/editar
    contact = drf_serializers.PrimaryKeyRelatedField(read_only=True)
    contact_id = drf_serializers.PrimaryKeyRelatedField(
        source='contact', write_only=True, required=False, allow_null=True,
        queryset=Contact.objects.all(),
    )

    class Meta:
        from apps.telephony.models import CallbackRequest
        model = CallbackRequest
        fields = [
            'id', 'phone', 'contact_name', 'notes', 'status', 'priority',
            'scheduled_at', 'attempts', 'max_attempts',
            'call', 'campaign', 'campaign_name', 'agent', 'agent_name',
            'contact', 'contact_id',
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

class _DenyAnalystWrites(BasePermission):
    """El analista solo lee: cualquier método de escritura recibe 403."""
    message = 'El rol analista solo tiene acceso de lectura.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if getattr(request.user, 'is_superuser', False):
            return True
        return getattr(request.user, 'role', None) != 'analyst'


def _is_agent_role(user) -> bool:
    return not getattr(user, 'is_superuser', False) and getattr(user, 'role', None) == 'agent'


class CallbackViewSet(viewsets.ModelViewSet):
    """
    CRUD + acciones para devoluciones de llamada.

    admin/supervisor: todo. analyst: solo lectura. agent: solo los asignados a
    él o creados por él, sin poder reasignarlos ni borrarlos.
    """
    serializer_class = CallbackSerializer
    permission_classes = [IsAuthenticated, _DenyAnalystWrites]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'campaign', 'agent']
    search_fields = ['phone', 'contact_name', 'notes']
    ordering_fields = ['scheduled_at', 'priority', 'created_at']

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminOrSupervisor()]
        return super().get_permissions()

    def get_queryset(self):
        from apps.telephony.models import CallbackRequest
        qs = CallbackRequest.objects.select_related(
            'agent__user', 'campaign', 'call', 'created_by'
        )
        user = self.request.user
        if getattr(user, 'is_superuser', False):
            return qs
        role = getattr(user, 'role', None)
        if role in ('admin', 'supervisor', 'analyst'):
            return qs
        if role == 'agent':
            return qs.filter(Q(agent__user=user) | Q(created_by=user))
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        if _is_agent_role(user):
            agent = getattr(user, 'agent_profile', None)
            if agent is None:
                raise drf_serializers.ValidationError(
                    {'agent': ['Su usuario no tiene perfil de agente']}
                )
            serializer.save(agent=agent, created_by=user)
            return
        serializer.save()

    def perform_update(self, serializer):
        if _is_agent_role(self.request.user):
            # El agente no puede reasignar el callback: se ignora el 'agent' del cuerpo
            serializer.save(agent=serializer.instance.agent)
            return
        serializer.save()

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
        """Conteo de callbacks pendientes (de los que el usuario puede ver)."""
        visible = self.get_queryset()
        count = visible.filter(
            status__in=['pending', 'scheduled']
        ).count()
        overdue = visible.filter(
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

def _check_call_control(request, channel):
    """
    Decide si el usuario puede actuar sobre `channel` (transferir, conferenciar).
    admin/supervisor: siempre. agent: solo canales de su llamada en curso, según
    CoreShowChannels. Otros roles: 403. Devuelve una Response de error o None.
    """
    user = request.user
    role = getattr(user, 'role', None)
    if getattr(user, 'is_superuser', False) or role in ('admin', 'supervisor'):
        return None
    if role != 'agent':
        return Response({'detail': 'No tiene permisos para controlar llamadas'},
                        status=status.HTTP_403_FORBIDDEN)
    agent = getattr(user, 'agent_profile', None)
    if agent is None:
        return Response({'detail': 'Su usuario no tiene perfil de agente'},
                        status=status.HTTP_403_FORBIDDEN)

    from apps.telephony.asterisk_ami import AsteriskAMI
    from apps.telephony.channel_guard import agent_owns_channel

    ami = AsteriskAMI()
    if not ami.connect():
        return Response({'detail': 'Asterisk no disponible'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    try:
        channels = ami.core_show_channels(timeout=5)
    except Exception as e:
        logger.error(f"CoreShowChannels falló: {e}")
        return Response({'detail': 'Asterisk no disponible'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    finally:
        ami.disconnect()

    if not agent_owns_channel(agent, channel, channels):
        logger.warning(
            f"Agente {agent.sip_extension} intentó actuar sobre el canal {channel}, que no es de su llamada"
        )
        return Response({'detail': 'El canal no pertenece a su llamada'},
                        status=status.HTTP_403_FORBIDDEN)
    return None


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
        blind=True  → transferencia ciega (Redirect inmediato, recomendado para producción).
        blind=False → transferencia consultiva (2 pasos: hold + originate al agente receptor).
                      Requiere que el frontend gestione la señalización del segundo leg.
        """
        channel = str(request.data.get('channel') or '').strip()
        extension = str(request.data.get('extension') or '').strip()
        blind = request.data.get('blind', True)

        if not channel or not extension:
            return Response({'error': 'channel y extension requeridos'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Formato y ausencia de CR/LF (ValidationError → 400)
        channel = validate_ami_channel(channel, 'channel')
        extension = validate_dial_extension(extension, 'extension')

        denied = _check_call_control(request, channel)
        if denied is not None:
            return denied

        from apps.telephony.services import CallService

        if blind:
            # Transferencia ciega: redirigir el canal directamente
            result = CallService.transfer_call(channel, extension)
            result['transfer_type'] = 'blind'
            return Response(result)

        # Transferencia consultiva (attended transfer):
        # Paso 1 — poner al cliente en hold mientras el agente habla con el receptor
        # Paso 2 — originar llamada al agente receptor desde el canal del agente actual
        # El frontend debe completar el bridge cuando el receptor esté listo.
        try:
            from apps.telephony.asterisk_ami import AsteriskAMI
            ami = AsteriskAMI()
            if not ami.connect():
                return Response({'error': 'No se pudo conectar a Asterisk AMI'},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)

            # Originar llamada al agente receptor; cuando conteste,
            # el agente actual podrá completar el bridge con AMI Bridge action.
            caller_id = sanitize_caller_id(request.data.get('caller_id'), default='Transferencia')
            response_raw = ami.originate(
                channel=f"PJSIP/{extension}",
                context='from-internal',
                exten=extension,
                caller_id=caller_id,
                variable={'TRANSFER_SOURCE_CHANNEL': channel},
            )
            ami.disconnect()
            logger.info(
                f"Consultive transfer: originating to {extension} from {channel}"
            )
            return Response({
                'status': 'consultive_leg_initiated',
                'transfer_type': 'consultive',
                'channel': channel,
                'extension': extension,
                'message': (
                    'Llamada originada al agente receptor. '
                    'Llame a POST /api/cc/consultive-transfer/ con blind=true '
                    'para completar la transferencia cuando esté listo.'
                ),
            })
        except Exception as e:
            logger.error(f"Consultive transfer error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        channel = str(request.data.get('channel') or '').strip()
        third_party = str(request.data.get('third_party') or '').strip()
        caller_id = sanitize_caller_id(request.data.get('caller_id'), default='ConferenceBridge')
        # Lo genera siempre el servidor: el conference_id del cliente se ignora
        conf_bridge_id = f"conf-{int(time.time() * 1000)}"

        if not channel or not third_party:
            return Response({'error': 'channel y third_party requeridos'},
                            status=status.HTTP_400_BAD_REQUEST)

        channel = validate_ami_channel(channel, 'channel')
        # third_party puede ser un número externo o una extensión interna
        try:
            third_party = validate_dial_number(third_party, 'third_party')
        except drf_serializers.ValidationError:
            third_party = validate_dial_extension(third_party, 'third_party')

        denied = _check_call_control(request, channel)
        if denied is not None:
            return denied

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
    # Parsers explícitos para aceptar multipart/form-data (subida de archivos)
    from rest_framework.parsers import MultiPartParser, FormParser
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
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
    permission_classes = [IsAdminSupervisorOrAnalyst]

    PASS_THRESHOLD = 80  # puntaje (0-100) a partir del cual una evaluación "aprueba"

    def get(self, request):
        from datetime import timedelta
        from apps.recordings.models import RecordingEvaluation
        from django.db.models import Avg, Count, Min, Max
        from django.db.models.functions import TruncDate

        qs = RecordingEvaluation.objects.all()

        # Filtros: ?days=N  ó  ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        days = request.query_params.get('days')
        agent_id = request.query_params.get('agent_id')
        template_id = request.query_params.get('template')

        if days and not date_from:
            try:
                qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=int(days)))
            except ValueError:
                pass
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if agent_id:
            qs = qs.filter(recording__agent_id=agent_id)
        if template_id:
            qs = qs.filter(template_id=template_id)

        # total_score está normalizado a 0-100 (migración recordings 0003)
        totals = qs.aggregate(
            count=Count('id'),
            avg_total=Avg('total_score'),
            min_score=Min('total_score'),
            max_score=Max('total_score'),
            avg_greeting=Avg('greeting'),
            avg_clarity=Avg('clarity'),
            avg_professionalism=Avg('professionalism'),
            avg_resolution=Avg('resolution'),
            avg_closing=Avg('closing'),
        )
        count = totals['count'] or 0
        passed = qs.filter(total_score__gte=self.PASS_THRESHOLD).count()

        daily = [
            {'date': d['date'], 'avg_score': round(d['avg_score'] or 0, 1), 'count': d['count']}
            for d in qs.annotate(date=TruncDate('created_at'))
                       .values('date')
                       .annotate(avg_score=Avg('total_score'), count=Count('id'))
                       .order_by('date')
        ]

        top_agents = []
        for row in (qs.exclude(recording__agent__isnull=True)
                      .values('recording__agent_id',
                              'recording__agent__user__first_name',
                              'recording__agent__user__last_name',
                              'recording__agent__user__username')
                      .annotate(avg_score=Avg('total_score'), count=Count('id'))
                      .order_by('-avg_score')[:10]):
            name = f"{row['recording__agent__user__first_name'] or ''} {row['recording__agent__user__last_name'] or ''}".strip()
            top_agents.append({
                'agent_id': row['recording__agent_id'],
                'name': name or row['recording__agent__user__username'],
                'avg_score': round(row['avg_score'] or 0, 1),
                'count': row['count'],
            })

        # Desglose por criterio (criterios legacy, escala 0-5 → 0-100)
        labels = {
            'greeting': 'Saludo', 'clarity': 'Claridad', 'professionalism': 'Profesionalismo',
            'resolution': 'Resolución', 'closing': 'Cierre',
        }
        category_breakdown = [
            {'category': key, 'label': label, 'avg_score': round((totals[f'avg_{key}'] or 0) * 20, 1)}
            for key, label in labels.items()
        ] if count else []

        return Response({
            'total_evaluations': count,
            'average_score': round(totals['avg_total'] or 0, 1) if count else None,
            'min_score': totals['min_score'],
            'max_score': totals['max_score'],
            'agents_evaluated': qs.exclude(recording__agent__isnull=True)
                                  .values('recording__agent_id').distinct().count(),
            'pass_rate': round(passed / count * 100, 1) if count else None,
            'pass_threshold': self.PASS_THRESHOLD,
            'top_agents': top_agents,
            'daily_trend': daily,
            'category_breakdown': category_breakdown,
            # Compatibilidad con clientes anteriores
            'totals': totals,
            'daily_trending': daily,
        })
