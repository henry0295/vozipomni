from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChannelViewSet, ConversationViewSet, MessageViewSet, MetaWebhookView,
    WhatsAppLineViewSet, WhatsAppProviderViewSet, WhatsAppTemplateViewSet,
)

router = DefaultRouter()
router.register(r'channels', ChannelViewSet, basename='messaging-channel')
router.register(r'conversations', ConversationViewSet, basename='messaging-conversation')
router.register(r'messages', MessageViewSet, basename='messaging-message')
router.register(r'whatsapp/providers', WhatsAppProviderViewSet, basename='whatsapp-provider')
router.register(r'whatsapp/lines', WhatsAppLineViewSet, basename='whatsapp-line')
router.register(r'whatsapp/templates', WhatsAppTemplateViewSet, basename='whatsapp-template')

urlpatterns = [
    # Webhook público de Meta (verificación GET + eventos POST)
    path('webhooks/meta/<str:app_id>/', MetaWebhookView.as_view(), name='whatsapp-meta-webhook'),
    path('', include(router.urls)),
]
