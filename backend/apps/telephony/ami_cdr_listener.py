"""
AMI Event Listener — Servicio persistente que escucha TODOS los eventos
relevantes de Asterisk vía AMI para un Contact Center completo.

Eventos capturados:
  CDR:       Cdr (fin de llamada con detalle)
  Cola:      QueueCallerJoin, QueueCallerAbandon, QueueCallerLeave,
             AgentConnect, AgentComplete, AgentRingNoAnswer
  Hold:      Hold, Unhold
  Transfer:  BlindTransfer, AttendedTransfer
  Voicemail: VoicemailUserEntry
  Agentes:   QueueMemberStatus, QueueMemberPause, QueueMemberAdded,
             QueueMemberRemoved, AgentLogin, AgentLogoff

Se ejecuta como hilo daemon dentro del worker Celery.
"""
import os
import re
import socket
import time
import logging
import threading
from collections import defaultdict
from datetime import datetime, timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────────────────────────
AMI_HOST = os.environ.get('ASTERISK_HOST', 'asterisk')
AMI_PORT = int(os.environ.get('ASTERISK_AMI_PORT', '5038'))
AMI_USER = os.environ.get('ASTERISK_AMI_USER', 'admin')
AMI_SECRET = os.environ.get('ASTERISK_AMI_PASSWORD', 'vozipomni_ami_2026')

RECONNECT_DELAY = 5
MAX_RECONNECT_DELAY = 60
PING_INTERVAL = 30

_listener_thread = None
_stop_event = threading.Event()

# ─────────────────────────────────────────────────────────────────
# Estado en memoria para correlacionar eventos por canal/uniqueid
# ─────────────────────────────────────────────────────────────────
# Estructura: { uniqueid: { campo: valor, ... } }
_call_state: dict[str, dict] = {}
_call_state_lock = threading.Lock()

# Limpieza de estados viejos (>2h) para evitar memory leak
_STATE_TTL = 7200  # 2 horas en segundos


def _cleanup_stale_state():
    """Elimina estados de llamadas que llevan más de _STATE_TTL sin actualización."""
    now = time.time()
    with _call_state_lock:
        stale = [uid for uid, s in _call_state.items()
                 if now - s.get('_ts', 0) > _STATE_TTL]
        for uid in stale:
            del _call_state[uid]
        if stale:
            logger.debug(f"[AMI] Limpiados {len(stale)} estados de llamada stale")


def _get_state(uniqueid: str) -> dict:
    """Obtiene o crea el estado en memoria de una llamada."""
    with _call_state_lock:
        if uniqueid not in _call_state:
            _call_state[uniqueid] = {'_ts': time.time()}
        else:
            _call_state[uniqueid]['_ts'] = time.time()
        return _call_state[uniqueid]


def _pop_state(uniqueid: str) -> dict:
    """Obtiene y elimina el estado en memoria de una llamada."""
    with _call_state_lock:
        return _call_state.pop(uniqueid, {})


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def _parse_ami_event(raw: str) -> dict:
    """Convierte un bloque AMI (líneas 'Key: Value') en un dict."""
    data = {}
    for line in raw.strip().splitlines():
        if ':' in line:
            key, _, value = line.partition(':')
            data[key.strip()] = value.strip()
    return data


def _ami_login(sock: socket.socket) -> bool:
    """Autenticación AMI con suscripción a TODOS los eventos necesarios."""
    _read_until_blank(sock)
    # Events: system,call,agent,cdr,dialplan,dtmf — cubrir todo lo relevante
    cmd = (
        f"Action: Login\r\n"
        f"Username: {AMI_USER}\r\n"
        f"Secret: {AMI_SECRET}\r\n"
        f"Events: system,call,agent,cdr,dialplan\r\n"
        f"\r\n"
    )
    sock.sendall(cmd.encode())
    resp = _read_until_blank(sock)
    return 'Success' in resp


def _read_until_blank(sock: socket.socket, timeout: float = 10.0) -> str:
    """Lee del socket hasta encontrar \\r\\n\\r\\n o timeout."""
    sock.settimeout(timeout)
    buf = b''
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
            if b'\r\n\r\n' in buf:
                break
        except socket.timeout:
            break
    return buf.decode('utf-8', errors='ignore')


def _determine_direction(src: str, dst: str, channel: str, dcontext: str) -> str:
    """Determina si la llamada es inbound u outbound."""
    if dcontext in ('from-pstn', 'from-trunk', 'from-external'):
        return 'inbound'
    if dcontext in ('from-internal', 'outbound', 'to-pstn'):
        return 'outbound'
    if channel and 'PJSIP/' in channel.upper():
        if len(src) > 5 and len(dst) <= 5:
            return 'inbound'
    return 'outbound'


def _map_disposition(disposition: str) -> str:
    """Mapea disposición Asterisk a estado del modelo Call."""
    d = disposition.upper()
    mapping = {
        'ANSWERED': 'completed',
        'NO ANSWER': 'no_answer',
        'BUSY': 'busy',
        'FAILED': 'failed',
        'CONGESTION': 'failed',
    }
    return mapping.get(d, 'completed')


def _parse_datetime(date_str: str):
    """Parsea fecha de CDR de Asterisk."""
    if not date_str:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return timezone.make_aware(datetime.strptime(date_str, fmt))
        except (ValueError, TypeError):
            continue
    return None


def _extract_extension(channel: str) -> str | None:
    """Extrae número de extensión de un canal PJSIP/1001-xxxxx."""
    if not channel:
        return None
    m = re.match(r'PJSIP/(\d+)-', channel)
    return m.group(1) if m else None


def _find_agent_by_extension(ext: str):
    """Busca un Agent por extensión SIP."""
    if not ext:
        return None
    from apps.agents.models import Agent
    try:
        return Agent.objects.get(sip_extension=ext)
    except Agent.DoesNotExist:
        return None


def _find_queue_by_name(queue_name: str):
    """Busca una Queue por nombre."""
    if not queue_name:
        return None
    from apps.queues.models import Queue
    try:
        return Queue.objects.get(name=queue_name)
    except Queue.DoesNotExist:
        # Intentar por extensión
        try:
            return Queue.objects.get(extension=queue_name)
        except Queue.DoesNotExist:
            return None


def _update_agent_status(agent, new_status: str, save_history: bool = True):
    """
    Actualiza el estado de un agente y crea registro de historial.
    Cierra el registro anterior de AgentStatusHistory.
    """
    from apps.agents.models import Agent, AgentStatusHistory

    old_status = agent.status
    if old_status == new_status:
        return

    now = timezone.now()

    # Cerrar registro de historial anterior
    if save_history:
        prev_record = AgentStatusHistory.objects.filter(
            agent=agent, ended_at__isnull=True
        ).first()
        if prev_record:
            prev_record.ended_at = now
            prev_record.duration = int(
                (now - prev_record.started_at).total_seconds()
            )
            prev_record.save(update_fields=['ended_at', 'duration'])

            # Acumular tiempo en métricas diarias
            if old_status == 'available':
                agent.available_time_today += prev_record.duration
            elif old_status == 'break':
                agent.break_time_today += prev_record.duration
            elif old_status in ('oncall', 'busy'):
                agent.oncall_time_today += prev_record.duration
            elif old_status == 'wrapup':
                agent.wrapup_time_today += prev_record.duration

        # Crear nuevo registro de historial
        AgentStatusHistory.objects.create(
            agent=agent,
            status=new_status,
            started_at=now,
        )

    agent.status = new_status
    agent.save(update_fields=[
        'status', 'available_time_today', 'break_time_today',
        'oncall_time_today', 'wrapup_time_today',
    ])

    logger.info(f"[AMI] Agente {agent.sip_extension}: {old_status} → {new_status}")


def _update_queue_stats(queue, **kwargs):
    """Actualiza las estadísticas en tiempo real de una cola."""
    from apps.queues.models import QueueStats

    stats, _ = QueueStats.objects.get_or_create(queue=queue)
    for field, value in kwargs.items():
        if hasattr(stats, field):
            if isinstance(value, int) and field.startswith('calls_'):
                # Incrementar contadores
                setattr(stats, field, getattr(stats, field, 0) + value)
            else:
                setattr(stats, field, value)
    stats.save()


# ─────────────────────────────────────────────────────────────────
# Procesadores de eventos
# ─────────────────────────────────────────────────────────────────

def _process_cdr_event(event: dict):
    """Crea/actualiza un registro Call a partir de un evento CDR de AMI."""
    from apps.telephony.models import Call
    from apps.agents.models import Agent
    from apps.recordings.models import Recording

    unique_id = event.get('UniqueID', '') or event.get('Uniqueid', '')
    src = event.get('Source', '') or event.get('CallerID', '')
    dst = event.get('Destination', '') or event.get('CallerIDNum', '')
    channel = event.get('Channel', '')
    dcontext = event.get('DestinationContext', '') or event.get('Context', '')
    disposition = event.get('Disposition', 'ANSWERED')
    duration = int(event.get('Duration', 0) or 0)
    billsec = int(event.get('BillableSeconds', 0) or event.get('Billsec', 0) or 0)
    start_str = event.get('StartTime', '') or event.get('Start', '')
    answer_str = event.get('AnswerTime', '') or event.get('Answer', '')
    end_str = event.get('EndTime', '') or event.get('End', '')

    if not unique_id:
        logger.warning("[CDR] Evento sin UniqueID, ignorado")
        return

    call_id = f"ast-{unique_id}"
    direction = _determine_direction(src, dst, channel, dcontext)

    # Recuperar estado acumulado durante la vida de la llamada
    state = _pop_state(unique_id)

    # Si fue marcado como voicemail, abandoned o transferred usar ese estado
    call_status = state.get('final_status') or _map_disposition(disposition)

    start_time = _parse_datetime(start_str) or timezone.now()
    answer_time = _parse_datetime(answer_str)
    end_time = _parse_datetime(end_str) or (start_time + timedelta(seconds=duration))

    wait_time = 0
    if answer_time and start_time:
        wait_time = max(0, int((answer_time - start_time).total_seconds()))

    # Si tenemos queue_enter_time del evento QueueCallerJoin, usarla
    queue_enter = state.get('queue_enter_time')
    if queue_enter and answer_time:
        wait_time = max(0, int((answer_time - queue_enter).total_seconds()))
    elif queue_enter and not answer_time:
        # Llamada no contestada en cola — el wait_time es hasta end_time
        wait_time = max(0, int((end_time - queue_enter).total_seconds()))

    # Hold time acumulado de eventos Hold/Unhold
    hold_time = state.get('hold_time', 0)

    # Buscar agente — primero del estado, luego del canal
    agent = state.get('agent')
    if not agent:
        dst_channel = event.get('DestinationChannel', '')
        ext = _extract_extension(dst_channel or channel)
        agent = _find_agent_by_extension(ext)

    # Queue del estado en memoria
    queue = state.get('queue')

    # Transfer info del estado
    transferred = state.get('transferred', False)
    transfer_to = state.get('transfer_to', '')

    dst_channel = event.get('DestinationChannel', '')

    defaults = {
        'direction': direction,
        'status': call_status,
        'caller_id': src or 'unknown',
        'called_number': dst or 'unknown',
        'channel': channel,
        'unique_id': unique_id,
        'start_time': start_time,
        'answer_time': answer_time,
        'end_time': end_time,
        'wait_time': wait_time,
        'talk_time': billsec,
        'hold_time': hold_time,
        'agent': agent,
        'queue': queue,
        'transferred': transferred,
        'transfer_to': transfer_to,
        'queue_enter_time': queue_enter,
        'metadata': {
            'ami_channel': channel,
            'ami_dst_channel': dst_channel,
            'ami_context': dcontext,
            'ami_disposition': disposition,
            'ami_duration': duration,
            'ami_accountcode': event.get('AccountCode', ''),
            'queue_name': state.get('queue_name', ''),
            'hold_events': state.get('hold_events', 0),
            'ring_no_answer_count': state.get('ring_no_answer_count', 0),
        },
    }

    call, created = Call.objects.update_or_create(
        call_id=call_id,
        defaults=defaults,
    )

    action_name = "CREADO" if created else "ACTUALIZADO"
    logger.info(
        f"[CDR] {action_name} Call {call.id}: {call_id}  "
        f"{src} → {dst}  {direction}  {call_status}  "
        f"dur={duration}s  bill={billsec}s  hold={hold_time}s  "
        f"queue={state.get('queue_name', '-')}  transferred={transferred}"
    )

    # Actualizar métricas del agente
    if agent and call_status == 'completed':
        agent.calls_today += 1
        agent.talk_time_today += billsec
        agent.last_call_time = timezone.now()
        agent.save(update_fields=['calls_today', 'talk_time_today', 'last_call_time'])

    # Buscar grabación asociada
    _link_recording(call, event)

    return call


def _process_queue_caller_join(event: dict):
    """
    Evento: QueueCallerJoin — Un llamante entra a la cola.
    Campos: Channel, CallerIDNum, CallerIDName, Queue, Position, Count, Uniqueid.
    """
    uniqueid = event.get('Uniqueid', '')
    queue_name = event.get('Queue', '')
    caller = event.get('CallerIDNum', '')

    if not uniqueid:
        return

    state = _get_state(uniqueid)
    state['queue_enter_time'] = timezone.now()
    state['queue_name'] = queue_name
    state['queue'] = _find_queue_by_name(queue_name)
    state['caller'] = caller

    logger.info(f"[QUEUE] Llamante {caller} entró a cola '{queue_name}' (pos {event.get('Position', '?')})")

    # Actualizar QueueStats
    queue = state.get('queue')
    if queue:
        _update_queue_stats(queue, calls_waiting=1)


def _process_queue_caller_abandon(event: dict):
    """
    Evento: QueueCallerAbandon — Llamante abandona la cola antes de ser atendido.
    Campos: Channel, Uniqueid, Queue, Position, OriginalPosition, HoldTime.
    """
    uniqueid = event.get('Uniqueid', '')
    queue_name = event.get('Queue', '')
    hold_time = int(event.get('HoldTime', 0) or 0)

    if not uniqueid:
        return

    state = _get_state(uniqueid)
    state['final_status'] = 'abandoned'
    state['queue_name'] = queue_name

    queue = state.get('queue') or _find_queue_by_name(queue_name)
    state['queue'] = queue

    logger.info(f"[QUEUE] Llamada {uniqueid} ABANDONADA en cola '{queue_name}' tras {hold_time}s")

    # Actualizar QueueStats
    if queue:
        from apps.queues.models import QueueStats
        stats, _ = QueueStats.objects.get_or_create(queue=queue)
        stats.calls_abandoned += 1
        stats.calls_waiting = max(0, stats.calls_waiting - 1)
        stats.save(update_fields=['calls_abandoned', 'calls_waiting'])


def _process_queue_caller_leave(event: dict):
    """
    Evento: QueueCallerLeave — Llamante sale de la cola (puede ser por abandon, timeout, o atendida).
    Campos: Channel, Queue, Count, Position, Uniqueid.
    """
    uniqueid = event.get('Uniqueid', '')
    queue_name = event.get('Queue', '')

    if not uniqueid:
        return

    queue = _find_queue_by_name(queue_name)
    if queue:
        from apps.queues.models import QueueStats
        stats, _ = QueueStats.objects.get_or_create(queue=queue)
        stats.calls_waiting = max(0, stats.calls_waiting - 1)
        stats.save(update_fields=['calls_waiting'])

    logger.debug(f"[QUEUE] Llamante salió de cola '{queue_name}'")


def _process_agent_connect(event: dict):
    """
    Evento: AgentConnect — Agente conectó con llamante de la cola.
    Campos: Channel, MemberName, Interface, Queue, Uniqueid, HoldTime, RingTime.
    """
    uniqueid = event.get('Uniqueid', '')
    queue_name = event.get('Queue', '')
    interface = event.get('Interface', '')  # PJSIP/1001
    hold_time_str = event.get('HoldTime', '0')
    ring_time_str = event.get('RingTime', '0')

    if not uniqueid:
        return

    ext = _extract_extension(interface)
    agent = _find_agent_by_extension(ext)

    state = _get_state(uniqueid)
    state['agent'] = agent
    state['queue_name'] = queue_name
    if not state.get('queue'):
        state['queue'] = _find_queue_by_name(queue_name)

    logger.info(
        f"[QUEUE] Agente {ext or interface} conectó con llamada {uniqueid} "
        f"en cola '{queue_name}' (espera={hold_time_str}s ring={ring_time_str}s)"
    )

    # Actualizar estado del agente a 'oncall'
    if agent:
        _update_agent_status(agent, 'oncall')
        agent.current_calls = max(1, agent.current_calls + 1)
        agent.save(update_fields=['current_calls'])

    # Actualizar QueueStats
    queue = state.get('queue')
    if queue:
        from apps.queues.models import QueueStats
        stats, _ = QueueStats.objects.get_or_create(queue=queue)
        stats.calls_completed += 1
        stats.calls_waiting = max(0, stats.calls_waiting - 1)
        stats.save(update_fields=['calls_completed', 'calls_waiting'])


def _process_agent_complete(event: dict):
    """
    Evento: AgentComplete — Llamada de cola completada por el agente.
    Campos: Channel, MemberName, Interface, Queue, Uniqueid, HoldTime, TalkTime, Reason.
    """
    uniqueid = event.get('Uniqueid', '')
    interface = event.get('Interface', '')
    talk_time = int(event.get('TalkTime', 0) or 0)
    reason = event.get('Reason', '')  # caller | agent | transfer

    if not uniqueid:
        return

    ext = _extract_extension(interface)
    agent = _find_agent_by_extension(ext)

    logger.info(
        f"[QUEUE] Agente {ext or interface} completó llamada {uniqueid} "
        f"(talk={talk_time}s reason={reason})"
    )

    # Devolver agente a estado 'available' (o 'wrapup' si hay wrap_up_time)
    if agent:
        agent.current_calls = max(0, agent.current_calls - 1)
        agent.save(update_fields=['current_calls'])

        # Si la cola tiene wrap_up_time configurado, poner en wrapup
        state = _get_state(uniqueid)
        queue = state.get('queue')
        if queue and queue.wrap_up_time > 0:
            _update_agent_status(agent, 'wrapup')
        else:
            if agent.current_calls <= 0:
                _update_agent_status(agent, 'available')

    # Actualizar QueueMember stats
    if ext:
        from apps.queues.models import QueueMember
        queue_name = event.get('Queue', '')
        queue_obj = _find_queue_by_name(queue_name)
        if queue_obj:
            try:
                member = QueueMember.objects.get(
                    queue=queue_obj,
                    agent__sip_extension=ext,
                )
                member.calls_taken += 1
                member.last_call = timezone.now()
                member.save(update_fields=['calls_taken', 'last_call'])
            except QueueMember.DoesNotExist:
                pass


def _process_agent_ring_no_answer(event: dict):
    """
    Evento: AgentRingNoAnswer — Agente no contestó llamada de cola (ring timeout).
    Campos: Channel, MemberName, Interface, Queue, Uniqueid, RingTime.
    """
    uniqueid = event.get('Uniqueid', '')
    interface = event.get('Interface', '')
    ring_time = event.get('RingTime', '0')

    ext = _extract_extension(interface)

    logger.info(f"[QUEUE] Agente {ext or interface} NO contestó — ring {ring_time}s")

    if uniqueid:
        state = _get_state(uniqueid)
        state['ring_no_answer_count'] = state.get('ring_no_answer_count', 0) + 1


def _process_hold(event: dict):
    """
    Evento: Hold — Canal puesto en espera.
    Campos: Channel, Uniqueid, MusicClass.
    """
    uniqueid = event.get('Uniqueid', '')
    if not uniqueid:
        return

    state = _get_state(uniqueid)
    state['hold_start'] = time.time()
    state['hold_events'] = state.get('hold_events', 0) + 1

    logger.debug(f"[HOLD] Llamada {uniqueid} puesta en espera")


def _process_unhold(event: dict):
    """
    Evento: Unhold — Canal sacado de espera.
    Campos: Channel, Uniqueid.
    """
    uniqueid = event.get('Uniqueid', '')
    if not uniqueid:
        return

    state = _get_state(uniqueid)
    hold_start = state.pop('hold_start', None)
    if hold_start:
        elapsed = int(time.time() - hold_start)
        state['hold_time'] = state.get('hold_time', 0) + elapsed
        logger.debug(f"[HOLD] Llamada {uniqueid} sacada de espera ({elapsed}s)")


def _process_blind_transfer(event: dict):
    """
    Evento: BlindTransfer — Transferencia ciega.
    Campos: TransfererChannel, TransfererUniqueid, TransfereeChannel,
            TransfereeUniqueid, Extension, Context, Result.
    """
    uniqueid = event.get('TransfererUniqueid', '') or event.get('Uniqueid', '')
    extension = event.get('Extension', '')
    result = event.get('Result', '')

    if not uniqueid:
        return

    state = _get_state(uniqueid)
    if result == 'Success':
        state['transferred'] = True
        state['transfer_to'] = extension
        state['final_status'] = 'transferred'
        logger.info(f"[TRANSFER] Transferencia ciega {uniqueid} → ext {extension}")
    else:
        logger.warning(f"[TRANSFER] Transferencia ciega fallida {uniqueid}: {result}")


def _process_attended_transfer(event: dict):
    """
    Evento: AttendedTransfer — Transferencia asistida.
    Campos: OrigTransfererChannel, OrigTransfererUniqueid,
            SecondTransfererChannel, TransfereeChannel, Result, DestExten.
    """
    uniqueid = event.get('OrigTransfererUniqueid', '') or event.get('Uniqueid', '')
    dest_exten = event.get('DestExten', '') or event.get('Extension', '')
    result = event.get('Result', '')

    if not uniqueid:
        return

    state = _get_state(uniqueid)
    if result == 'Success':
        state['transferred'] = True
        state['transfer_to'] = dest_exten
        state['final_status'] = 'transferred'
        logger.info(f"[TRANSFER] Transferencia asistida {uniqueid} → {dest_exten}")


def _process_voicemail_entry(event: dict):
    """
    Evento: VoicemailUserEntry — Llamante dejó un mensaje de voz.
    Campos: Channel, Uniqueid, VMContext, VMBox.
    """
    uniqueid = event.get('Uniqueid', '')
    vm_box = event.get('VMBox', '') or event.get('Mailbox', '')

    if not uniqueid:
        return

    state = _get_state(uniqueid)
    state['final_status'] = 'voicemail'
    state['voicemail_box'] = vm_box

    logger.info(f"[VOICEMAIL] Llamada {uniqueid} entró a buzón {vm_box}")


def _process_queue_member_status(event: dict):
    """
    Evento: QueueMemberStatus — Cambio de estado de un miembro de cola.
    Campos: Queue, MemberName, Interface, Status, Paused, PausedReason.
    Status: 1=not in use, 2=in use, 3=busy, 5=unavailable, 6=ringing, 7=ring+in use, 8=on hold.
    """
    interface = event.get('Interface', '')
    status_code = event.get('Status', '')
    queue_name = event.get('Queue', '')

    ext = _extract_extension(interface)
    if not ext:
        return

    agent = _find_agent_by_extension(ext)
    if not agent:
        return

    # Mapear códigos de estado de QueueMember a estados del agente
    status_map = {
        '1': 'available',    # Not in use
        '2': 'oncall',       # In use
        '3': 'busy',         # Busy
        '5': 'offline',      # Unavailable
        '6': 'oncall',       # Ringing (marcamos como oncall ya que está recibiendo llamada)
        '7': 'oncall',       # Ring+InUse
        '8': 'oncall',       # On Hold (sigue en llamada)
    }

    new_status = status_map.get(str(status_code))
    if new_status:
        _update_agent_status(agent, new_status)

    logger.debug(
        f"[QUEUE] MemberStatus: {ext} en cola '{queue_name}' → status_code={status_code}"
    )


def _process_queue_member_pause(event: dict):
    """
    Evento: QueueMemberPause — Agente puesto en pausa/despausa en cola.
    Campos: Queue, MemberName, Interface, Paused, PausedReason, Reason.
    """
    interface = event.get('Interface', '')
    paused = event.get('Paused', '0')
    reason = event.get('PausedReason', '') or event.get('Reason', '')

    ext = _extract_extension(interface)
    if not ext:
        return

    agent = _find_agent_by_extension(ext)
    if not agent:
        return

    if paused == '1':
        _update_agent_status(agent, 'break')
        logger.info(f"[QUEUE] Agente {ext} EN PAUSA: {reason or 'sin razón'}")
    else:
        _update_agent_status(agent, 'available')
        logger.info(f"[QUEUE] Agente {ext} DESPAUSADO")

    # Actualizar QueueMember.paused
    from apps.queues.models import QueueMember
    queue_name = event.get('Queue', '')
    queue = _find_queue_by_name(queue_name)
    if queue:
        QueueMember.objects.filter(
            queue=queue, agent__sip_extension=ext
        ).update(paused=(paused == '1'))


def _process_agent_login_logoff(event: dict, is_login: bool):
    """Procesa AgentLogin / AgentLogoff."""
    interface = event.get('Interface', '') or event.get('Channel', '')
    ext = _extract_extension(interface)
    agent = _find_agent_by_extension(ext)

    if not agent:
        return

    if is_login:
        agent.logged_in_at = timezone.now()
        _update_agent_status(agent, 'available')
        logger.info(f"[AGENT] Login: {ext}")
    else:
        _update_agent_status(agent, 'offline')
        agent.logged_in_at = None
        agent.current_calls = 0
        agent.save(update_fields=['logged_in_at', 'current_calls'])
        logger.info(f"[AGENT] Logoff: {ext}")


# ─────────────────────────────────────────────────────────────────
# Grabaciones
# ─────────────────────────────────────────────────────────────────

def _link_recording(call, event: dict):
    """Busca archivo de grabación y crea el registro Recording si existe."""
    from apps.recordings.models import Recording

    unique_id = call.unique_id or ''
    recording_dirs = [
        '/var/spool/asterisk/monitor',
        '/app/recordings',
    ]

    found_path = ''
    for rdir in recording_dirs:
        if not os.path.isdir(rdir):
            continue
        for fname in os.listdir(rdir):
            if unique_id in fname or call.call_id.replace('ast-', '') in fname:
                candidate = os.path.join(rdir, fname)
                size = os.path.getsize(candidate)
                if size > 100:
                    found_path = candidate
                    break
        if found_path:
            break

    if found_path:
        file_size = os.path.getsize(found_path)
        filename = os.path.basename(found_path)

        Recording.objects.update_or_create(
            call=call,
            defaults={
                'filename': filename,
                'file_path': found_path,
                'file_size': file_size,
                'duration': call.talk_time or 0,
                'format': filename.rsplit('.', 1)[-1] if '.' in filename else 'wav',
                'status': 'completed',
                'agent': call.agent,
            },
        )
        call.recording_file = found_path
        call.is_recorded = True
        call.save(update_fields=['recording_file', 'is_recorded'])
        logger.info(f"[CDR] Grabación vinculada: {filename} ({file_size} bytes)")


# ─────────────────────────────────────────────────────────────────
# Dispatcher de eventos
# ─────────────────────────────────────────────────────────────────

# Mapa de eventos → funciones handler
_EVENT_HANDLERS = {
    'Cdr':                  _process_cdr_event,
    'QueueCallerJoin':      _process_queue_caller_join,
    'QueueCallerAbandon':   _process_queue_caller_abandon,
    'QueueCallerLeave':     _process_queue_caller_leave,
    'AgentConnect':         _process_agent_connect,
    'AgentComplete':        _process_agent_complete,
    'AgentRingNoAnswer':    _process_agent_ring_no_answer,
    'Hold':                 _process_hold,
    'Unhold':               _process_unhold,
    'BlindTransfer':        _process_blind_transfer,
    'AttendedTransfer':     _process_attended_transfer,
    'VoicemailUserEntry':   _process_voicemail_entry,
    'QueueMemberStatus':    _process_queue_member_status,
    'QueueMemberPause':     _process_queue_member_pause,
    'QueueMemberPaused':    _process_queue_member_pause,  # alias
}


# ─────────────────────────────────────────────────────────────────
# Loop principal del listener
# ─────────────────────────────────────────────────────────────────

def _listener_loop():
    """Loop principal: conecta, escucha TODOS los eventos, reconecta en fallo."""
    delay = RECONNECT_DELAY
    last_cleanup = time.time()

    while not _stop_event.is_set():
        sock = None
        try:
            logger.info(f"[AMI Listener] Conectando a AMI {AMI_HOST}:{AMI_PORT}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((AMI_HOST, AMI_PORT))

            if not _ami_login(sock):
                logger.error("[AMI Listener] Login AMI fallido")
                raise ConnectionError("Login AMI fallido")

            logger.info(
                "[AMI Listener] ✓ Conectado a AMI — escuchando eventos: "
                "CDR, Queue, Hold, Transfer, Voicemail, Agent"
            )
            delay = RECONNECT_DELAY

            sock.settimeout(PING_INTERVAL + 5)
            buffer = ''
            last_ping = time.time()

            while not _stop_event.is_set():
                now = time.time()

                # Keepalive
                if now - last_ping > PING_INTERVAL:
                    try:
                        sock.sendall(b"Action: Ping\r\n\r\n")
                        last_ping = now
                    except Exception:
                        break

                # Limpieza periódica de estados stale
                if now - last_cleanup > 600:  # cada 10 min
                    _cleanup_stale_state()
                    last_cleanup = now

                try:
                    data = sock.recv(4096)
                    if not data:
                        logger.warning("[AMI Listener] Socket cerrado por Asterisk")
                        break
                    buffer += data.decode('utf-8', errors='ignore')
                except socket.timeout:
                    continue

                # Procesar eventos completos
                while '\r\n\r\n' in buffer:
                    event_raw, _, buffer = buffer.partition('\r\n\r\n')
                    event = _parse_ami_event(event_raw)
                    event_type = event.get('Event', '')

                    # Despachar al handler correspondiente
                    handler = _EVENT_HANDLERS.get(event_type)
                    if handler:
                        try:
                            handler(event)
                        except Exception as e:
                            logger.error(
                                f"[AMI Listener] Error procesando {event_type}: {e}",
                                exc_info=True,
                            )

                    # Eventos especiales sin handler dedicado
                    elif event_type == 'AgentLogin':
                        try:
                            _process_agent_login_logoff(event, is_login=True)
                        except Exception as e:
                            logger.error(f"[AMI] Error AgentLogin: {e}")
                    elif event_type == 'AgentLogoff':
                        try:
                            _process_agent_login_logoff(event, is_login=False)
                        except Exception as e:
                            logger.error(f"[AMI] Error AgentLogoff: {e}")

        except Exception as e:
            logger.error(f"[AMI Listener] Error: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

        if not _stop_event.is_set():
            logger.info(f"[AMI Listener] Reconectando en {delay}s...")
            _stop_event.wait(delay)
            delay = min(delay * 2, MAX_RECONNECT_DELAY)


# ─────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────

def start_listener():
    """Arranca el listener en un hilo daemon (idempotente)."""
    global _listener_thread

    if _listener_thread and _listener_thread.is_alive():
        logger.info("[AMI Listener] Ya está ejecutándose")
        return

    _stop_event.clear()
    _listener_thread = threading.Thread(
        target=_listener_loop,
        name='ami-event-listener',
        daemon=True,
    )
    _listener_thread.start()
    logger.info("[AMI Listener] Hilo iniciado")


def stop_listener():
    """Detiene el listener de forma limpia."""
    global _listener_thread
    _stop_event.set()
    if _listener_thread:
        _listener_thread.join(timeout=10)
        _listener_thread = None
    logger.info("[AMI Listener] Detenido")


def is_running() -> bool:
    """Verifica si el listener está corriendo."""
    return _listener_thread is not None and _listener_thread.is_alive()
