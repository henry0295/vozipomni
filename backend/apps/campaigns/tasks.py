"""
Tareas Celery de campañas.

Responsabilidades:
  - queue_campaign_in_dialer  → publica config + contactos en Redis para el Dialer Engine
  - stop_campaign_in_dialer   → publica señal de parada al Dialer Engine
  - process_pending_calls     → ciclo periódico: asegura que campañas activas estén en Redis
  - update_campaign_statistics → actualiza contadores de contactados/exitosos
"""
import json
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_redis():
    """Obtener cliente Redis (síncrono) reutilizando la configuración de Django."""
    import redis as sync_redis
    from django.conf import settings
    return sync_redis.from_url(settings.REDIS_URL, decode_responses=True)


def _build_campaign_config(campaign):
    """Construir el dict de configuración que el Dialer Engine espera en Redis."""
    return {
        'id': campaign.id,
        'name': campaign.name,
        'campaign_type': campaign.campaign_type,
        'dialer_type': campaign.dialer_type or 'progressive',
        'trunk': _get_default_trunk(),
        'queue_name': campaign.queue.name if campaign.queue else '',
        'caller_id': campaign.queue.caller_id if campaign.queue and hasattr(campaign.queue, 'caller_id') else '1000',
        'context': 'from-internal',
        'max_retries': campaign.max_retries,
        'retry_delay': campaign.retry_delay,
        'call_timeout': campaign.call_timeout,
        'preview_timeout': campaign.preview_timeout,
        'dnc_enabled': campaign.dnc_enabled,
        'timezone': campaign.timezone,
        'vip_priority_boost': campaign.vip_priority_boost,
        'audio_file': 'welcome',       # para call_blasting
        'max_concurrent_calls': 50,    # para call_blasting
        'batch_delay': 5,              # para call_blasting
    }


def _get_default_trunk():
    """Obtener la primera troncal SIP activa como trunk por defecto."""
    try:
        from apps.telephony.models import SIPTrunk
        trunk = SIPTrunk.objects.filter(is_active=True).first()
        return trunk.name if trunk else 'default_trunk'
    except Exception:
        return 'default_trunk'


def _push_contacts_to_redis(r, campaign):
    """
    Carga los contactos pendientes de la campaña en la lista Redis
    `campaign:{id}:contacts:pending`.
    Solo añade contactos que aún no estén en la cola (idempotente).
    """
    from apps.contacts.models import Contact

    pending_key = f'campaign:{campaign.id}:contacts:pending'

    # No recargar si ya hay contactos en la cola
    if r.llen(pending_key) > 0:
        return 0

    if not campaign.contact_list:
        return 0

    contacts = Contact.objects.filter(
        contact_list=campaign.contact_list,
        status__in=['new', 'pending', 'callback'],
    ).order_by('-priority', 'id')

    count = 0
    pipe = r.pipeline(transaction=False)
    for contact in contacts:
        payload = {
            'id': contact.id,
            'phone_number': contact.phone,
            'phone_2': contact.phone2,
            'phone_3': contact.phone3,
            'name': contact.full_name,
            'email': contact.email,
            'company': contact.company,
            'priority': contact.priority,
            'is_vip': contact.is_vip,
            'timezone': contact.timezone,
            'custom_fields': contact.custom_fields,
        }
        pipe.rpush(pending_key, json.dumps(payload))
        count += 1

    if count:
        pipe.expire(pending_key, 86400)  # TTL 24h
        pipe.execute()

    logger.info(f"[Dialer] {count} contactos cargados en Redis para campaña {campaign.id}")
    return count


# ──────────────────────────────────────────────────────────────────────────────
# Tareas
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={'max_retries': 3, 'countdown': 10},
    retry_backoff=True,
    name='campaigns.queue_campaign_in_dialer',
)
def queue_campaign_in_dialer(self, campaign_id: int):
    """
    Publica la configuración de una campaña en Redis para que el Dialer Engine
    la inicie. También precarga los contactos pendientes.

    Flujo:
        CampaignService.start_campaign() → campaign_started signal
        → event_handlers.on_campaign_started() → esta tarea.delay()
        → Dialer Engine (asyncio) levanta el loop de discado
    """
    from apps.campaigns.models import Campaign

    try:
        campaign = Campaign.objects.select_related(
            'contact_list', 'queue'
        ).get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.warning(f"[Dialer] Campaña {campaign_id} no encontrada, omitiendo")
        return

    r = _get_redis()

    # 1. Publicar configuración
    config = _build_campaign_config(campaign)
    r.setex(f'campaign:{campaign_id}:config', 86400, json.dumps(config))

    # 2. Precargar contactos (idempotente)
    contacts_loaded = _push_contacts_to_redis(r, campaign)

    # 3. Publicar evento de inicio para el Dialer Engine
    r.publish('dialer:control', json.dumps({
        'action': 'start_campaign',
        'campaign_id': campaign_id,
        'campaign_type': config['dialer_type'],
    }))

    logger.info(
        f"[Dialer] Campaña {campaign.name} publicada en Redis "
        f"({contacts_loaded} contactos cargados)"
    )
    return {'campaign_id': campaign_id, 'contacts_loaded': contacts_loaded}


@shared_task(
    bind=True,
    name='campaigns.stop_campaign_in_dialer',
)
def stop_campaign_in_dialer(self, campaign_id: int):
    """Notifica al Dialer Engine que pare el loop de una campaña."""
    r = _get_redis()
    r.publish('dialer:control', json.dumps({
        'action': 'stop_campaign',
        'campaign_id': campaign_id,
    }))
    logger.info(f"[Dialer] Señal de parada enviada para campaña {campaign_id}")


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    name='campaigns.process_pending_calls',
)
def process_pending_calls(self):
    """
    Ciclo periódico (ejecutado por Celery Beat cada 60s).
    Asegura que todas las campañas activas tengan su config y contactos en Redis.
    Actúa como red de seguridad si el Dialer Engine reinició y perdió estado.
    """
    from apps.campaigns.models import Campaign

    active_campaigns = Campaign.objects.filter(
        status='active',
        start_date__lte=timezone.now(),
    ).exclude(end_date__lt=timezone.now())

    r = _get_redis()
    processed = 0
    errors = 0

    for campaign in active_campaigns:
        try:
            config_key = f'campaign:{campaign.id}:config'
            # Si no hay config en Redis, republicar (el dialer puede haber reiniciado)
            if not r.exists(config_key):
                logger.warning(
                    f"[Dialer] Config de campaña {campaign.id} ausente en Redis, republicando…"
                )
                queue_campaign_in_dialer.delay(campaign.id)
            else:
                # Refrescar TTL de contactos para evitar expiración durante campañas largas
                pending_key = f'campaign:{campaign.id}:contacts:pending'
                if r.exists(pending_key):
                    r.expire(pending_key, 86400)
            processed += 1
        except Exception as e:
            logger.error(f"[Dialer] Error procesando campaña {campaign.id}: {e}")
            errors += 1

    return f"Verificadas {processed} campañas activas, {errors} errores"


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 10},
    retry_backoff=True,
    name='campaigns.update_campaign_statistics',
)
def update_campaign_statistics(self, campaign_id: int):
    """
    Actualizar contadores de la campaña desde la BD de llamadas.
    Se llama desde el event handler on_call_completed.
    """
    from apps.campaigns.models import Campaign
    from apps.telephony.models import Call

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.warning(f"[Stats] Campaña {campaign_id} no encontrada")
        return f"Campaign {campaign_id} not found"

    try:
        calls = Call.objects.filter(campaign=campaign)
        total = campaign.contact_list.total_contacts if campaign.contact_list else 0
        contacted = calls.filter(status__in=['completed', 'no_answer', 'busy']).count()
        successful = calls.filter(
            status='completed',
            disposition__is_success=True
        ).count()

        campaign.total_contacts = total
        campaign.contacted = contacted
        campaign.successful = successful
        campaign.save(update_fields=['total_contacts', 'contacted', 'successful', 'updated_at'])

        return f"Stats actualizadas: campaña={campaign.name} contactados={contacted} exitosos={successful}"
    except Exception as e:
        logger.error(f"[Stats] Error actualizando campaña {campaign_id}: {e}")
        raise
