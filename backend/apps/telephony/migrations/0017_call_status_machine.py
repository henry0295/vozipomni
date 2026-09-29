from django.db import migrations, models


class Migration(migrations.Migration):
    """Nuevo estado 'machine' (contestador detectado por AMD en el marcador)."""

    dependencies = [
        ('telephony', '0016_add_missing_validators'),
    ]

    operations = [
        migrations.AlterField(
            model_name='call',
            name='status',
            field=models.CharField(
                choices=[
                    ('initiated', 'Iniciada'), ('ringing', 'Timbrando'), ('answered', 'Contestada'),
                    ('completed', 'Completada'), ('busy', 'Ocupado'), ('no_answer', 'No Contestada'),
                    ('failed', 'Fallida'), ('cancelled', 'Cancelada'), ('voicemail', 'Buzón de Voz'),
                    ('machine', 'Contestador automático'), ('abandoned', 'Abandonada'),
                    ('transferred', 'Transferida'),
                ],
                default='initiated', max_length=20, verbose_name='Estado',
            ),
        ),
    ]
