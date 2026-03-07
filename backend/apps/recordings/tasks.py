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
    retry_kwargs={'max_retries': 2, 'countdown': 60},
    retry_backoff=True
)
def cleanup_old_recordings(self):
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
