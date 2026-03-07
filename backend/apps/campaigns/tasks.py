from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def process_pending_calls(self):
    """
    Procesar llamadas pendientes en campañas activas
    Con retry automático en caso de errores de conexión
    """
    from apps.campaigns.models import Campaign
    from apps.telephony.services import DialerService
    
    active_campaigns = Campaign.objects.filter(
        status='active',
        start_date__lte=timezone.now(),
    ).exclude(end_date__lt=timezone.now())
    
    processed = 0
    errors = 0
    
    for campaign in active_campaigns:
        try:
            dialer = DialerService(campaign)
            dialer.process_pending_contacts()
            processed += 1
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Connection error processing campaign {campaign.id}: {str(e)}")
            errors += 1
            raise  # Permitir retry automático
        except Exception as e:
            logger.error(f"Error processing campaign {campaign.id}: {str(e)}")
            errors += 1
            # No hacer raise para continuar con otras campañas
    
    return f"Processed {processed} campaigns, {errors} errors"


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 10},
    retry_backoff=True
)
def update_campaign_statistics(self, campaign_id):
    """
    Actualizar estadísticas de una campaña
    Con retry automático
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
        logger.error(f"Campaign {campaign_id} not found")
        return f"Campaign {campaign_id} not found"
    except Exception as e:
        logger.error(f"Error updating campaign {campaign_id} statistics: {e}")
        raise  # Permitir retry
