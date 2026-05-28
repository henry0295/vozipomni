from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('agents', '0004_agentgroup_agentbreakreason_updates'),
        ('campaigns', '0001_initial'),
        ('contacts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nombre')),
                ('channel_type', models.CharField(choices=[('whatsapp', 'WhatsApp'), ('sms', 'SMS'), ('email', 'Email'), ('chat', 'Chat Web')], max_length=20, verbose_name='Tipo')),
                ('identifier', models.CharField(help_text='Número de teléfono, dirección de email o URL del canal', max_length=200, verbose_name='Identificador')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={'verbose_name': 'Canal', 'verbose_name_plural': 'Canales', 'db_table': 'messaging_channels', 'ordering': ['channel_type', 'name']},
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contact_identifier', models.CharField(help_text='Número/email del contacto en este canal', max_length=200, verbose_name='Identificador del contacto')),
                ('status', models.CharField(choices=[('open', 'Abierta'), ('waiting', 'En espera'), ('closed', 'Cerrada')], default='open', max_length=20)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('agent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conversations', to='agents.agent')),
                ('campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conversations', to='campaigns.campaign')),
                ('channel', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='conversations', to='messaging.channel')),
                ('contact', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='conversations', to='contacts.contact')),
            ],
            options={'verbose_name': 'Conversación', 'verbose_name_plural': 'Conversaciones', 'db_table': 'messaging_conversations', 'ordering': ['-started_at']},
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('direction', models.CharField(choices=[('inbound', 'Entrante'), ('outbound', 'Saliente')], max_length=10)),
                ('body', models.TextField(verbose_name='Cuerpo del mensaje')),
                ('media_url', models.URLField(blank=True, null=True, verbose_name='Adjunto')),
                ('is_read', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('external_id', models.CharField(blank=True, help_text='ID del mensaje en la plataforma externa', max_length=255, null=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='messaging.conversation')),
            ],
            options={'verbose_name': 'Mensaje', 'verbose_name_plural': 'Mensajes', 'db_table': 'messaging_messages', 'ordering': ['sent_at']},
        ),
        migrations.AddIndex(model_name='conversation', index=models.Index(fields=['status', 'agent'], name='messaging_c_status_idx')),
        migrations.AddIndex(model_name='conversation', index=models.Index(fields=['channel', 'contact_identifier'], name='messaging_c_channel_idx')),
        migrations.AddIndex(model_name='message', index=models.Index(fields=['conversation', 'sent_at'], name='messaging_m_conv_idx')),
    ]
