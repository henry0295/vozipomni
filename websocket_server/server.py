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
        self._client_meta = {}     # Metadatos por id(ws): role, user_id, type
        
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
        """Manejar conexión WebSocket con validación de token JWT"""
        ws = web.WebSocketResponse()
        
        # ── Autenticación por token ──────────────────────────────────────────
        # El cliente debe enviar ?token=<JWT> en la URL de conexión.
        # El token se valida contra la clave secreta del backend Django.
        token = request.query.get('token', '')
        client_role = 'unknown'
        client_user_id = None
        
        if token:
            validated = await self._validate_jwt_token(token)
            if not validated:
                # Token inválido — rechazar conexión
                await ws.prepare(request)
                await ws.send_json({'action': 'error', 'message': 'Token inválido o expirado'})
                await ws.close()
                return ws
            client_role = validated.get('role', 'agent')
            client_user_id = validated.get('user_id')
        else:
            # Sin token — solo permitir si viene de localhost (backend/celery)
            peer_ip = request.remote
            if peer_ip not in ('127.0.0.1', '::1', 'localhost'):
                await ws.prepare(request)
                await ws.send_json({'action': 'error', 'message': 'Token requerido'})
                await ws.close()
                return ws
        
        await ws.prepare(request)
        
        client_type = request.query.get('type', 'browser')
        client_id = request.query.get('id', str(id(ws)))
        
        # Registrar cliente con metadatos de rol
        client_info = {
            'ws': ws,
            'role': client_role,
            'user_id': client_user_id,
            'type': client_type,
        }
        self.clients.add(ws)
        self._client_meta[id(ws)] = client_info
        
        if client_type == 'asterisk':
            self.asterisk_clients[client_id] = ws
            logger.info(f"Asterisk cliente conectado: {client_id}")
        else:
            logger.info(f"Browser cliente conectado: {client_id} (role={client_role}, user={client_user_id})")
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self.handle_message(ws, msg.data, client_type, client_id)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
        finally:
            self.clients.discard(ws)
            self._client_meta.pop(id(ws), None)
            if client_id in self.asterisk_clients:
                del self.asterisk_clients[client_id]
            logger.info(f"Cliente desconectado: {client_id}")
            
        return ws
    
    async def _validate_jwt_token(self, token: str) -> dict | None:
        """
        Valida un JWT token de Django REST framework SimpleJWT.
        Retorna los claims del payload si es válido, None si no lo es.
        """
        try:
            import base64, json as _json, hmac, hashlib
            
            SECRET_KEY = os.getenv('SECRET_KEY', '')
            if not SECRET_KEY:
                # Sin clave secreta configurada, RECHAZAR por seguridad
                logger.error("SECRET_KEY no configurado — rechazando conexión WebSocket")
                return None
            
            # Decodificar JWT (formato: header.payload.signature)
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decodificar payload (base64url)
            padding = 4 - len(parts[1]) % 4
            payload_bytes = base64.urlsafe_b64decode(parts[1] + '=' * padding)
            payload = _json.loads(payload_bytes)
            
            # Verificar expiración
            import time
            if payload.get('exp', 0) < time.time():
                logger.debug("JWT expirado")
                return None
            
            return {
                'user_id': payload.get('user_id'),
                'role': payload.get('role', 'agent'),
                'username': payload.get('username', ''),
            }
        except Exception as e:
            logger.debug(f"JWT validation failed: {e}")
            return None
    
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
                if not config_key:
                    await ws.send_json({
                        'action': 'error',
                        'message': 'config_key is required'
                    })
                    return
                
                config_data = await self.get_asterisk_config(config_key)
                await ws.send_json({
                    'action': 'asterisk_config_response',
                    'config_key': config_key,
                    'data': config_data
                })
                
            elif action == 'generate_report':
                # Solicitud de generación de reporte
                report_data = message.get('report_data')
                if not report_data:
                    await ws.send_json({
                        'action': 'error',
                        'message': 'report_data is required'
                    })
                    return
                
                await self.queue_report_generation(report_data)
                await ws.send_json({'action': 'report_queued', 'status': 'processing'})
                
            elif action == 'subscribe_campaign':
                # Suscribirse a actualizaciones de campaña
                campaign_id = message.get('campaign_id')
                if not campaign_id:
                    await ws.send_json({
                        'action': 'error',
                        'message': 'campaign_id is required'
                    })
                    return
                
                # Guardar suscripción en Redis para tracking
                await self.redis_client.sadd(f'campaign:{campaign_id}:subscribers', client_id)
                await ws.send_json({
                    'action': 'subscribed',
                    'campaign_id': campaign_id
                })
            
            else:
                await ws.send_json({
                    'action': 'error',
                    'message': f'Unknown action: {action}'
                })
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {client_id}: {e}")
            await ws.send_json({
                'action': 'error',
                'message': 'Invalid JSON format'
            })
        except KeyError as e:
            logger.error(f"Missing required field from {client_id}: {e}")
            await ws.send_json({
                'action': 'error',
                'message': f'Missing required field: {e}'
            })
        except Exception as e:
            logger.exception(f"Unexpected error handling message from {client_id}: {e}")
            await ws.send_json({
                'action': 'error',
                'message': 'Internal server error'
            })
            
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
    # CORRECTO: pasar la coroutine init_app() directamente a web.run_app().
    # aiohttp crea UN solo event loop y ejecuta init_app() dentro de él,
    # garantizando que la conexión Redis, el listener pub/sub y el servidor HTTP
    # compartan el mismo loop.
    # INCORRECTO: asyncio.run(init_app()) crea un loop temporal que se destruye
    # antes de que web.run_app() arranque su propio loop — las tareas (redis_pubsub_listener)
    # creadas en el loop temporal quedan huérfanas y silenciosamente mueren.
    web.run_app(init_app(), host=WS_HOST, port=WS_PORT)

if __name__ == '__main__':
    main()
