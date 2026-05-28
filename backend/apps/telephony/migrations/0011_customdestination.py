from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telephony', '0010_add_performance_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomDestination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
                ('description', models.TextField(blank=True, verbose_name='Descripción')),
                ('context', models.CharField(max_length=100, verbose_name='Context')),
                ('extension', models.CharField(default='s', max_length=50, verbose_name='Extension')),
                ('priority', models.PositiveIntegerField(default=1, verbose_name='Priority')),
                ('failover_context', models.CharField(blank=True, max_length=100, verbose_name='Context (fallo)')),
                ('failover_extension', models.CharField(blank=True, max_length=50, verbose_name='Extension (fallo)')),
                ('failover_priority', models.PositiveIntegerField(blank=True, null=True, verbose_name='Priority (fallo)')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Destino Personalizado',
                'verbose_name_plural': 'Destinos Personalizados',
                'db_table': 'custom_destinations',
                'ordering': ['name'],
            },
        ),
        migrations.AlterField(
            model_name='timecondition',
            name='true_destination_type',
            field=models.CharField(
                choices=[
                    ('ivr', 'IVR'),
                    ('queue', 'Cola'),
                    ('extension', 'Extensión'),
                    ('voicemail', 'Buzón de Voz'),
                    ('announcement', 'Anuncio'),
                    ('custom_destination', 'Destino Personalizado'),
                ],
                max_length=20,
                verbose_name='Tipo destino (true)',
            ),
        ),
        migrations.AlterField(
            model_name='timecondition',
            name='false_destination_type',
            field=models.CharField(
                choices=[
                    ('ivr', 'IVR'),
                    ('queue', 'Cola'),
                    ('extension', 'Extensión'),
                    ('voicemail', 'Buzón de Voz'),
                    ('announcement', 'Anuncio'),
                    ('custom_destination', 'Destino Personalizado'),
                ],
                max_length=20,
                verbose_name='Tipo destino (false)',
            ),
        ),
    ]
