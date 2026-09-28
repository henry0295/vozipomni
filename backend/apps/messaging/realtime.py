"""
Notificaciones en tiempo real de mensajería (Django Channels).

Grupos:
  messaging_all              → administradores y supervisores (bandeja omnicanal)
  messaging_agent_<agent_id> → agente asignado a la conversación
  messaging_unassigned       → agentes (para tomar conversaciones sin asignar)
"""
import logging

from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def push(conversation, event: str, payload: dict | None = None, also_agents=None, also_unassigned=False):
    """
    also_agents: ids de agentes adicionales a notificar (ej: el agente anterior
    en una reasignación, para que la conversación desaparezca de su bandeja).
    also_unassigned: avisar también al grupo de sin asignar (ej: alguien tomó
    la conversación y debe desaparecer de la cola de los demás agentes).
    """
    try:
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer is None:
            return
        data = {
            'event': event,
            'conversation_id': conversation.id,
            'agent_id': conversation.agent_id,
            'status': conversation.status,
            **(payload or {}),
        }
        message = {'type': 'messaging_event', 'payload': data}
        send = async_to_sync(layer.group_send)
        send('messaging_all', message)
        if conversation.agent_id:
            send(f'messaging_agent_{conversation.agent_id}', message)
        else:
            send('messaging_unassigned', message)
        if also_unassigned and conversation.agent_id:
            send('messaging_unassigned', message)
        for agent_id in set(also_agents or []):
            if agent_id and agent_id != conversation.agent_id:
                send(f'messaging_agent_{agent_id}', message)
    except Exception as e:
        logger.debug(f"[Messaging WS] No se pudo notificar {event}: {e}")
