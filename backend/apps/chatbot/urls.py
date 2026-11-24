from rest_framework.routers import DefaultRouter

from .views import (
    AIProviderViewSet, BotFlowViewSet, ConnectorViewSet, KnowledgeArticleViewSet, KnowledgeAssistView,
    KnowledgeBaseViewSet,
)

router = DefaultRouter()
router.register(r'flows', BotFlowViewSet, basename='bot-flow')
router.register(r'connectors', ConnectorViewSet, basename='bot-connector')
router.register(r'ai-providers', AIProviderViewSet, basename='bot-ai-provider')
router.register(r'knowledge-bases', KnowledgeBaseViewSet, basename='kb-base')
router.register(r'knowledge-articles', KnowledgeArticleViewSet, basename='kb-article')
router.register(r'knowledge', KnowledgeAssistView, basename='kb-assist')

urlpatterns = router.urls
