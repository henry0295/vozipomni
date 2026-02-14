# WebSocket Server Dedicado para VozipOmni
# Tareas asíncronas, notificaciones en tiempo real, aprovisionamiento Asterisk

import asyncio
import json
import logging
import redis.asyncio as aioredis
from aiohttp import web
import aiohttp
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración desde variables de entorno
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
WS_PORT = int(os.getenv('WS_PORT', 8765))
WS_HOST = os.getenv('WS_HOST', '0.0.0.0')

class WebSocketServer:
    def __init__(self):
        self.clients = set()
        self.redis_client = None
        self.asterisk_clients = {}  # Clientes de Asterisk conectados
        
    async def initialize(self):
        """Inicializar conexión a Redis"""
        self.redis_client = await aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("Conectado a Redis")
        
        # Iniciar listener de eventos de Redis
        asyncio.create_task(self.redis_pubsub_listener())
        
    async def redis_pubsub_listener(self):
        """Escuchar eventos de Redis para notificaciones"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(
            'asterisk:config',
            'campaigns:updates',
            'reports:generated',
            'calls:events'
        )
        
        logger.info("Suscrito a canales de Redis")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await self.broadcast_to_clients(message['data'])
                
    async def handle_websocket(self, request):
        """Manejar conexión WebSocket"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        client_type = request.query.get('type', 'browser')
        client_id = request.query.get('id', str(id(ws)))
        
        # Registrar cliente
        self.clients.add(ws)
        
        if client_type == 'asterisk':
            self.asterisk_clients[client_id] = ws
            logger.info(f"Asterisk cliente conectado: {client_id}")
        else:
            logger.info(f"Browser cliente conectado: {client_id}")
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self.handle_message(ws, msg.data, client_type, client_id)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        finally:
            self.clients.discard(ws)
            if client_id in self.asterisk_clients:
                del self.asterisk_clients[client_id]
            logger.info(f"Cliente desconectado: {client_id}")
            
        return ws
    
    async def handle_message(self, ws, data, client_type, client_id):
        """Procesar mensajes recibidos"""
        try:
            message = json.loads(data)
            action = message.get('action')
            
            if action == 'ping':
                await ws.send_json({'action': 'pong', 'timestamp': datetime.now().isoformat()})
                
            elif action == 'asterisk_config_request':
                # Asterisk solicita configuración
                config_key = message.get('config_key')
                config_data = await self.get_asterisk_config(config_key)
                await ws.send_json({
                    'action': 'asterisk_config_response',
                    'config_key': config_key,
                    'data': config_data
                })
                
            elif action == 'generate_report':
                # Solicitud de generación de reporte
                await self.queue_report_generation(message.get('report_data'))
                await ws.send_json({'action': 'report_queued', 'status': 'processing'})
                
            elif action == 'subscribe_campaign':
                # Suscribirse a actualizaciones de campaña
                campaign_id = message.get('campaign_id')
                # Guardar suscripción en Redis para tracking
                await self.redis_client.sadd(f'campaign:{campaign_id}:subscribers', client_id)
                
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON: {data}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
    async def get_asterisk_config(self, config_key):
        """Obtener configuración de Asterisk desde Redis"""
        config = await self.redis_client.get(f'asterisk:config:{config_key}')
        return config or ""
        
    async def queue_report_generation(self, report_data):
        """Encolar generación de reporte en background"""
        await self.redis_client.rpush('reports:queue', json.dumps(report_data))
        await self.redis_client.publish('reports:new', json.dumps(report_data))
        
    async def broadcast_to_clients(self, message):
        """Enviar mensaje a todos los clientes conectados"""
        if self.clients:
            await asyncio.gather(
                *[client.send_str(message) for client in self.clients],
                return_exceptions=True
            )
            
    async def send_to_asterisk(self, asterisk_id, data):
        """Enviar datos específicamente a un cliente Asterisk"""
        if asterisk_id in self.asterisk_clients:
            ws = self.asterisk_clients[asterisk_id]
            await ws.send_json(data)
            
    async def health_check(self, request):
        """Endpoint de health check"""
        return web.json_response({
            'status': 'healthy',
            'clients': len(self.clients),
            'asterisk_clients': len(self.asterisk_clients),
            'timestamp': datetime.now().isoformat()
        })

async def init_app():
    """Inicializar aplicación"""
    app = web.Application()
    server = WebSocketServer()
    
    await server.initialize()
    
    app['websocket_server'] = server
    app.router.add_get('/ws', server.handle_websocket)
    app.router.add_get('/health', server.health_check)
    
    return app

def main():
    """Punto de entrada principal"""
    logger.info(f"Iniciando WebSocket Server en {WS_HOST}:{WS_PORT}")
    app = asyncio.run(init_app())
    web.run_app(app, host=WS_HOST, port=WS_PORT)

if __name__ == '__main__':
    main()
