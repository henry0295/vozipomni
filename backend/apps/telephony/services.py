"""
Servicios de telefonía de alto nivel.

Cada método crea su propia conexión AMI síncrona (por-request), la usa y la cierra.
Esto evita depender del singleton asíncrono global y funciona correctamente desde
vistas Django y handlers Celery (contexto síncrono).
"""
import logging

from .asterisk_ami import AsteriskAMI

logger = logging.getLogger(__name__)


def _ami_connect() -> AsteriskAMI:
    """Crear y conectar una instancia AMI síncrona. Lanza ConnectionError si falla."""
    ami = AsteriskAMI()
    if not ami.connect():
        raise ConnectionError("No se pudo conectar a Asterisk AMI")
    return ami


class CallService:
    """Servicio para gestionar llamadas via Asterisk AMI."""

    @staticmethod
    def originate_call(
        agent_extension: str,
        destination: str,
        caller_id: str = None,
        campaign_id: int = None,
        context: str = 'from-internal',
    ) -> dict:
        """
        Originar una llamada desde la extensión del agente hacia el destino.
        El agente es el A-leg; cuando contesta, Asterisk marca al destino.
        """
        variables = {}
        if campaign_id:
            variables['CAMPAIGN_ID'] = str(campaign_id)
        variables['DESTINATION'] = destination

        ami = None
        try:
            ami = _ami_connect()
            ami.originate(
                channel=f'PJSIP/{agent_extension}',
                context=context,
                exten=destination,
                caller_id=caller_id,
                variable=variables,
            )
            logger.info(f"[Call] Originada {agent_extension} → {destination}")
            return {'success': True}
        except Exception as e:
            logger.error(f"[Call] Error originando llamada: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if ami:
                ami.disconnect()

    @staticmethod
    def hangup_call(channel: str) -> dict:
        """Colgar un canal activo via AMI Hangup."""
        ami = None
        try:
            ami = _ami_connect()
            ami._send_command(
                f"Action: Hangup\r\n"
                f"Channel: {channel}\r\n"
                f"Cause: 16\r\n\r\n"
            )
            response = ami._read_response()
            success = 'Success' in response or 'Queued' in response
            logger.info(f"[Call] Hangup canal={channel} success={success}")
            return {'success': success, 'response': response[:200]}
        except Exception as e:
            logger.error(f"[Call] Error colgando canal {channel}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if ami:
                ami.disconnect()

    @staticmethod
    def transfer_call(channel: str, extension: str, context: str = 'from-internal') -> dict:
        """Transferir un canal via AMI Redirect."""
        ami = None
        try:
            ami = _ami_connect()
            ami._send_command(
                f"Action: Redirect\r\n"
                f"Channel: {channel}\r\n"
                f"Context: {context}\r\n"
                f"Exten: {extension}\r\n"
                f"Priority: 1\r\n\r\n"
            )
            response = ami._read_response()
            success = 'Success' in response
            logger.info(f"[Call] Transferencia {channel} → {extension} success={success}")
            return {'success': success, 'response': response[:200]}
        except Exception as e:
            logger.error(f"[Call] Error transfiriendo {channel}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if ami:
                ami.disconnect()

    @staticmethod
    def start_recording(channel: str, filename: str) -> dict:
        """Iniciar grabación MixMonitor en un canal."""
        ami = None
        try:
            ami = _ami_connect()
            ami._send_command(
                f"Action: MixMonitor\r\n"
                f"Channel: {channel}\r\n"
                f"File: {filename}.wav\r\n"
                f"Options: ab\r\n\r\n"   # a=append, b=beep
            )
            response = ami._read_response()
            success = 'Success' in response or 'Response: Success' in response
            logger.info(f"[Recording] Iniciada en canal={channel} archivo={filename}")
            return {'success': success}
        except Exception as e:
            logger.error(f"[Recording] Error iniciando en {channel}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if ami:
                ami.disconnect()

    @staticmethod
    def stop_recording(channel: str) -> dict:
        """Detener grabación MixMonitor en un canal."""
        ami = None
        try:
            ami = _ami_connect()
            ami._send_command(
                f"Action: StopMixMonitor\r\n"
                f"Channel: {channel}\r\n\r\n"
            )
            response = ami._read_response()
            success = 'Success' in response
            logger.info(f"[Recording] Detenida en canal={channel}")
            return {'success': success}
        except Exception as e:
            logger.error(f"[Recording] Error deteniendo en {channel}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if ami:
                ami.disconnect()


class TelephonyService:
    """Alias y helpers de alto nivel usados en viewsets."""

    @staticmethod
    def hangup_call(channel: str) -> dict:
        return CallService.hangup_call(channel)

    @staticmethod
    def originate_call(agent_extension: str, destination: str, **kwargs) -> dict:
        return CallService.originate_call(agent_extension, destination, **kwargs)

    @staticmethod
    def transfer_call(channel: str, extension: str) -> dict:
        return CallService.transfer_call(channel, extension)


class QueueService:
    """Servicio para gestionar miembros de colas ACD via Asterisk AMI."""

    @staticmethod
    def add_agent_to_queue(
        queue_name: str,
        agent_extension: str,
        agent_name: str = None,
        penalty: int = 0,
    ) -> dict:
        """Agregar un agente a una cola ACD."""
        ami = None
        try:
            ami = _ami_connect()
            ami._send_command(
                f"Action: QueueAdd\r\n"
                f"Queue: {queue_name}\r\n"
                f"Interface: PJSIP/{agent_extension}\r\n"
                f"Penalty: {penalty}\r\n"
                f"MemberName: {agent_name or 'Agent ' + agent_extension}\r\n\r\n"
            )
            response = ami._read_response()
            success = 'Success' in response
            logger.info(
                f"[Queue] Agente {agent_extension} añadido a {queue_name} success={success}"
            )
            return {'success': success}
        except Exception as e:
            logger.error(f"[Queue] Error añadiendo {agent_extension} a {queue_name}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if ami:
                ami.disconnect()

    @staticmethod
    def remove_agent_from_queue(queue_name: str, agent_extension: str) -> dict:
        """Retirar un agente de una cola ACD."""
        ami = None
        try:
            ami = _ami_connect()
            ami._send_command(
                f"Action: QueueRemove\r\n"
                f"Queue: {queue_name}\r\n"
                f"Interface: PJSIP/{agent_extension}\r\n\r\n"
            )
            response = ami._read_response()
            success = 'Success' in response
            logger.info(
                f"[Queue] Agente {agent_extension} retirado de {queue_name} success={success}"
            )
            return {'success': success}
        except Exception as e:
            logger.error(f"[Queue] Error retirando {agent_extension} de {queue_name}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if ami:
                ami.disconnect()

    @staticmethod
    def pause_agent(
        queue_name: str,
        agent_extension: str,
        paused: bool = True,
        reason: str = None,
    ) -> dict:
        """Pausar o despausar un agente en una cola."""
        ami = None
        try:
            ami = _ami_connect()
            cmd = (
                f"Action: QueuePause\r\n"
                f"Queue: {queue_name}\r\n"
                f"Interface: PJSIP/{agent_extension}\r\n"
                f"Paused: {'true' if paused else 'false'}\r\n"
            )
            if reason:
                cmd += f"Reason: {reason}\r\n"
            cmd += "\r\n"
            ami._send_command(cmd)
            response = ami._read_response()
            success = 'Success' in response
            action = "pausado" if paused else "despausado"
            logger.info(
                f"[Queue] Agente {agent_extension} {action} en {queue_name} success={success}"
            )
            return {'success': success}
        except Exception as e:
            logger.error(f"[Queue] Error pausando {agent_extension}: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if ami:
                ami.disconnect()

    @staticmethod
    def get_queue_status(queue_name: str = None) -> dict:
        """Obtener estado de cola(s) via AMI QueueStatus."""
        ami = None
        try:
            ami = _ami_connect()
            cmd = "Action: QueueStatus\r\n"
            if queue_name:
                cmd += f"Queue: {queue_name}\r\n"
            cmd += "\r\n"
            ami._send_command(cmd)
            response = ami._read_command_response(timeout=5)
            return {'success': True, 'data': response[:4000]}
        except Exception as e:
            logger.error(f"[Queue] Error obteniendo status: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if ami:
                ami.disconnect()
