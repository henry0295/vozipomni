from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_policy(apps, schema_editor):
    Policy = apps.get_model('telephony', 'TelephonySecurityPolicy')
    Policy.objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    """Política antifraude de llamadas salientes y registro de eventos de seguridad."""

    dependencies = [
        ('telephony', '0017_call_status_machine'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TelephonySecurityPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('block_international', models.BooleanField(
                    default=True, verbose_name='Bloquear llamadas internacionales',
                    help_text='Números que empiezan por 00 o por + distinto al indicativo del país.')),
                ('home_country_code', models.CharField(default='57', max_length=4, verbose_name='Indicativo del país')),
                ('blocked_prefixes', models.TextField(
                    blank=True, default='01900\n1900', verbose_name='Prefijos bloqueados',
                    help_text='Uno por línea (tarifas especiales, satelitales, destinos de fraude).')),
                ('allowed_prefixes', models.TextField(
                    blank=True, default='', verbose_name='Prefijos permitidos (lista blanca)',
                    help_text='Si se llena, SOLO se permiten números que empiecen por estos prefijos.')),
                ('max_number_length', models.PositiveIntegerField(default=15, verbose_name='Longitud máxima del número')),
                ('max_concurrent_outbound', models.PositiveIntegerField(
                    default=0, help_text='0 = sin límite', verbose_name='Llamadas salientes simultáneas (total)')),
                ('enforce_trunk_channels', models.BooleanField(default=True, verbose_name='Respetar canales máximos por troncal')),
                ('max_calls_per_extension_hour', models.PositiveIntegerField(
                    default=0, help_text='0 = sin límite', verbose_name='Llamadas por extensión por hora')),
                ('alert_emails', models.TextField(
                    blank=True, default='', help_text='Uno por línea. Vacío = administradores activos con email.',
                    verbose_name='Correos de alerta')),
                ('alert_calls_per_10min', models.PositiveIntegerField(
                    default=150, help_text='0 = desactivada', verbose_name='Alerta: llamadas salientes en 10 min')),
                ('alert_international_per_hour', models.PositiveIntegerField(
                    default=5, help_text='0 = desactivada', verbose_name='Alerta: llamadas internacionales por hora')),
                ('alert_blocked_per_10min', models.PositiveIntegerField(
                    default=10, help_text='0 = desactivada', verbose_name='Alerta: intentos bloqueados en 10 min')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'telephony_security_policy',
                'verbose_name': 'Política de seguridad telefónica',
                'verbose_name_plural': 'Política de seguridad telefónica',
            },
        ),
        migrations.CreateModel(
            name='TelephonySecurityEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[
                    ('international', 'Internacional bloqueada'), ('blocked_prefix', 'Prefijo bloqueado'),
                    ('not_allowed', 'Fuera de la lista blanca'), ('too_long', 'Número demasiado largo'),
                    ('trunk_full', 'Troncal sin canales'), ('global_limit', 'Límite total de llamadas'),
                    ('extension_rate', 'Límite por extensión'), ('dialer_blocked', 'Bloqueada en el marcador'),
                    ('alert_spike', 'Alerta: pico de llamadas'),
                    ('alert_international', 'Alerta: llamadas internacionales'),
                    ('alert_blocked', 'Alerta: muchos intentos bloqueados'),
                ], db_index=True, max_length=30)),
                ('severity', models.CharField(choices=[('info', 'Info'), ('warning', 'Advertencia'), ('critical', 'Crítico')],
                                              default='warning', max_length=10)),
                ('number', models.CharField(blank=True, default='', max_length=50)),
                ('trunk', models.CharField(blank=True, default='', max_length=100)),
                ('source', models.CharField(blank=True, default='', help_text='Extensión o sistema de origen', max_length=100)),
                ('detail', models.TextField(blank=True, default='')),
                ('notified', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'db_table': 'telephony_security_events',
                'ordering': ['-created_at'],
                'verbose_name': 'Evento de seguridad telefónica',
                'verbose_name_plural': 'Eventos de seguridad telefónica',
            },
        ),
        migrations.RunPython(create_policy, migrations.RunPython.noop),
    ]
