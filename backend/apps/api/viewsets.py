from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse

from apps.users.models import User
from apps.campaigns.models import Campaign
from apps.agents.models import Agent
from apps.contacts.models import Contact, ContactList
from apps.queues.models import Queue
from apps.telephony.models import Call
from apps.recordings.models import Recording
from apps.reports.models import Report

from apps.api import serializers


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_active', 'is_active_agent']


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.select_related(
        'queue', 'contact_list', 'created_by', 'current_campaign'
    ).prefetch_related(
        'dispositions', 'agents', 'calls'
    )
    serializer_class = serializers.CampaignSerializer
    permission_classes = [IsAuthenticated]
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


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.select_related('user').prefetch_related('campaigns')
    serializer_class = serializers.AgentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['agent_id', 'sip_extension', 'user__username', 'user__first_name', 'user__last_name', 'user__email']
    filterset_fields = ['status', 'webrtc_enabled']
    ordering_fields = ['created_at', 'agent_id', 'status', 'calls_today']
    ordering = ['-created_at']
    
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
        """Marcar agente como conectado"""
        agent = self.get_object()
        agent.login()
        return Response({
            'status': 'logged in',
            'agent_id': agent.agent_id,
            'sip_extension': agent.sip_extension
        })
    
    @action(detail=True, methods=['post'])
    def logout(self, request, pk=None):
        """Marcar agente como desconectado"""
        agent = self.get_object()
        agent.logout()
        return Response({'status': 'logged out'})
    
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


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.select_related('contact_list').prefetch_related('notes')
    serializer_class = serializers.ContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'phone', 'email', 'company']
    filterset_fields = ['contact_list', 'status']


class ContactListViewSet(viewsets.ModelViewSet):
    queryset = ContactList.objects.all()
    serializer_class = serializers.ContactListSerializer
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['call_id', 'caller_id', 'called_number']
    filterset_fields = ['direction', 'status', 'agent', 'campaign']
    ordering_fields = ['start_time', 'talk_time']


class RecordingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Recording.objects.all()
    serializer_class = serializers.RecordingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['filename', 'call__call_id']
    filterset_fields = ['status', 'agent', 'campaign']


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = serializers.ReportSerializer
    permission_classes = [IsAuthenticated]
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
