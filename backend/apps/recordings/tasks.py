from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
import os
from config.recording_config import RECORDING_RETENTION

logger = logging.getLogger(__name__)

# MixMonitor escribe en el spool de Asterisk (volumen asterisk_spool montado en backend y celery)
RECORDING_DIRS = ('/var/spool/asterisk/monitor', '/app/recordings')
RECORDING_EXTS = ('.wav', '.wav49', '.gsm', '.mp3', '.ogg')


def _id_in_name(token: str, fname: str) -> bool:
    """El Uniqueid de Asterisk (p. ej. 1727630981.12) aparece completo en el nombre, no como parte
    de otro (1727630981.123) — los nombres del dialplan son FECHA_${UNIQUEID}_origen_destino.wav."""
    import re
    return bool(token) and re.search(rf'(?<![\d.]){re.escape(token)}(?![\d])', fname) is not None


def find_recording_file(unique_id: str = '', call_id: str = '') -> str:
    raw_id = (call_id or '').replace('ast-', '')
    for rdir in RECORDING_DIRS:
        if not os.path.isdir(rdir):
            continue
        try:
            names = os.listdir(rdir)
        except OSError:
            continue
        for fname in names:
            if not fname.lower().endswith(RECORDING_EXTS):
                continue
            if _id_in_name(unique_id, fname) or (raw_id != unique_id and _id_in_name(raw_id, fname)):
                candidate = os.path.join(rdir, fname)
                try:
                    if os.path.getsize(candidate) > 100:
                        return candidate
                except OSError:
                    continue
    return ''


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 30},
    retry_backoff=True,
    name='recordings.link_recording_to_call',
)
def link_recording_to_call(self, call_id: str):
    """
    Tarea diferida para vincular el archivo de grabación a un Call.
    Se lanza con countdown=30s desde el listener CDR para dar tiempo a que
    MixMonitor cierre el archivo WAV correctamente antes de buscar el archivo.
    Reintenta hasta 3 veces con backoff si el archivo aún no está disponible.
    """
    from apps.telephony.models import Call
    from apps.recordings.models import Recording

    try:
        call = Call.objects.get(call_id=call_id)
    except Call.DoesNotExist:
        logger.warning(f"[Recording] Call {call_id} no encontrado para vincular grabación")
        return

    unique_id = call.unique_id or ''
    found_path = find_recording_file(unique_id, call_id)

    if not found_path:
        if self.request.retries >= self.max_retries:
            logger.warning(f"[Recording] Sin archivo de grabación para call {call_id} (unique_id={unique_id})")
            return
        logger.debug(f"[Recording] Archivo no encontrado para call {call_id} (unique_id={unique_id}), reintentando…")
        raise self.retry(countdown=30)

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
            'campaign': call.campaign if hasattr(call, 'campaign') else None,
        },
    )
    call.recording_file = found_path
    call.is_recorded = True
    call.save(update_fields=['recording_file', 'is_recorded'])
    logger.info(f"[Recording] ✓ Grabación vinculada a call {call_id}: {filename} ({file_size} bytes)")


@shared_task(
    name='recordings.scan_unlinked_recordings',
)
def scan_unlinked_recordings():
    """
    Tarea periódica que escanea el directorio de grabaciones y vincula
    cualquier archivo que aún no tenga un registro Recording en la BD.
    Útil como red de seguridad para llamadas que fallaron en la vinculación inicial.
    """
    from apps.telephony.models import Call
    from apps.recordings.models import Recording

    linked = 0
    pending = [c for c in Call.objects.filter(recording_file='').exclude(unique_id='')
               .order_by('-start_time')[:500]]
    for rdir in RECORDING_DIRS:
        if not os.path.isdir(rdir) or not pending:
            continue
        for fname in os.listdir(rdir):
            if not fname.lower().endswith(RECORDING_EXTS):
                continue
            full_path = os.path.join(rdir, fname)
            try:
                if os.path.getsize(full_path) < 100:
                    continue
            except OSError:
                continue
            # Ya vinculado
            if Recording.objects.filter(file_path=full_path).exists():
                continue
            # Identificar la llamada por el Uniqueid del nombre de archivo
            matched_call = next((c for c in pending if _id_in_name(c.unique_id, fname)), None)
            if matched_call:
                pending.remove(matched_call)
            if matched_call:
                file_size = os.path.getsize(full_path)
                Recording.objects.update_or_create(
                    call=matched_call,
                    defaults={
                        'filename': fname,
                        'file_path': full_path,
                        'file_size': file_size,
                        'duration': matched_call.talk_time or 0,
                        'format': fname.rsplit('.', 1)[-1],
                        'status': 'completed',
                        'agent': matched_call.agent,
                    },
                )
                matched_call.recording_file = full_path
                matched_call.is_recorded = True
                matched_call.save(update_fields=['recording_file', 'is_recorded'])
                linked += 1

    if linked:
        logger.info(f"[Recording] Scan periódico: {linked} grabaciones vinculadas")
    return linked


@shared_task(
    name='recordings.cleanup_old_recordings',
)
def cleanup_old_recordings():
    """
    Política de retención de grabaciones (ejecutar diariamente a las 02:00 via Celery Beat):
      - ARCHIVE_DAYS: archivar grabaciones más antiguas que N días (marcarlas como 'archived')
      - DELETE_DAYS:  eliminar físicamente los archivos archivados más antiguos que N días

    Configurable con variables en RECORDING_RETENTION:
      ARCHIVE_DAYS = 90   → archivar después de 90 días
      DELETE_DAYS  = 180  → eliminar archivo físico después de 180 días
    """
    from apps.recordings.models import Recording

    archive_days = RECORDING_RETENTION.get('ARCHIVE_DAYS', 90)
    delete_days  = RECORDING_RETENTION.get('DELETE_DAYS', 180)

    # ── 1. Archivar grabaciones completadas antiguas ─────────────────────────
    archive_cutoff = timezone.now() - timedelta(days=archive_days)
    to_archive = Recording.objects.filter(
        created_at__lt=archive_cutoff,
        status='completed',
    )
    archived_count = 0
    for recording in to_archive:
        recording.status = 'archived'
        recording.archived_at = timezone.now()
        recording.save(update_fields=['status', 'archived_at'])
        archived_count += 1

    if archived_count:
        logger.info(f"[Retention] Archivadas {archived_count} grabaciones (>{archive_days} días)")

    # ── 2. Eliminar archivos físicos de grabaciones muy antiguas ─────────────
    delete_cutoff = timezone.now() - timedelta(days=delete_days)
    to_delete = Recording.objects.filter(
        created_at__lt=delete_cutoff,
        status='archived',
    ).exclude(file_path='')

    deleted_count = 0
    deleted_bytes = 0
    for recording in to_delete:
        try:
            if recording.file_path and os.path.exists(recording.file_path):
                size = os.path.getsize(recording.file_path)
                os.remove(recording.file_path)
                deleted_bytes += size
                logger.debug(f"[Retention] Eliminado archivo: {recording.file_path}")

            # Conservar el registro en BD, solo limpiar la ruta
            recording.file_path = ''
            recording.status = 'archived'
            recording.save(update_fields=['file_path'])
            deleted_count += 1
        except Exception as e:
            logger.error(f"[Retention] Error eliminando {recording.file_path}: {e}")

    deleted_mb = deleted_bytes / (1024 * 1024)
    if deleted_count:
        logger.info(
            f"[Retention] Eliminados {deleted_count} archivos ({deleted_mb:.1f} MB liberados)"
        )

    return {
        'archived': archived_count,
        'deleted': deleted_count,
        'freed_mb': round(deleted_mb, 2),
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 60},
    name='recordings.transcribe_recording',
)
def transcribe_recording(self, recording_id: int):
    """
    Transcribir una grabación usando Whisper (modelo local, sin dependencia de APIs externas).

    Modelos disponibles (orden de velocidad/calidad):
      tiny, base, small, medium, large, large-v2, large-v3
    Se configura con la variable de entorno WHISPER_MODEL (default: 'base').

    El archivo debe estar en formato WAV, MP3, GSM o cualquier formato soportado por ffmpeg.
    """
    from apps.recordings.models import Recording

    try:
        recording = Recording.objects.get(id=recording_id)
    except Recording.DoesNotExist:
        logger.warning(f"[Whisper] Recording {recording_id} no encontrado")
        return f"Recording {recording_id} not found"

    if not recording.file_path or not os.path.exists(recording.file_path):
        logger.warning(f"[Whisper] Archivo no encontrado: {recording.file_path}")
        recording.transcription_status = 'failed'
        recording.save(update_fields=['transcription_status'])
        return "File not found"

    recording.transcription_status = 'processing'
    recording.save(update_fields=['transcription_status'])

    try:
        import whisper

        model_name = os.getenv('WHISPER_MODEL', 'base')
        language = os.getenv('WHISPER_LANGUAGE', None)  # None = auto-detect

        logger.info(f"[Whisper] Cargando modelo '{model_name}' para recording {recording_id}")
        model = whisper.load_model(model_name)

        # Opciones de transcripción
        options = {
            'fp16': False,   # Usar FP32 para compatibilidad con CPU
            'verbose': False,
        }
        if language:
            options['language'] = language

        logger.info(f"[Whisper] Transcribiendo {recording.file_path}")
        result = model.transcribe(recording.file_path, **options)

        transcription_text = result.get('text', '').strip()
        detected_language = result.get('language', '')

        recording.transcription = transcription_text
        recording.transcription_status = 'completed'
        recording.save(update_fields=['transcription', 'transcription_status'])

        logger.info(
            f"[Whisper] ✓ Transcripción completada para recording {recording_id} "
            f"({len(transcription_text)} chars, idioma={detected_language})"
        )
        return {
            'recording_id': recording_id,
            'chars': len(transcription_text),
            'language': detected_language,
        }

    except ImportError:
        logger.error(
            "[Whisper] openai-whisper no está instalado. "
            "Instalar con: pip install openai-whisper"
        )
        recording.transcription = ''
        recording.transcription_status = 'failed'
        recording.save(update_fields=['transcription', 'transcription_status'])
        return "Whisper not installed"

    except Exception as e:
        logger.error(f"[Whisper] Error transcribiendo recording {recording_id}: {e}")
        recording.transcription_status = 'failed'
        recording.save(update_fields=['transcription_status'])
        raise  # allow retry
