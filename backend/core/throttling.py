"""
VozipCX — Throttles de DRF tolerantes a fallos de Redis.

Los throttles guardan sus contadores en la caché compartida (Redis, `settings.CACHES`).
Si Redis no responde, la petición pasa (fail-open) y se registra un ERROR como mucho una
vez por minuto por proceso, para que una caída de Redis no deje la API en 500.
El límite de nginx sigue protegiendo el login mientras tanto.
"""
import logging
import time

from redis.exceptions import RedisError
from rest_framework import throttling

logger = logging.getLogger(__name__)

_ERROR_LOG_INTERVAL = 60.0
_last_error_log = 0.0


def _log_cache_error(exc):
    global _last_error_log
    now = time.monotonic()
    if now - _last_error_log >= _ERROR_LOG_INTERVAL:
        _last_error_log = now
        logger.error('Throttle sin caché (Redis no disponible), se deja pasar la petición: %s', exc)


class FailOpenThrottleMixin:
    """Deja pasar la petición si la caché de Redis falla."""

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except RedisError as exc:
            _log_cache_error(exc)
            return True


class AnonRateThrottle(FailOpenThrottleMixin, throttling.AnonRateThrottle):
    pass


class UserRateThrottle(FailOpenThrottleMixin, throttling.UserRateThrottle):
    pass


class ScopedRateThrottle(FailOpenThrottleMixin, throttling.ScopedRateThrottle):
    pass
