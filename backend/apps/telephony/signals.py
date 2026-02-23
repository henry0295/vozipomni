"""
Signal handlers para sincronizar cambios en modelos con Asterisk.
Ejecución SÍNCRONA directa via threads (sin dependencia de Celery).
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import (
    SIPTrunk, InboundRoute, OutboundRoute, Extension, IVR,
    Voicemail, TimeCondition, Call
)
from apps.queues.models import Queue, QueueMember
import logging
import threading

logger = logging.getLogger(__name__)

# Flag para evitar re-entrancia de sincronización
_sync_lock = threading.Lock()


def _sync_asterisk_config():
    """
    Regenera TODA la config de Asterisk y recarga.
    Se ejecuta en un thread separado para no bloquear el request HTTP.
    """
    if not _sync_lock.acquire(blocking=False):
        logger.debug("Sincronización ya en curso, omitiendo")
        return

    try:
        from .pjsip_config_generator import PJSIPConfigGenerator
        from .asterisk_config import AsteriskConfigGenerator

        # 1. Regenerar troncales (pjsip_wizard.conf)
        pjsip_gen = PJSIPConfigGenerator()
        success, msg = pjsip_gen.save_and_reload()
        if success:
            logger.info(f"✓ Troncales PJSIP sincronizadas: {msg}")
        else:
            logger.error(f"✗ Error sincronizando troncales: {msg}")

        # 2. Regenerar extensiones, dialplan, voicemail, etc.
        config_gen = AsteriskConfigGenerator()
        config_gen.write_all_configs()

        # 3. Recargar módulos de Asterisk
        from .asterisk_ami import AsteriskAMI
        ami = AsteriskAMI()
        if ami.connect():
            ami.reload_module('res_pjsip.so')
            ami.reload_module('chan_pjsip.so')
            ami.reload_dialplan()
            ami.reload_module('app_voicemail.so')
            ami.reload_module('app_queue.so')
            ami.disconnect()
            logger.info("✓ Asterisk recargado (PJSIP, dialplan, voicemail, queues)")

    except Exception as e:
        logger.error(f"✗ Error sincronizando config Asterisk: {e}")
    finally:
        _sync_lock.release()


def sync_asterisk_now():
    """Lanza la sincronización en background thread"""
    t = threading.Thread(target=_sync_asterisk_config, daemon=True)
    t.start()


# ============= SEÑALES PARA TRONCALES SIP =============

@receiver(post_save, sender=SIPTrunk)
def on_sip_trunk_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"✨ Nueva troncal SIP creada: {instance.name}")
    else:
        logger.info(f"🔄 Troncal SIP actualizada: {instance.name}")
    sync_asterisk_now()


@receiver(post_delete, sender=SIPTrunk)
def on_sip_trunk_delete(sender, instance, **kwargs):
    logger.info(f"🗑️  Troncal SIP eliminada: {instance.name}")
    sync_asterisk_now()


# ============= SEÑALES PARA RUTAS ENTRANTES =============

@receiver(post_save, sender=InboundRoute)
def on_inbound_route_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"✨ Nueva ruta entrante creada: {instance.did}")
    else:
        logger.info(f"🔄 Ruta entrante actualizada: {instance.did}")
    sync_asterisk_now()


@receiver(post_delete, sender=InboundRoute)
def on_inbound_route_delete(sender, instance, **kwargs):
    logger.info(f"🗑️  Ruta entrante eliminada: {instance.did}")
    sync_asterisk_now()


# ============= SEÑALES PARA RUTAS SALIENTES =============

@receiver(post_save, sender=OutboundRoute)
def on_outbound_route_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"✨ Nueva ruta saliente creada: {instance.name}")
    else:
        logger.info(f"🔄 Ruta saliente actualizada: {instance.name}")
    sync_asterisk_now()


@receiver(post_delete, sender=OutboundRoute)
def on_outbound_route_delete(sender, instance, **kwargs):
    logger.info(f"🗑️  Ruta saliente eliminada: {instance.name}")
    sync_asterisk_now()


# ============= SEÑALES PARA EXTENSIONES =============

@receiver(post_save, sender=Extension)
def on_extension_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"✨ Nueva extensión creada: {instance.extension}")
    else:
        logger.info(f"🔄 Extensión actualizada: {instance.extension}")
    sync_asterisk_now()


@receiver(post_delete, sender=Extension)
def on_extension_delete(sender, instance, **kwargs):
    logger.info(f"🗑️  Extensión eliminada: {instance.extension}")
    sync_asterisk_now()


# ============= SEÑALES PARA IVRs =============

@receiver(post_save, sender=IVR)
def on_ivr_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"✨ Nuevo IVR creado: {instance.name}")
    else:
        logger.info(f"🔄 IVR actualizado: {instance.name}")
    sync_asterisk_now()


@receiver(post_delete, sender=IVR)
def on_ivr_delete(sender, instance, **kwargs):
    logger.info(f"🗑️  IVR eliminado: {instance.name}")
    sync_asterisk_now()


# ============= SEÑALES PARA BUZONES DE VOZ =============

@receiver(post_save, sender=Voicemail)
def on_voicemail_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"✨ Nuevo buzón de voz creado: {instance.mailbox}")
    else:
        logger.info(f"🔄 Buzón de voz actualizado: {instance.mailbox}")
    sync_asterisk_now()


@receiver(post_delete, sender=Voicemail)
def on_voicemail_delete(sender, instance, **kwargs):
    logger.info(f"🗑️  Buzón de voz eliminado: {instance.mailbox}")
    sync_asterisk_now()


# ============= SEÑALES PARA CONDICIONES DE HORARIO =============

@receiver(post_save, sender=TimeCondition)
def on_time_condition_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"✨ Nueva condición de horario creada: {instance.name}")
    else:
        logger.info(f"🔄 Condición de horario actualizada: {instance.name}")
    sync_asterisk_now()


@receiver(post_delete, sender=TimeCondition)
def on_time_condition_delete(sender, instance, **kwargs):
    logger.info(f"🗑️  Condición de horario eliminada: {instance.name}")
    sync_asterisk_now()


# ============= SEÑALES PARA COLAS =============

@receiver(post_save, sender=Queue)
def on_queue_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"✨ Nueva cola creada: {instance.name}")
    else:
        logger.info(f"🔄 Cola actualizada: {instance.name}")
    sync_asterisk_now()


@receiver(post_delete, sender=Queue)
def on_queue_delete(sender, instance, **kwargs):
    logger.info(f"🗑️  Cola eliminada: {instance.name}")
    sync_asterisk_now()


@receiver(post_save, sender=QueueMember)
def on_queue_member_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"✨ Miembro agregado a cola {instance.queue.name}: agente {instance.agent}")
    else:
        logger.info(f"🔄 Miembro actualizado en cola {instance.queue.name}")
    sync_asterisk_now()


@receiver(post_delete, sender=QueueMember)
def on_queue_member_delete(sender, instance, **kwargs):
    logger.info(f"🗑️  Miembro eliminado de cola {instance.queue.name}")
    sync_asterisk_now()


# ============= SEÑALES PARA LLAMADAS =============

@receiver(post_save, sender=Call)
def on_call_save(sender, instance, created, **kwargs):
    if created and instance.status == 'completed':
        if instance.agent:
            from django.db.models import F
            instance.agent.total_calls = F('total_calls') + 1
            instance.agent.total_talk_time = F('total_talk_time') + instance.talk_time
            instance.agent.save(update_fields=['total_calls', 'total_talk_time'])
            logger.debug(f"Estadística del agente {instance.agent.user.username} actualizada")


# ============= INSTALACIÓN DE SEÑALES =============

def register_telephony_signals():
    """Registrar todos los signal handlers - llamar en apps.py"""
    logger.info("📡 Signal handlers de telefonía registrados")
