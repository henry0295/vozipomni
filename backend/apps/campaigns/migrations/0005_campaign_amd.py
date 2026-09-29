from django.db import migrations, models


class Migration(migrations.Migration):
    """Detección de contestador automático (AMD) por campaña."""

    dependencies = [
        ('campaigns', '0004_campaignform_campaign_form_campaign_is_template_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='amd_enabled',
            field=models.BooleanField(
                default=False, verbose_name='Detectar contestador (AMD)',
                help_text='Solo marcador predictivo: las llamadas atendidas por buzón no pasan a los agentes.',
            ),
        ),
        migrations.AddField(
            model_name='campaign',
            name='amd_action',
            field=models.CharField(
                choices=[('hangup', 'Colgar'), ('message', 'Dejar mensaje grabado')],
                default='hangup', max_length=20, verbose_name='Acción ante contestador',
            ),
        ),
        migrations.AddField(
            model_name='campaign',
            name='amd_message',
            field=models.CharField(
                blank=True, default='', max_length=200, verbose_name='Audio para el contestador',
                help_text='Nombre del audio en Asterisk (sin extensión), ej: custom/mensaje-campana',
            ),
        ),
    ]
