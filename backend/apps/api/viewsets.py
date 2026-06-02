from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from django.utils import timezone
import bleach

from apps.users.models import User
from apps.campaigns.models import Campaign
from apps.agents.models import Agent
from apps.contacts.models import Contact, ContactList
from apps.queues.models import Queue
from apps.telephony.models import Call
from apps.recordings.models import Recording
from apps.reports.models import Report

from apps.api import serializers
from core.permissions import (
    IsAdminUser,
    IsAdminOrSupervisor,
    IsAdminOrSupervisorOrReadOnly,
    IsAdminSupervisorOrAnalyst,
    IsOwnerAgentOrAdminSupervisor,
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    # Solo admin puede gestionar usuarios
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_active', 'is_active_agent']


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.select_related(
        'queue', 'contact_list', 'created_by'
    ).prefetch_related(
        'dispositions', 'agents', 'calls'
    )
    serializer_class = serializers.CampaignSerializer
    # Admin y supervisor gestionan campañas; analyst y agent solo leen
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['campaign_type', 'status', 'dialer_type']
    
    @extend_schema(
        summary="Iniciar campaña",
        description="""
        Activa una campaña y comienza el proceso de discado automático.
        
        La campaña debe estar en estado 'draft' o 'paused' para poder iniciarla.
        Se validará que tenga contactos y configuración válida antes de iniciar.
        """,
        request=None,
        responses={
            200: OpenApiResponse(
                response={'type': 'object'},
                description='Campaña iniciada exitosamente',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={'success': True, 'campaign_id': 123, 'campaign_name': 'Test Campaign', 'status': 'active'},
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Error al iniciar campaña',
                examples=[
                    OpenApiExample(
                        'Already Active',
                        value={'error': 'Campaign is already active'},
                    ),
                    OpenApiExample(
                        'No Contacts',
                        value={'error': 'Campaign has no contacts'},
                    )
                ]
            ),
        },
        tags=['campaigns']
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Iniciar campaña usando capa de servicio"""
        from apps.campaigns.services import CampaignService
        from core.exceptions import (
            CampaignAlreadyActiveError,
            NoContactsError,
            CampaignNotFoundError
        )
        
        try:
            result = CampaignService.start_campaign(pk, request.user)
            return Response(result)
        except CampaignAlreadyActiveError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except NoContactsError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except CampaignNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pausar campaña usando capa de servicio"""
        from apps.campaigns.services import CampaignService
        from core.exceptions import InvalidCampaignStateError, CampaignNotFoundError
        
        try:
            result = CampaignService.pause_campaign(pk, request.user)
            return Response(result)
        except InvalidCampaignStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except CampaignNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Obtener estadísticas detalladas de campaña"""
        from apps.campaigns.services import CampaignService
        from core.exceptions import CampaignNotFoundError
        
        try:
            stats = CampaignService.get_campaign_statistics(pk)
            return Response(stats)
        except CampaignNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def next_contact(self, request, pk=None):
        """Obtener siguiente contacto para marcación (dialer)"""
        campaign = self.get_object()
        agent_id = request.query_params.get('agent_id')
        
        if not agent_id:
            return Response(
                {'error': 'agent_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from apps.contacts.models import Contact
            from django.db.models import Q
            
            # Buscar contactos pendientes de la campaña
            contact = Contact.objects.filter(
                contact_list=campaign.contact_list,
                status__in=['pending', 'callback']
            ).exclude(
                # Excluir contactos llamados en las últimas 24h
                calls__start_time__gte=timezone.now() - timezone.timedelta(hours=24)
            ).order_by('priority', 'id').first()
            
            if not contact:
                return Response(
                    {'contact': None, 'message': 'No pending contacts'},
                    status=status.HTTP_200_OK
                )
            
            return Response({
                'contact': {
                    'id': contact.id,
                    'name': contact.full_name,
                    'phone': contact.phone,
                    'email': contact.email,
                    'company': contact.company,
                    'notes': contact.notes,
                    'custom_fields': contact.custom_fields,
                    'priority': contact.priority,
                    'call_history': [
                        {
                            'id': c.id,
                            'date': c.start_time.strftime('%Y-%m-%d %H:%M'),
                            'disposition': c.disposition.name if c.disposition else 'N/A',
                            'notes': c.notes
                        } for c in contact.calls.order_by('-start_time')[:5]
                    ]
                }
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        
        return super().get_permissions()
    
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
        try:
            agent = self.get_object()

            # Un agente solo puede iniciar su propia sesión.
            # Admin/supervisor pueden iniciar sesión de cualquier agente.
            user_role = getattr(request.user, 'role', None)
            if user_role not in ['admin', 'supervisor'] and agent.user_id != request.user.id:
                return Response(
                    {'error': 'No tiene permisos para iniciar sesión de este agente'},
                    status=status.HTTP_403_FORBIDDEN
                )

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
        try:
            agent = self.get_object()

            user_role = getattr(request.user, 'role', None)
            if user_role not in ['admin', 'supervisor'] and agent.user_id != request.user.id:
                return Response(
                    {'error': 'No tiene permisos para cerrar sesión de este agente'},
                    status=status.HTTP_403_FORBIDDEN
                )

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
        agent = self.get_object()
        new_status = request.data.get('status')
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
    
    @action(detail=True, methods=['post'])
    def save_disposition(self, request, pk=None):
        """Guardar disposición de llamada (para agentes logueados)"""
        agent = self.get_object()
        
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
        if disposition and disposition.requires_callback and callback_date:
            from apps.telephony.models import CallbackRequest
            from datetime import datetime
            
            callback_datetime = datetime.fromisoformat(callback_date.replace('Z', '+00:00'))
            
            CallbackRequest.objects.create(
                phone=call.called_number if call else '',
                contact_name=call.contact.full_name if call and call.contact else '',
                notes=notes,
                scheduled_at=callback_datetime,
                campaign_id=campaign_id,
                agent=agent,
                call=call,
                contact_id=contact_id,
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


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.select_related('contact_list').prefetch_related('notes')
    serializer_class = serializers.ContactSerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'phone', 'email', 'company']
    filterset_fields = ['contact_list', 'status']


class ContactListViewSet(viewsets.ModelViewSet):
    queryset = ContactList.objects.all()
    serializer_class = serializers.ContactListSerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'description']


class QueueViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de colas.
    La sincronización con Asterisk se maneja automáticamente via signals.py
    (Queue post_save/post_delete → regenera queues_dynamic.conf + recarga app_queue.so)
    """
    queryset = Queue.objects.all()
    serializer_class = serializers.QueueSerializer
    # Colas: admin las crea/borra; supervisor las lee y recarga
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'extension']
    filterset_fields = ['is_active', 'strategy']
    
    @action(detail=True, methods=['post'])
    def reload_config(self, request, pk=None):
        """Forzar recarga manual de la configuración de colas en Asterisk"""
        queue = self.get_object()
        try:
            from apps.telephony.asterisk_config import AsteriskConfigGenerator
            from apps.telephony.asterisk_ami import AsteriskAMI
            
            generator = AsteriskConfigGenerator()
            generator.write_all_configs()
            
            ami = AsteriskAMI()
            if ami.connect():
                ami.reload_module('app_queue.so')
                ami.reload_dialplan()
                ami.disconnect()
            
            return Response({
                'success': True,
                'message': f'Configuración de cola {queue.name} recargada en Asterisk'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Obtener estadísticas de la cola"""
        queue = self.get_object()
        try:
            stats = getattr(queue, 'stats', None)
            if stats:
                return Response({
                    'queue': queue.name,
                    'calls_waiting': stats.calls_waiting,
                    'calls_completed': stats.calls_completed,
                    'calls_abandoned': stats.calls_abandoned,
                    'avg_wait_time': stats.avg_wait_time,
                    'avg_talk_time': stats.avg_talk_time,
                    'agents_available': stats.agents_available,
                    'agents_busy': stats.agents_busy,
                    'service_level_percentage': stats.service_level_percentage,
                })
            return Response({
                'queue': queue.name,
                'message': 'Sin estadísticas disponibles',
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Obtener miembros de la cola"""
        queue = self.get_object()
        members_data = []
        for m in queue.members.select_related('agent__user').all():
            members_data.append({
                'id': m.id,
                'agent_id': m.agent.id,
                'agent_name': str(m.agent),
                'penalty': m.penalty,
                'paused': m.paused,
                'calls_taken': m.calls_taken,
                'last_call': m.last_call,
            })
        return Response({
            'queue': queue.name,
            'members': members_data,
            'count': len(members_data),
        })


class CallViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Call.objects.select_related(
        'agent__user', 'campaign', 'contact', 'queue', 'disposition'
    ).order_by('-start_time')
    serializer_class = serializers.CallSerializer
    # Llamadas son de solo lectura; accesibles a admin, supervisor y analyst
    permission_classes = [IsAdminSupervisorOrAnalyst]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['call_id', 'caller_id', 'called_number']
    filterset_fields = ['direction', 'status', 'agent', 'campaign']
    ordering_fields = ['start_time', 'talk_time']


class RecordingViewSet(viewsets.ModelViewSet):
    queryset = Recording.objects.all()
    serializer_class = serializers.RecordingSerializer
    # Grabaciones: admin y supervisor; analyst puede leer también
    permission_classes = [IsAdminSupervisorOrAnalyst]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['filename', 'call__call_id']
    filterset_fields = ['status', 'agent', 'campaign']
    http_method_names = ['get', 'delete', 'head', 'options']  # Solo lectura + borrado

    def perform_destroy(self, instance):
        import os
        if instance.file_path and os.path.exists(instance.file_path):
            try:
                os.remove(instance.file_path)
            except OSError:
                pass
        instance.delete()


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = serializers.ReportSerializer
    # Reportes: todos los roles con acceso (analyst también genera reportes)
    permission_classes = [IsAdminSupervisorOrAnalyst]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']
    filterset_fields = ['report_type', 'format', 'status']
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generar reporte"""
        report = self.get_object()
        from apps.reports.tasks import generate_report
        generate_report.delay(report.id)
        return Response({'status': 'generating report'})


# =====================================================================
# NOTA: TrunkViewSet REAL está en apps.telephony.views.SIPTrunkViewSet
# con integración completa de Asterisk AMI (test_connection real,
# force_register, preview_config, etc.)
# Si necesitas registrar rutas de troncales en urls.py de api/,
# importa desde telephony: from apps.telephony.views import SIPTrunkViewSet
# =====================================================================
