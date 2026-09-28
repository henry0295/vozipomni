"""
Global event handlers for cross-module communication.
Usa Django signals para desacoplar módulos entre sí.

Correcciones respecto a la versión original:
  - queue_campaign_in_dialer → tarea real en campaigns/tasks.py
  - generate_campaign_report → generate_report (nombre real de la tarea)
  - send_campaign_update     → push via Django Channels group_send
  - call.recording_filename  → call.recording_file (nombre real del campo)
  - process_recording        → link_recording_to_call (nombre real de la tarea)
"""
import logging
from asgiref.sync import async_to_sync
from django.dispatch import receiver
from core.events import (
    campaign_started,
    campaign_stopped,
    agent_logged_in,
    agent_logged_out,
    agent_status_changed,
    call_completed,
    ami_connection_lost,
    ami_connection_restored,
    circuit_breaker_opened,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _push_campaign_update(campaign_id: int, event: str):
    """Envía una actualización de campaña via Django Channels a todos los clientes conectados."""
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            'dashboard',
            {
                'type': 'dashboard_update',
                'event': event,
                'campaign_id': campaign_id,
            }
        )
    except Exception as e:
        logger.warning(f"[WS] No se pudo enviar update de campaña {campaign_id}: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Campaign event handlers
# ──────────────────────────────────────────────────────────────────────────────

@receiver(campaign_started)
def on_campaign_started(sender, campaign, user, **kwargs):
    """
    Al iniciar una campaña:
    1. Publica config + contactos en Redis para el Dialer Engine.
    2. Notifica al dashboard via WebSocket.
    """
    logger.info(
        "Campaign started",
        extra={'campaign_id': campaign.id, 'campaign_name': campaign.name, 'user_id': user.id},
    )

    # Publicar en el Dialer Engine via Redis
    try:
        from apps.campaigns.tasks import queue_campaign_in_dialer
        queue_campaign_in_dialer.delay(campaign.id)
    except Exception as e:
        logger.error(f"[Dialer] Error encolando campaña {campaign.id}: {e}")

    # Notificar dashboard
    _push_campaign_update(campaign.id, 'started')


@receiver(campaign_stopped)
def on_campaign_stopped(sender, campaign, user, reason=None, **kwargs):
    """
    Al detener una campaña:
    1. Señala al Dialer Engine que pare el loop.
    2. Genera el reporte final.
    3. Notifica al dashboard.
    """
    logger.info(
        "Campaign stopped",
        extra={'campaign_id': campaign.id, 'reason': reason, 'user_id': user.id},
    )

    # Señal de parada al Dialer Engine
    try:
        from apps.campaigns.tasks import stop_campaign_in_dialer
        stop_campaign_in_dialer.delay(campaign.id)
    except Exception as e:
        logger.error(f"[Dialer] Error enviando parada de campaña {campaign.id}: {e}")

    # Reporte final asíncrono (crea el Report de cierre y genera el Excel)
    try:
        from apps.reports.tasks import generate_campaign_report
        generate_campaign_report.delay(campaign.id)
    except Exception as e:
        logger.error(f"[Reports] Error generando reporte final de campaña {campaign.id}: {e}")

    # Notificar dashboard
    _push_campaign_update(campaign.id, 'stopped')


# ──────────────────────────────────────────────────────────────────────────────
# Agent event handlers
# ──────────────────────────────────────────────────────────────────────────────

@receiver(agent_logged_in)
def on_agent_logged_in(sender, agent, user, **kwargs):
    """Al hacer login, añadir el agente a todas sus colas ACD."""
    logger.info(
        "Agent logged in",
        extra={'agent_id': agent.id, 'agent_code': agent.agent_id, 'user_id': user.id},
    )

    from apps.queues.models import QueueMember
    for membership in QueueMember.objects.filter(agent=agent).select_related('queue'):
        try:
            from apps.telephony.services import QueueService
            QueueService.add_agent_to_queue(
                queue_name=membership.queue.name,
                agent_extension=agent.sip_extension,
                agent_name=str(agent),
                penalty=membership.penalty,
            )
        except Exception as e:
            logger.error(f"[Queue] Error añadiendo {agent.agent_id} a {membership.queue.name}: {e}")


@receiver(agent_logged_out)
def on_agent_logged_out(sender, agent, user, session_duration=None, **kwargs):
    """Al hacer logout, retirar el agente de todas sus colas ACD."""
    logger.info(
        "Agent logged out",
        extra={'agent_id': agent.id, 'session_duration': session_duration, 'user_id': user.id},
    )

    from apps.queues.models import QueueMember
    for membership in QueueMember.objects.filter(agent=agent).select_related('queue'):
        try:
            from apps.telephony.services import QueueService
            QueueService.remove_agent_from_queue(
                queue_name=membership.queue.name,
                agent_extension=agent.sip_extension,
            )
        except Exception as e:
            logger.error(f"[Queue] Error retirando {agent.agent_id} de {membership.queue.name}: {e}")


@receiver(agent_status_changed)
def on_agent_status_changed(sender, agent, old_status, new_status, reason=None, **kwargs):
    """Al cambiar estado, pausar/despausar al agente en sus colas."""
    logger.info(
        "Agent status changed",
        extra={
            'agent_id': agent.id, 'old_status': old_status,
            'new_status': new_status, 'reason': reason,
        },
    )

    should_pause = new_status in ('break', 'offline', 'wrapup')

    from apps.queues.models import QueueMember
    for membership in QueueMember.objects.filter(agent=agent).select_related('queue'):
        try:
            from apps.telephony.services import QueueService
            QueueService.pause_agent(
                queue_name=membership.queue.name,
                agent_extension=agent.sip_extension,
                paused=should_pause,
                reason=reason,
            )
        except Exception as e:
            logger.error(
                f"[Queue] Error pausando/despausando {agent.agent_id} en {membership.queue.name}: {e}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Call event handlers
# ──────────────────────────────────────────────────────────────────────────────

@receiver(call_completed)
def on_call_completed(sender, call, disposition=None, duration=None, **kwargs):
    """
    Al completar una llamada:
    1. Actualizar estadísticas de la campaña.
    2. Encolar procesamiento de grabación si existe.
    """
    logger.info(
        "Call completed",
        extra={
            'call_id': call.id,
            'duration': duration,
            'disposition': disposition.code if disposition else None,
        },
    )

    # Actualizar estadísticas de campaña
    if call.campaign_id:
        try:
            from apps.campaigns.tasks import update_campaign_statistics
            update_campaign_statistics.delay(call.campaign_id)
        except Exception as e:
            logger.error(f"[Stats] Error actualizando campaña {call.campaign_id}: {e}")

    # Procesar grabación si el campo tiene ruta
    if call.recording_file:
        try:
            from apps.recordings.tasks import link_recording_to_call
            link_recording_to_call.apply_async(args=[call.call_id], countdown=30)
        except Exception as e:
            logger.error(f"[Recording] Error encolando grabación para {call.call_id}: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# System event handlers
# ──────────────────────────────────────────────────────────────────────────────

@receiver(ami_connection_lost)
def on_ami_connection_lost(sender, error, **kwargs):
    """Registrar pérdida de conexión AMI y emitir alerta."""
    logger.error("AMI connection lost", extra={'error': str(error)}, exc_info=True)
    # TODO: enviar alerta (email / Slack / PagerDuty)


@receiver(ami_connection_restored)
def on_ami_connection_restored(sender, **kwargs):
    logger.info("AMI connection restored")


@receiver(circuit_breaker_opened)
def on_circuit_breaker_opened(sender, service, error_count, **kwargs):
    logger.warning(
        f"Circuit breaker opened for {service}",
        extra={'service': service, 'error_count': error_count},
    )
    # TODO: enviar alerta


def register_event_handlers():
    """Registrar todos los event handlers. Llamado en apps.CoreConfig.ready()."""
    logger.info("Event handlers registered")
