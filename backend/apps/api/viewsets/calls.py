from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

from apps.telephony.models import Call

from apps.api import serializers
from core.permissions import IsAdminSupervisorOrAnalyst


def hangup_by_call_id(request):
    """Colgar una llamada activa via AMI Hangup usando call_id
    
    **VALIDACIÓN DE PERMISOS:**
    - El agente solo puede colgar sus propias llamadas
    - Admin y Supervisor pueden colgar cualquier llamada
    """
    import logging
    from apps.telephony.services import TelephonyService
    from apps.telephony.models import Call
    from apps.agents.models import Agent
    from django.utils import timezone
    _log = logging.getLogger(__name__)
    
    try:
        call_id = request.data.get('call_id')
        if not call_id:
            return Response(
                {'error': 'Se requiere call_id en el body'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Buscar la llamada por call_id
        try:
            call = Call.objects.select_related('agent__user').get(call_id=call_id)
        except Call.DoesNotExist:
            return Response(
                {'error': f'No se encontró llamada con ID: {call_id}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ═══════════════════════════════════════════════════════════════
        # VALIDACIÓN DE PERMISOS - SOLO EL AGENTE DUEÑO PUEDE COLGAR
        # ═══════════════════════════════════════════════════════════════
        user_role = getattr(request.user, 'role', None)
        is_admin_or_supervisor = user_role in ['admin', 'supervisor']
        
        # Si no es admin/supervisor, verificar que sea el agente dueño
        if not is_admin_or_supervisor:
            # Obtener agente del usuario actual
            try:
                current_agent = Agent.objects.get(user=request.user)
            except Agent.DoesNotExist:
                return Response(
                    {'error': 'Usuario no tiene perfil de agente'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Verificar que sea el agente dueño de la llamada
            if call.agent_id != current_agent.id:
                _log.warning(
                    f"Intento no autorizado: Agente {current_agent.agent_id} "
                    f"intentó colgar llamada {call_id} del agente "
                    f"{call.agent.agent_id if call.agent else 'sin agente'}"
                )
                return Response(
                    {'error': 'No tiene permisos para colgar esta llamada'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Solo permitir colgar llamadas activas o en progreso
        if call.status not in ['initiated', 'ringing', 'answered', 'queued']:
            # Si ya está completada, no es un error
            if call.status in ['completed', 'cancelled', 'failed']:
                return Response({
                    'status': 'already_ended',
                    'message': 'La llamada ya finalizó',
                    'call_id': call.call_id
                })
            return Response(
                {'error': f'No se puede colgar una llamada con estado: {call.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener el canal activo de la llamada
        channel = getattr(call, 'channel', None)
        if not channel:
            _log.warning(f'Llamada {call_id} no tiene canal asociado, marcando como completada')
            call.status = 'completed'
            call.end_time = timezone.now()
            call.save()
            return Response({
                'status': 'success',
                'message': 'Llamada marcada como completada (sin canal activo)',
                'call_id': call.call_id
            })
        
        # Ejecutar hangup via AMI
        try:
            result = TelephonyService.hangup_call(channel)
            if result.get('success'):
                # Actualizar estado de la llamada
                call.status = 'completed'
                call.end_time = timezone.now()
                call.save()
                
                _log.info(
                    f"Hangup exitoso: {call_id} | Canal: {channel} | "
                    f"Solicitado por: {request.user.username} ({user_role})"
                )
                
                return Response({
                    'status': 'success',
                    'message': 'Llamada terminada correctamente',
                    'call_id': call.call_id
                })
            else:
                return Response(
                    {'error': result.get('error', 'Error desconocido al colgar')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as ami_err:
            _log.error(f'Error al ejecutar hangup AMI para canal {channel}: {ami_err}')
            # Marcar como completada de todas formas
            call.status = 'completed'
            call.end_time = timezone.now()
            call.save()
            return Response({
                'status': 'success',
                'message': 'Llamada marcada como completada (error en AMI)',
                'call_id': call.call_id,
                'warning': str(ami_err)
            })
            
    except Exception as e:
        _log.exception('Error inesperado en hangup_call_by_id')
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class CallViewSet(viewsets.ModelViewSet):
    queryset = Call.objects.select_related(
        'agent__user', 'campaign', 'contact', 'queue', 'disposition'
    ).order_by('-start_time')
    serializer_class = serializers.CallSerializer
    # Admin/supervisor/analyst ven todas; agentes solo sus propias llamadas
    permission_classes = [IsAdminSupervisorOrAnalyst]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['call_id', 'caller_id', 'called_number']
    filterset_fields = ['direction', 'status', 'agent', 'campaign']
    ordering_fields = ['start_time', 'talk_time']

    def get_permissions(self):
        # Permitir a agentes crear llamadas (WebRTC) y colgar sus propias llamadas
        if self.action in ['create', 'hangup_call_by_id']:
            return [IsAuthenticated()]
        if getattr(self.request.user, 'role', None) == 'agent':
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self.request.user, 'role', None) == 'agent':
            # Agente solo ve sus propias llamadas
            return qs.filter(agent__user=self.request.user)
        return qs
    
    def perform_create(self, serializer):
        """Al crear llamada desde WebRTC, generar call_id si no existe"""
        import uuid
        from django.utils import timezone
        
        # Generar call_id único si no se proporciona
        if not serializer.validated_data.get('call_id'):
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            unique_suffix = str(uuid.uuid4())[:8]
            serializer.validated_data['call_id'] = f"WEB-{timestamp}-{unique_suffix}"
        
        # Establecer estado inicial
        if not serializer.validated_data.get('status'):
            serializer.validated_data['status'] = 'initiated'
        
        # Si no se especifica start_time, usar ahora
        if not serializer.validated_data.get('start_time'):
            serializer.validated_data['start_time'] = timezone.now()
        
        # Guardar llamada
        call = serializer.save()
        
        # Log de auditoría
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Llamada creada: {call.call_id} | "
            f"Agente: {call.agent.agent_id if call.agent else 'N/A'} | "
            f"Origen: {call.caller_id} → Destino: {call.called_number}"
        )
        
        return call
    
    @action(detail=True, methods=['post'], url_path='heartbeat')
    def heartbeat(self, request, pk=None):
        """Recibir heartbeat de llamada activa para detectar llamadas huérfanas
        
        El frontend envía heartbeat cada 30s durante una llamada activa.
        Esto permite detectar llamadas huérfanas si el cliente se desconecta.
        """
        import logging
        from django.utils import timezone
        _log = logging.getLogger(__name__)
        
        try:
            call = self.get_object()
            
            # Actualizar timestamp de último heartbeat
            if not call.metadata:
                call.metadata = {}
            
            call.metadata['last_heartbeat'] = timezone.now().isoformat()
            
            # Actualizar métricas de calidad si se envían
            quality_metrics = request.data.get('quality_metrics')
            if quality_metrics:
                call.metadata['quality_metrics'] = quality_metrics
            
            # Actualizar duración reportada por el cliente
            duration = request.data.get('duration')
            if duration:
                call.metadata['client_duration'] = duration
            
            call.save(update_fields=['metadata'])
            
            return Response({
                'status': 'ok',
                'call_id': call.call_id,
                'server_time': timezone.now().isoformat()
            })
            
        except Exception as e:
            _log.exception(f'Error en heartbeat para llamada pk={pk}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='hangup')
    def hangup_call_by_id(self, request):
        """Colgar una llamada activa via AMI Hangup usando call_id
        
        **VALIDACIÓN DE PERMISOS:**
        - El agente solo puede colgar sus propias llamadas
        - Admin y Supervisor pueden colgar cualquier llamada
        """
        return hangup_by_call_id(request)
