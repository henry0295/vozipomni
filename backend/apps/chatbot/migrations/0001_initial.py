import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import core.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('messaging', '0004_omnichannel_features'),
    ]

    operations = [
        migrations.CreateModel(
            name='Connector',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
                ('connector_type', models.CharField(choices=[('glpi', 'GLPI (mesa de ayuda)'), ('http', 'API HTTP genérica')], max_length=20, verbose_name='Tipo')),
                ('base_url', models.URLField(max_length=500, verbose_name='URL base')),
                ('config', models.JSONField(blank=True, default=dict)),
                ('secrets', core.fields.EncryptedTextField(blank=True, default='')),
                ('timeout_seconds', models.PositiveIntegerField(default=15)),
                ('verify_ssl', models.BooleanField(default=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'chatbot_connectors', 'ordering': ['name'], 'verbose_name': 'Conector', 'verbose_name_plural': 'Conectores'},
        ),
        migrations.CreateModel(
            name='ConnectorLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=64)),
                ('status', models.CharField(choices=[('success', 'Éxito'), ('empty', 'Sin resultados'), ('error', 'Error')], max_length=10)),
                ('duration_ms', models.PositiveIntegerField(default=0)),
                ('error', models.TextField(blank=True, default='')),
                ('conversation_id', models.BigIntegerField(blank=True, null=True)),
                ('source', models.CharField(default='bot', max_length=20)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('connector', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='chatbot.connector')),
            ],
            options={'db_table': 'chatbot_connector_logs', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='BotFlow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='Nombre')),
                ('description', models.TextField(blank=True, default='')),
                ('is_active', models.BooleanField(default=False, verbose_name='Activo')),
                ('draft', models.JSONField(blank=True, default=dict)),
                ('session_timeout_minutes', models.PositiveIntegerField(default=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('channels', models.ManyToManyField(blank=True, related_name='bot_flows', to='messaging.channel')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'chatbot_flows', 'ordering': ['name'], 'verbose_name': 'Flujo de bot', 'verbose_name_plural': 'Flujos de bot'},
        ),
        migrations.CreateModel(
            name='BotFlowVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveIntegerField()),
                ('definition', models.JSONField(default=dict)),
                ('notes', models.CharField(blank=True, default='', max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('flow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='chatbot.botflow')),
            ],
            options={'db_table': 'chatbot_flow_versions', 'ordering': ['-number'], 'unique_together': {('flow', 'number')}},
        ),
        migrations.AddField(
            model_name='botflow',
            name='published_version',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='chatbot.botflowversion'),
        ),
        migrations.CreateModel(
            name='BotSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_node', models.CharField(blank=True, default='', max_length=64)),
                ('waiting', models.BooleanField(default=False)),
                ('variables', models.JSONField(blank=True, default=dict)),
                ('path', models.JSONField(blank=True, default=list)),
                ('retries', models.PositiveIntegerField(default=0)),
                ('status', models.CharField(choices=[('active', 'Activa'), ('busy', 'Consultando sistema externo'), ('handed_off', 'Pasada a asesor'), ('completed', 'Terminada'), ('timeout', 'Expirada'), ('error', 'Error')], default='active', max_length=20)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_activity_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('conversation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bot_session', to='messaging.conversation')),
                ('flow', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sessions', to='chatbot.botflow')),
                ('version', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sessions', to='chatbot.botflowversion')),
            ],
            options={'db_table': 'chatbot_sessions', 'ordering': ['-last_activity_at']},
        ),
    ]
