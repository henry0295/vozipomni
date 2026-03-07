# Generated migration for encrypting SIP passwords

from django.db import migrations
import core.fields


class Migration(migrations.Migration):

    dependencies = [
        ('telephony', '0008_create_default_extensions'),
    ]

    operations = [
        # Nota: Esta migración cambia el tipo de campo pero NO encripta datos existentes
        # Para encriptar datos existentes, ejecutar: python manage.py encrypt_sip_passwords
        
        migrations.AlterField(
            model_name='extension',
            name='secret',
            field=core.fields.EncryptedCharField(max_length=100, verbose_name='Contraseña'),
        ),
        migrations.AlterField(
            model_name='siptrunk',
            name='outbound_auth_password',
            field=core.fields.EncryptedCharField(blank=True, max_length=100, verbose_name='Contraseña Saliente'),
        ),
        migrations.AlterField(
            model_name='siptrunk',
            name='inbound_auth_password',
            field=core.fields.EncryptedCharField(blank=True, max_length=100, verbose_name='Contraseña Entrante'),
        ),
    ]
