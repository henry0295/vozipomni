from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.throttling import UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import bleach
import logging

from apps.agents.models import Agent

from apps.api import serializers
from apps.api.viewsets.calls import hangup_by_call_id
from core.permissions import IsAdminOrSupervisor, IsAdminOrSupervisorOrReadOnly

logger = logging.getLogger(__name__)


class AgentActionThrottle(UserRateThrottle):
    """Limitar acciones de agente a 10 req/min"""
    rate = '10/min'
    scope = 'agent_action'


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.select_related('user').prefetch_related('campaigns')
    serializer_class = serializers.AgentSerializer
    # Escritura solo admin; supervisor puede leer y ejecutar acciones de agente
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['agent_id', 'sip_extension', 'user__username', 'user__first_name', 'user__last_name', 'user__email']
    filterset_fields = ['status', 'webrtc_enabled', 'user']
    ordering_fields = ['created_at', 'agent_id', 'status', 'calls_today']
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Permitir a los agentes ejecutar sus propias acciones
        Admin/Supervisor pueden hacer todo
        """
        # Acciones que los agentes autenticados pueden ejecutar
        agent_allowed_actions = [
            'login', 'logout', 'change_status', 
            'start_break', 'end_break', 'save_disposition'
        ]
        
        if self.action in agent_allowed_actions:
            return [IsAuthenticated()]

        # Asistentes del formulario de alta: solo quien puede crear agentes
        if self.action in ('next_available', 'check_availability'):
            return [IsAdminOrSupervisor()]
        
        return super().get_permissions()

    def get_queryset(self):
        """El rol agente solo ve su propio registro (otro agente → 404)."""
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'role', None) == 'agent' and not getattr(user, 'is_superuser', False):
            qs = qs.filter(user=user)
        return qs

    def _deny_if_not_owner(self, agent):
        """403 si el usuario no es admin/supervisor/superusuario ni dueño del agente."""
        user = self.request.user
        if getattr(user, 'is_superuser', False):
            return None
        if getattr(user, 'role', None) in ('admin', 'supervisor'):
            return None
        if agent.user_id == user.id:
            return None
        return Response(
            {'detail': 'No tiene permisos sobre este agente'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    def get_throttles(self):
        """Aplicar rate limiting solo a acciones de agente"""
        if self.action in ['save_disposition', 'change_status', 'start_break', 'end_break']:
            return [AgentActionThrottle()]
        return super().get_throttles()
    
    def perform_destroy(self, instance):
        """Al eliminar un agente, desactivar su endpoint PJSIP"""
        try:
            from apps.telephony.asterisk_config import AsteriskConfigGenerator
            generator = AsteriskConfigGenerator()
            generator.delete_pjsip_endpoint(instance.sip_extension)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error eliminando endpoint PJSIP al borrar agente: {e}")
        
        # Desactivar usuario también
        if instance.user:
            instance.user.is_active = False
            instance.user.is_active_agent = False
            instance.user.save()
        
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def login(self, request, pk=None):
        """Marcar agente como conectado y unirlo a las colas ACD de Asterisk"""
        import logging
        _log = logging.getLogger(__name__)
        # Fuera del try: un agente ajeno debe dar 404 (queryset filtrado), no 500
        agent = self.get_object()

        # Un agente solo puede iniciar su propia sesión.
        # Admin/supervisor pueden iniciar sesión de cualquier agente.
        denied = self._deny_if_not_owner(agent)
        if denied:
            return denied
        try:
            # ── Operación crítica: escribir directamente sobre el modelo ──
            # No depende de AgentService, Prometheus, AMI ni event bus.
            agent.status = 'available'
            agent.logged_in_at = timezone.now()
            agent.save(update_fields=['status', 'logged_in_at'])

            # ── Integración no-bloqueante: métricas, colas, eventos ──
            try:
                from apps.agents.services import AgentService
                AgentService.login_agent(agent.id, request.user)
            except Exception as svc_err:
                _log.warning(
                    'AgentService.login_agent failed (non-critical, agent is logged in): %s',
                    svc_err
                )

            return Response({
                'status': 'logged in',
                'agent_id': agent.agent_id,
                'sip_extension': agent.sip_extension,
            })
        except Exception as e:
            _log.exception('Unexpected error in agent login pk=%s', pk)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def logout(self, request, pk=None):
        """Marcar agente como desconectado y retirarlo de las colas ACD de Asterisk"""
        import logging
        _log = logging.getLogger(__name__)
        agent = self.get_object()

        denied = self._deny_if_not_owner(agent)
        if denied:
            return denied
        try:
            # Operación crítica directa sobre el modelo
            agent.status = 'offline'
            agent.logged_in_at = None
            agent.current_calls = 0
            agent.save(update_fields=['status', 'logged_in_at', 'current_calls'])

            # Integración no-bloqueante
            try:
                from apps.agents.services import AgentService
                AgentService.logout_agent(agent.id, request.user)
            except Exception as svc_err:
                _log.warning(
                    'AgentService.logout_agent failed (non-critical, agent is logged out): %s',
                    svc_err
                )

            return Response({'status': 'logged out'})
        except Exception as e:
            _log.exception('Unexpected error in agent logout pk=%s', pk)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Cambiar estado del agente"""
        import logging
        _log = logging.getLogger(__name__)
        agent = self.get_object()
        denied = self._deny_if_not_owner(agent)
        if denied:
            return denied
        try:
            new_status = request.data.get('status')

            # Validar que sea una cadena (evita TypeError si llega un objeto JSON)
            if not isinstance(new_status, str):
                return Response(
                    {'error': 'El campo status debe ser una cadena de texto.',
                     'valid_statuses': [s[0] for s in Agent.STATUS_CHOICES]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if new_status in dict(Agent.STATUS_CHOICES):
                agent.status = new_status
                agent.save()
                return Response({
                    'status': 'updated',
                    'new_status': new_status
                })

            return Response(
                {'error': 'Invalid status', 'valid_statuses': [s[0] for s in Agent.STATUS_CHOICES]},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            _log.exception('Unexpected error in change_status pk=%s', pk)
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Obtener estadísticas del agente"""
        agent = self.get_object()
        return Response({
            'agent_id': agent.agent_id,
            'status': agent.status,
            'is_available': agent.is_available,
            'calls_today': agent.calls_today,
            'talk_time_today': agent.talk_time_today,
            'available_time_today': agent.available_time_today,
            'break_time_today': agent.break_time_today,
            'oncall_time_today': agent.oncall_time_today,
            'wrapup_time_today': agent.wrapup_time_today,
            'session_duration': agent.session_duration,
            'occupancy': agent.occupancy,
            'logged_in_at': agent.logged_in_at
        })
    
    @action(detail=True, methods=['post'])
    def start_break(self, request, pk=None):
        """Iniciar descanso del agente"""
        agent = self.get_object()
        denied = self._deny_if_not_owner(agent)
        if denied:
            return denied
        reason = request.data.get('reason', 'personal')
        
        agent.status = 'break'
        agent.save()
        
        return Response({
            'status': 'break started',
            'reason': reason
        })
    
    @action(detail=True, methods=['post'])
    def end_break(self, request, pk=None):
        """Finalizar descanso del agente"""
        agent = self.get_object()
        denied = self._deny_if_not_owner(agent)
        if denied:
            return denied
        
        agent.status = 'available'
        agent.save()
        
        return Response({
            'status': 'break ended',
            'new_status': 'available'
        })
    
    @action(detail=False, methods=['GET'])
    def next_available(self, request):
        """Obtener siguiente ID de agente y extensión SIP disponibles"""
        import re
        
        # Obtener último agent_id
        last_agent = Agent.objects.order_by('-agent_id').first()
        if last_agent and last_agent.agent_id:
            # Extraer el número del ID (ej: AGT001 -> 001)
            match = re.search(r'(\d+)$', last_agent.agent_id)
            if match:
                number = int(match.group(1))
                next_number = number + 1
                # Mantener el mismo formato con ceros a la izquierda
                prefix = last_agent.agent_id[:match.start()]
                next_agent_id = f"{prefix}{next_number:03d}"
            else:
                next_agent_id = "AGT001"
        else:
            next_agent_id = "AGT001"
        
        # Verificar que no exista (por si fue eliminado uno intermedio)
        while Agent.objects.filter(agent_id=next_agent_id).exists():
            match = re.search(r'(\d+)$', next_agent_id)
            if match:
                number = int(match.group(1))
                prefix = next_agent_id[:match.start()]
                next_agent_id = f"{prefix}{number + 1:03d}"
            else:
                break
        
        # Obtener última extensión
        last_extension = Agent.objects.order_by('-sip_extension').first()
        if last_extension and last_extension.sip_extension:
            try:
                next_extension = str(int(last_extension.sip_extension) + 1)
            except (ValueError, TypeError):
                next_extension = "100"
        else:
            next_extension = "100"
        
        # Verificar que la extensión no exista (buscar huecos)
        while Agent.objects.filter(sip_extension=next_extension).exists():
            next_extension = str(int(next_extension) + 1)
        
        return Response({
            'agent_id': next_agent_id,
            'sip_extension': next_extension
        })
    
    @action(detail=False, methods=['POST'])
    def check_availability(self, request):
        """Verificar disponibilidad de agent_id o sip_extension"""
        agent_id = request.data.get('agent_id')
        sip_extension = request.data.get('sip_extension')
        
        result = {}
        
        if agent_id:
            result['agent_id_available'] = not Agent.objects.filter(agent_id=agent_id).exists()
        
        if sip_extension:
            result['sip_extension_available'] = not Agent.objects.filter(sip_extension=sip_extension).exists()
        
        return Response(result)
    
    @action(detail=False, methods=['post'], url_path='hangup')
    def hangup_call_by_id(self, request):
        """Colgar una llamada activa via AMI Hangup usando call_id
        
        **VALIDACIÓN DE PERMISOS:**
        - El agente solo puede colgar sus propias llamadas
        - Admin y Supervisor pueden colgar cualquier llamada
        """
        return hangup_by_call_id(request)

    @action(detail=True, methods=['post'])
    def save_disposition(self, request, pk=None):
        """Guardar disposición de llamada (para agentes logueados)"""
        agent = self.get_object()
        denied = self._deny_if_not_owner(agent)
        if denied:
            return denied
        
        # Extraer datos
        call_id = request.data.get('call_id')
        disposition_code = request.data.get('disposition_code')
        notes = request.data.get('notes', '')
        callback_date = request.data.get('callback_date')
        form_data = request.data.get('form_data', {})
        campaign_id = request.data.get('campaign_id')
        contact_id = request.data.get('contact_id')
        
        # Sanitizar inputs (protección XSS)
        notes = bleach.clean(notes, tags=[], strip=True)
        form_data = {k: bleach.clean(str(v), tags=[], strip=True) for k, v in form_data.items()}
        
        # Validar disposición
        from apps.campaigns.models import CampaignDisposition, Campaign
        from apps.telephony.models import Call
        from apps.contacts.models import Contact

        # Fecha de rellamada (ISO 8601); se valida antes de modificar nada
        callback_datetime = None
        if callback_date:
            try:
                callback_datetime = parse_datetime(callback_date) if isinstance(callback_date, str) else None
            except ValueError:
                callback_datetime = None
            if callback_datetime is None:
                return Response(
                    {'callback_date': ['Fecha inválida (ISO 8601)']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if timezone.is_naive(callback_datetime):
                callback_datetime = timezone.make_aware(callback_datetime)

        # Contacto: si no existe se ignora (el callback queda sin contacto)
        if contact_id:
            try:
                contact_exists = Contact.objects.filter(pk=contact_id).exists()
            except (ValueError, TypeError):
                contact_exists = False
            if not contact_exists:
                logger.debug('save_disposition: contact_id %r no existe, se ignora', contact_id)
                contact_id = None
        
        disposition = None
        if campaign_id and disposition_code:
            try:
                # Validar que el agente pertenece a la campaña
                campaign = Campaign.objects.get(id=campaign_id)
                if not campaign.agents.filter(id=agent.id).exists():
                    return Response(
                        {'error': 'Agent is not assigned to this campaign'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                disposition = CampaignDisposition.objects.get(
                    campaign_id=campaign_id,
                    code=disposition_code
                )
            except Campaign.DoesNotExist:
                return Response(
                    {'error': f'Campaign {campaign_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except CampaignDisposition.DoesNotExist:
                return Response(
                    {'error': f'Disposition {disposition_code} not found for campaign {campaign_id}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Actualizar Call si existe
        call = None
        if call_id:
            try:
                call = Call.objects.get(call_id=call_id)
                
                # Validar que la llamada pertenece al agente
                if call.agent_id != agent.id:
                    return Response(
                        {'error': 'Call does not belong to this agent'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                call.disposition = disposition
                call.notes = notes
                if call.metadata is None:
                    call.metadata = {}
                call.metadata['form_data'] = form_data
                call.save()
            except Call.DoesNotExist:
                pass
        
        # Crear callback si es necesario
        if disposition and disposition.requires_callback and callback_datetime:
            from apps.telephony.models import CallbackRequest

            contact = Contact.objects.filter(pk=contact_id).first() if contact_id else None
            if call and call.contact:
                contact_name = call.contact.full_name
            else:
                contact_name = contact.full_name if contact else ''
            
            CallbackRequest.objects.create(
                phone=(call.called_number if call else '') or (contact.phone if contact else ''),
                contact_name=contact_name,
                notes=notes,
                scheduled_at=callback_datetime,
                campaign_id=campaign_id,
                agent=agent,
                call=call,
                contact_id=contact_id or None,
                created_by=request.user
            )
        
        # Actualizar contacto con form_data
        if contact_id and form_data:
            try:
                contact = Contact.objects.get(id=contact_id)
                if contact.custom_fields is None:
                    contact.custom_fields = {}
                contact.custom_fields.update(form_data)
                contact.save()
            except Contact.DoesNotExist:
                pass
        
        return Response({
            'status': 'disposition saved',
            'disposition': disposition.name if disposition else None,
            'callback_created': disposition.requires_callback if disposition else False
        })
