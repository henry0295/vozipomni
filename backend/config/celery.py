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
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
