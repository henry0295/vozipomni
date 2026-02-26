"""
Migración: Agregar nuevos estados de llamada (voicemail, abandoned, transferred)
y campo queue_enter_time para tracking preciso de colas.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telephony', '0006_extension_pjsip_upgrade'),
    ]

    operations = [
        # Actualizar STATUS_CHOICES en el campo status del modelo Call
        migrations.AlterField(
            model_name='call',
            name='status',
            field=models.CharField(
                choices=[
                    ('initiated', 'Iniciada'),
                    ('ringing', 'Timbrando'),
                    ('answered', 'Contestada'),
                    ('completed', 'Completada'),
                    ('busy', 'Ocupado'),
                    ('no_answer', 'No Contestada'),
                    ('failed', 'Fallida'),
                    ('cancelled', 'Cancelada'),
                    ('voicemail', 'Buzón de Voz'),
                    ('abandoned', 'Abandonada'),
                    ('transferred', 'Transferida'),
                ],
                default='initiated',
                max_length=20,
                verbose_name='Estado',
            ),
        ),
        # Agregar campo queue_enter_time
        migrations.AddField(
            model_name='call',
            name='queue_enter_time',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Hora entrada cola',
            ),
        ),
    ]
