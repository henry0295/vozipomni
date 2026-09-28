from django.urls import re_path
from apps.api import consumers, consumers_enhanced

websocket_urlpatterns = [
    # ── Consola del agente ───────────────────────────────────────────────────
    re_path(r'ws/agent/(?P<agent_id>\w+)/$', consumers.AgentConsumer.as_asgi()),

    # ── Monitoreo de campaña ─────────────────────────────────────────────────
    re_path(r'ws/campaign/(?P<campaign_id>\w+)/$', consumers.CampaignConsumer.as_asgi()),

    # ── Dashboard de supervisión (métricas en tiempo real) ───────────────────
    # Versión enhanced: envía datos iniciales al conectar y hace push en eventos AMI
    re_path(r'ws/dashboard/$', consumers_enhanced.RealtimeDashboardConsumer.as_asgi()),

    # ── Eventos Asterisk (agentes y admin) ────────────────────────────────────
    re_path(r'ws/asterisk/$', consumers_enhanced.AsteriskEventConsumer.as_asgi()),

    # ── Mensajería omnicanal / WhatsApp ───────────────────────────────────────
    re_path(r'ws/messaging/$', consumers.MessagingConsumer.as_asgi()),
]
