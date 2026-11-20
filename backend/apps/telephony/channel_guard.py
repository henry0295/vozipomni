"""
Comprobación de que un agente solo actúa sobre canales de su propia llamada.

Las funciones reciben la lista de canales de `AsteriskAMI.core_show_channels()`
(dicts con Channel, Uniqueid, Linkedid, CallerIDNum, …) y no abren conexiones.

Un agente tiene dos formatos de canal:
- teléfono SIP registrado directamente: PJSIP/<ext>-XXXXXXXX
- softphone WebRTC, que entra por Kamailio y Asterisk identifica por IP como
  `kamailio-endpoint`: PJSIP/kamailio-endpoint-XXXXXXXX con la extensión en
  CallerIDNum. Ese endpoint usa trust_id_inbound=yes y Kamailio fija la
  identidad del agente autenticado, así que CallerIDNum es fiable ahí.
"""
from typing import List, Optional

KAMAILIO_CHANNEL_PREFIX = 'PJSIP/kamailio-endpoint-'


def agent_channels(agent, channels: List[dict]) -> List[dict]:
    """Canales que pertenecen al agente (su teléfono o su softphone WebRTC)."""
    ext = getattr(agent, 'sip_extension', None)
    if not ext:
        return []
    own_prefix = f'PJSIP/{ext}-'
    return [
        c for c in channels
        if c.get('Channel', '').startswith(own_prefix)
        or (c.get('Channel', '').startswith(KAMAILIO_CHANNEL_PREFIX)
            and c.get('CallerIDNum') == ext)
    ]


def linkedid_for_agent(agent, channels: List[dict]) -> Optional[str]:
    """Linkedid de la llamada en curso del agente, o None si no tiene ninguna."""
    for c in agent_channels(agent, channels):
        if c.get('Linkedid'):
            return c['Linkedid']
    return None


def channels_in_linkedid(linkedid: str, channels: List[dict]) -> List[dict]:
    """Todos los canales que forman parte de la llamada `linkedid`."""
    if not linkedid:
        return []
    return [c for c in channels if c.get('Linkedid') == linkedid]


def agent_owns_channel(agent, channel_name: str, channels: List[dict]) -> bool:
    """True si `channel_name` pertenece a una de las llamadas del agente."""
    if not channel_name:
        return False
    linkedids = {c['Linkedid'] for c in agent_channels(agent, channels) if c.get('Linkedid')}
    if not linkedids:
        return False
    return any(
        c.get('Channel') == channel_name and c.get('Linkedid') in linkedids
        for c in channels
    )
