from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_pending_calls():
    """
    Procesar llamadas pendientes en campañas activas
    """
    from apps.campaigns.models import Campaign
    from apps.telephony.services import DialerService
    
    active_campaigns = Campaign.objects.filter(
        status='active',
        start_date__lte=timezone.now(),
    ).exclude(end_date__lt=timezone.now())
    
    for campaign in active_campaigns:
        try:
            dialer = DialerService(campaign)
            dialer.process_pending_contacts()
        except Exception as e:
            logger.error(f"Error processing campaign {campaign.id}: {str(e)}")
    
    return f"Processed {active_campaigns.count()} campaigns"


@shared_task
def update_campaign_statistics(campaign_id):
    """
    Actualizar estadísticas de una campaña
    """
    from apps.campaigns.models import Campaign
    from apps.telephony.models import Call
    
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        calls = Call.objects.filter(campaign=campaign)
        
        campaign.total_contacts = campaign.contact_list.contacts.count() if campaign.contact_list else 0
        campaign.contacted = calls.filter(status='completed').count()
        campaign.successful = calls.filter(
            status='completed',
            disposition__is_success=True
        ).count()
        campaign.save()
        
        return f"Updated statistics for campaign {campaign.name}"
    except Campaign.DoesNotExist:
        return f"Campaign {campaign_id} not found"
