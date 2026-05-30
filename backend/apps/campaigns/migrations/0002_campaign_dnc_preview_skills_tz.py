from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega campos a Campaign:
    - dnc_enabled: integrar lista negra / DNC antes de marcar
    - preview_timeout: segundos que el agente revisa el contacto antes de marcar (Preview mode)
    - required_skills: skills (AgentGroups) necesarios para agentes de esta campaña
    - timezone: zona horaria de los contactos de la campaña (fallback cuando contacto no tiene TZ)
    """

    dependencies = [
        ('campaigns', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='dnc_enabled',
            field=models.BooleanField(
                default=True, verbose_name='Activar DNC',
                help_text='Verificar lista negra / Do Not Call antes de marcar.',
            ),
        ),
        migrations.AddField(
            model_name='campaign',
            name='preview_timeout',
            field=models.IntegerField(
                default=30, verbose_name='Timeout Preview (seg)',
                help_text='Segundos que el agente dispone para revisar datos del contacto antes de que el sistema marque automáticamente.',
            ),
        ),
        migrations.AddField(
            model_name='campaign',
            name='timezone',
            field=models.CharField(
                blank=True, default='America/Bogota', max_length=50,
                verbose_name='Zona horaria campaña',
                help_text='TZ por defecto para contactos sin zona horaria propia.',
            ),
        ),
        migrations.AddField(
            model_name='campaign',
            name='required_skills',
            field=models.ManyToManyField(
                blank=True,
                to='agents.AgentGroup',
                related_name='campaigns_requiring',
                verbose_name='Skills requeridos',
                help_text='AgentGroups cuyos miembros son elegibles para esta campaña.',
            ),
        ),
        migrations.AddField(
            model_name='campaign',
            name='vip_priority_boost',
            field=models.IntegerField(
                default=10, verbose_name='Boost de prioridad VIP',
                help_text='Valor sumado a la prioridad de contactos marcados como VIP.',
            ),
        ),
    ]
