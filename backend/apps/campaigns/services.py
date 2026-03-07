"""
Campaign business logic services

This module provides a service layer for campaign operations, separating
business logic from views and providing a clean API for campaign management.

Example:
    >>> from apps.campaigns.services import CampaignService
    >>> result = CampaignService.start_campaign(campaign_id=1, user=request.user)
    >>> print(result['status'])
    'active'
"""
import logging
from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Optional

from core.exceptions import (
    CampaignAlreadyActiveError,
    CampaignNotFoundError,
    NoContactsError,
    InvalidCampaignStateError
)
from apps.campaigns.models import Campaign, CampaignDisposition
from apps.contacts.models import Contact
from core.metrics import campaign_calls_total, campaign_active
from core.events import emit_event, campaign_started, campaign_stopped, campaign_paused

logger = logging.getLogger(__name__)


class CampaignService:
    """
    Service class for campaign business logic operations.
    
    This service handles all campaign-related business logic including
    starting, pausing, stopping campaigns, and managing campaign statistics.
    It emits events for cross-module communication and maintains metrics.
    
    All methods are static and can be called without instantiation.
    """
    
    @staticmethod
    @transaction.atomic
    def start_campaign(campaign_id: int, user) -> Dict:
        """
        Start a campaign with comprehensive validation and setup.
        
        This method performs the following operations:
        1. Validates campaign exists and is not already active
        2. Checks campaign has contacts (for outbound campaigns)
        3. Updates campaign status to active
        4. Updates Prometheus metrics
        5. Queues campaign in dialer engine
        6. Emits campaign_started event
        7. Logs the action
        
        Args:
            campaign_id (int): The ID of the campaign to start
            user: The User object of the person starting the campaign
            
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded
                - campaign_id (int): The campaign ID
                - campaign_name (str): The campaign name
                - status (str): The new campaign status ('active')
            
        Raises:
            CampaignNotFoundError: If the campaign with given ID doesn't exist
            CampaignAlreadyActiveError: If the campaign is already in active status
            NoContactsError: If outbound/preview campaign has no contacts to process
            
        Example:
            >>> result = CampaignService.start_campaign(campaign_id=1, user=request.user)
            >>> if result['success']:
            ...     print(f"Campaign {result['campaign_name']} started")
        """
        try:
            campaign = Campaign.objects.select_related(
                'contact_list', 'queue'
            ).get(id=campaign_id)
        except Campaign.DoesNotExist:
            raise CampaignNotFoundError(f"Campaign {campaign_id} not found")
        
        # Validations
        if campaign.status == 'active':
            raise CampaignAlreadyActiveError(
                f"Campaign '{campaign.name}' is already active"
            )
        
        if campaign.campaign_type in ['outbound', 'preview']:
            if not campaign.contact_list or campaign.contact_list.total_contacts == 0:
                raise NoContactsError(
                    f"Campaign '{campaign.name}' has no contacts to process"
                )
        
        # Start campaign
        campaign.status = 'active'
        campaign.save()
        
        # Update metrics
        campaign_active.labels(
            campaign_type=campaign.campaign_type,
            dialer_type=campaign.dialer_type or 'none'
        ).inc()
        
        # Emit event for cross-module communication
        emit_event(campaign_started, sender=Campaign, campaign=campaign, user=user)
        
        # Log action
        logger.info(
            "Campaign started",
            extra={
                'campaign_id': campaign_id,
                'campaign_name': campaign.name,
                'user_id': user.id,
                'contacts_count': campaign.total_contacts
            }
        )
        
        return {
            'success': True,
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'status': campaign.status
        }
    
    @staticmethod
    @transaction.atomic
    def pause_campaign(campaign_id: int, user) -> Dict:
        """
        Pause an active campaign temporarily.
        
        Pausing a campaign stops new calls from being initiated but allows
        current calls to complete. The campaign can be resumed later.
        
        Args:
            campaign_id (int): The ID of the campaign to pause
            user: The User object of the person pausing the campaign
            
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded
                - campaign_id (int): The campaign ID
                - campaign_name (str): The campaign name
                - status (str): The new campaign status ('paused')
            
        Raises:
            CampaignNotFoundError: If the campaign with given ID doesn't exist
            InvalidCampaignStateError: If the campaign is not in active status
            
        Example:
            >>> result = CampaignService.pause_campaign(campaign_id=1, user=request.user)
            >>> print(result['status'])
            'paused'
        """
        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            raise CampaignNotFoundError(f"Campaign {campaign_id} not found")
        
        if campaign.status != 'active':
            raise InvalidCampaignStateError(
                f"Campaign '{campaign.name}' is not active"
            )
        
        campaign.status = 'paused'
        campaign.save()
        
        # Update metrics
        campaign_active.labels(
            campaign_type=campaign.campaign_type,
            dialer_type=campaign.dialer_type or 'none'
        ).dec()
        
        # Emit event
        emit_event(campaign_paused, sender=Campaign, campaign=campaign, user=user)
        
        logger.info(
            "Campaign paused",
            extra={
                'campaign_id': campaign_id,
                'campaign_name': campaign.name,
                'user_id': user.id
            }
        )
        
        return {
            'success': True,
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'status': campaign.status
        }
    
    @staticmethod
    @transaction.atomic
    def stop_campaign(campaign_id: int, user) -> Dict:
        """
        Stop a campaign completely and permanently.
        
        Stopping a campaign marks it as finished and sets the end date.
        Unlike pausing, a stopped campaign cannot be resumed and is considered
        complete. Final reports are generated automatically.
        
        Args:
            campaign_id (int): The ID of the campaign to stop
            user: The User object of the person stopping the campaign
            
        Returns:
            dict: A dictionary containing:
                - success (bool): True if operation succeeded
                - campaign_id (int): The campaign ID
                - campaign_name (str): The campaign name
                - status (str): The new campaign status ('finished')
            
        Raises:
            CampaignNotFoundError: If the campaign with given ID doesn't exist
            
        Example:
            >>> result = CampaignService.stop_campaign(campaign_id=1, user=request.user)
            >>> print(result['status'])
            'finished'
        """
        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            raise CampaignNotFoundError(f"Campaign {campaign_id} not found")
        
        old_status = campaign.status
        campaign.status = 'finished'
        campaign.end_date = timezone.now()
        campaign.save()
        
        # Update metrics
        if old_status == 'active':
            campaign_active.labels(
                campaign_type=campaign.campaign_type,
                dialer_type=campaign.dialer_type or 'none'
            ).dec()
        
        # Emit event
        emit_event(campaign_stopped, sender=Campaign, campaign=campaign, user=user, reason='Manual stop')
        
        logger.info(
            "Campaign stopped",
            extra={
                'campaign_id': campaign_id,
                'campaign_name': campaign.name,
                'user_id': user.id,
                'old_status': old_status
            }
        )
        
        return {
            'success': True,
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'status': campaign.status
        }
    
    @staticmethod
    def get_campaign_statistics(campaign_id: int) -> Dict:
        """
        Get detailed campaign statistics
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            dict: Campaign statistics
        """
        try:
            campaign = Campaign.objects.select_related(
                'contact_list'
            ).prefetch_related(
                'calls', 'dispositions'
            ).get(id=campaign_id)
        except Campaign.DoesNotExist:
            raise CampaignNotFoundError(f"Campaign {campaign_id} not found")
        
        # Calculate statistics
        from apps.telephony.models import Call
        
        calls = Call.objects.filter(campaign=campaign)
        
        stats = {
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'status': campaign.status,
            'total_contacts': campaign.total_contacts,
            'contacted': campaign.contacted,
            'successful': campaign.successful,
            'success_rate': campaign.success_rate,
            'calls': {
                'total': calls.count(),
                'completed': calls.filter(status='completed').count(),
                'answered': calls.filter(status='answered').count(),
                'no_answer': calls.filter(status='no_answer').count(),
                'busy': calls.filter(status='busy').count(),
                'failed': calls.filter(status='failed').count(),
            },
            'dispositions': []
        }
        
        # Disposition breakdown
        for disposition in campaign.dispositions.all():
            count = calls.filter(disposition=disposition).count()
            stats['dispositions'].append({
                'code': disposition.code,
                'name': disposition.name,
                'count': count,
                'is_success': disposition.is_success
            })
        
        return stats
    
    @staticmethod
    @transaction.atomic
    def add_contacts_to_campaign(
        campaign_id: int,
        contact_ids: List[int],
        user
    ) -> Dict:
        """
        Add contacts to a campaign
        
        Args:
            campaign_id: Campaign ID
            contact_ids: List of contact IDs
            user: User adding contacts
            
        Returns:
            dict: Result with count of added contacts
        """
        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            raise CampaignNotFoundError(f"Campaign {campaign_id} not found")
        
        if campaign.status == 'active':
            raise InvalidCampaignStateError(
                "Cannot add contacts to active campaign"
            )
        
        # Validate contacts exist
        contacts = Contact.objects.filter(id__in=contact_ids)
        added_count = contacts.count()
        
        if added_count == 0:
            raise NoContactsError("No valid contacts found")
        
        # Update campaign
        campaign.total_contacts += added_count
        campaign.save()
        
        logger.info(
            "Contacts added to campaign",
            extra={
                'campaign_id': campaign_id,
                'contacts_added': added_count,
                'user_id': user.id
            }
        )
        
        return {
            'success': True,
            'campaign_id': campaign.id,
            'contacts_added': added_count,
            'total_contacts': campaign.total_contacts
        }
