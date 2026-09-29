"""
Omnicanal:
  - Conversation: tipificación, etiquetas, notas y motivo de cierre, métricas (asignación,
    primera respuesta), aviso fuera de horario, asunto y metadatos
  - Channel: tipos webchat, messenger, instagram
  - WhatsAppLine: horario de atención, mensaje fuera de horario, palabras clave opt-in/opt-out
  - ConversationTag, QuickReply
  - WhatsAppBroadcast, WhatsAppBroadcastRecipient (envíos masivos)
  - EmailAccount, WebChatWidget, MetaPage (Messenger / Instagram)
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import apps.messaging.models
import core.fields


def _routing_fields():
    return [
        ('default_campaign', models.ForeignKey(
            blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
            related_name='+', to='campaigns.campaign', verbose_name='Campaña por defecto')),
        ('auto_assign', models.BooleanField(default=True)),
        ('max_chats_per_agent', models.PositiveIntegerField(default=5)),
        ('welcome_message', models.TextField(blank=True, default='')),
        ('time_condition', models.ForeignKey(
            blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
            related_name='+', to='telephony.timecondition', verbose_name='Horario de atención')),
        ('after_hours_message', models.TextField(blank=True, default='')),
        ('is_active', models.BooleanField(default=True)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('updated_at', models.DateTimeField(auto_now=True)),
    ]


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0003_whatsapp_cloud_api'),
        ('campaigns', '0005_campaign_amd'),
        ('contacts', '0006_contact_whatsapp_opt_in'),
        ('telephony', '0017_call_status_machine'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Channel ───────────────────────────────────────────────────────────
        migrations.AlterField(
            model_name='channel', name='channel_type',
            field=models.CharField(choices=[
                ('whatsapp', 'WhatsApp'), ('sms', 'SMS'), ('email', 'Email'),
                ('chat', 'Chat Web (legacy)'), ('webchat', 'Chat Web'),
                ('messenger', 'Facebook Messenger'), ('instagram', 'Instagram'),
            ], max_length=20, verbose_name='Tipo'),
        ),

        # ── Etiquetas y respuestas rápidas ────────────────────────────────────
        migrations.CreateModel(
            name='ConversationTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Etiqueta')),
                ('color', models.CharField(default='gray', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'messaging_tags', 'ordering': ['name'],
                     'verbose_name': 'Etiqueta de conversación',
                     'verbose_name_plural': 'Etiquetas de conversación'},
        ),
        migrations.CreateModel(
            name='QuickReply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100, verbose_name='Título')),
                ('shortcut', models.CharField(blank=True, default='', help_text='Ej: /saludo', max_length=30)),
                ('body', models.TextField(verbose_name='Texto')),
                ('channel_type', models.CharField(blank=True, default='', help_text='Vacío = todos los canales', max_length=20)),
                ('order', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('campaign', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='quick_replies', to='campaigns.campaign')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'messaging_quick_replies', 'ordering': ['order', 'title'],
                     'verbose_name': 'Respuesta rápida', 'verbose_name_plural': 'Respuestas rápidas'},
        ),

        # ── Conversation ──────────────────────────────────────────────────────
        migrations.AddField(
            model_name='conversation', name='disposition',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='conversations', to='campaigns.campaigndisposition', verbose_name='Tipificación'),
        ),
        migrations.AddField(
            model_name='conversation', name='tags',
            field=models.ManyToManyField(blank=True, related_name='conversations', to='messaging.conversationtag'),
        ),
        migrations.AddField(
            model_name='conversation', name='close_notes',
            field=models.TextField(blank=True, default='', verbose_name='Notas de cierre'),
        ),
        migrations.AddField(
            model_name='conversation', name='closed_reason',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='conversation', name='assigned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation', name='first_response_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation', name='after_hours_notified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation', name='subject',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
        migrations.AddField(
            model_name='conversation', name='metadata',
            field=models.JSONField(blank=True, default=dict),
        ),

        # ── WhatsAppLine ──────────────────────────────────────────────────────
        migrations.AddField(
            model_name='whatsappline', name='time_condition',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='whatsapp_lines', to='telephony.timecondition', verbose_name='Horario de atención'),
        ),
        migrations.AddField(
            model_name='whatsappline', name='after_hours_message',
            field=models.TextField(blank=True, default='', verbose_name='Mensaje fuera de horario'),
        ),
        migrations.AddField(
            model_name='whatsappline', name='opt_out_keywords',
            field=models.CharField(blank=True, default='BAJA,STOP,CANCELAR', max_length=200),
        ),
        migrations.AddField(
            model_name='whatsappline', name='opt_in_keywords',
            field=models.CharField(blank=True, default='ALTA,SUSCRIBIR', max_length=200),
        ),
        migrations.AddField(
            model_name='whatsappline', name='opt_out_reply',
            field=models.TextField(blank=True, default='Listo, no volverás a recibir mensajes promocionales. Escribe ALTA para suscribirte de nuevo.'),
        ),
        migrations.AddField(
            model_name='whatsappline', name='opt_in_reply',
            field=models.TextField(blank=True, default='¡Gracias! Quedaste suscrito a nuestras novedades.'),
        ),

        # ── Envíos masivos ────────────────────────────────────────────────────
        migrations.CreateModel(
            name='WhatsAppBroadcast',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('body_params', models.JSONField(blank=True, default=list)),
                ('header_params', models.JSONField(blank=True, default=list)),
                ('require_opt_in', models.BooleanField(
                    default=True, help_text='Solo enviar a contactos con consentimiento (opt-in) de WhatsApp.')),
                ('rate_per_minute', models.PositiveIntegerField(default=60)),
                ('status', models.CharField(choices=[
                    ('draft', 'Borrador'), ('scheduled', 'Programado'), ('running', 'Enviando'),
                    ('paused', 'Pausado'), ('completed', 'Completado'), ('cancelled', 'Cancelado'),
                    ('failed', 'Fallido'),
                ], default='draft', max_length=20)),
                ('scheduled_at', models.DateTimeField(blank=True, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('total_recipients', models.PositiveIntegerField(default=0)),
                ('skipped_count', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('contact_list', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='whatsapp_broadcasts', to='contacts.contactlist')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL)),
                ('line', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name='broadcasts', to='messaging.whatsappline')),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name='broadcasts', to='messaging.whatsapptemplate')),
            ],
            options={'db_table': 'whatsapp_broadcasts', 'ordering': ['-created_at'],
                     'verbose_name': 'Envío masivo WhatsApp', 'verbose_name_plural': 'Envíos masivos WhatsApp'},
        ),
        migrations.CreateModel(
            name='WhatsAppBroadcastRecipient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=30)),
                ('status', models.CharField(choices=[
                    ('pending', 'Pendiente'), ('sent', 'Enviado'), ('delivered', 'Entregado'),
                    ('read', 'Leído'), ('failed', 'Fallido'),
                ], db_index=True, default='pending', max_length=20)),
                ('error', models.TextField(blank=True, default='')),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('broadcast', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='recipients', to='messaging.whatsappbroadcast')),
                ('contact', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contacts.contact')),
                ('message', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='broadcast_recipients', to='messaging.message')),
            ],
            options={'db_table': 'whatsapp_broadcast_recipients', 'unique_together': {('broadcast', 'phone')}},
        ),
        migrations.AddIndex(
            model_name='whatsappbroadcastrecipient',
            index=models.Index(fields=['broadcast', 'status'], name='wa_bc_rcpt_status_idx'),
        ),

        # ── Email ─────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='EmailAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                *_routing_fields(),
                ('name', models.CharField(max_length=100)),
                ('email_address', models.EmailField(max_length=254, unique=True)),
                ('from_name', models.CharField(blank=True, default='', max_length=100)),
                ('signature', models.TextField(blank=True, default='')),
                ('imap_host', models.CharField(max_length=200)),
                ('imap_port', models.PositiveIntegerField(default=993)),
                ('imap_ssl', models.BooleanField(default=True)),
                ('imap_username', models.CharField(max_length=200)),
                ('imap_password', core.fields.EncryptedCharField(blank=True, default='', max_length=500)),
                ('imap_folder', models.CharField(default='INBOX', max_length=100)),
                ('smtp_host', models.CharField(max_length=200)),
                ('smtp_port', models.PositiveIntegerField(default=587)),
                ('smtp_starttls', models.BooleanField(default=True)),
                ('smtp_ssl', models.BooleanField(default=False)),
                ('smtp_username', models.CharField(blank=True, default='', max_length=200)),
                ('smtp_password', core.fields.EncryptedCharField(blank=True, default='', max_length=500)),
                ('last_uid', models.BigIntegerField(default=0)),
                ('last_polled_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.TextField(blank=True, default='')),
                ('channel', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name='email_account', to='messaging.channel')),
            ],
            options={'db_table': 'messaging_email_accounts', 'ordering': ['name'],
                     'verbose_name': 'Cuenta de email', 'verbose_name_plural': 'Cuentas de email'},
        ),

        # ── Chat web ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='WebChatWidget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                *_routing_fields(),
                ('name', models.CharField(max_length=100)),
                ('widget_key', models.CharField(default=apps.messaging.models._generate_widget_key, max_length=64, unique=True)),
                ('allowed_origins', models.TextField(
                    blank=True, default='',
                    help_text='Un dominio por línea (ej: https://www.miempresa.com). Vacío = cualquier sitio.')),
                ('title', models.CharField(default='¿Hablamos?', max_length=100)),
                ('subtitle', models.CharField(blank=True, default='Te respondemos en minutos', max_length=200)),
                ('primary_color', models.CharField(default='#16a34a', max_length=20)),
                ('position', models.CharField(default='right', max_length=10)),
                ('require_name', models.BooleanField(default=True)),
                ('require_email', models.BooleanField(default=False)),
                ('intro_text', models.TextField(blank=True, default='Déjanos tus datos y cuéntanos en qué te ayudamos.')),
                ('channel', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name='webchat_widget', to='messaging.channel')),
            ],
            options={'db_table': 'messaging_webchat_widgets', 'ordering': ['name'],
                     'verbose_name': 'Widget de chat web', 'verbose_name_plural': 'Widgets de chat web'},
        ),

        # ── Messenger / Instagram ─────────────────────────────────────────────
        migrations.CreateModel(
            name='MetaPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                *_routing_fields(),
                ('platform', models.CharField(choices=[('messenger', 'Facebook Messenger'), ('instagram', 'Instagram')], max_length=20)),
                ('name', models.CharField(max_length=200)),
                ('page_id', models.CharField(help_text='ID de la página de Facebook', max_length=64)),
                ('instagram_account_id', models.CharField(
                    blank=True, default='', help_text='ID de la cuenta profesional de Instagram (solo para Instagram)',
                    max_length=64)),
                ('page_access_token', core.fields.EncryptedTextField(blank=True, default='')),
                ('subscribed', models.BooleanField(default=False)),
                ('last_error', models.TextField(blank=True, default='')),
                ('channel', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE, related_name='meta_page', to='messaging.channel')),
                ('provider', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name='pages', to='messaging.whatsappprovider')),
            ],
            options={'db_table': 'messaging_meta_pages', 'ordering': ['platform', 'name'],
                     'verbose_name': 'Página Messenger / Instagram',
                     'verbose_name_plural': 'Páginas Messenger / Instagram',
                     'unique_together': {('platform', 'page_id')}},
        ),
    ]
