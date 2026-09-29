"""Asigna una clave SIP aleatoria a los agentes que no tenían (antes se usaba la extensión)."""
import secrets

from django.db import migrations


def fill_passwords(apps, schema_editor):
    Agent = apps.get_model('agents', 'Agent')
    for agent in Agent.objects.filter(sip_password=''):
        agent.sip_password = secrets.token_urlsafe(12)
        agent.save(update_fields=['sip_password'])


class Migration(migrations.Migration):

    dependencies = [
        ('agents', '0007_agentstatushistory_reason'),
    ]

    operations = [
        migrations.RunPython(fill_passwords, migrations.RunPython.noop),
    ]
