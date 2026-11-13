from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from apps.queues.models import Queue

from apps.api import serializers
from core.permissions import IsAdminOrSupervisorOrReadOnly


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
