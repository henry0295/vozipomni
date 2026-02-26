"""
AMI CDR Listener — Servicio persistente que escucha eventos CDR de Asterisk
vía AMI y crea registros Call + Recording en la base de datos.

Se ejecuta como tarea Celery de larga duración (o hilo dentro del worker).
Captura TODOS los eventos Cdr emitidos por cdr_manager.so.
"""
import os
import re
import socket
import time
import logging
import threading
from datetime import datetime, timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

# Configuración AMI desde variables de entorno (con defaults seguros)
AMI_HOST = os.environ.get('ASTERISK_HOST', 'asterisk')
AMI_PORT = int(os.environ.get('ASTERISK_AMI_PORT', '5038'))
AMI_USER = os.environ.get('ASTERISK_AMI_USER', 'admin')
AMI_SECRET = os.environ.get('ASTERISK_AMI_PASSWORD', 'vozipomni_ami_2026')

# Reconexión
RECONNECT_DELAY = 5        # segundos entre reintentos
MAX_RECONNECT_DELAY = 60   # máximo backoff
PING_INTERVAL = 30         # keepalive cada 30 s

_listener_thread = None
_stop_event = threading.Event()


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
    """Autenticación AMI; devuelve True si fue exitosa."""
    # Leer banner
    _read_until_blank(sock)
    cmd = (
        f"Action: Login\r\n"
        f"Username: {AMI_USER}\r\n"
        f"Secret: {AMI_SECRET}\r\n"
        f"Events: cdr,call\r\n"
        f"\r\n"
    )
    sock.sendall(cmd.encode())
    resp = _read_until_blank(sock)
    return 'Success' in resp


def _read_until_blank(sock: socket.socket, timeout: float = 10.0) -> str:
    """Lee del socket hasta encontrar \r\n\r\n o timeout."""
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
    # Llamadas desde PSTN / troncal
    if dcontext in ('from-pstn', 'from-trunk', 'from-external'):
        return 'inbound'
    # Llamadas internas hacia afuera
    if dcontext in ('from-internal', 'outbound', 'to-pstn'):
        return 'outbound'
    # Heurística: si el canal contiene PJSIP/ y el destino es numérico corto → inbound
    if channel and 'PJSIP/' in channel.upper():
        trunk_match = re.match(r'PJSIP/(.+?)-', channel)
        if trunk_match:
            trunk_name = trunk_match.group(1)
            # Si src es externo (largo) y dst es ext corta → inbound
            if len(src) > 5 and len(dst) <= 5:
                return 'inbound'
    # Default: outbound
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


def _parse_datetime(date_str: str) -> datetime | None:
    """Parsea fecha de CDR de Asterisk."""
    if not date_str:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return timezone.make_aware(datetime.strptime(date_str, fmt))
        except (ValueError, TypeError):
            continue
    return None


# ─────────────────────────────────────────────────────────────────
# Procesamiento del evento CDR
# ─────────────────────────────────────────────────────────────────

def _process_cdr_event(event: dict):
    """Crea/actualiza un registro Call a partir de un evento CDR de AMI."""
    # Importar aquí para evitar AppNotReady
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
    call_status = _map_disposition(disposition)

    start_time = _parse_datetime(start_str) or timezone.now()
    answer_time = _parse_datetime(answer_str)
    end_time = _parse_datetime(end_str) or (start_time + timedelta(seconds=duration))

    wait_time = 0
    if answer_time and start_time:
        wait_time = max(0, int((answer_time - start_time).total_seconds()))

    # Buscar agente asociado
    agent = None
    dst_channel = event.get('DestinationChannel', '')
    # Extraer extensión del canal PJSIP/1001-xxxxx
    ext_match = re.match(r'PJSIP/(\d+)-', dst_channel or channel)
    if ext_match:
        ext_num = ext_match.group(1)
        try:
            agent = Agent.objects.get(sip_extension=ext_num)
        except Agent.DoesNotExist:
            pass

    # Crear o actualizar la llamada
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
        'agent': agent,
        'metadata': {
            'ami_channel': channel,
            'ami_dst_channel': dst_channel,
            'ami_context': dcontext,
            'ami_disposition': disposition,
            'ami_duration': duration,
            'ami_accountcode': event.get('AccountCode', ''),
        },
    }

    call, created = Call.objects.update_or_create(
        call_id=call_id,
        defaults=defaults,
    )

    action = "CREADO" if created else "ACTUALIZADO"
    logger.info(
        f"[CDR] {action} Call {call.id}: {call_id}  "
        f"{src} → {dst}  {direction}  {call_status}  "
        f"dur={duration}s  bill={billsec}s"
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


def _link_recording(call, event: dict):
    """Busca archivo de grabación y crea el registro Recording si existe."""
    from apps.recordings.models import Recording

    # MixMonitor suele guardar en /var/spool/asterisk/monitor/
    # Los archivos se nombran con el uniqueid
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
                if size > 100:  # Ignorar archivos vacíos (solo header WAV = 44 bytes)
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
# Loop principal del listener
# ─────────────────────────────────────────────────────────────────

def _listener_loop():
    """Loop principal: conecta, escucha eventos CDR, reconecta en fallo."""
    delay = RECONNECT_DELAY

    while not _stop_event.is_set():
        sock = None
        try:
            logger.info(f"[CDR Listener] Conectando a AMI {AMI_HOST}:{AMI_PORT}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((AMI_HOST, AMI_PORT))

            if not _ami_login(sock):
                logger.error("[CDR Listener] Login AMI fallido")
                raise ConnectionError("Login AMI fallido")

            logger.info("[CDR Listener] ✓ Conectado a AMI — esperando eventos CDR...")
            delay = RECONNECT_DELAY  # reset backoff

            # Leer eventos continuamente
            sock.settimeout(PING_INTERVAL + 5)
            buffer = ''
            last_ping = time.time()

            while not _stop_event.is_set():
                # Keepalive
                now = time.time()
                if now - last_ping > PING_INTERVAL:
                    try:
                        sock.sendall(b"Action: Ping\r\n\r\n")
                        last_ping = now
                    except Exception:
                        break

                try:
                    data = sock.recv(4096)
                    if not data:
                        logger.warning("[CDR Listener] Socket cerrado por Asterisk")
                        break
                    buffer += data.decode('utf-8', errors='ignore')
                except socket.timeout:
                    continue

                # Procesar eventos completos
                while '\r\n\r\n' in buffer:
                    event_raw, _, buffer = buffer.partition('\r\n\r\n')
                    event = _parse_ami_event(event_raw)
                    event_type = event.get('Event', '')

                    if event_type == 'Cdr':
                        try:
                            _process_cdr_event(event)
                        except Exception as e:
                            logger.error(f"[CDR Listener] Error procesando CDR: {e}", exc_info=True)
                    # También capturar eventos de fin de llamada como backup
                    elif event_type == 'Hangup':
                        # Los CDR se generan después del hangup, 
                        # pero podemos usar esto como complemento
                        pass

        except Exception as e:
            logger.error(f"[CDR Listener] Error: {e}")
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

        if not _stop_event.is_set():
            logger.info(f"[CDR Listener] Reconectando en {delay}s...")
            _stop_event.wait(delay)
            delay = min(delay * 2, MAX_RECONNECT_DELAY)


# ─────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────

def start_listener():
    """Arranca el listener en un hilo daemon (idempotente)."""
    global _listener_thread

    if _listener_thread and _listener_thread.is_alive():
        logger.info("[CDR Listener] Ya está ejecutándose")
        return

    _stop_event.clear()
    _listener_thread = threading.Thread(
        target=_listener_loop,
        name='ami-cdr-listener',
        daemon=True,
    )
    _listener_thread.start()
    logger.info("[CDR Listener] Hilo iniciado")


def stop_listener():
    """Detiene el listener de forma limpia."""
    global _listener_thread
    _stop_event.set()
    if _listener_thread:
        _listener_thread.join(timeout=10)
        _listener_thread = None
    logger.info("[CDR Listener] Detenido")


def is_running() -> bool:
    """Verifica si el listener está corriendo."""
    return _listener_thread is not None and _listener_thread.is_alive()
