import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import core.fields


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AIProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('provider_type', models.CharField(choices=[('openai', 'OpenAI'), ('azure_openai', 'Azure OpenAI'), ('openai_compatible', 'Compatible con OpenAI (Ollama, vLLM, Gemini, LM Studio…)')], default='openai_compatible', max_length=30)),
                ('base_url', models.URLField(blank=True, default='', help_text='OpenAI: vacío. Azure: https://<recurso>.openai.azure.com. Ollama: http://host:11434/v1', max_length=500)),
                ('model', models.CharField(help_text='Modelo o deployment (Azure)', max_length=150)),
                ('api_key', core.fields.EncryptedTextField(blank=True, default='')),
                ('api_version', models.CharField(blank=True, default='2024-06-01', max_length=30)),
                ('temperature', models.FloatField(default=0.0)),
                ('timeout_seconds', models.PositiveIntegerField(default=30)),
                ('mask_personal_data', models.BooleanField(default=True)),
                ('monthly_token_limit', models.PositiveIntegerField(default=0, help_text='0 = sin límite')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'chatbot_ai_providers', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='AIUsageLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('purpose', models.CharField(max_length=30)),
                ('status', models.CharField(max_length=10)),
                ('prompt_tokens', models.PositiveIntegerField(default=0)),
                ('completion_tokens', models.PositiveIntegerField(default=0)),
                ('duration_ms', models.PositiveIntegerField(default=0)),
                ('result', models.CharField(blank=True, default='', max_length=120)),
                ('error', models.TextField(blank=True, default='')),
                ('conversation_id', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage', to='chatbot.aiprovider')),
            ],
            options={'db_table': 'chatbot_ai_usage', 'ordering': ['-created_at']},
        ),
    ]
