# Generated migration for adding performance indexes to agents

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0002_agent_oncall_wrapup_time'),
    ]

    operations = [
        # Índices para Agent model
        migrations.AddIndex(
            model_name='agent',
            index=models.Index(fields=['status', 'logged_in_at'], name='agents_status_login_idx'),
        ),
        migrations.AddIndex(
            model_name='agent',
            index=models.Index(fields=['current_campaign', 'status'], name='agents_campaign_status_idx'),
        ),
        
        # Índices para AgentStatusHistory model
        migrations.AddIndex(
            model_name='agentstatushistory',
            index=models.Index(fields=['agent', 'started_at'], name='agent_hist_agent_start_idx'),
        ),
        migrations.AddIndex(
            model_name='agentstatushistory',
            index=models.Index(fields=['status', 'started_at'], name='agent_hist_status_start_idx'),
        ),
        migrations.AddIndex(
            model_name='agentstatushistory',
            index=models.Index(fields=['ended_at'], name='agent_hist_ended_idx'),
        ),
    ]
