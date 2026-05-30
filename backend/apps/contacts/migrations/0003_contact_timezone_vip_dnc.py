from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Agrega campo timezone a Contact para time zone intelligence,
    y campos priority_vip, dnc_opt_out para DNC y priorización VIP.
    """

    dependencies = [
        ('contacts', '0002_rename_contacts_contact_c87e9d_idx_contacts_contact_2ce835_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='timezone',
            field=models.CharField(
                blank=True, default='', max_length=50,
                verbose_name='Zona horaria',
                help_text='Ej: America/Bogota, America/New_York. Usado para no marcar fuera de horario.',
            ),
        ),
        migrations.AddField(
            model_name='contact',
            name='is_vip',
            field=models.BooleanField(default=False, verbose_name='VIP'),
        ),
        migrations.AddField(
            model_name='contact',
            name='dnc_opt_out',
            field=models.BooleanField(
                default=False, verbose_name='No llamar (DNC)',
                help_text='Contacto solicitó no ser contactado (Do Not Call).',
            ),
        ),
    ]
