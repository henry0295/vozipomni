# Generated migration for adding performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telephony', '0009_encrypt_passwords'),
    ]

    operations = [
        # Índices para Call model
        migrations.AddIndex(
            model_name='call',
            index=models.Index(fields=['start_time', 'status'], name='calls_start_status_idx'),
        ),
        migrations.AddIndex(
            model_name='call',
            index=models.Index(fields=['agent', 'start_time', 'status'], name='calls_agent_time_idx'),
        ),
        migrations.AddIndex(
            model_name='call',
            index=models.Index(fields=['campaign', 'disposition'], name='calls_campaign_disp_idx'),
        ),
        migrations.AddIndex(
            model_name='call',
            index=models.Index(fields=['unique_id'], name='calls_uniqueid_idx'),
        ),
        migrations.AddIndex(
            model_name='call',
            index=models.Index(fields=['direction', 'status', 'start_time'], name='calls_dir_status_time_idx'),
        ),
        
        # Índices para SIPTrunk model
        migrations.AddIndex(
            model_name='siptrunk',
            index=models.Index(fields=['is_active', 'is_registered'], name='trunks_active_reg_idx'),
        ),
        migrations.AddIndex(
            model_name='siptrunk',
            index=models.Index(fields=['trunk_type', 'is_active'], name='trunks_type_active_idx'),
        ),
        
        # Índices para Extension model
        migrations.AddIndex(
            model_name='extension',
            index=models.Index(fields=['extension_type', 'is_active'], name='ext_type_active_idx'),
        ),
        
        # Índices para InboundRoute model
        migrations.AddIndex(
            model_name='inboundroute',
            index=models.Index(fields=['is_active', 'priority'], name='inbound_active_priority_idx'),
        ),
        
        # Índices para OutboundRoute model
        migrations.AddIndex(
            model_name='outboundroute',
            index=models.Index(fields=['is_active', 'priority'], name='outbound_active_priority_idx'),
        ),
    ]
