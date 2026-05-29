from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0004_agentgroup_agentbreakreason_updates'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='sip_password',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Password SIP'),
        ),
    ]
