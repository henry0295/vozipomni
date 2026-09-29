from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChannelViewSet, ConversationViewSet, MessageViewSet, MetaWebhookView,
    WhatsAppLineViewSet, WhatsAppProviderViewSet, WhatsAppTemplateViewSet,
)
from .views_omni import (
    ChatMetricsView, ConversationTagViewSet, EmailAccountViewSet, MetaPageViewSet, QuickReplyViewSet,
    WebChatConfigView, WebChatMediaView, WebChatMessagesView, WebChatSessionView, WebChatWidgetViewSet,
    WhatsAppBroadcastViewSet,
)

router = DefaultRouter()
router.register(r'channels', ChannelViewSet, basename='messaging-channel')
router.register(r'conversations', ConversationViewSet, basename='messaging-conversation')
router.register(r'messages', MessageViewSet, basename='messaging-message')
router.register(r'whatsapp/providers', WhatsAppProviderViewSet, basename='whatsapp-provider')
router.register(r'whatsapp/lines', WhatsAppLineViewSet, basename='whatsapp-line')
router.register(r'whatsapp/templates', WhatsAppTemplateViewSet, basename='whatsapp-template')
router.register(r'whatsapp/broadcasts', WhatsAppBroadcastViewSet, basename='whatsapp-broadcast')
router.register(r'tags', ConversationTagViewSet, basename='messaging-tag')
router.register(r'quick-replies', QuickReplyViewSet, basename='messaging-quick-reply')
router.register(r'email/accounts', EmailAccountViewSet, basename='messaging-email-account')
router.register(r'webchat/widgets', WebChatWidgetViewSet, basename='messaging-webchat-widget')
router.register(r'meta/pages', MetaPageViewSet, basename='messaging-meta-page')

urlpatterns = [
    # Ruta anterior del webhook de Meta. La oficial ahora es /api/webhooks/whatsapp/<app_id>/
    # (apps/api/urls.py); esta se conserva para Apps que ya la tengan registrada en Meta.
    path('webhooks/meta/<str:app_id>/', MetaWebhookView.as_view(), name='whatsapp-meta-webhook-legacy'),
    # API pública del widget de chat web
    path('webchat/public/<str:key>/config/', WebChatConfigView.as_view(), name='webchat-config'),
    path('webchat/public/<str:key>/session/', WebChatSessionView.as_view(), name='webchat-session'),
    path('webchat/public/<str:key>/messages/', WebChatMessagesView.as_view(), name='webchat-messages'),
    path('webchat/public/<str:key>/media/<int:message_id>/', WebChatMediaView.as_view(), name='webchat-media'),
    path('metrics/', ChatMetricsView.as_view(), name='messaging-metrics'),
    path('', include(router.urls)),
]
