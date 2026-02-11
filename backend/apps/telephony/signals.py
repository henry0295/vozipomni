"""
Signal handlers para sincronizar cambios en modelos con Asterisk y Redis
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import (
    SIPTrunk, InboundRoute, OutboundRoute, Extension, IVR, 
    Voicemail, MusicOnHold, TimeCondition, Call
)
from .tasks import (
    sync_sip_trunk_to_asterisk,
    sync_inbound_route_to_asterisk,
    sync_outbound_route_to_asterisk,
    sync_extension_to_asterisk,
    sync_ivr_to_asterisk,
    sync_voicemail_to_asterisk,
    sync_time_condition_to_asterisk,
    remove_sip_trunk_from_asterisk,
    remove_inbound_route_from_asterisk
)
import logging

logger = logging.getLogger(__name__)


# ============= SEÑALES PARA TRONCALES SIP =============

@receiver(post_save, sender=SIPTrunk)
def on_sip_trunk_save(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza una troncal SIP,
    sincronizar con Asterisk en background
    """
    if created:
        logger.info(f"✨ Nueva troncal SIP creada: {instance.name}")
    else:
        logger.info(f"🔄 Troncal SIP actualizada: {instance.name}")
    
    # Ejecutar tarea de sincronización en background
    sync_sip_trunk_to_asterisk.apply_async(args=[instance.id], countdown=2)


@receiver(post_delete, sender=SIPTrunk)
def on_sip_trunk_delete(sender, instance, **kwargs):
    """
    Cuando se elimina una troncal SIP,
    limpiar de Asterisk
    """
    logger.info(f"🗑️  Troncal SIP eliminada: {instance.name}")
    remove_sip_trunk_from_asterisk.apply_async(args=[instance.name], countdown=2)


# ============= SEÑALES PARA RUTAS ENTRANTES =============

@receiver(post_save, sender=InboundRoute)
def on_inbound_route_save(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza una ruta entrante,
    sincronizar con Asterisk
    """
    if created:
        logger.info(f"✨ Nueva ruta entrante creada: {instance.did}")
    else:
        logger.info(f"🔄 Ruta entrante actualizada: {instance.did}")
    
    sync_inbound_route_to_asterisk.apply_async(args=[instance.id], countdown=2)


@receiver(post_delete, sender=InboundRoute)
def on_inbound_route_delete(sender, instance, **kwargs):
    """
    Cuando se elimina una ruta entrante,
    limpiar de Asterisk
    """
    logger.info(f"🗑️  Ruta entrante eliminada: {instance.did}")
    remove_inbound_route_from_asterisk.apply_async(args=[instance.did], countdown=2)


# ============= SEÑALES PARA RUTAS SALIENTES =============

@receiver(post_save, sender=OutboundRoute)
def on_outbound_route_save(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza una ruta saliente,
    sincronizar con Asterisk
    """
    if created:
        logger.info(f"✨ Nueva ruta saliente creada: {instance.name}")
    else:
        logger.info(f"🔄 Ruta saliente actualizada: {instance.name}")
    
    sync_outbound_route_to_asterisk.apply_async(args=[instance.id], countdown=2)


@receiver(post_delete, sender=OutboundRoute)
def on_outbound_route_delete(sender, instance, **kwargs):
    """Limpiar ruta saliente de Asterisk"""
    logger.info(f"🗑️  Ruta saliente eliminada: {instance.name}")
    from django.core.cache import cache
    cache.delete(f"outbound_route:{instance.id}")


# ============= SEÑALES PARA EXTENSIONES =============

@receiver(post_save, sender=Extension)
def on_extension_save(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza una extensión,
    sincronizar con Asterisk
    """
    if created:
        logger.info(f"✨ Nueva extensión creada: {instance.extension}")
    else:
        logger.info(f"🔄 Extensión actualizada: {instance.extension}")
    
    sync_extension_to_asterisk.apply_async(args=[instance.id], countdown=2)


@receiver(post_delete, sender=Extension)
def on_extension_delete(sender, instance, **kwargs):
    """Limpiar extensión de Asterisk"""
    logger.info(f"🗑️  Extensión eliminada: {instance.extension}")
    from django.core.cache import cache
    cache.delete(f"extension:{instance.extension}")


# ============= SEÑALES PARA IVRs =============

@receiver(post_save, sender=IVR)
def on_ivr_save(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza un IVR,
    sincronizar con Asterisk
    """
    if created:
        logger.info(f"✨ Nuevo IVR creado: {instance.name}")
    else:
        logger.info(f"🔄 IVR actualizado: {instance.name}")
    
    sync_ivr_to_asterisk.apply_async(args=[instance.id], countdown=2)


@receiver(post_delete, sender=IVR)
def on_ivr_delete(sender, instance, **kwargs):
    """Limpiar IVR de Asterisk"""
    logger.info(f"🗑️  IVR eliminado: {instance.name}")
    from django.core.cache import cache
    cache.delete(f"ivr:{instance.extension}")


# ============= SEÑALES PARA BUZONES DE VOZ =============

@receiver(post_save, sender=Voicemail)
def on_voicemail_save(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza un buzón de voz,
    sincronizar con Asterisk
    """
    if created:
        logger.info(f"✨ Nuevo buzón de voz creado: {instance.mailbox}")
    else:
        logger.info(f"🔄 Buzón de voz actualizado: {instance.mailbox}")
    
    sync_voicemail_to_asterisk.apply_async(args=[instance.id], countdown=2)


@receiver(post_delete, sender=Voicemail)
def on_voicemail_delete(sender, instance, **kwargs):
    """Limpiar buzón de voz de Asterisk"""
    logger.info(f"🗑️  Buzón de voz eliminado: {instance.mailbox}")
    from django.core.cache import cache
    cache.delete(f"voicemail:{instance.mailbox}")


# ============= SEÑALES PARA CONDICIONES DE HORARIO =============

@receiver(post_save, sender=TimeCondition)
def on_time_condition_save(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza una condición de horario,
    sincronizar con Asterisk
    """
    if created:
        logger.info(f"✨ Nueva condición de horario creada: {instance.name}")
    else:
        logger.info(f"🔄 Condición de horario actualizada: {instance.name}")
    
    sync_time_condition_to_asterisk.apply_async(args=[instance.id], countdown=2)


@receiver(post_delete, sender=TimeCondition)
def on_time_condition_delete(sender, instance, **kwargs):
    """Limpiar condición de horario de Asterisk"""
    logger.info(f"🗑️  Condición de horario eliminada: {instance.name}")
    from django.core.cache import cache
    cache.delete(f"time_condition:{instance.id}")


# ============= SEÑALES PARA LLAMADAS =============

@receiver(post_save, sender=Call)
def on_call_save(sender, instance, created, **kwargs):
    """
    Cuando se crea o actualiza un registro de llamada,
    actualizar estadísticas
    """
    if created and instance.status == 'completed':
        # Actualizar métricas del agente
        if instance.agent:
            from django.db.models import F
            instance.agent.total_calls = F('total_calls') + 1
            instance.agent.total_talk_time = F('total_talk_time') + instance.talk_time
            instance.agent.save(update_fields=['total_calls', 'total_talk_time'])
            logger.debug(f"Estadística del agente {instance.agent.user.username} actualizada")


# ============= INSTALACIÓN DE SEÑALES =============

def register_telephony_signals():
    """
    Registrar todos los signal handlers
    Llamar en apps.py
    """
    logger.info("📡 Signal handlers de telefonía registrados")
