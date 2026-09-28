from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChannelViewSet, ConversationViewSet

router = DefaultRouter()
router.register(r'channels', ChannelViewSet, basename='messaging-channel')
router.register(r'conversations', ConversationViewSet, basename='messaging-conversation')

urlpatterns = [
    path('', include(router.urls)),
]
