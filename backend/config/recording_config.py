"""
Configuración centralizada de grabaciones
"""
from decouple import config


# ============= RETENCIÓN DE GRABACIONES =============

RECORDING_RETENTION = {
    # Días antes de archivar grabaciones
    'ARCHIVE_DAYS': config('RECORDING_ARCHIVE_DAYS', default=90, cast=int),
    
    # Días antes de eliminar grabaciones archivadas
    'DELETE_DAYS': config('RECORDING_DELETE_DAYS', default=180, cast=int),
    
    # Días antes de eliminar grabaciones de baja prioridad
    'DELETE_LOW_PRIORITY_DAYS': config('RECORDING_DELETE_LOW_PRIORITY', default=30, cast=int),
}


# ============= ALMACENAMIENTO =============

RECORDING_STORAGE = {
    # Directorio base de grabaciones
    'BASE_DIR': config('RECORDING_BASE_DIR', default='/app/recordings'),
    
    # Formato de archivo
    'FILE_FORMAT': config('RECORDING_FORMAT', default='wav'),
    
    # Calidad de audio (kbps)
    'AUDIO_QUALITY': config('RECORDING_QUALITY', default=64, cast=int),
    
    # Compresión habilitada
    'COMPRESSION_ENABLED': config('RECORDING_COMPRESSION', default=True, cast=bool),
}


# ============= TRANSCRIPCIÓN =============

TRANSCRIPTION_CONFIG = {
    # Servicio de transcripción (google, aws, azure, none)
    'SERVICE': config('TRANSCRIPTION_SERVICE', default='none'),
    
    # Idioma por defecto
    'DEFAULT_LANGUAGE': config('TRANSCRIPTION_LANGUAGE', default='es-CO'),
    
    # Transcripción automática habilitada
    'AUTO_TRANSCRIBE': config('TRANSCRIPTION_AUTO', default=False, cast=bool),
    
    # Transcribir solo llamadas exitosas
    'ONLY_SUCCESSFUL': config('TRANSCRIPTION_ONLY_SUCCESS', default=True, cast=bool),
}


def get_recording_config():
    """Obtener configuración completa de grabaciones"""
    return {
        'retention': RECORDING_RETENTION,
        'storage': RECORDING_STORAGE,
        'transcription': TRANSCRIPTION_CONFIG,
    }
