# Generated manually for CampaignForm + is_template + form FK on disposition

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0003_alter_campaign_dnc_enabled_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create CampaignForm table
        migrations.CreateModel(
            name='CampaignForm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nombre del formulario')),
                ('description', models.TextField(blank=True, verbose_name='Descripción')),
                ('fields_schema', models.JSONField(default=list, verbose_name='Esquema de campos')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_forms', to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Formulario de Campaña',
                'verbose_name_plural': 'Formularios de Campaña',
                'db_table': 'campaign_forms',
                'ordering': ['name'],
            },
        ),
        # 2. Add form FK to Campaign
        migrations.AddField(
            model_name='campaign',
            name='form',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='campaigns',
                to='campaigns.campaignform',
                verbose_name='Formulario de gestión',
            ),
        ),
        # 3. Add is_template to Campaign
        migrations.AddField(
            model_name='campaign',
            name='is_template',
            field=models.BooleanField(
                default=False,
                help_text='Si True, esta campaña puede clonarse como punto de partida.',
                verbose_name='Es plantilla',
            ),
        ),
        # 4. Add template_name to Campaign
        migrations.AddField(
            model_name='campaign',
            name='template_name',
            field=models.CharField(blank=True, max_length=200, verbose_name='Nombre de plantilla'),
        ),
        # 5. Add form FK to CampaignDisposition
        migrations.AddField(
            model_name='campaigndisposition',
            name='form',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='dispositions',
                to='campaigns.campaignform',
                verbose_name='Formulario de disposición',
            ),
        ),
    ]
