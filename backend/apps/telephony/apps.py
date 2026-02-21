from django.apps import AppConfig
import threading
import logging

logger = logging.getLogger(__name__)


def _startup_sync_asterisk():
    """
    Al iniciar el backend, verificar si pjsip_wizard.conf tiene contenido real.
    Si solo tiene el placeholder del entrypoint, regenerar la config
    para que Asterisk cargue las troncales existentes en la BD.
    Se ejecuta con delay para dar tiempo a Asterisk a arrancar.
    """
    import time
    time.sleep(10)  # Esperar a que Asterisk esté listo

    try:
        config_path = '/var/lib/asterisk/dynamic/pjsip_wizard.conf'
        needs_regen = False

        try:
            with open(config_path, 'r') as f:
                content = f.read().strip()
            # Si solo tiene el placeholder o está vacío, regenerar
            if not content or content.startswith('; Auto-generated placeholder'):
                needs_regen = True
                logger.info("pjsip_wizard.conf es placeholder, verificando troncales en BD...")
        except FileNotFoundError:
            needs_regen = True
            logger.info("pjsip_wizard.conf no existe, verificando troncales en BD...")

        if needs_regen:
            from .models import SIPTrunk
            active_count = SIPTrunk.objects.filter(is_active=True).count()
            if active_count > 0:
                logger.info(f"Regenerando config PJSIP para {active_count} troncales activas...")
                from .pjsip_config_generator import PJSIPConfigGenerator
                gen = PJSIPConfigGenerator()
                success, msg = gen.save_and_reload()
                if success:
                    logger.info(f"✓ Config PJSIP regenerada al inicio: {msg}")
                else:
                    logger.warning(f"✗ Error regenerando config al inicio: {msg}")
            else:
                logger.info("No hay troncales activas en BD, nada que regenerar")
    except Exception as e:
        logger.warning(f"Error en startup sync de Asterisk (no crítico): {e}")


class TelephonyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.telephony'
    verbose_name = 'Telefonía'
    
    def ready(self):
        """Registrar signal handlers cuando la app se carga"""
        from .signals import register_telephony_signals
        register_telephony_signals()

        # Sincronizar config Asterisk al iniciar (en background para no bloquear)
        import os
        if os.environ.get('RUN_MAIN') != 'true':  # Evitar doble ejecución en dev
            t = threading.Thread(target=_startup_sync_asterisk, daemon=True)
            t.start()
