"""
Structured logging configuration for VoziPOmni
"""
import logging
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional fields
    """
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add level name
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname
        
        # Add service name
        log_record['service'] = 'vozipomni'
        
        # Add environment
        import os
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')


def get_logging_config(log_level='INFO', log_file=None):
    """
    Get logging configuration dictionary
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
    
    Returns:
        dict: Logging configuration
    """
    
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'level': log_level,
        },
    }
    
    if log_file:
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
    Helper class for structured logging
    """
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
    
    def log(self, level, message, **kwargs):
        """
        Log with structured data
        
        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            **kwargs: Additional structured data
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
        """Log exception with traceback"""
        extra = {'extra_data': kwargs}
        self.logger.exception(message, extra=extra)


# Convenience function
def get_logger(name):
    """Get a structured logger instance"""
    return StructuredLogger(name)


# Example usage:
"""
from core.logging_config import get_logger

logger = get_logger(__name__)

logger.info(
    "Campaign started",
    campaign_id=123,
    campaign_name="Test Campaign",
    user_id=456,
    contacts_count=1000
)

logger.error(
    "Failed to originate call",
    campaign_id=123,
    contact_id=789,
    error_code="AMI_CONNECTION_ERROR",
    trunk_name="trunk1"
)
"""
