from django.urls import re_path
from apps.api import consumers

websocket_urlpatterns = [
    re_path(r'ws/agent/(?P<agent_id>\w+)/$', consumers.AgentConsumer.as_asgi()),
    re_path(r'ws/campaign/(?P<campaign_id>\w+)/$', consumers.CampaignConsumer.as_asgi()),
    re_path(r'ws/dashboard/$', consumers.DashboardConsumer.as_asgi()),
]
