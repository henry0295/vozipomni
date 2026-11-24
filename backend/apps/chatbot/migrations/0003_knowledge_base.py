import django.contrib.postgres.indexes
import django.contrib.postgres.search
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chatbot', '0002_ai_providers'),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeBase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('description', models.TextField(blank=True, default='')),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('glpi_connector', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='knowledge_bases', to='chatbot.connector')),
            ],
            options={'db_table': 'kb_bases', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='KnowledgeArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=250)),
                ('body', models.TextField()),
                ('category', models.CharField(blank=True, default='', max_length=100)),
                ('keywords', models.CharField(blank=True, default='', help_text='Separadas por coma', max_length=500)),
                ('source', models.CharField(choices=[('manual', 'Escrito a mano'), ('file', 'Documento cargado'), ('glpi', 'GLPI')], default='manual', max_length=10)),
                ('external_id', models.CharField(blank=True, default='', max_length=100)),
                ('file_name', models.CharField(blank=True, default='', max_length=255)),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('knowledge_base', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='articles', to='chatbot.knowledgebase')),
            ],
            options={'db_table': 'kb_articles', 'ordering': ['title']},
        ),
        migrations.CreateModel(
            name='KnowledgeChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=0)),
                ('text', models.TextField()),
                ('search_vector', django.contrib.postgres.search.SearchVectorField(null=True)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='chatbot.knowledgearticle')),
            ],
            options={'db_table': 'kb_chunks', 'ordering': ['article', 'order']},
        ),
        migrations.AddIndex(
            model_name='knowledgechunk',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='kb_chunks_search_idx'),
        ),
        migrations.CreateModel(
            name='KnowledgeQuery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField()),
                ('found', models.BooleanField(default=False)),
                ('article_ids', models.JSONField(blank=True, default=list)),
                ('source', models.CharField(default='bot', max_length=20)),
                ('conversation_id', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('knowledge_base', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='queries', to='chatbot.knowledgebase')),
            ],
            options={'db_table': 'kb_queries', 'ordering': ['-created_at']},
        ),
    ]
