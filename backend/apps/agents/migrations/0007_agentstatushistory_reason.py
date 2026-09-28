# Generated manually to add reason field to AgentStatusHistory

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0006_alter_agentbreakreason_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentstatushistory',
            name='reason',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Razón'),
        ),
    ]
