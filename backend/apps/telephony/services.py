"""
Servicios de telefonía de alto nivel
Wrappers síncronos para operaciones AMI
"""
from asgiref.sync import async_to_sync
from .asterisk_ami import asterisk_ami
import logging

logger = logging.getLogger(__name__)


class CallService:
    """Servicio para gestionar llamadas"""
    
    @staticmethod
    def originate_call(agent_extension: str, destination: str, 
                      caller_id: str = None, campaign_id: int = None):
        """
        Originar una llamada desde un agente
        
        Args:
            agent_extension: Extensión del agente (ej: 1000)
            destination: Número destino
            caller_id: Caller ID a mostrar
            campaign_id: ID de campaña (opcional)
        """
        channel = f"PJSIP/{agent_extension}"
        variables = {}
        
        if campaign_id:
            variables['CAMPAIGN_ID'] = str(campaign_id)
        
        variables['DESTINATION'] = destination
        
        try:
            result = async_to_sync(asterisk_ami.originate_call)(
                channel=channel,
                extension=destination,
                context='from-internal',
                caller_id=caller_id,
                variables=variables
            )
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"Error originating call: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def hangup_call(channel: str):
        """Colgar una llamada"""
        try:
            result = async_to_sync(asterisk_ami.hangup)(channel)
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"Error hanging up call: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def transfer_call(channel: str, extension: str):
        """Transferir una llamada"""
        try:
            result = async_to_sync(asterisk_ami.transfer)(
                channel=channel,
                extension=extension
            )
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"Error transferring call: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def start_recording(channel: str, filename: str):
        """Iniciar grabación de llamada"""
        try:
            result = async_to_sync(asterisk_ami.monitor_start)(
                channel=channel,
                filename=filename
            )
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def stop_recording(channel: str):
        """Detener grabación"""
        try:
            result = async_to_sync(asterisk_ami.monitor_stop)(channel)
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return {'success': False, 'error': str(e)}


class QueueService:
    """Servicio para gestionar colas ACD"""
    
    @staticmethod
    def add_agent_to_queue(queue_name: str, agent_extension: str, 
                          agent_name: str = None, penalty: int = 0):
        """Agregar agente a una cola"""
        interface = f"PJSIP/{agent_extension}"
        
        try:
            result = async_to_sync(asterisk_ami.add_queue_member)(
                queue=queue_name,
                interface=interface,
                member_name=agent_name or f"Agent {agent_extension}",
                penalty=penalty
            )
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"Error adding agent to queue: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def remove_agent_from_queue(queue_name: str, agent_extension: str):
        """Remover agente de una cola"""
        interface = f"PJSIP/{agent_extension}"
        
        try:
            result = async_to_sync(asterisk_ami.remove_queue_member)(
                queue=queue_name,
                interface=interface
            )
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"Error removing agent from queue: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def pause_agent(queue_name: str, agent_extension: str, 
                   paused: bool = True, reason: str = None):
        """Pausar/Despausar agente en cola"""
        interface = f"PJSIP/{agent_extension}"
        
        try:
            result = async_to_sync(asterisk_ami.pause_queue_member)(
                queue=queue_name,
                interface=interface,
                paused=paused,
                reason=reason
            )
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"Error pausing agent: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_queue_status(queue_name: str = None):
        """Obtener estado de cola(s)"""
        try:
            result = async_to_sync(asterisk_ami.get_queue_status)(queue_name)
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {'success': False, 'error': str(e)}
