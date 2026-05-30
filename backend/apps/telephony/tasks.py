"""
Tareas Celery para sincronización con Asterisk.

La sincronización principal se ejecuta desde signals.py usando threads directos.
Estas tareas Celery se usan para:
- Tareas periódicas programadas en beat_schedule (sync cada 5 min, health check)
- Stubs de compatibilidad para llamadas legacy (reload_asterisk_trunk.delay())
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


def _sync_via_signals():
    """Delegamos al mecanismo centralizado de signals.py"""
    from apps.telephony.signals import sync_asterisk_now
    sync_asterisk_now()


# ============= STUBS QUE DELEGAN A signals.py =============

def sync_sip_trunk_to_asterisk(trunk_id=None):
    logger.info(f"[stub] sync_sip_trunk_to_asterisk({trunk_id}) → delegando a signals")
    _sync_via_signals()


def sync_inbound_route_to_asterisk(route_id=None):
    logger.info(f"[stub] sync_inbound_route_to_asterisk({route_id}) → delegando a signals")
    _sync_via_signals()


def sync_outbound_route_to_asterisk(route_id=None):
    logger.info(f"[stub] sync_outbound_route_to_asterisk({route_id}) → delegando a signals")
    _sync_via_signals()


def sync_extension_to_asterisk(ext_id=None):
    logger.info(f"[stub] sync_extension_to_asterisk({ext_id}) → delegando a signals")
    _sync_via_signals()


def sync_ivr_to_asterisk(ivr_id=None):
    logger.info(f"[stub] sync_ivr_to_asterisk({ivr_id}) → delegando a signals")
    _sync_via_signals()


def sync_voicemail_to_asterisk(vm_id=None):
    logger.info(f"[stub] sync_voicemail_to_asterisk({vm_id}) → delegando a signals")
    _sync_via_signals()


def sync_time_condition_to_asterisk(cond_id=None):
    logger.info(f"[stub] sync_time_condition_to_asterisk({cond_id}) → delegando a signals")
    _sync_via_signals()


def remove_sip_trunk_from_asterisk(trunk_name=None):
    logger.info(f"[stub] remove_sip_trunk_from_asterisk({trunk_name}) → delegando a signals")
    _sync_via_signals()


def remove_inbound_route_from_asterisk(did=None):
    logger.info(f"[stub] remove_inbound_route_from_asterisk({did}) → delegando a signals")
    _sync_via_signals()


class _FakeDelay:
    """Objeto que simula .delay() y .apply_async() para no romper llamadas antiguas."""
    def __init__(self, fn):
        self._fn = fn

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    def delay(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    def apply_async(self, args=None, kwargs=None, **_kw):
        return self._fn(*(args or []), **(kwargs or {}))


# Permite: reload_asterisk_trunk.delay(id) o reload_asterisk_trunk(id)
def _reload_asterisk_trunk(trunk_id=None):
    logger.info(f"[stub] reload_asterisk_trunk({trunk_id}) → delegando a signals")
    _sync_via_signals()


reload_asterisk_trunk = _FakeDelay(_reload_asterisk_trunk)


@shared_task(name='apps.telephony.tasks.sync_all_telephony_config_to_redis')
def sync_all_telephony_config_to_redis():
    """Tarea periódica: re-sincronizar toda la configuración con Asterisk"""
    logger.info("[celery] sync_all_telephony_config_to_redis")
    _sync_via_signals()


@shared_task(name='apps.telephony.tasks.check_asterisk_health')
def check_asterisk_health():
    from apps.telephony.asterisk_ami import AsteriskAMI
    from django.core.cache import cache
    try:
        ami = AsteriskAMI()
        if ami.connect():
            ami.disconnect()
            cache.set('asterisk_health', {'status': 'connected'}, timeout=120)
            return {'status': 'connected'}
    except Exception as e:
        logger.error(f"Health check error: {e}")
    cache.set('asterisk_health', {'status': 'disconnected'}, timeout=120)
    return {'status': 'disconnected'}


@shared_task(name='apps.telephony.tasks.run_ami_cdr_listener')
def run_ami_cdr_listener():
    """Arranca el listener AMI CDR como hilo daemon dentro del worker Celery."""
    from apps.telephony.ami_cdr_listener import start_listener, is_running
    if not is_running():
        start_listener()
        logger.info("[celery] AMI CDR Listener iniciado")
    else:
        logger.info("[celery] AMI CDR Listener ya estaba corriendo")
    return {'cdr_listener': 'running'}


# ──────────────────────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    name='apps.telephony.tasks.deliver_webhook',
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 30},
    retry_backoff=True,
)
def deliver_webhook(self, endpoint_id: int, event_type: str, payload: dict, attempt: int = 1):
    """Entrega asincrónica de un evento webhook a un endpoint externo."""
    from apps.telephony.webhook_service import WebhookService
    WebhookService.deliver_now(endpoint_id, event_type, payload, attempt)


# ──────────────────────────────────────────────────────────────────────────────
# Callbacks - procesar devoluciones de llamada pendientes
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    name='apps.telephony.tasks.process_pending_callbacks',
    autoretry_for=(ConnectionError,),
    retry_kwargs={'max_retries': 2, 'countdown': 15},
)
def process_pending_callbacks(self):
    """
    Tarea periódica (cada 60s): procesa callbacks pendientes cuya hora
    programada ya llegó y origina la llamada vía AMI.
    """
    from django.utils import timezone as tz
    from apps.telephony.models import CallbackRequest
    from apps.telephony.services import CallService
    from apps.telephony.webhook_service import WebhookService

    now = tz.now()
    pending = CallbackRequest.objects.filter(
        status__in=['pending', 'scheduled'],
        scheduled_at__lte=now,
        attempts__lt=models.F('max_attempts'),
    ).select_related('agent', 'campaign')[:50]

    processed = 0
    for cb in pending:
        try:
            cb.status = 'dialing'
            cb.attempts += 1
            cb.save(update_fields=['status', 'attempts', 'updated_at'])

            # Originar la llamada
            agent_ext = cb.agent.sip_extension if cb.agent else None
            result = CallService.originate_call(
                agent_extension=agent_ext or 'callback',
                destination=cb.phone,
                caller_id='Callback',
                campaign_id=cb.campaign_id,
            )

            if result.get('success'):
                cb.status = 'completed'
                WebhookService.dispatch('callback.completed', {
                    'callback_id': cb.id,
                    'phone': cb.phone,
                    'campaign_id': cb.campaign_id,
                })
            else:
                # Si aún quedan intentos, volver a pending
                cb.status = 'pending' if cb.attempts < cb.max_attempts else 'failed'
            cb.save(update_fields=['status', 'updated_at'])
            processed += 1
        except Exception as e:
            logger.error(f"Error processing callback {cb.id}: {e}")
            cb.status = 'pending' if cb.attempts < cb.max_attempts else 'failed'
            cb.save(update_fields=['status', 'updated_at'])

    return f"Processed {processed} callbacks"


# Importar models aquí para evitar importación circular en la tarea anterior
from django.db import models as models  # noqa: E402