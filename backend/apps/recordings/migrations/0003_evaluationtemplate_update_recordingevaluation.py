"""
Migration: Add EvaluationTemplate model and update RecordingEvaluation
to support configurable criteria via template + scores_data.

Legacy fields (greeting, clarity, professionalism, resolution, closing)
are kept for backwards compatibility with existing evaluations.
total_score changes from IntegerField to FloatField (normalized 0-100).
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recordings', '0002_rename_recordings_created_a_3b26c7_idx_recordings_created_3645f5_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. Crear EvaluationTemplate ──────────────────────────────────────
        migrations.CreateModel(
            name='EvaluationTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200, unique=True, verbose_name='Nombre de la plantilla')),
                ('description', models.TextField(blank=True)),
                ('criteria', models.JSONField(
                    default=list,
                    verbose_name='Criterios de evaluación',
                    help_text='Lista de objetos {name, label, weight, max_score}',
                )),
                ('is_active', models.BooleanField(default=True)),
                ('is_default', models.BooleanField(
                    default=False,
                    verbose_name='Plantilla por defecto',
                    help_text='Solo puede haber una plantilla por defecto.',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_evaluation_templates',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Plantilla de Evaluación',
                'verbose_name_plural': 'Plantillas de Evaluación',
                'db_table': 'recording_evaluation_templates',
                'ordering': ['-is_default', 'name'],
            },
        ),

        # ── 2. Agregar campos nuevos a RecordingEvaluation ───────────────────
        migrations.AddField(
            model_name='recordingevaluation',
            name='template',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='evaluations',
                to='recordings.evaluationtemplate',
                verbose_name='Plantilla de evaluación',
            ),
        ),
        migrations.AddField(
            model_name='recordingevaluation',
            name='scores_data',
            field=models.JSONField(
                default=dict, blank=True,
                verbose_name='Scores por criterio',
            ),
        ),

        # ── 3. Cambiar total_score de IntegerField a FloatField ──────────────
        migrations.AlterField(
            model_name='recordingevaluation',
            name='total_score',
            field=models.FloatField(default=0.0, verbose_name='Puntuación total'),
        ),

        # ── 4. Migrar datos: calcular total_score normalizado (0-100) ─────────
        migrations.RunSQL(
            sql="""
                UPDATE recording_evaluations
                SET total_score = ROUND(
                    ((greeting + clarity + professionalism + resolution + closing)::float / 25.0) * 100.0,
                    2
                )
                WHERE total_score = 0 OR total_score <= 25;
            """,
            reverse_sql="""
                UPDATE recording_evaluations
                SET total_score = ROUND(total_score * 25.0 / 100.0)
                WHERE total_score > 25;
            """,
        ),
    ]
