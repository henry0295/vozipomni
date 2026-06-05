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
from apps.agents.models import Agent
import logging
import os
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
    # Actualizar estadísticas de agente
    if instance.status == 'completed' and instance.agent:
        try:
            from django.db.models import F
            instance.agent.__class__.objects.filter(pk=instance.agent_id).update(
                calls_today=F('calls_today') + (1 if created else 0),
            )
        except Exception as e:
            logger.debug(f"Error updating agent stats: {e}")

    # Disparar webhooks según estado
    _dispatch_call_webhook(instance, created)


def _dispatch_call_webhook(instance, created):
    """Despachar webhook para eventos de llamada en background."""
    try:
        event_map = {
            'answered':  'call.answered',
            'completed': 'call.completed',
            'abandoned': 'call.abandoned',
        }
        if created:
            event_type = 'call.initiated'
        else:
            event_type = event_map.get(instance.status)

        if not event_type:
            return

        payload = {
            'event': event_type,
            'call_id': instance.call_id,
            'direction': instance.direction,
            'status': instance.status,
            'caller_id': instance.caller_id,
            'called_number': instance.called_number,
            'agent_id': instance.agent_id,
            'campaign_id': instance.campaign_id,
            'queue_id': instance.queue_id,
            'duration': instance.duration,
            'talk_time': instance.talk_time,
            'start_time': instance.start_time.isoformat() if instance.start_time else None,
        }
        # Asincrónico via Celery para no bloquear el request
        from apps.telephony.tasks import deliver_webhook as _dw
        from apps.telephony.models import WebhookEndpoint
        endpoints = WebhookEndpoint.objects.filter(is_active=True).values_list('id', 'events')
        for ep_id, ep_events in endpoints:
            if not ep_events or event_type in ep_events:
                _dw.delay(ep_id, event_type, payload)
    except Exception as e:
        logger.debug(f"Webhook dispatch error (non-critical): {e}")


# ============= SEÑALES PARA AGENTES (PJSIP WebRTC) =============

@receiver(post_save, sender=Agent)
def on_agent_save(sender, instance, created, **kwargs):
    """Regenerar pjsip_agents.conf cuando un agente es creado o modificado."""
    action = 'creado' if created else 'actualizado'
    logger.info(f"👤 Agente {action}: {instance.sip_extension}")
    _sync_agent_pjsip()


@receiver(post_delete, sender=Agent)
def on_agent_delete(sender, instance, **kwargs):
    """Regenerar pjsip_agents.conf cuando un agente es eliminado."""
    logger.info(f"🗑️  Agente eliminado: {instance.sip_extension}")
    _sync_agent_pjsip()


def _sync_agent_pjsip():
    """Regenerar /var/lib/asterisk/dynamic/pjsip_agents.conf y recargar PJSIP."""
    def _do_sync():
        try:
            agents = Agent.objects.filter(webrtc_enabled=True).select_related('user')
            config_path = '/var/lib/asterisk/dynamic/pjsip_agents.conf'
            # KAMAILIO_HOST: nombre DNS del contenedor Kamailio (bridge) o IP del servidor (host network)
            # En docker-compose bridge: 'kamailio' (service name resuelve en la red interna)
            # En producción network_mode:host: configurar KAMAILIO_HOST=localhost o IP real
            kamailio_host = os.environ.get('KAMAILIO_HOST', 'kamailio')
            lines = [
                '; Auto-generated by VozipOmni – NO EDITAR MANUALMENTE',
                '; Agentes WebRTC para Asterisk PJSIP',
                '',
            ]
            for a in agents:
                ext = a.sip_extension
                password = a.sip_password or ext
                display = a.user.get_full_name() or ext
                lines += [
                    f'[{ext}](webrtc_endpoint)',
                    f'auth={ext}-auth',
                    f'aors={ext}-aor',
                    f'callerid="{display}" <{ext}>',
                    '',
                    f'[{ext}-auth]',
                    'type=auth',
                    'auth_type=userpass',
                    f'username={ext}',
                    f'password={password}',
                    '',
                    f'[{ext}-aor]',
                    'type=aor',
                    'max_contacts=2',
                    # remove_existing=no: NO borrar el contacto estático al recibir un REGISTER
                    # desde Kamailio. Con =yes Asterisk eliminaría el contact cada vez que
                    # procesa un REGISTER y el agente quedaría inalcanzable.
                    'remove_existing=no',
                    # Contacto estático apuntando a Kamailio: cuando Asterisk marca PJSIP/{ext},
                    # envía el INVITE a Kamailio que lo enruta al browser del agente vía WebSocket.
                    # Sin este contact= el AOR queda vacío y la llamada falla con CHANUNAVAIL.
                    f'contact=sip:{ext}@{kamailio_host}:5060',
                    'qualify_frequency=30',
                    '',
                ]
            try:
                with open(config_path, 'w') as f:
                    f.write('\n'.join(lines))
                logger.info(f"✓ pjsip_agents.conf generado con {agents.count()} agentes")
            except OSError as e:
                logger.warning(f"No se pudo escribir pjsip_agents.conf (normal fuera de Docker): {e}")
                return

            from .asterisk_ami import AsteriskAMI
            ami = AsteriskAMI()
            if ami.connect():
                ami.reload_module('res_pjsip.so')
                ami.disconnect()
                logger.info("✓ Asterisk PJSIP recargado para agentes WebRTC")
        except Exception as e:
            logger.error(f"✗ Error sincronizando PJSIP de agentes: {e}")

    t = threading.Thread(target=_do_sync, daemon=True)
    t.start()


# ============= INSTALACIÓN DE SEÑALES =============

def register_telephony_signals():
    """Registrar todos los signal handlers - llamar en apps.py"""
    logger.info("📡 Signal handlers de telefonía registrados")
