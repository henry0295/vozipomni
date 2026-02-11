from django.apps import AppConfig


class TelephonyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.telephony'
    verbose_name = 'Telefonía'
    
    def ready(self):
        """Registrar signal handlers cuando la app se carga"""
        from .signals import register_telephony_signals
        register_telephony_signals()
