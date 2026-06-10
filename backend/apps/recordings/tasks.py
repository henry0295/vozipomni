from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
import os
from config.recording_config import RECORDING_RETENTION

logger = logging.getLogger(__name__)


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
    recording_dirs = [
        '/var/spool/asterisk/monitor',
        '/app/recordings',
    ]

    found_path = ''
    for rdir in recording_dirs:
        if not os.path.isdir(rdir):
            continue
        try:
            for fname in os.listdir(rdir):
                if unique_id and unique_id in fname:
                    candidate = os.path.join(rdir, fname)
                    if os.path.getsize(candidate) > 100:
                        found_path = candidate
                        break
                # Fallback: buscar por call_id sin prefijo "ast-"
                raw_id = call_id.replace('ast-', '')
                if raw_id and raw_id in fname:
                    candidate = os.path.join(rdir, fname)
                    if os.path.getsize(candidate) > 100:
                        found_path = candidate
                        break
        except OSError:
            continue
        if found_path:
            break

    if not found_path:
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

    recording_dirs = [
        '/var/spool/asterisk/monitor',
        '/app/recordings',
    ]
    linked = 0
    for rdir in recording_dirs:
        if not os.path.isdir(rdir):
            continue
        for fname in os.listdir(rdir):
            if not fname.endswith(('.wav', '.mp3', '.gsm', '.ogg')):
                continue
            full_path = os.path.join(rdir, fname)
            if os.path.getsize(full_path) < 100:
                continue
            # Ya vinculado
            if Recording.objects.filter(file_path=full_path).exists():
                continue
            # Intentar identificar la llamada por nombre de archivo (contiene unique_id)
            matched_call = None
            for call in Call.objects.filter(recording_file='').order_by('-start_time')[:500]:
                uid = call.unique_id or ''
                if uid and uid in fname:
                    matched_call = call
                    break
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


    """
    Limpiar grabaciones antiguas según política de retención configurada
    """
    from apps.recordings.models import Recording
    from django.conf import settings
    
    # Obtener configuración
    archive_days = RECORDING_RETENTION['ARCHIVE_DAYS']
    delete_days = RECORDING_RETENTION['DELETE_DAYS']
    
    # Archivar grabaciones antiguas
    archive_date = timezone.now() - timedelta(days=archive_days)
    old_recordings = Recording.objects.filter(
        created_at__lt=archive_date,
        status='completed'
    ).exclude(status='archived')
    
    archived_count = 0
    for recording in old_recordings:
        recording.status = 'archived'
        recording.archived_at = timezone.now()
        recording.save()
        archived_count += 1
    
    logger.info(f"Archived {archived_count} recordings older than {archive_days} days")
    
    # Eliminar archivos de grabaciones muy antiguas
    delete_date = timezone.now() - timedelta(days=delete_days)
    very_old_recordings = Recording.objects.filter(
        created_at__lt=delete_date,
        status='archived'
    )
    
    deleted_count = 0
    deleted_size = 0
    
    for recording in very_old_recordings:
        try:
            # Eliminar archivo físico
            if recording.file_path and os.path.exists(recording.file_path):
                file_size = os.path.getsize(recording.file_path)
                os.remove(recording.file_path)
                deleted_size += file_size
                logger.debug(f"Deleted recording file: {recording.file_path}")
            
            # Marcar como eliminado en DB (no borrar registro)
            recording.status = 'deleted'
            recording.file_path = ''
            recording.save()
            deleted_count += 1
            
        except Exception as e:
            logger.error(f"Error deleting recording file {recording.file_path}: {str(e)}")
    
    deleted_size_mb = deleted_size / (1024 * 1024)
    logger.info(
        f"Deleted {deleted_count} recording files older than {delete_days} days "
        f"({deleted_size_mb:.2f} MB freed)"
    )
    
    return {
        'archived': archived_count,
        'deleted': deleted_count,
        'freed_mb': round(deleted_size_mb, 2)
    }


@shared_task
def transcribe_recording(recording_id):
    """
    Transcribir una grabación usando servicios de speech-to-text
    """
    from apps.recordings.models import Recording
    
    try:
        recording = Recording.objects.get(id=recording_id)
        recording.transcription_status = 'processing'
        recording.save()
        
        # Aquí se integraría con servicios de transcripción
        # Por ejemplo: Google Speech-to-Text, AWS Transcribe, etc.
        
        # Simulación
        recording.transcription = "Transcripción pendiente de implementación"
        recording.transcription_status = 'completed'
        recording.save()
        
        return f"Transcribed recording {recording_id}"
    except Recording.DoesNotExist:
        return f"Recording {recording_id} not found"
