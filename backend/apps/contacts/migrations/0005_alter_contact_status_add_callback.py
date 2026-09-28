# Generated manually to add 'callback' status choice to Contact

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0004_alter_contact_dnc_opt_out_alter_contact_timezone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='status',
            field=models.CharField(
                choices=[
                    ('new', 'Nuevo'),
                    ('pending', 'Pendiente'),
                    ('callback', 'Rellamada'),
                    ('contacted', 'Contactado'),
                    ('success', 'Exitoso'),
                    ('failed', 'Fallido'),
                    ('blacklisted', 'Lista Negra'),
                ],
                default='new',
                max_length=20,
                verbose_name='Estado',
            ),
        ),
    ]
