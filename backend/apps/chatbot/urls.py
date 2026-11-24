from rest_framework.routers import DefaultRouter

from .views import AIProviderViewSet, BotFlowViewSet, ConnectorViewSet

router = DefaultRouter()
router.register(r'flows', BotFlowViewSet, basename='bot-flow')
router.register(r'connectors', ConnectorViewSet, basename='bot-connector')
router.register(r'ai-providers', AIProviderViewSet, basename='bot-ai-provider')

urlpatterns = router.urls
