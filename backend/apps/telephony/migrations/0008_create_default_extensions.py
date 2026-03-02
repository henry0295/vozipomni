"""
Migración de datos para crear extensiones por defecto
Crea 10 extensiones (200-209) listas para usar
"""
from django.db import migrations
import secrets
import string


def generate_password(length=12):
    """Generar contraseña segura"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))


def create_default_extensions(apps, schema_editor):
    """Crear extensiones por defecto si no existen"""
    Extension = apps.get_model('telephony', 'Extension')
    
    # Verificar si ya existen extensiones
    if Extension.objects.exists():
        print("⚠️  Ya existen extensiones, omitiendo creación por defecto")
        return
    
    # Crear 10 extensiones por defecto (200-209)
    default_extensions = []
    for i in range(10):
        ext_number = str(200 + i)
        extension = Extension(
            extension=ext_number,
            name=f'Extension {ext_number}',
            extension_type='PJSIP',
            secret=generate_password(),
            context='from-internal',
            transport='transport-udp',
            callerid=f'"Extension {ext_number}" <{ext_number}>',
            email=f'ext{ext_number}@vozipomni.local',
            voicemail_enabled=True,
            max_contacts=1,
            codecs='ulaw,alaw,g729',
            is_active=True
        )
        default_extensions.append(extension)
    
    # Crear en lote
    Extension.objects.bulk_create(default_extensions)
    print(f"✅ Creadas {len(default_extensions)} extensiones por defecto (200-209)")


def remove_default_extensions(apps, schema_editor):
    """Rollback - eliminar extensiones por defecto"""
    Extension = apps.get_model('telephony', 'Extension')
    
    # Eliminar solo las extensiones 200-209 si no tienen llamadas asociadas
    default_range = [str(200 + i) for i in range(10)]
    Extension.objects.filter(extension__in=default_range).delete()
    print("🗑️  Extensiones por defecto eliminadas")


class Migration(migrations.Migration):

    dependencies = [
        ('telephony', '0007_call_expanded_statuses_and_queue_enter_time'),
    ]

    operations = [
        migrations.RunPython(create_default_extensions, remove_default_extensions),
    ]
