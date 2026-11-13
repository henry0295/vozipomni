import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer para comunicación en tiempo real con agentes
    """
    
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(code=4401)
            return
        self.agent_id = self.scope['url_route']['kwargs']['agent_id']
        if not await self.can_access_agent():
            await self.close(code=4403)
            return
        self.room_group_name = f'agent_{self.agent_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Agent {self.agent_id} connected")

    @database_sync_to_async
    def can_access_agent(self):
        from apps.agents.models import Agent
        user = self.scope['user']
        if getattr(user, 'role', None) in ('admin', 'supervisor') or user.is_superuser:
            return True
        return Agent.objects.filter(id=self.agent_id, user=user).exists()
    
    async def disconnect(self, close_code):
        if not hasattr(self, 'room_group_name'):
            return
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"Agent {self.agent_id} disconnected")
    
    async def receive_json(self, content):
        """
        Recibir mensajes del WebSocket
        """
        message_type = content.get('type')
        
        if message_type == 'status_change':
            await self.handle_status_change(content)
        elif message_type == 'call_action':
            await self.handle_call_action(content)
    
    async def handle_status_change(self, content):
        """
        Manejar cambios de estado del agente
        """
        new_status = content.get('status')
        # Aquí actualizar el estado en la base de datos
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'agent_status_update',
                'status': new_status
            }
        )
    
    async def handle_call_action(self, content):
        """
        Manejar acciones de llamada
        """
        action = content.get('action')
        # Implementar lógica de llamadas
    
    async def agent_status_update(self, event):
        """
        Enviar actualización de estado al WebSocket
        """
        await self.send_json({
            'type': 'status_update',
            'status': event['status']
        })
    
    async def incoming_call(self, event):
        """
        Notificar llamada entrante
        """
        await self.send_json({
            'type': 'incoming_call',
            'call_data': event['call_data']
        })


class CampaignConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer para monitoreo de campañas en tiempo real
    """
    
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close(code=4401)
            return
        self.campaign_id = self.scope['url_route']['kwargs']['campaign_id']
        if not await self.can_access_campaign():
            await self.close(code=4403)
            return
        self.room_group_name = f'campaign_{self.campaign_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()

    @database_sync_to_async
    def can_access_campaign(self):
        from apps.campaigns.models import Campaign
        user = self.scope['user']
        if getattr(user, 'role', None) in ('admin', 'supervisor', 'analyst') or user.is_superuser:
            return True
        return Campaign.objects.filter(id=self.campaign_id, agents__user=user).exists()
    
    async def disconnect(self, close_code):
        if not hasattr(self, 'room_group_name'):
            return
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def campaign_stats_update(self, event):
        """
        Enviar actualización de estadísticas
        """
        await self.send_json({
            'type': 'stats_update',
            'stats': event['stats']
        })


class MessagingConsumer(AsyncJsonWebsocketConsumer):
    """
    Eventos en tiempo real de mensajería (WhatsApp/omnicanal).
    - admin/supervisor → grupo messaging_all (toda la bandeja)
    - agente           → messaging_agent_<id> + messaging_unassigned
    Eventos: message.new, message.status, message.media, conversation.assigned/closed/reopened
    """

    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close(code=4401)
            return
        self.groups_joined = await self._resolve_groups()
        if not self.groups_joined:
            await self.close(code=4403)
            return
        for group in self.groups_joined:
            await self.channel_layer.group_add(group, self.channel_name)
        await self.accept()

    @database_sync_to_async
    def _resolve_groups(self):
        from apps.agents.models import Agent
        user = self.scope['user']
        if user.is_superuser or getattr(user, 'role', None) in ('admin', 'supervisor'):
            return ['messaging_all']
        agent = Agent.objects.filter(user=user).first()
        if agent:
            return [f'messaging_agent_{agent.id}', 'messaging_unassigned']
        return []

    async def disconnect(self, close_code):
        for group in getattr(self, 'groups_joined', []) or []:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def messaging_event(self, event):
        await self.send_json({'type': 'messaging', **event.get('payload', {})})


class NotFoundConsumer(AsyncJsonWebsocketConsumer):
    """Rutas WebSocket inexistentes: rechaza con 4404 (sin traza 500 en Daphne)."""

    async def connect(self):
        await self.close(code=4404)


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
        """Admin, supervisor y analista pueden ver el dashboard en tiempo real."""
        return self.user.is_superuser or getattr(self.user, 'role', None) in ['supervisor', 'admin', 'analyst']
    
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
        from django.db.models import Avg, Count

        now = timezone.now()
        today = now.date()

        # Llamadas de hoy
        calls_today = Call.objects.filter(start_time__date=today)

        # Agentes por estado
        agents_available = Agent.objects.filter(status='available').count()
        agents_oncall   = Agent.objects.filter(status__in=['oncall', 'busy']).count()
        agents_wrapup   = Agent.objects.filter(status='wrapup').count()
        agents_break    = Agent.objects.filter(status='break').count()

        # Promedios
        avg_talk = calls_today.filter(status='completed').aggregate(
            avg=Avg('talk_time')
        )['avg'] or 0

        return {
            'calls_today': calls_today.count(),
            'calls_answered': calls_today.filter(status='completed').count(),
            'calls_abandoned': calls_today.filter(status='abandoned').count(),
            'calls_active': Call.objects.filter(
                status__in=['initiated', 'ringing', 'answered']
            ).count(),
            'agents_available': agents_available,
            'agents_oncall': agents_oncall,
            'agents_wrapup': agents_wrapup,
            'agents_break': agents_break,
            'avg_talk_time': round(avg_talk, 2),
            'service_level': self._calculate_service_level(calls_today),
            'timestamp': now.isoformat()
        }

    def _calculate_service_level(self, calls):
        """Calcular nivel de servicio (% respondidas en ≤ 20s)"""
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
                'talk_time_today': agent.talk_time_today,
                'last_call': agent.last_call_time.isoformat() if agent.last_call_time else None,
                'logged_in_at': agent.logged_in_at.isoformat() if agent.logged_in_at else None,
            }
            for agent in agents
        ]
    
    @database_sync_to_async
    def get_queues(self):
        """Obtener estado de colas"""
        from apps.queues.models import Queue, QueueStats

        queues = Queue.objects.all()
        queue_data = []

        for queue in queues:
            stats = QueueStats.objects.filter(queue=queue).first()

            queue_data.append({
                'id': queue.id,
                'name': queue.name,
                'strategy': queue.strategy,
                'members_count': queue.queuemember_set.filter(paused=False).count(),
                'calls_waiting': stats.calls_waiting if stats else 0,
                'calls_completed': stats.calls_completed if stats else 0,
                'calls_abandoned': stats.calls_abandoned if stats else 0,
                'service_level_percentage': stats.service_level_percentage if stats else 0,
            })

        return queue_data
    
    @database_sync_to_async
    def get_active_calls(self):
        """Obtener llamadas activas"""
        from apps.telephony.models import Call

        active_calls = Call.objects.filter(
            status__in=['initiated', 'ringing', 'answered']
        ).select_related('agent__user')

        return [
            {
                'id': call.id,
                'channel': call.channel,
                'caller_id': call.caller_id,
                'agent': call.agent.user.get_full_name() if call.agent else None,
                'duration': call.duration,
                'start_time': call.start_time.isoformat(),
            }
            for call in active_calls
        ]
    
    @database_sync_to_async
    def get_campaigns(self):
        """Obtener campañas activas"""
        from apps.campaigns.models import Campaign
        from django.utils import timezone
        
        now = timezone.now()
        campaigns = Campaign.objects.filter(
            status='active',
            start_date__lte=now,
        )
        
        return [
            {
                'id': campaign.id,
                'name': campaign.name,
                'type': campaign.campaign_type,
                'contacts_total': campaign.total_contacts,
                'contacts_called': campaign.contacted,
                'success_rate': campaign.success_rate,
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
