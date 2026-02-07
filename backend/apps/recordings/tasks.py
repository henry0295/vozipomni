from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
import os

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_recordings():
    """
    Limpiar grabaciones antiguas según política de retención
    """
    from apps.recordings.models import Recording
    from django.conf import settings
    
    # Archivar grabaciones mayores a 90 días
    archive_date = timezone.now() - timedelta(days=90)
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
    
    # Eliminar archivos de grabaciones mayores a 180 días
    delete_date = timezone.now() - timedelta(days=180)
    very_old_recordings = Recording.objects.filter(
        created_at__lt=delete_date,
        status='archived'
    )
    
    deleted_count = 0
    for recording in very_old_recordings:
        try:
            # Eliminar archivo físico
            if os.path.exists(recording.file_path):
                os.remove(recording.file_path)
            deleted_count += 1
        except Exception as e:
            logger.error(f"Error deleting recording file {recording.file_path}: {str(e)}")
    
    return f"Archived {archived_count} recordings, deleted {deleted_count} files"


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
