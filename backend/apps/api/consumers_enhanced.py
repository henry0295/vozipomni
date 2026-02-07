"""
WebSocket Consumers mejorados con integración Asterisk AMI
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db import models

logger = logging.getLogger(__name__)
User = get_user_model()


class AsteriskEventConsumer(AsyncWebsocketConsumer):
    """
    Consumer para eventos de Asterisk en tiempo real
    Conecta los eventos del AMI con los clientes WebSocket
    """
    
    async def connect(self):
        """Cliente conectado"""
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Determinar tipo de usuario y permisos
        self.is_admin = self.user.is_staff or self.user.is_superuser
        self.agent = await self.get_agent()
        
        # Unirse al grupo de eventos de Asterisk
        await self.channel_layer.group_add(
            'asterisk_events',
            self.channel_name
        )
        
        # Si es agente, unirse a su grupo específico
        if self.agent:
            self.agent_group = f'agent_{self.agent.id}'
            await self.channel_layer.group_add(
                self.agent_group,
                self.channel_name
            )
        
        await self.accept()
        logger.info(f"Asterisk events connected: {self.user.username}")
    
    async def disconnect(self, close_code):
        """Cliente desconectado"""
        await self.channel_layer.group_discard('asterisk_events', self.channel_name)
        
        if self.agent:
            await self.channel_layer.group_discard(
                self.agent_group,
                self.channel_name
            )
        
        logger.info(f"Asterisk events disconnected: {self.user.username}")
    
    @database_sync_to_async
    def get_agent(self):
        """Obtener agente si el usuario es agente"""
        from apps.agents.models import Agent
        try:
            return Agent.objects.get(user=self.user)
        except Agent.DoesNotExist:
            return None
    
    async def asterisk_event(self, event):
        """
        Recibir evento de Asterisk y filtrarlo antes de enviar
        """
        event_type = event.get('event_type', '')
        data = event.get('data', {})
        
        # Si es admin, enviar todos los eventos
        if self.is_admin:
            await self.send(text_data=json.dumps(event))
            return
        
        # Si es agente, filtrar solo sus eventos
        if self.agent:
            agent_extension = self.agent.sip_extension
            agent_channel = f"PJSIP/{agent_extension}"
            
            # Eventos de llamadas que involucran al agente
            if event_type.startswith('call.'):
                channel = data.get('channel', '')
                if agent_channel in channel or data.get('member', '').endswith(agent_extension):
                    await self.send(text_data=json.dumps(event))
            
            # Eventos de agente específico
            elif event_type.startswith('agent.'):
                member = data.get('member', '')
                if agent_extension in member:
                    await self.send(text_data=json.dumps(event))
            
            # Eventos de cola
            elif event_type.startswith('queue.'):
                # Verificar si el agente está en la cola
                interface = data.get('interface', '')
                member = data.get('member', '')
                if agent_extension in interface or agent_extension in member:
                    await self.send(text_data=json.dumps(event))


class RealtimeDashboardConsumer(AsyncWebsocketConsumer):
    """
    Consumer para dashboard con estadísticas en tiempo real
    """
    
    async def connect(self):
        """Cliente conectado al dashboard"""
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Verificar permisos (solo staff y supervisores)
        if not (self.user.is_staff or await self.is_supervisor()):
            await self.close()
            return
        
        # Unirse a grupos
        await self.channel_layer.group_add('dashboard', self.channel_name)
        await self.channel_layer.group_add('asterisk_events', self.channel_name)
        
        await self.accept()
        logger.info(f"Dashboard connected: {self.user.username}")
        
        # Enviar datos iniciales
        await self.send_initial_data()
    
    async def disconnect(self, close_code):
        """Cliente desconectado"""
        await self.channel_layer.group_discard('dashboard', self.channel_name)
        await self.channel_layer.group_discard('asterisk_events', self.channel_name)
        logger.info(f"Dashboard disconnected: {self.user.username}")
    
    async def receive(self, text_data):
        """Mensaje recibido del cliente"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'refresh_stats':
                await self.send_stats()
            elif action == 'refresh_agents':
                await self.send_agents()
            elif action == 'refresh_queues':
                await self.send_queues()
            elif action == 'refresh_campaigns':
                await self.send_campaigns()
                
        except Exception as e:
            logger.error(f"Error in dashboard consumer: {e}")
    
    @database_sync_to_async
    def is_supervisor(self):
        """Verificar si el usuario es supervisor"""
        return self.user.role in ['supervisor', 'admin']
    
    async def send_initial_data(self):
        """Enviar datos iniciales del dashboard"""
        data = {
            'type': 'initial_data',
            'stats': await self.get_stats(),
            'agents': await self.get_agents(),
            'queues': await self.get_queues(),
            'active_calls': await self.get_active_calls()
        }
        await self.send(text_data=json.dumps(data))
    
    async def send_stats(self):
        """Enviar estadísticas actualizadas"""
        stats = await self.get_stats()
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'data': stats
        }))
    
    async def send_agents(self):
        """Enviar lista de agentes"""
        agents = await self.get_agents()
        await self.send(text_data=json.dumps({
            'type': 'agents_update',
            'data': agents
        }))
    
    async def send_queues(self):
        """Enviar estado de colas"""
        queues = await self.get_queues()
        await self.send(text_data=json.dumps({
            'type': 'queues_update',
            'data': queues
        }))
    
    async def send_campaigns(self):
        """Enviar campañas activas"""
        campaigns = await self.get_campaigns()
        await self.send(text_data=json.dumps({
            'type': 'campaigns_update',
            'data': campaigns
        }))
    
    @database_sync_to_async
    def get_stats(self):
        """Obtener estadísticas generales"""
        from apps.telephony.models import Call
        from apps.agents.models import Agent
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        today = now.date()
        
        # Llamadas de hoy
        calls_today = Call.objects.filter(start_time__date=today)
        
        # Agentes por estado
        agents_ready = Agent.objects.filter(status='ready').count()
        agents_in_call = Agent.objects.filter(status='in_call').count()
        agents_acw = Agent.objects.filter(status='acw').count()
        agents_paused = Agent.objects.filter(status='paused').count()
        
        # Promedios
        avg_talk_time = calls_today.aggregate(
            avg=models.Avg('duration')
        )['avg'] or 0
        
        return {
            'calls_today': calls_today.count(),
            'calls_answered': calls_today.filter(status='completed').count(),
            'calls_abandoned': calls_today.filter(status='abandoned').count(),
            'calls_active': calls_today.filter(status='active').count(),
            'agents_ready': agents_ready,
            'agents_in_call': agents_in_call,
            'agents_acw': agents_acw,
            'agents_paused': agents_paused,
            'avg_talk_time': round(avg_talk_time, 2),
            'service_level': self._calculate_service_level(calls_today),
            'timestamp': now.isoformat()
        }
    
    def _calculate_service_level(self, calls):
        """Calcular nivel de servicio (% respondidas en < 20s)"""
        total = calls.filter(status='completed').count()
        if total == 0:
            return 100
        
        answered_in_time = calls.filter(
            status='completed',
            wait_time__lte=20
        ).count()
        
        return round((answered_in_time / total) * 100, 2)
    
    @database_sync_to_async
    def get_agents(self):
        """Obtener lista de agentes con su estado"""
        from apps.agents.models import Agent
        
        agents = Agent.objects.select_related('user').all()
        return [
            {
                'id': agent.id,
                'name': agent.user.get_full_name() or agent.user.username,
                'extension': agent.sip_extension,
                'status': agent.status,
                'calls_today': agent.calls_today,
                'avg_talk_time': agent.avg_talk_time or 0,
                'last_call': agent.last_call_time.isoformat() if agent.last_call_time else None
            }
            for agent in agents
        ]
    
    @database_sync_to_async
    def get_queues(self):
        """Obtener estado de colas"""
        from apps.queues.models import Queue, QueueStats
        from django.utils import timezone
        
        queues = Queue.objects.all()
        queue_data = []
        
        for queue in queues:
            # Obtener stats del día
            stats = QueueStats.objects.filter(
                queue=queue,
                timestamp__date=timezone.now().date()
            ).first()
            
            queue_data.append({
                'id': queue.id,
                'name': queue.name,
                'strategy': queue.strategy,
                'members_count': queue.queuemember_set.count(),
                'calls_waiting': stats.calls_waiting if stats else 0,
                'calls_answered': stats.calls_answered if stats else 0,
                'calls_abandoned': stats.calls_abandoned if stats else 0,
                'avg_hold_time': stats.avg_hold_time if stats else 0
            })
        
        return queue_data
    
    @database_sync_to_async
    def get_active_calls(self):
        """Obtener llamadas activas"""
        from apps.telephony.models import Call
        
        active_calls = Call.objects.filter(status='active').select_related(
            'agent__user'
        )
        
        return [
            {
                'id': call.id,
                'channel': call.channel,
                'caller_id': call.caller_id_number,
                'agent': call.agent.user.get_full_name() if call.agent else None,
                'duration': call.get_duration(),
                'start_time': call.start_time.isoformat()
            }
            for call in active_calls
        ]
    
    @database_sync_to_async
    def get_campaigns(self):
        """Obtener campañas activas"""
        from apps.campaigns.models import Campaign
        from django.utils import timezone
        
        today = timezone.now().date()
        campaigns = Campaign.objects.filter(
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        )
        
        return [
            {
                'id': campaign.id,
                'name': campaign.name,
                'type': campaign.campaign_type,
                'contacts_total': campaign.contactlist.contact_set.count() if campaign.contactlist else 0,
                'contacts_called': campaign.call_set.count(),
', 'success_rate': campaign.get_success_rate()
            }
            for campaign in campaigns
        ]
    
    # Handlers de eventos
    async def dashboard_update(self, event):
        """Actualización general del dashboard"""
        await self.send(text_data=json.dumps(event))
    
    async def asterisk_event(self, event):
        """Evento de Asterisk - actualizar stats automáticamente"""
        event_type = event.get('event_type', '')
        
        # En ciertos eventos, recargar stats
        if event_type in ['call.hangup', 'agent.call_completed', 'queue.caller_abandon']:
            await self.send_stats()
