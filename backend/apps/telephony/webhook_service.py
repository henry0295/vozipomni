"""
Servicio de Webhooks
Envía notificaciones HTTP a endpoints externos cuando ocurren eventos.
"""
import hashlib
import hmac
import json
import logging
import time
import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

# Eventos disponibles
EVENTS = {
    'call.initiated':     'Llamada iniciada',
    'call.answered':      'Llamada contestada',
    'call.completed':     'Llamada completada',
    'call.abandoned':     'Llamada abandonada',
    'agent.login':        'Agente conectado',
    'agent.logout':       'Agente desconectado',
    'agent.status':       'Cambio estado agente',
    'campaign.started':   'Campaña iniciada',
    'campaign.paused':    'Campaña pausada',
    'campaign.finished':  'Campaña finalizada',
    'callback.created':   'Callback creado',
    'callback.completed': 'Callback completado',
}


class WebhookService:
    """Gestión de entrega de webhooks."""

    @staticmethod
    def dispatch(event_type: str, payload: dict) -> int:
        """
        Despacha un evento a todos los endpoints configurados.
        Lanza tareas Celery asíncronas para no bloquear el request.

        Returns:
            int: Número de endpoints notificados.
        """
        from apps.telephony.models import WebhookEndpoint
        from apps.telephony.tasks import deliver_webhook

        endpoints = WebhookEndpoint.objects.filter(is_active=True)
        count = 0
        for ep in endpoints:
            if ep.should_notify(event_type):
                deliver_webhook.delay(ep.id, event_type, payload)
                count += 1
        return count

    @staticmethod
    def deliver_now(endpoint_id: int, event_type: str, payload: dict, attempt: int = 1):
        """Entrega sincrónica (llamada desde tarea Celery)."""
        from apps.telephony.models import WebhookEndpoint, WebhookDelivery

        try:
            ep = WebhookEndpoint.objects.get(id=endpoint_id)
        except WebhookEndpoint.DoesNotExist:
            logger.warning(f"Webhook endpoint {endpoint_id} not found")
            return

        body = json.dumps(payload, default=str)
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Event': event_type,
            'X-Webhook-Delivery': f"{endpoint_id}-{event_type}-{int(time.time())}",
            **ep.headers,
        }

        if ep.secret:
            sig = hmac.new(ep.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers['X-Webhook-Signature'] = f"sha256={sig}"

        start = time.time()
        status_code = None
        response_body = ''
        error_message = ''
        success = False

        try:
            resp = requests.post(ep.url, data=body, headers=headers, timeout=ep.timeout_seconds)
            status_code = resp.status_code
            response_body = resp.text[:1000]
            success = 200 <= status_code < 300
        except requests.Timeout:
            error_message = 'Timeout'
        except requests.RequestException as e:
            error_message = str(e)

        duration_ms = int((time.time() - start) * 1000)

        WebhookDelivery.objects.create(
            endpoint=ep,
            event_type=event_type,
            payload=payload,
            status_code=status_code,
            response_body=response_body,
            success=success,
            duration_ms=duration_ms,
            attempt=attempt,
            error_message=error_message,
        )

        # Actualizar stats del endpoint
        ep.last_triggered_at = timezone.now()
        ep.last_status_code = status_code
        ep.total_deliveries += 1
        if not success:
            ep.failed_deliveries += 1
        ep.save(update_fields=[
            'last_triggered_at', 'last_status_code',
            'total_deliveries', 'failed_deliveries',
        ])

        if not success and ep.retry_on_failure and attempt < 3:
            # Reintento exponencial: 30s, 120s
            countdown = 30 * (attempt ** 2)
            from apps.telephony.tasks import deliver_webhook
            deliver_webhook.apply_async(
                args=[endpoint_id, event_type, payload, attempt + 1],
                countdown=countdown,
            )
            logger.warning(f"Webhook {ep.name} failed (attempt {attempt}), retry in {countdown}s")
        elif success:
            logger.info(f"Webhook {ep.name} delivered OK ({status_code}) in {duration_ms}ms")
