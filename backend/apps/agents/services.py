"""
Agent business logic services

This module provides a service layer for agent operations, handling all
agent-related business logic including login/logout, status changes, breaks,
and statistics. It emits events for cross-module communication.

Example:
    >>> from apps.agents.services import AgentService
    >>> result = AgentService.login_agent(agent_id=1, user=request.user)
    >>> print(result['status'])
    'available'
"""
import logging
from django.db import transaction
from django.utils import timezone
from typing import Dict, Optional
from datetime import timedelta

from core.exceptions import (
    AgentNotFoundError,
    AgentNotAvailableError,
    InvalidAgentStateError
)
from apps.agents.models import Agent, AgentStatusHistory
from core.metrics import agent_status_gauge
from core.events import emit_event, agent_logged_in, agent_logged_out, agent_status_changed

logger = logging.getLogger(__name__)


class AgentService:
    """
    Service class for agent business logic operations.
    
    This service handles all agent-related operations including authentication,
    status management, breaks, and performance statistics. It maintains metrics
    and emits events for cross-module communication.
    
    All methods are static and can be called without instantiation.
    """
    
    @staticmethod
    @transaction.atomic
    def login_agent(agent_id: int, user) -> Dict:
        """
        Log in an agent and mark them as available for calls.
        
        This method performs the following operations:
        1. Validates agent exists
        2. Updates agent status to available
        3. Records login time
        4. Updates Prometheus metrics
        5. Emits agent_logged_in event (which adds agent to queues)
        6. Logs the action
        
        Args:
            agent_id (int): The ID of the agent to log in
            user: The User object of the person logging in (usually the agent themselves)
            
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded
                - agent_id (int): The agent database ID
                - agent_code (str): The agent's code (e.g., 'AGT001')
                - status (str): The new agent status ('available')
                - sip_extension (str): The agent's SIP extension
            
        Raises:
            AgentNotFoundError: If the agent with given ID doesn't exist
            
        Example:
            >>> result = AgentService.login_agent(agent_id=1, user=request.user)
            >>> print(f"Agent {result['agent_code']} logged in on ext {result['sip_extension']}")
        """
        try:
            agent = Agent.objects.select_related('user').get(id=agent_id)
        except Agent.DoesNotExist:
            raise AgentNotFoundError(f"Agent {agent_id} not found")
        
        # Login agent
        agent.login()
        
        # Update metrics
        agent_status_gauge.labels(
            agent_id=agent.agent_id,
            status='available'
        ).set(1)
        
        # Emit event (will add agent to queues)
        emit_event(agent_logged_in, sender=Agent, agent=agent, user=user)
        
        logger.info(
            "Agent logged in",
            extra={
                'agent_id': agent_id,
                'agent_code': agent.agent_id,
                'user_id': user.id,
                'sip_extension': agent.sip_extension
            }
        )
        
        return {
            'success': True,
            'agent_id': agent.id,
            'agent_code': agent.agent_id,
            'status': agent.status,
            'sip_extension': agent.sip_extension
        }
    
    @staticmethod
    @transaction.atomic
    def logout_agent(agent_id: int, user) -> Dict:
        """
        Log out an agent
        
        Args:
            agent_id: Agent ID
            user: User logging out
            
        Returns:
            dict: Result with agent info
        """
        try:
            agent = Agent.objects.get(id=agent_id)
        except Agent.DoesNotExist:
            raise AgentNotFoundError(f"Agent {agent_id} not found")
        
        old_status = agent.status
        agent.logout()
        
        # Update metrics
        agent_status_gauge.labels(
            agent_id=agent.agent_id,
            status=old_status
        ).set(0)
        
        # Emit event (will remove agent from queues)
        emit_event(
            agent_logged_out,
            sender=Agent,
            agent=agent,
            user=user,
            session_duration=agent.session_duration
        )
        
        logger.info(
            "Agent logged out",
            extra={
                'agent_id': agent_id,
                'agent_code': agent.agent_id,
                'user_id': user.id,
                'session_duration': agent.session_duration
            }
        )
        
        return {
            'success': True,
            'agent_id': agent.id,
            'status': agent.status,
            'session_duration': agent.session_duration
        }
    
    @staticmethod
    @transaction.atomic
    def change_status(
        agent_id: int,
        new_status: str,
        reason: Optional[str] = None,
        user = None
    ) -> Dict:
        """
        Change agent status
        
        Args:
            agent_id: Agent ID
            new_status: New status (available, oncall, break, wrapup, offline)
            reason: Optional reason for status change
            user: User making the change
            
        Returns:
            dict: Result with agent info
            
        Raises:
            AgentNotFoundError: If agent doesn't exist
            InvalidAgentStateError: If status transition is invalid
        """
        try:
            agent = Agent.objects.get(id=agent_id)
        except Agent.DoesNotExist:
            raise AgentNotFoundError(f"Agent {agent_id} not found")
        
        # Validate status
        valid_statuses = dict(Agent.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            raise InvalidAgentStateError(
                f"Invalid status '{new_status}'. Valid: {list(valid_statuses)}"
            )
        
        old_status = agent.status
        
        # Update status
        agent.status = new_status
        agent.save()
        
        # Create status history
        AgentStatusHistory.objects.create(
            agent=agent,
            status=new_status,
            reason=reason or f"Changed from {old_status}"
        )
        
        # Update metrics
        agent_status_gauge.labels(
            agent_id=agent.agent_id,
            status=old_status
        ).set(0)
        agent_status_gauge.labels(
            agent_id=agent.agent_id,
            status=new_status
        ).set(1)
        
        # Emit event (will pause/unpause in queues)
        emit_event(
            agent_status_changed,
            sender=Agent,
            agent=agent,
            old_status=old_status,
            new_status=new_status,
            reason=reason
        )
        
        logger.info(
            "Agent status changed",
            extra={
                'agent_id': agent_id,
                'agent_code': agent.agent_id,
                'old_status': old_status,
                'new_status': new_status,
                'reason': reason,
                'user_id': user.id if user else None
            }
        )
        
        return {
            'success': True,
            'agent_id': agent.id,
            'old_status': old_status,
            'new_status': new_status
        }
    
    @staticmethod
    def get_agent_statistics(agent_id: int, date: Optional[timezone.datetime] = None) -> Dict:
        """
        Get detailed agent statistics
        
        Args:
            agent_id: Agent ID
            date: Optional date for statistics (defaults to today)
            
        Returns:
            dict: Agent statistics
        """
        try:
            agent = Agent.objects.select_related('user').get(id=agent_id)
        except Agent.DoesNotExist:
            raise AgentNotFoundError(f"Agent {agent_id} not found")
        
        if date is None:
            date = timezone.now().date()
        
        # Get calls for the date
        from apps.telephony.models import Call
        
        calls = Call.objects.filter(
            agent=agent,
            start_time__date=date
        )
        
        # Calculate statistics
        total_calls = calls.count()
        answered_calls = calls.filter(status='answered').count()
        completed_calls = calls.filter(status='completed').count()
        
        # Calculate times
        total_talk_time = sum(
            (call.talk_time or 0 for call in calls),
            timedelta()
        )
        
        # Get status history for the date
        status_history = AgentStatusHistory.objects.filter(
            agent=agent,
            started_at__date=date
        ).order_by('started_at')
        
        # Calculate time in each status
        status_times = {}
        for status_code, status_name in Agent.STATUS_CHOICES:
            duration = sum(
                (
                    (h.ended_at or timezone.now()) - h.started_at
                    for h in status_history.filter(status=status_code)
                ),
                timedelta()
            )
            status_times[status_code] = duration.total_seconds()
        
        stats = {
            'agent_id': agent.id,
            'agent_code': agent.agent_id,
            'agent_name': str(agent),
            'date': date.isoformat(),
            'current_status': agent.status,
            'is_available': agent.is_available,
            'calls': {
                'total': total_calls,
                'answered': answered_calls,
                'completed': completed_calls,
                'answer_rate': (answered_calls / total_calls * 100) if total_calls > 0 else 0
            },
            'times': {
                'talk_time': total_talk_time.total_seconds(),
                'available_time': status_times.get('available', 0),
                'break_time': status_times.get('break', 0),
                'oncall_time': status_times.get('oncall', 0),
                'wrapup_time': status_times.get('wrapup', 0),
            },
            'performance': {
                'occupancy': agent.occupancy,
                'avg_talk_time': (total_talk_time.total_seconds() / total_calls) if total_calls > 0 else 0
            }
        }
        
        return stats
    
    @staticmethod
    @transaction.atomic
    def start_break(
        agent_id: int,
        reason: str = 'personal',
        user = None
    ) -> Dict:
        """
        Start agent break
        
        Args:
            agent_id: Agent ID
            reason: Break reason
            user: User starting break
            
        Returns:
            dict: Result with agent info
        """
        return AgentService.change_status(
            agent_id=agent_id,
            new_status='break',
            reason=reason,
            user=user
        )
    
    @staticmethod
    @transaction.atomic
    def end_break(agent_id: int, user = None) -> Dict:
        """
        End agent break and return to available
        
        Args:
            agent_id: Agent ID
            user: User ending break
            
        Returns:
            dict: Result with agent info
        """
        return AgentService.change_status(
            agent_id=agent_id,
            new_status='available',
            reason='Break ended',
            user=user
        )
    
    @staticmethod
    def get_available_agents(campaign_id: Optional[int] = None) -> list:
        """
        Get list of available agents
        
        Args:
            campaign_id: Optional campaign ID to filter agents
            
        Returns:
            list: List of available agent dictionaries
        """
        queryset = Agent.objects.filter(
            status='available',
            is_available=True
        ).select_related('user')
        
        if campaign_id:
            queryset = queryset.filter(campaigns__id=campaign_id)
        
        agents = []
        for agent in queryset:
            agents.append({
                'id': agent.id,
                'agent_id': agent.agent_id,
                'name': str(agent),
                'sip_extension': agent.sip_extension,
                'calls_today': agent.calls_today,
                'occupancy': agent.occupancy
            })
        
        return agents
