"""
WhatsApp Business Cloud API (integración directa con Meta):
  - WhatsAppProvider, WhatsAppLine, WhatsAppTemplate
  - Message: message_type, status, error_message, sender, metadata; body opcional
  - Conversation: contact_name, last_message_at, last_inbound_at
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import apps.messaging.models
import core.fields


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0002_alter_message_external_id'),
        ('campaigns', '0004_campaignform_campaign_form_campaign_is_template_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Conversation ──────────────────────────────────────────────────────
        migrations.AddField(
            model_name='conversation', name='contact_name',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='conversation', name='last_message_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation', name='last_inbound_at',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # ── Message ───────────────────────────────────────────────────────────
        migrations.AlterField(
            model_name='message', name='body',
            field=models.TextField(blank=True, verbose_name='Cuerpo del mensaje'),
        ),
        migrations.AddField(
            model_name='message', name='message_type',
            field=models.CharField(choices=[
                ('text', 'Texto'), ('template', 'Plantilla'), ('image', 'Imagen'), ('audio', 'Audio'),
                ('video', 'Video'), ('document', 'Documento'), ('sticker', 'Sticker'),
                ('location', 'Ubicación'), ('contacts', 'Contactos'), ('interactive', 'Interactivo'),
                ('button', 'Botón'), ('reaction', 'Reacción'), ('system', 'Sistema'), ('unknown', 'Desconocido'),
            ], default='text', max_length=20),
        ),
        migrations.AddField(
            model_name='message', name='status',
            field=models.CharField(choices=[
                ('pending', 'Pendiente'), ('sent', 'Enviado'), ('delivered', 'Entregado'),
                ('read', 'Leído'), ('failed', 'Fallido'), ('received', 'Recibido'),
            ], default='sent', max_length=20),
        ),
        migrations.AddField(
            model_name='message', name='error_message',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='message', name='metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='message', name='sender',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='sent_messages', to=settings.AUTH_USER_MODEL,
                help_text='Usuario que envió el mensaje (salientes)',
            ),
        ),
        migrations.AlterField(
            model_name='message', name='external_id',
            field=models.CharField(
                blank=True, db_index=True, max_length=255, null=True,
                help_text='ID del mensaje en la plataforma externa (WhatsApp, Twilio, etc.)',
            ),
        ),

        # ── WhatsAppProvider ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='WhatsAppProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nombre')),
                ('app_id', models.CharField(max_length=64, unique=True, verbose_name='App ID')),
                ('app_secret', core.fields.EncryptedCharField(
                    blank=True, default='', max_length=255, verbose_name='App Secret',
                    help_text='Se usa para validar la firma X-Hub-Signature-256 de los webhooks.')),
                ('access_token', core.fields.EncryptedTextField(
                    blank=True, default='', verbose_name='Token de acceso',
                    help_text='Token permanente del Usuario del Sistema (Business Manager) con permisos '
                              'whatsapp_business_messaging y whatsapp_business_management.')),
                ('verify_token', models.CharField(
                    default=apps.messaging.models._generate_verify_token, max_length=100,
                    verbose_name='Token de verificación',
                    help_text='Se ingresa en Meta al configurar el webhook.')),
                ('api_version', models.CharField(default='v21.0', max_length=10, verbose_name='Versión Graph API')),
                ('business_id', models.CharField(blank=True, default='', max_length=64, verbose_name='Business Portfolio ID')),
                ('is_active', models.BooleanField(default=True)),
                ('webhook_verified', models.BooleanField(default=False)),
                ('webhook_verified_at', models.DateTimeField(blank=True, null=True)),
                ('last_webhook_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Proveedor WhatsApp (Meta)',
                'verbose_name_plural': 'Proveedores WhatsApp (Meta)',
                'db_table': 'whatsapp_providers',
                'ordering': ['name'],
            },
        ),

        # ── WhatsAppLine ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name='WhatsAppLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nombre de la línea')),
                ('waba_id', models.CharField(max_length=64, verbose_name='WhatsApp Business Account ID')),
                ('phone_number_id', models.CharField(max_length=64, unique=True, verbose_name='Phone Number ID')),
                ('display_phone_number', models.CharField(blank=True, default='', max_length=30)),
                ('verified_name', models.CharField(blank=True, default='', max_length=200)),
                ('quality_rating', models.CharField(blank=True, default='', max_length=20)),
                ('messaging_limit', models.CharField(blank=True, default='', max_length=40)),
                ('status', models.CharField(choices=[
                    ('pending', 'Pendiente de verificación'), ('connected', 'Conectada'),
                    ('error', 'Error'), ('disabled', 'Deshabilitada'),
                ], default='pending', max_length=20)),
                ('status_detail', models.TextField(blank=True, default='')),
                ('webhook_subscribed', models.BooleanField(default=False)),
                ('auto_assign', models.BooleanField(
                    default=True, verbose_name='Asignación automática',
                    help_text='Asignar las conversaciones nuevas al agente disponible con menos chats abiertos.')),
                ('max_chats_per_agent', models.PositiveIntegerField(default=5, verbose_name='Chats simultáneos por agente')),
                ('welcome_message', models.TextField(
                    blank=True, default='', verbose_name='Mensaje de bienvenida',
                    help_text='Respuesta automática al primer mensaje de una conversación nueva.')),
                ('is_active', models.BooleanField(default=True)),
                ('last_sync_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('channel', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name='whatsapp_line', to='messaging.channel')),
                ('default_campaign', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='whatsapp_lines', to='campaigns.campaign', verbose_name='Campaña por defecto')),
                ('provider', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name='lines', to='messaging.whatsappprovider')),
            ],
            options={
                'verbose_name': 'Línea WhatsApp',
                'verbose_name_plural': 'Líneas WhatsApp',
                'db_table': 'whatsapp_lines',
                'ordering': ['name'],
            },
        ),

        # ── WhatsAppTemplate ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='WhatsAppTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('meta_id', models.CharField(blank=True, default='', max_length=64)),
                ('name', models.CharField(max_length=512)),
                ('language', models.CharField(default='es', max_length=15)),
                ('category', models.CharField(blank=True, default='', max_length=30)),
                ('status', models.CharField(blank=True, default='', max_length=30)),
                ('rejected_reason', models.CharField(blank=True, default='', max_length=200)),
                ('components', models.JSONField(blank=True, default=list)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('line', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='templates', to='messaging.whatsappline')),
            ],
            options={
                'verbose_name': 'Plantilla WhatsApp',
                'verbose_name_plural': 'Plantillas WhatsApp',
                'db_table': 'whatsapp_templates',
                'ordering': ['name', 'language'],
                'unique_together': {('line', 'name', 'language')},
            },
        ),
    ]
