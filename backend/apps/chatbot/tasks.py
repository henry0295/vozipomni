import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='chatbot.run_connector_step', ignore_result=True)
def run_connector_step(session_id: int, node_id: str):
    """Llama al sistema externo de un bloque Conector y continúa el flujo."""
    from .engine import continue_after_connector
    continue_after_connector(session_id, node_id)


@shared_task(name='chatbot.run_ai_step', ignore_result=True)
def run_ai_step(session_id: int, node_id: str):
    """Clasifica con IA el mensaje pendiente de un bloque "Entender intención"."""
    from .engine import continue_after_ai
    continue_after_ai(session_id, node_id)


@shared_task(bind=True, name='chatbot.run_file_step', ignore_result=True, max_retries=12)
def run_file_step(self, session_id: int, node_id: str):
    """Lee o analiza el archivo de un bloque «Analizar archivo». Espera a que termine la descarga."""
    from .engine import continue_after_file, fail_file_step
    from .media import NotReady
    try:
        continue_after_file(session_id, node_id)
    except NotReady:
        if self.request.retries >= self.max_retries:
            fail_file_step(session_id, node_id)
            return
        raise self.retry(countdown=5)


@shared_task(name='chatbot.expire_sessions', ignore_result=True)
def expire_sessions():
    """Marca como expiradas las sesiones inactivas y borra los datos que capturaron."""
    from .models import BotSession
    count = 0
    for s in BotSession.objects.filter(status__in=['active', 'busy']).select_related('flow'):
        minutes = (s.flow.session_timeout_minutes if s.flow else 30) or 30
        if s.last_activity_at < timezone.now() - timedelta(minutes=minutes):
            s.status = 'timeout'
            s.variables = {}
            s.save(update_fields=['status', 'variables'])
            count += 1
    # Datos capturados por el bot en sesiones viejas: no se conservan más de 7 días
    BotSession.objects.filter(last_activity_at__lt=timezone.now() - timedelta(days=7)).exclude(
        variables={}).update(variables={})
    return count
