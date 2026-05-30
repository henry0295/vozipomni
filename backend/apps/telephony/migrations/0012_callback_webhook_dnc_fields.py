from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('telephony', '0011_customdestination'),
        ('agents', '0005_add_sip_password'),
        ('contacts', '0002_rename_contacts_contact_c87e9d_idx_contacts_contact_2ce835_idx_and_more'),
        ('campaigns', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Modelo CallbackRequest
        migrations.CreateModel(
            name='CallbackRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=30, verbose_name='Teléfono')),
                ('contact_name', models.CharField(blank=True, max_length=200, verbose_name='Nombre contacto')),
                ('notes', models.TextField(blank=True, verbose_name='Notas')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pendiente'),
                        ('scheduled', 'Programado'),
                        ('dialing', 'Marcando'),
                        ('completed', 'Completado'),
                        ('failed', 'Fallido'),
                        ('cancelled', 'Cancelado'),
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='Estado',
                )),
                ('priority', models.IntegerField(default=0, verbose_name='Prioridad')),
                ('scheduled_at', models.DateTimeField(null=True, blank=True, verbose_name='Programado para')),
                ('attempts', models.IntegerField(default=0, verbose_name='Intentos')),
                ('max_attempts', models.IntegerField(default=3, verbose_name='Máx. intentos')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('call', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='callbacks',
                    to='telephony.call',
                    verbose_name='Llamada origen',
                )),
                ('campaign', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='callbacks',
                    to='campaigns.campaign',
                    verbose_name='Campaña',
                )),
                ('agent', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='callbacks_assigned',
                    to='agents.agent',
                    verbose_name='Agente asignado',
                )),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Creado por',
                )),
            ],
            options={
                'db_table': 'callback_requests',
                'ordering': ['-priority', 'scheduled_at'],
                'verbose_name': 'Devolución de Llamada',
                'verbose_name_plural': 'Devoluciones de Llamada',
            },
        ),
        # Índices para CallbackRequest
        migrations.AddIndex(
            model_name='callbackrequest',
            index=models.Index(fields=['status', 'scheduled_at'], name='callback_status_sched_idx'),
        ),
        migrations.AddIndex(
            model_name='callbackrequest',
            index=models.Index(fields=['phone'], name='callback_phone_idx'),
        ),

        # Modelo WebhookEndpoint
        migrations.CreateModel(
            name='WebhookEndpoint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nombre')),
                ('url', models.URLField(max_length=500, verbose_name='URL')),
                ('secret', models.CharField(blank=True, max_length=200, verbose_name='Secret HMAC')),
                ('events', models.JSONField(default=list, verbose_name='Eventos a notificar',
                    help_text='Lista de eventos: call.answered, call.completed, agent.login, campaign.started, etc.')),
                ('headers', models.JSONField(default=dict, blank=True, verbose_name='Headers adicionales')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('retry_on_failure', models.BooleanField(default=True, verbose_name='Reintentar en fallo')),
                ('timeout_seconds', models.IntegerField(default=10, verbose_name='Timeout (seg)')),
                ('last_triggered_at', models.DateTimeField(null=True, blank=True, verbose_name='Última ejecución')),
                ('last_status_code', models.IntegerField(null=True, blank=True, verbose_name='Último código HTTP')),
                ('total_deliveries', models.IntegerField(default=0, verbose_name='Entregas totales')),
                ('failed_deliveries', models.IntegerField(default=0, verbose_name='Entregas fallidas')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'webhook_endpoints',
                'ordering': ['name'],
                'verbose_name': 'Webhook',
                'verbose_name_plural': 'Webhooks',
            },
        ),

        # Modelo WebhookDelivery (log de entregas)
        migrations.CreateModel(
            name='WebhookDelivery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(max_length=100, verbose_name='Tipo de evento')),
                ('payload', models.JSONField(verbose_name='Payload enviado')),
                ('status_code', models.IntegerField(null=True, blank=True, verbose_name='HTTP Status')),
                ('response_body', models.TextField(blank=True, verbose_name='Respuesta')),
                ('success', models.BooleanField(default=False, verbose_name='Exitoso')),
                ('duration_ms', models.IntegerField(default=0, verbose_name='Duración (ms)')),
                ('attempt', models.IntegerField(default=1, verbose_name='Intento')),
                ('error_message', models.TextField(blank=True, verbose_name='Error')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('endpoint', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='deliveries',
                    to='telephony.webhookendpoint',
                )),
            ],
            options={
                'db_table': 'webhook_deliveries',
                'ordering': ['-created_at'],
                'verbose_name': 'Entrega de Webhook',
                'verbose_name_plural': 'Entregas de Webhook',
            },
        ),
    ]
