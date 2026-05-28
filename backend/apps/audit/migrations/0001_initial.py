from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('agents', '0004_agentgroup_agentbreakreason_updates'),
        ('campaigns', '0001_initial'),
        ('telephony', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CallDispositionAudit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent_notes', models.TextField(blank=True, verbose_name='Notas del agente')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pendiente revisión'),
                        ('approved', 'Aprobada'),
                        ('rejected', 'Rechazada'),
                        ('corrected', 'Corregida'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                    verbose_name='Estado auditoría',
                )),
                ('supervisor_notes', models.TextField(blank=True, verbose_name='Notas del supervisor')),
                ('quality_score', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Puntuación calidad')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creado')),
                ('audited_at', models.DateTimeField(blank=True, null=True, verbose_name='Auditado')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('agent', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='audits',
                    to='agents.agent',
                    verbose_name='Agente',
                )),
                ('audited_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='performed_audits',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Auditado por',
                )),
                ('call', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='audit',
                    to='telephony.call',
                    verbose_name='Llamada',
                )),
                ('campaign', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='audits',
                    to='campaigns.campaign',
                    verbose_name='Campaña',
                )),
                ('corrected_disposition', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='corrected_audits',
                    to='campaigns.campaigndisposition',
                    verbose_name='Calificación corregida',
                )),
                ('original_disposition', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='original_audits',
                    to='campaigns.campaigndisposition',
                    verbose_name='Calificación original',
                )),
            ],
            options={
                'verbose_name': 'Auditoría de Gestión',
                'verbose_name_plural': 'Auditorías de Gestiones',
                'db_table': 'call_disposition_audits',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='calldispositionaudit',
            index=models.Index(fields=['status', 'created_at'], name='audit_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='calldispositionaudit',
            index=models.Index(fields=['agent', 'created_at'], name='audit_agent_created_idx'),
        ),
        migrations.AddIndex(
            model_name='calldispositionaudit',
            index=models.Index(fields=['campaign', 'created_at'], name='audit_campaign_created_idx'),
        ),
    ]
