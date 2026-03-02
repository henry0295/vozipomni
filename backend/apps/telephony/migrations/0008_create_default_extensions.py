"""
Migración vacía - Preparación para gestión de extensiones mejorada
No crea datos por defecto - Cada instalación crea sus propias extensiones desde cero
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('telephony', '0007_call_expanded_statuses_and_queue_enter_time'),
    ]

    operations = [
        # Sin operaciones - Solo actualización de funcionalidad
        # Las extensiones se crean desde el frontend o API según necesidades de cada cliente
    ]
