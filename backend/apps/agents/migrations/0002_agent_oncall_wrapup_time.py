"""
Migración: Agregar campos oncall_time_today y wrapup_time_today al modelo Agent
para tracking de tiempo en llamada y post-llamada.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='oncall_time_today',
            field=models.IntegerField(
                default=0,
                help_text='Segundos',
                verbose_name='Tiempo en llamada hoy',
            ),
        ),
        migrations.AddField(
            model_name='agent',
            name='wrapup_time_today',
            field=models.IntegerField(
                default=0,
                help_text='Segundos',
                verbose_name='Tiempo post-llamada hoy',
            ),
        ),
    ]
