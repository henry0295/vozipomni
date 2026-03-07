"""
Event system for decoupling modules
Uses Django signals for event-driven architecture
"""
from django.dispatch import Signal
import logging

logger = logging.getLogger(__name__)

# Campaign events
campaign_started = Signal()  # providing_args=['campaign', 'user']
campaign_paused = Signal()  # providing_args=['campaign', 'user']
campaign_stopped = Signal()  # providing_args=['campaign', 'user', 'reason']
campaign_completed = Signal()  # providing_args=['campaign', 'stats']

# Agent events
agent_logged_in = Signal()  # providing_args=['agent', 'user']
agent_logged_out = Signal()  # providing_args=['agent', 'user', 'session_duration']
agent_status_changed = Signal()  # providing_args=['agent', 'old_status', 'new_status', 'reason']
agent_break_started = Signal()  # providing_args=['agent', 'reason']
agent_break_ended = Signal()  # providing_args=['agent', 'duration']

# Call events
call_initiated = Signal()  # providing_args=['call', 'agent', 'campaign']
call_answered = Signal()  # providing_args=['call', 'agent']
call_completed = Signal()  # providing_args=['call', 'disposition', 'duration']
call_failed = Signal()  # providing_args=['call', 'reason']
call_transferred = Signal()  # providing_args=['call', 'from_agent', 'to_agent']

# Contact events
contact_created = Signal()  # providing_args=['contact', 'contact_list']
contact_updated = Signal()  # providing_args=['contact', 'changes']
contact_status_changed = Signal()  # providing_args=['contact', 'old_status', 'new_status']
contacts_imported = Signal()  # providing_args=['contact_list', 'count', 'user']

# Queue events
queue_member_added = Signal()  # providing_args=['queue', 'agent']
queue_member_removed = Signal()  # providing_args=['queue', 'agent']
queue_member_paused = Signal()  # providing_args=['queue', 'agent', 'reason']
queue_member_unpaused = Signal()  # providing_args=['queue', 'agent']

# Recording events
recording_started = Signal()  # providing_args=['call', 'filename']
recording_completed = Signal()  # providing_args=['recording', 'duration']
recording_transcribed = Signal()  # providing_args=['recording', 'transcription']

# System events
ami_connection_lost = Signal()  # providing_args=['error']
ami_connection_restored = Signal()  # providing_args=[]
circuit_breaker_opened = Signal()  # providing_args=['service', 'error_count']
circuit_breaker_closed = Signal()  # providing_args=['service']


def emit_event(signal, sender, **kwargs):
    """
    Helper function to emit events with logging
    
    Args:
        signal: Django signal to emit
        sender: Sender object
        **kwargs: Event data
    """
    try:
        signal.send(sender=sender, **kwargs)
        logger.debug(
            f"Event emitted: {signal}",
            extra={
                'signal': str(signal),
                'sender': str(sender),
                'data': kwargs
            }
        )
    except Exception as e:
        logger.error(
            f"Error emitting event: {signal}",
            extra={
                'signal': str(signal),
                'sender': str(sender),
                'error': str(e)
            },
            exc_info=True
        )
