"""
Asterisk Manager Interface (AMI) Service
Maneja la conexión y comunicación con Asterisk
"""
import asyncio
import socket
import logging
from typing import Optional, Dict, Callable
from panoramisk import Manager
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class AsteriskAMI:
    """Cliente AMI para Asterisk con soporte de eventos"""
    
    def __init__(self):
        self.manager: Optional[Manager] = None
        self.connected = False
        self.event_handlers: Dict[str, Callable] = {}
        self.channel_layer = get_channel_layer()
        
        # Configuración AMI
        self.ami_host = getattr(settings, 'ASTERISK_HOST', 'asterisk')
        self.ami_port = getattr(settings, 'ASTERISK_AMI_PORT', 5038)
        self.ami_user = getattr(settings, 'ASTERISK_AMI_USER', 'admin')
        self.ami_password = getattr(settings, 'ASTERISK_AMI_PASSWORD', 'VoziPOmni2026!')
    
    # ========== MÉTODOS SINCRÓNICOS PARA COMANDOS SIMPLES ==========
    
    def connect(self):
        """Conectar al AMI de Asterisk (versión sincrónica)"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.ami_host, self.ami_port))
            
            # Leer banner
            self._read_response()
            
            # Autenticarse
            self._send_command(f"Action: Login\r\nUsername: {self.ami_user}\r\nSecret: {self.ami_password}\r\n\r\n")
            response = self._read_response()
            
            if 'Success' in response:
                self.connected = True
                logger.info(f"✓ Conectado a Asterisk AMI en {self.ami_host}:{self.ami_port}")
                return True
            else:
                logger.error("Error de autenticación AMI")
                return False
                
        except Exception as e:
            logger.error(f"Error conectando a Asterisk AMI: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Desconectar del AMI (versión sincrónica)"""
        if hasattr(self, 'sock'):
            try:
                self._send_command("Action: Logoff\r\n\r\n")
                self.sock.close()
            except:
                pass
            self.connected = False
            logger.info("Desconectado de Asterisk AMI")
    
    def _send_command(self, command):
        """Enviar comando al AMI"""
        if hasattr(self, 'sock'):
            self.sock.sendall(command.encode('utf-8'))
    
    def _read_response(self):
        """Leer respuesta del AMI"""
        response = b''
        while True:
            try:
                chunk = self.sock.recv(1024)
                if not chunk:
                    break
                response += chunk
                if b'\r\n\r\n' in response:
                    break
            except socket.timeout:
                break
        return response.decode('utf-8', errors='ignore')
    
    def reload_module(self, module_name):
        """Recargar un módulo específico de Asterisk"""
        if not self.connected:
            return False
        
        try:
            self._send_command(f"Action: ModuleLoad\r\nLoadType: reload\r\nModule: {module_name}\r\n\r\n")
            response = self._read_response()
            logger.info(f"Módulo {module_name} recargado")
            return 'Success' in response
        except Exception as e:
            logger.error(f"Error recargando módulo {module_name}: {e}")
            return False
    
    def reload_dialplan(self):
        """Recargar el dialplan (extensions.conf)"""
        if not self.connected:
            return False
        
        try:
            self._send_command("Action: Command\r\nCommand: dialplan reload\r\n\r\n")
            response = self._read_response()
            logger.info("Dialplan recargado")
            return True
        except Exception as e:
            logger.error(f"Error recargando dialplan: {e}")
            return False
    
    def sip_show_peers(self):
        """Obtener lista de peers SIP"""
        if not self.connected:
            return []
        
        try:
            self._send_command("Action: SIPpeers\r\n\r\n")
            response = self._read_response()
            # Parsear respuesta (simplificado)
            return response
        except Exception as e:
            logger.error(f"Error obteniendo peers SIP: {e}")
            return []
    
    def pjsip_show_endpoints(self):
        """Obtener lista de endpoints PJSIP con sus contactos"""
        if not self.connected:
            return {}
        
        try:
            self._send_command("Action: PJSIPShowEndpoints\r\n\r\n")
            response = self._read_response()
            
            # Parsear respuesta para obtener endpoints y sus contactos
            endpoints = {}
            lines = response.split('\r\n')
            current_endpoint = None
            
            for line in lines:
                if 'ObjectName:' in line:
                    current_endpoint = line.split(':', 1)[1].strip()
                    endpoints[current_endpoint] = {
                        'name': current_endpoint,
                        'state': 'Unknown',
                        'contacts': []
                    }
                elif 'DeviceState:' in line and current_endpoint:
                    state = line.split(':', 1)[1].strip()
                    endpoints[current_endpoint]['state'] = state
                elif 'Contacts:' in line and current_endpoint:
                    # El formato es generalmente "Contacts: endpoint/uri"
                    contacts = line.split(':', 1)[1].strip()
                    if contacts and contacts != '<none>':
                        endpoints[current_endpoint]['contacts'].append(contacts)
            
            return endpoints
        except Exception as e:
            logger.error(f"Error obteniendo endpoints PJSIP: {e}")
            return {}
    
    def pjsip_show_registrations(self):
        """Obtener estado de registros PJSIP (troncales)"""
        if not self.connected:
            return []
        
        try:
            self._send_command("Action: PJSIPShowRegistrations\r\n\r\n")
            response = self._read_response()
            
            # Parsear respuesta para obtener estado de cada registro
            registrations = {}
            lines = response.split('\r\n')
            current_reg = None
            
            for line in lines:
                if 'ObjectName:' in line:
                    current_reg = line.split(':', 1)[1].strip()
                    registrations[current_reg] = {'status': 'Unknown', 'name': current_reg}
                elif 'Status:' in line and current_reg:
                    status = line.split(':', 1)[1].strip()
                    registrations[current_reg]['status'] = status
            
            return registrations
        except Exception as e:
            logger.error(f"Error obteniendo registros PJSIP: {e}")
            return {}
    
    def get_trunk_registration_status(self, trunk_name):
        """Obtener estado de registro de una troncal específica"""
        try:
            registrations = self.pjsip_show_registrations()
            
            # Buscar por nombre de troncal o nombre con sufijo -reg
            trunk_key = trunk_name
            if trunk_key not in registrations:
                trunk_key = f"{trunk_name}-reg"
            
            if trunk_key in registrations:
                status = registrations[trunk_key].get('status', 'Unknown')
                # Normalizar estados
                if 'Registered' in status:
                    return 'Registered'
                elif 'Rejected' in status or 'Failed' in status:
                    return 'Failed'
                elif 'Unregistered' in status:
                    return 'Unregistered'
                else:
                    return 'Unknown'
            
            return 'Not Configured'
        except Exception as e:
            logger.error(f"Error verificando estado de troncal {trunk_name}: {e}")
            return 'Error'
    
    # ========== MÉTODOS ASINCRÓNICOS PARA EVENTOS ==========
    
    async def connect_async(self):
        """Conectar al AMI de Asterisk (versión asíncrona para eventos)"""
        try:
            self.manager = Manager(
                host=self.ami_host,
                port=self.ami_port,
                username=self.ami_user,
                secret=self.ami_password,
                ping_delay=10,
                ping_tries=3
            )
            
            await self.manager.connect()
            self.connected = True
            logger.info(f"✓ Conectado a Asterisk AMI (async) en {self.ami_host}:{self.ami_port}")
            
            # Registrar handlers de eventos
            self._register_event_handlers()
            
        except Exception as e:
            logger.error(f"Error conectando a Asterisk AMI (async): {e}")
            self.connected = False
            raise
    
    async def disconnect_async(self):
        """Desconectar del AMI (versión asíncrona)"""
        if self.manager:
            await self.manager.close()
            self.connected = False
            logger.info("Desconectado de Asterisk AMI (async)")
    
    def _register_event_handlers(self):
        """Registrar handlers para eventos de Asterisk"""
        if not self.manager:
            return
        
        # Eventos de llamadas
        self.manager.register_event('Newchannel', self._on_new_channel)
        self.manager.register_event('Newstate', self._on_new_state)
        self.manager.register_event('Hangup', self._on_hangup)
        self.manager.register_event('Bridge', self._on_bridge)
        self.manager.register_event('AgentConnect', self._on_agent_connect)
        self.manager.register_event('AgentComplete', self._on_agent_complete)
        
        # Eventos de colas
        self.manager.register_event('QueueMemberAdded', self._on_queue_member_added)
        self.manager.register_event('QueueMemberRemoved', self._on_queue_member_removed)
        self.manager.register_event('QueueMemberStatus', self._on_queue_member_status)
        self.manager.register_event('QueueCallerJoin', self._on_queue_caller_join)
        self.manager.register_event('QueueCallerLeave', self._on_queue_caller_leave)
        self.manager.register_event('QueueCallerAbandon', self._on_queue_caller_abandon)
        
        logger.info("Event handlers registrados")
    
    async def _on_new_channel(self, manager, event):
        """Nuevo canal creado"""
        logger.debug(f"Nuevo canal: {event.Channel}")
        
        # Notificar via WebSocket
        await self._broadcast_event('call.new_channel', {
            'channel': event.Channel,
            'caller_id': event.CallerIDNum,
            'state': event.ChannelStateDesc,
            'context': event.Context,
            'exten': event.Exten
        })
    
    async def _on_new_state(self, manager, event):
        """Cambio de estado en canal"""
        logger.debug(f"Cambio de estado: {event.Channel} -> {event.ChannelStateDesc}")
        
        await self._broadcast_event('call.state_change', {
            'channel': event.Channel,
            'state': event.ChannelStateDesc,
            'caller_id': event.CallerIDNum
        })
    
    async def _on_hangup(self, manager, event):
        """Llamada colgada"""
        logger.info(f"Hangup: {event.Channel} - Cause: {event.Cause}")
        
        # Guardar estadísticas de llamada
        await self._save_call_stats(event)
        
        await self._broadcast_event('call.hangup', {
            'channel': event.Channel,
            'cause': event.Cause,
            'cause_text': event.get('Cause-txt', 'Unknown')
        })
    
    async def _on_bridge(self, manager, event):
        """Dos canales conectados (bridge)"""
        logger.info(f"Bridge: {event.Channel1} <-> {event.Channel2}")
        
        await self._broadcast_event('call.bridge', {
            'channel1': event.Channel1,
            'channel2': event.Channel2,
            'bridge_state': event.Bridgestate
        })
    
    async def _on_agent_connect(self, manager, event):
        """Agente conectado a una llamada"""
        logger.info(f"Agente conectado: {event.Member} - Queue: {event.Queue}")
        
        await self._broadcast_event('agent.call_connected', {
            'queue': event.Queue,
            'member': event.Member,
            'caller_id': event.CallerIDNum,
            'hold_time': event.HoldTime,
            'unique_id': event.Uniqueid
        })
    
    async def _on_agent_complete(self, manager, event):
        """Agente completó una llamada"""
        logger.info(f"Llamada completada: {event.Member} - Duration: {event.TalkTime}s")
        
        await self._broadcast_event('agent.call_completed', {
            'queue': event.Queue,
            'member': event.Member,
            'talk_time': event.TalkTime,
            'hold_time': event.HoldTime,
            'reason': event.Reason
        })
    
    async def _on_queue_member_added(self, manager, event):
        """Agente agregado a cola"""
        await self._broadcast_event('queue.member_added', {
            'queue': event.Queue,
            'member': event.MemberName,
            'interface': event.Interface
        })
    
    async def _on_queue_member_removed(self, manager, event):
        """Agente removido de cola"""
        await self._broadcast_event('queue.member_removed', {
            'queue': event.Queue,
            'member': event.MemberName
        })
    
    async def _on_queue_member_status(self, manager, event):
        """Estado de agente en cola"""
        await self._broadcast_event('queue.member_status', {
            'queue': event.Queue,
            'member': event.MemberName,
            'status': event.Status,
            'paused': event.Paused == '1',
            'calls_taken': event.CallsTaken,
            'in_call': event.InCall == '1'
        })
    
    async def _on_queue_caller_join(self, manager, event):
        """Llamada ingresa a cola"""
        await self._broadcast_event('queue.caller_join', {
            'queue': event.Queue,
            'caller_id': event.CallerIDNum,
            'position': event.Position,
            'count': event.Count
        })
    
    async def _on_queue_caller_leave(self, manager, event):
        """Llamada sale de cola (atendida)"""
        await self._broadcast_event('queue.caller_leave', {
            'queue': event.Queue,
            'caller_id': event.CallerIDNum,
            'hold_time': event.HoldTime,
            'count': event.Count
        })
    
    async def _on_queue_caller_abandon(self, manager, event):
        """Llamada abandonada en cola"""
        await self._broadcast_event('queue.caller_abandon', {
            'queue': event.Queue,
            'caller_id': event.CallerIDNum,
            'position': event.Position,
            'hold_time': event.HoldTime
        })
    
    async def _broadcast_event(self, event_type: str, data: dict):
        """Enviar evento via WebSocket a todos los agentes conectados"""
        if not self.channel_layer:
            return
        
        try:
            await self.channel_layer.group_send(
                'asterisk_events',
                {
                    'type': 'asterisk.event',
                    'event_type': event_type,
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")
    
    async def _save_call_stats(self, event):
        """Guardar estadísticas de llamada en base de datos"""
        from apps.telephony.models import Call
        from datetime import datetime
        
        try:
            # Extraer información del evento
            call = await Call.objects.filter(
                channel=event.Channel
            ).afirst()
            
            if call:
                call.end_time = datetime.now()
                call.duration = int(event.get('Duration', 0))
                call.hangup_cause = event.Cause
                call.status = 'completed'
                await call.asave()
        except Exception as e:
            logger.error(f"Error saving call stats: {e}")
    
    # ==================== Acciones AMI ====================
    
    async def originate_call(self, channel: str, extension: str, 
                           context: str = 'from-internal', 
                           caller_id: str = None,
                           variables: dict = None) -> dict:
        """
        Originar una llamada
        
        Args:
            channel: Canal a llamar (ej: PJSIP/1000)
            extension: Extensión destino
            context: Contexto del dialplan
            caller_id: Caller ID a mostrar
            variables: Variables de canal
        
        Returns:
            Respuesta de Asterisk
        """
        if not self.connected:
            raise ConnectionError("No conectado a Asterisk AMI")
        
        action = {
            'Action': 'Originate',
            'Channel': channel,
            'Exten': extension,
            'Context': context,
            'Priority': '1',
            'Timeout': '30000',
            'Async': 'true'
        }
        
        if caller_id:
            action['CallerID'] = caller_id
        
        if variables:
            var_list = [f"{k}={v}" for k, v in variables.items()]
            action['Variable'] = ','.join(var_list)
        
        response = await self.manager.send_action(action)
        logger.info(f"Originate call: {channel} -> {extension}")
        return response
    
    async def hangup(self, channel: str, cause: int = 16) -> dict:
        """
        Colgar una llamada
        
        Args:
            channel: Canal a colgar
            cause: Código de causa (16 = Normal Clearing)
        """
        if not self.connected:
            raise ConnectionError("No conectado a Asterisk AMI")
        
        response = await self.manager.send_action({
            'Action': 'Hangup',
            'Channel': channel,
            'Cause': str(cause)
        })
        
        logger.info(f"Hangup: {channel}")
        return response
    
    async def add_queue_member(self, queue: str, interface: str, 
                              member_name: str = None, 
                              penalty: int = 0) -> dict:
        """Agregar agente a cola"""
        if not self.connected:
            raise ConnectionError("No conectado a Asterisk AMI")
        
        action = {
            'Action': 'QueueAdd',
            'Queue': queue,
            'Interface': interface,
            'Penalty': str(penalty)
        }
        
        if member_name:
            action['MemberName'] = member_name
        
        response = await self.manager.send_action(action)
        logger.info(f"Added to queue {queue}: {interface}")
        return response
    
    async def remove_queue_member(self, queue: str, interface: str) -> dict:
        """Remover agente de cola"""
        if not self.connected:
            raise ConnectionError("No conectado a Asterisk AMI")
        
        response = await self.manager.send_action({
            'Action': 'QueueRemove',
            'Queue': queue,
            'Interface': interface
        })
        
        logger.info(f"Removed from queue {queue}: {interface}")
        return response
    
    async def pause_queue_member(self, queue: str, interface: str, 
                                paused: bool = True, 
                                reason: str = None) -> dict:
        """Pausar/Despausar agente en cola"""
        if not self.connected:
            raise ConnectionError("No conectado a Asterisk AMI")
        
        action = {
            'Action': 'QueuePause',
            'Queue': queue,
            'Interface': interface,
            'Paused': 'true' if paused else 'false'
        }
        
        if reason:
            action['Reason'] = reason
        
        response = await self.manager.send_action(action)
        logger.info(f"Queue member {'paused' if paused else 'unpaused'}: {interface}")
        return response
    
    async def get_queue_status(self, queue: str = None) -> dict:
        """Obtener estado de cola(s)"""
        if not self.connected:
            raise ConnectionError("No conectado a Asterisk AMI")
        
        action = {'Action': 'QueueStatus'}
        if queue:
            action['Queue'] = queue
        
        response = await self.manager.send_action(action)
        return response
    
    async def transfer(self, channel: str, extension: str, 
                      context: str = 'from-internal') -> dict:
        """Transferir llamada"""
        if not self.connected:
            raise ConnectionError("No conectado a Asterisk AMI")
        
        response = await self.manager.send_action({
            'Action': 'Redirect',
            'Channel': channel,
            'Exten': extension,
            'Context': context,
            'Priority': '1'
        })
        
        logger.info(f"Transfer: {channel} -> {extension}")
        return response
    
    async def monitor_start(self, channel: str, filename: str, 
                          format: str = 'wav', mix: bool = True) -> dict:
        """Iniciar grabación de llamada"""
        if not self.connected:
            raise ConnectionError("No conectado a Asterisk AMI")
        
        response = await self.manager.send_action({
            'Action': 'Monitor',
            'Channel': channel,
            'File': filename,
            'Format': format,
            'Mix': 'true' if mix else 'false'
        })
        
        logger.info(f"Recording started: {filename}")
        return response
    
    async def monitor_stop(self, channel: str) -> dict:
        """Detener grabación"""
        if not self.connected:
            raise ConnectionError("No conectado a Asterisk AMI")
        
        response = await self.manager.send_action({
            'Action': 'StopMonitor',
            'Channel': channel
        })
        
        logger.info(f"Recording stopped: {channel}")
        return response


# Instancia global del cliente AMI
asterisk_ami = AsteriskAMI()


async def start_ami_service():
    """Iniciar servicio AMI (llamar desde Django startup)"""
    try:
        await asterisk_ami.connect()
        logger.info("✓ Asterisk AMI service started")
    except Exception as e:
        logger.error(f"Failed to start AMI service: {e}")


async def stop_ami_service():
    """Detener servicio AMI"""
    await asterisk_ami.disconnect()
    logger.info("Asterisk AMI service stopped")
