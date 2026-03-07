"""
Global event handlers for cross-module communication
This reduces coupling by using events instead of direct imports
"""
import logging
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
    circuit_breaker_opened
)

logger = logging.getLogger(__name__)


# ============= CAMPAIGN EVENT HANDLERS =============

@receiver(campaign_started)
def on_campaign_started(sender, campaign, user, **kwargs):
    """
    Handle campaign start event
    - Queue campaign in dialer
    - Send notifications
    - Update metrics
    """
    logger.info(
        f"Campaign started: {campaign.name}",
        extra={
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'user_id': user.id
        }
    )
    
    # Queue in dialer (async task)
    from apps.campaigns.tasks import queue_campaign_in_dialer
    queue_campaign_in_dialer.delay(campaign.id)
    
    # Send WebSocket notification
    try:
        from apps.api.consumers import send_campaign_update
        send_campaign_update(campaign.id, 'started')
    except Exception as e:
        logger.error(f"Error sending campaign notification: {e}")


@receiver(campaign_stopped)
def on_campaign_stopped(sender, campaign, user, reason=None, **kwargs):
    """
    Handle campaign stop event
    - Remove from dialer
    - Generate final report
    - Send notifications
    """
    logger.info(
        f"Campaign stopped: {campaign.name}",
        extra={
            'campaign_id': campaign.id,
            'reason': reason,
            'user_id': user.id
        }
    )
    
    # Generate final report (async)
    from apps.reports.tasks import generate_campaign_report
    generate_campaign_report.delay(campaign.id)
    
    # Send WebSocket notification
    try:
        from apps.api.consumers import send_campaign_update
        send_campaign_update(campaign.id, 'stopped')
    except Exception as e:
        logger.error(f"Error sending campaign notification: {e}")


# ============= AGENT EVENT HANDLERS =============

@receiver(agent_logged_in)
def on_agent_logged_in(sender, agent, user, **kwargs):
    """
    Handle agent login event
    - Add to queues
    - Send notifications
    - Update metrics
    """
    logger.info(
        f"Agent logged in: {agent.agent_id}",
        extra={
            'agent_id': agent.id,
            'agent_code': agent.agent_id,
            'user_id': user.id
        }
    )
    
    # Add agent to their assigned queues
    from apps.queues.models import QueueMember
    for queue_member in QueueMember.objects.filter(agent=agent):
        try:
            from apps.telephony.services import QueueService
            QueueService.add_agent_to_queue(
                queue_name=queue_member.queue.name,
                agent_extension=agent.sip_extension,
                agent_name=str(agent),
                penalty=queue_member.penalty
            )
        except Exception as e:
            logger.error(f"Error adding agent to queue: {e}")


@receiver(agent_logged_out)
def on_agent_logged_out(sender, agent, user, session_duration=None, **kwargs):
    """
    Handle agent logout event
    - Remove from queues
    - Save session statistics
    - Send notifications
    """
    logger.info(
        f"Agent logged out: {agent.agent_id}",
        extra={
            'agent_id': agent.id,
            'session_duration': session_duration,
            'user_id': user.id
        }
    )
    
    # Remove agent from all queues
    from apps.queues.models import QueueMember
    for queue_member in QueueMember.objects.filter(agent=agent):
        try:
            from apps.telephony.services import QueueService
            QueueService.remove_agent_from_queue(
                queue_name=queue_member.queue.name,
                agent_extension=agent.sip_extension
            )
        except Exception as e:
            logger.error(f"Error removing agent from queue: {e}")


@receiver(agent_status_changed)
def on_agent_status_changed(sender, agent, old_status, new_status, reason=None, **kwargs):
    """
    Handle agent status change event
    - Pause/unpause in queues
    - Update availability
    - Send notifications
    """
    logger.info(
        f"Agent status changed: {agent.agent_id} {old_status} -> {new_status}",
        extra={
            'agent_id': agent.id,
            'old_status': old_status,
            'new_status': new_status,
            'reason': reason
        }
    )
    
    # Pause/unpause in queues based on status
    should_pause = new_status in ['break', 'offline', 'wrapup']
    
    from apps.queues.models import QueueMember
    for queue_member in QueueMember.objects.filter(agent=agent):
        try:
            from apps.telephony.services import QueueService
            QueueService.pause_agent(
                queue_name=queue_member.queue.name,
                agent_extension=agent.sip_extension,
                paused=should_pause,
                reason=reason
            )
        except Exception as e:
            logger.error(f"Error pausing/unpausing agent in queue: {e}")


# ============= CALL EVENT HANDLERS =============

@receiver(call_completed)
def on_call_completed(sender, call, disposition=None, duration=None, **kwargs):
    """
    Handle call completion event
    - Update agent statistics
    - Update campaign statistics
    - Trigger recording processing
    """
    logger.info(
        f"Call completed: {call.call_id}",
        extra={
            'call_id': call.id,
            'duration': duration,
            'disposition': disposition.code if disposition else None
        }
    )
    
    # Update campaign statistics (async)
    if call.campaign:
        from apps.campaigns.tasks import update_campaign_statistics
        update_campaign_statistics.delay(call.campaign.id)
    
    # Process recording if exists
    if call.recording_filename:
        from apps.recordings.tasks import process_recording
        process_recording.delay(call.id)


# ============= SYSTEM EVENT HANDLERS =============

@receiver(ami_connection_lost)
def on_ami_connection_lost(sender, error, **kwargs):
    """
    Handle AMI connection loss
    - Log error
    - Send alerts
    - Switch to degraded mode
    """
    logger.error(
        "AMI connection lost",
        extra={'error': str(error)},
        exc_info=True
    )
    
    # Send alert notification
    # TODO: Implement alerting system


@receiver(ami_connection_restored)
def on_ami_connection_restored(sender, **kwargs):
    """
    Handle AMI connection restoration
    - Log recovery
    - Resume normal operations
    """
    logger.info("AMI connection restored")


@receiver(circuit_breaker_opened)
def on_circuit_breaker_opened(sender, service, error_count, **kwargs):
    """
    Handle circuit breaker opening
    - Log event
    - Send alerts
    - Switch to fallback
    """
    logger.warning(
        f"Circuit breaker opened for {service}",
        extra={
            'service': service,
            'error_count': error_count
        }
    )
    
    # Send alert notification
    # TODO: Implement alerting system


def register_event_handlers():
    """
    Register all event handlers
    Call this in apps.py ready() method
    """
    logger.info("Event handlers registered")
