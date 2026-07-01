# Generated manually to sync model validators with migrations

from django.db import migrations, models
import core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('telephony', '0015_ivr_timeout_invalid_destinations'),
    ]

    operations = [
        migrations.AlterField(
            model_name='call',
            name='caller_id',
            field=models.CharField(max_length=50, validators=[core.validators.validate_phone_number], verbose_name='Llamante'),
        ),
        migrations.AlterField(
            model_name='call',
            name='called_number',
            field=models.CharField(max_length=50, validators=[core.validators.validate_phone_number], verbose_name='Número llamado'),
        ),
        migrations.AlterField(
            model_name='call',
            name='transfer_to',
            field=models.CharField(blank=True, max_length=100, validators=[core.validators.validate_phone_number], verbose_name='Transferida a'),
        ),
        migrations.AlterField(
            model_name='siptrunk',
            name='host',
            field=models.CharField(max_length=200, validators=[core.validators.validate_ip_address], verbose_name='Host/IP o FQDN'),
        ),
        migrations.AlterField(
            model_name='siptrunk',
            name='port',
            field=models.IntegerField(default=5060, validators=[core.validators.validate_port_number], verbose_name='Puerto'),
        ),
    ]
