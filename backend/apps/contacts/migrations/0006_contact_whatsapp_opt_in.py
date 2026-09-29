from django.db import migrations, models


class Migration(migrations.Migration):
    """Consentimiento (opt-in) de WhatsApp por contacto."""

    dependencies = [
        ('contacts', '0005_alter_contact_status_add_callback'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='whatsapp_opt_in',
            field=models.BooleanField(default=False, verbose_name='Acepta WhatsApp'),
        ),
        migrations.AddField(
            model_name='contact',
            name='whatsapp_opt_in_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='contact',
            name='whatsapp_opt_in_source',
            field=models.CharField(
                blank=True, default='', max_length=50,
                help_text='Origen del consentimiento: import, formulario, keyword, agente…',
            ),
        ),
    ]
