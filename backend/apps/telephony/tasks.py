"""
Stubs de compatibilidad para tareas Celery.

Toda la sincronización real con Asterisk ahora se ejecuta
desde signals.py usando threads directos (sin Celery).

Estas funciones se mantienen únicamente para que las importaciones
existentes (p.ej. viewsets.py → reload_asterisk_trunk) no rompan.
"""
import logging

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


def sync_all_telephony_config_to_redis():
    logger.info("[stub] sync_all_telephony_config_to_redis → delegando a signals")
    _sync_via_signals()


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