from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Contacto opcional en las devoluciones de llamada (calificación con rellamada, A-8)."""

    dependencies = [
        ('telephony', '0018_telephony_security'),
        ('contacts', '0006_contact_whatsapp_opt_in'),
    ]

    operations = [
        migrations.AddField(
            model_name='callbackrequest',
            name='contact',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='callbacks', to='contacts.contact', verbose_name='Contacto'),
        ),
    ]
