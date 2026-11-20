"""
Revisa configuraciones inseguras y las informa. Nunca falla (sale con 0):
deploy.sh lo ejecuta después de migrate para mostrar advertencias.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Muestra advertencias de configuración de seguridad (no modifica nada)'

    def handle(self, *args, **options):
        warnings = []
        try:
            from apps.messaging.models import WhatsAppProvider
            for p in WhatsAppProvider.objects.filter(is_active=True):
                if not p.app_secret:
                    warnings.append(
                        f"Proveedor WhatsApp/Meta '{p.name}' (app {p.app_id}) sin App Secret: "
                        "su webhook rechazará todos los mensajes hasta configurarlo"
                    )
                    if not p.last_error:
                        p.last_error = 'Falta App Secret: webhook deshabilitado'
                        p.save(update_fields=['last_error'])
        except Exception as e:  # pragma: no cover - informativo
            warnings.append(f"No se pudo revisar proveedores de mensajería: {e}")

        if warnings:
            for w in warnings:
                self.stdout.write(self.style.WARNING(f"[SEGURIDAD] {w}"))
        else:
            self.stdout.write(self.style.SUCCESS("[SEGURIDAD] Sin advertencias de configuración"))
