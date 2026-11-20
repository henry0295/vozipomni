"""
Celery configuration for VozipCX
"""

import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('vozipomni')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configuración de tareas periódicas
# La programación de tareas periódicas vive SOLO en settings.CELERY_BEAT_SCHEDULE.
# (Antes aquí se reasignaba app.conf.beat_schedule con nombres no registrados y
# se anulaba la de settings: retención, callbacks, antifraude, correo, etc. no corrían.)


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
