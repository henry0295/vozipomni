from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer para comunicación en tiempo real con agentes
    """
    
    async def connect(self):
        self.agent_id = self.scope['url_route']['kwargs']['agent_id']
        self.room_group_name = f'agent_{self.agent_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Agent {self.agent_id} connected")
    
    async def disconnect(self, close_code):
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
        self.campaign_id = self.scope['url_route']['kwargs']['campaign_id']
        self.room_group_name = f'campaign_{self.campaign_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
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


class DashboardConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer para dashboard en tiempo real
    """
    
    async def connect(self):
        self.room_group_name = 'dashboard'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def dashboard_update(self, event):
        """
        Enviar actualización del dashboard
        """
        await self.send_json({
            'type': 'dashboard_update',
            'data': event['data']
        })
