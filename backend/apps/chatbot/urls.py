from rest_framework.routers import DefaultRouter

from .views import BotFlowViewSet, ConnectorViewSet

router = DefaultRouter()
router.register(r'flows', BotFlowViewSet, basename='bot-flow')
router.register(r'connectors', ConnectorViewSet, basename='bot-connector')

urlpatterns = router.urls
