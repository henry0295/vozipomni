from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0003_add_performance_indexes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Agregar campo 'order' a AgentBreakReason
        migrations.AddField(
            model_name='agentbreakreason',
            name='order',
            field=models.IntegerField(default=0, verbose_name='Orden'),
        ),
        # Agregar campo 'created_at' a AgentBreakReason
        migrations.AddField(
            model_name='agentbreakreason',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        # Actualizar verbose_name en AgentBreakReason
        migrations.AlterField(
            model_name='agentbreakreason',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='Nombre'),
        ),
        migrations.AlterField(
            model_name='agentbreakreason',
            name='code',
            field=models.CharField(max_length=20, unique=True, verbose_name='Código'),
        ),
        migrations.AlterField(
            model_name='agentbreakreason',
            name='max_duration',
            field=models.IntegerField(
                blank=True,
                help_text='Minutos máximos (null = sin límite)',
                null=True,
                verbose_name='Duración máxima (min)',
            ),
        ),
        migrations.AlterField(
            model_name='agentbreakreason',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Activo'),
        ),
        migrations.AlterModelOptions(
            name='agentbreakreason',
            options={
                'ordering': ['order', 'name'],
                'verbose_name': 'Razón de Descanso',
                'verbose_name_plural': 'Razones de Descanso',
            },
        ),
        # Crear modelo AgentGroup
        migrations.CreateModel(
            name='AgentGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
                ('description', models.TextField(blank=True, verbose_name='Descripción')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('agents', models.ManyToManyField(
                    blank=True,
                    related_name='groups',
                    to='agents.agent',
                    verbose_name='Agentes',
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_agent_groups',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Grupo de Agentes',
                'verbose_name_plural': 'Grupos de Agentes',
                'db_table': 'agent_groups',
                'ordering': ['name'],
            },
        ),
    ]
