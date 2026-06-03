"""
Signals para sincronización automática de extensiones PJSIP de agentes.
Cuando un agente se crea o modifica, se asegura que su extensión en el
módulo de telefonía esté configurada correctamente (WEBRTC si webrtc_enabled).
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='agents.Agent')
def sync_agent_sip_extension(sender, instance, created, update_fields=None, **kwargs):
    """
    Auto-crea o actualiza el registro Extension para el agente.
    Garantiza que los agentes WebRTC tengan extension_type='WEBRTC' y transport='transport-wss'.
    Solo se ejecuta en creación o cuando cambian campos SIP relevantes.
    """
    # Evitar sync en saves que solo actualizan estado (status, last_activity, etc.)
    sip_fields = {'sip_extension', 'sip_password', 'webrtc_enabled'}
    if not created and update_fields is not None and not sip_fields.intersection(set(update_fields)):
        return

    try:
        from apps.telephony.models import Extension

        ext_type = 'WEBRTC' if instance.webrtc_enabled else 'PJSIP'
        transport = 'transport-wss' if instance.webrtc_enabled else 'transport-udp'
        name = instance.user.get_full_name() or instance.user.username

        ext_obj, was_created = Extension.objects.get_or_create(
            extension=instance.sip_extension,
            defaults={
                'name': name,
                'extension_type': ext_type,
                'transport': transport,
                'secret': instance.sip_password or 'VoziPOmni2026!',
                'context': 'from-internal',
                'is_active': True,
            }
        )

        # Si ya existía pero tiene tipo incorrecto, corregirlo
        needs_update = False
        if ext_obj.extension_type != ext_type:
            ext_obj.extension_type = ext_type
            needs_update = True
        if ext_obj.transport != transport:
            ext_obj.transport = transport
            needs_update = True
        if instance.sip_password and ext_obj.secret != instance.sip_password:
            ext_obj.secret = instance.sip_password
            needs_update = True

        if needs_update:
            ext_obj.save()
            logger.info(f"Extension {instance.sip_extension} actualizada → type={ext_type}, transport={transport}")
        elif was_created:
            logger.info(f"Extension {instance.sip_extension} creada → type={ext_type}, transport={transport}")

        # Regenerar configuración Asterisk y recargar PJSIP
        if was_created or needs_update:
            _reload_asterisk_pjsip()

    except Exception as e:
        logger.error(f"Error sincronizando extensión del agente {instance.sip_extension}: {e}")


def _reload_asterisk_pjsip():
    """Regenera pjsip_extensions.conf y recarga PJSIP en Asterisk via AMI."""
    try:
        from apps.telephony.asterisk_config import AsteriskConfigGenerator
        generator = AsteriskConfigGenerator()
        generator.write_all_configs()
        logger.info("Configuración Asterisk regenerada por cambio de agente")
    except Exception as e:
        logger.error(f"Error regenerando configuración Asterisk: {e}")
        return

    try:
        from apps.telephony.asterisk_ami import AsteriskAMI
        ami = AsteriskAMI()
        if ami.connect():
            ami.reload_module('res_pjsip.so')
            ami.disconnect()
            logger.info("PJSIP recargado en Asterisk")
    except Exception as e:
        logger.warning(f"No se pudo recargar PJSIP en Asterisk (no crítico): {e}")
