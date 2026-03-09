"""
Configuración de logging estructurado para VoziPOmni
"""
import logging
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Formateador JSON personalizado con campos adicionales
    """
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Agregar timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Agregar nombre del nivel
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        
        # Agregar nombre del servicio
        log_record['service'] = 'vozipomni'
        
        # Agregar entorno
        import os
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')


def get_logging_config(log_level='INFO', log_file=None):
    """
    Obtener diccionario de configuración de logging
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Ruta al archivo de log (opcional)
    
    Returns:
        dict: Configuración de logging
    """
    
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'level': log_level,
        },
    }
    
    # Solo agregar manejador de archivo si log_file está especificado y el directorio existe/es escribible
    if log_file:
        import os
        log_dir = os.path.dirname(log_file)
        
        # Intentar crear el directorio si no existe
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except (OSError, PermissionError):
                pass  # Silenciosamente ignorar - usaremos solo consola
        
        # Verificar si el directorio existe y es escribible
        if log_dir and (not os.path.exists(log_dir) or not os.access(log_dir, os.W_OK)):
            # Silenciosamente deshabilitar logging a archivo - solo consola
            pass
        else:
            handlers['file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_file,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'json',
                'level': log_level,
            }
    
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': 'core.logging_config.CustomJsonFormatter',
                'format': '%(timestamp)s %(level)s %(name)s %(message)s'
            },
            'verbose': {
                'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                'style': '{',
            },
            'simple': {
                'format': '{levelname} {asctime} {message}',
                'style': '{',
            },
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse',
            },
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },
        'handlers': handlers,
        'root': {
            'handlers': list(handlers.keys()),
            'level': log_level,
        },
        'loggers': {
            'django': {
                'handlers': list(handlers.keys()),
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': list(handlers.keys()),
                'level': 'ERROR',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': list(handlers.keys()),
                'level': 'WARNING',
                'propagate': False,
            },
            'celery': {
                'handlers': list(handlers.keys()),
                'level': 'INFO',
                'propagate': False,
            },
            'apps.campaigns': {
                'handlers': list(handlers.keys()),
                'level': 'INFO',
                'propagate': False,
            },
            'apps.agents': {
                'handlers': list(handlers.keys()),
                'level': 'INFO',
                'propagate': False,
            },
            'apps.telephony': {
                'handlers': list(handlers.keys()),
                'level': 'DEBUG',
                'propagate': False,
            },
            'apps.api': {
                'handlers': list(handlers.keys()),
                'level': 'INFO',
                'propagate': False,
            },
        },
    }
    
    return config


class StructuredLogger:
    """
    Clase auxiliar para logging estructurado
    """
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
    
    def log(self, level, message, **kwargs):
        """
        Registrar con datos estructurados
        
        Args:
            level: Nivel de log (debug, info, warning, error, critical)
            message: Mensaje de log
            **kwargs: Datos estructurados adicionales
        """
        extra = {'extra_data': kwargs}
        getattr(self.logger, level)(message, extra=extra)
    
    def debug(self, message, **kwargs):
        self.log('debug', message, **kwargs)
    
    def info(self, message, **kwargs):
        self.log('info', message, **kwargs)
    
    def warning(self, message, **kwargs):
        self.log('warning', message, **kwargs)
    
    def error(self, message, **kwargs):
        self.log('error', message, **kwargs)
    
    def critical(self, message, **kwargs):
        self.log('critical', message, **kwargs)
    
    def exception(self, message, **kwargs):
        """Registrar excepción con traceback"""
        extra = {'extra_data': kwargs}
        self.logger.exception(message, extra=extra)


# Función de conveniencia
def get_logger(name):
    """Obtener una instancia de logger estructurado"""
    return StructuredLogger(name)


# Ejemplo de uso:
"""
from core.logging_config import get_logger

logger = get_logger(__name__)

logger.info(
    "Campaña iniciada",
    campaign_id=123,
    campaign_name="Campaña de Prueba",
    user_id=456,
    contacts_count=1000
)

logger.error(
    "Fallo al originar llamada",
    campaign_id=123,
    contact_id=789,
    error_code="AMI_CONNECTION_ERROR",
    trunk_name="trunk1"
)
"""
