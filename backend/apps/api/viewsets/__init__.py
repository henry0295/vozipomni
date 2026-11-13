"""
ViewSets de la API divididos por dominio.

Se reexportan aquí para que ``from apps.api import viewsets`` y
``viewsets.CampaignViewSet`` sigan funcionando igual que antes.

NOTA: TrunkViewSet REAL está en apps.telephony.views.SIPTrunkViewSet
con integración completa de Asterisk AMI (test_connection real,
force_register, preview_config, etc.).
"""
from apps.api.viewsets.campaigns import CampaignViewSet, CampaignFormViewSet
from apps.api.viewsets.agents import AgentActionThrottle, AgentViewSet
from apps.api.viewsets.contacts import ContactViewSet, ContactListViewSet
from apps.api.viewsets.queues import QueueViewSet
from apps.api.viewsets.calls import CallViewSet, hangup_by_call_id
from apps.api.viewsets.recordings import RecordingViewSet

__all__ = [
    'CampaignViewSet',
    'CampaignFormViewSet',
    'AgentActionThrottle',
    'AgentViewSet',
    'ContactViewSet',
    'ContactListViewSet',
    'QueueViewSet',
    'CallViewSet',
    'hangup_by_call_id',
    'RecordingViewSet',
]
