"""
Celery configuration for VoziPOmni
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('vozipomni')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configuración de tareas periódicas
app.conf.beat_schedule = {
    'process-pending-calls': {
        'task': 'apps.campaigns.tasks.process_pending_calls',
        'schedule': 10.0,  # cada 10 segundos
    },
    'update-agent-statistics': {
        'task': 'apps.agents.tasks.update_agent_statistics',
        'schedule': 60.0,  # cada minuto
    },
    'cleanup-old-recordings': {
        'task': 'apps.recordings.tasks.cleanup_old_recordings',
        'schedule': crontab(hour=2, minute=0),  # 2 AM diario
    },
    'generate-daily-reports': {
        'task': 'apps.reports.tasks.generate_daily_reports',
        'schedule': crontab(hour=1, minute=0),  # 1 AM diario
    },
    
    # ===== TAREAS PERIODICAS DE TELEFONIA =====
    
    # Sincronizar configuración de telefonía a Redis cada 5 minutos
    'sync-telephony-redis': {
        'task': 'apps.telephony.tasks.sync_all_telephony_config_to_redis',
        'schedule': 300.0,  # 5 minutos
    },
    
    # Verificar salud de Asterisk cada minuto
    'check-asterisk-health': {
        'task': 'apps.telephony.tasks.check_asterisk_health',
        'schedule': 60.0,  # 1 minuto
    },
    
    # Reiniciar métricas diarias de agentes a medianoche
    'reset-daily-agent-metrics': {
        'task': 'apps.agents.tasks.reset_daily_agent_metrics',
        'schedule': crontab(hour=0, minute=0),  # 00:00 diario
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# ===== ARRANQUE AUTOMÁTICO DEL CDR LISTENER =====
from celery.signals import worker_ready

@worker_ready.connect
def start_cdr_listener_on_worker_ready(sender=None, **kwargs):
    """Arranca el AMI CDR Listener cuando el worker Celery está listo."""
    import logging
    _logger = logging.getLogger(__name__)
    try:
        from apps.telephony.ami_cdr_listener import start_listener
        start_listener()
        _logger.info("✓ AMI CDR Listener arrancado con el worker")
    except Exception as e:
        _logger.error(f"Error arrancando CDR Listener: {e}")
