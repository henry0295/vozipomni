from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Importar viewsets (se crearán después)
from apps.api import viewsets
from apps.api import views
from apps.telephony.views import SIPTrunkViewSet

router = DefaultRouter()
router.register(r'users', viewsets.UserViewSet, basename='user')
router.register(r'campaigns', viewsets.CampaignViewSet, basename='campaign')
router.register(r'agents', viewsets.AgentViewSet, basename='agent')
router.register(r'contacts', viewsets.ContactViewSet, basename='contact')
router.register(r'contact-lists', viewsets.ContactListViewSet, basename='contactlist')
router.register(r'queues', viewsets.QueueViewSet, basename='queue')
router.register(r'calls', viewsets.CallViewSet, basename='call')
router.register(r'recordings', viewsets.RecordingViewSet, basename='recording')
router.register(r'reports', viewsets.ReportViewSet, basename='report')
router.register(r'trunks', SIPTrunkViewSet, basename='trunk')

urlpatterns = [
    # Authentication
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.CurrentUserView.as_view(), name='current_user'),
    
    # ViewSets
    path('', include(router.urls)),
    
    # Telephony
    path('telephony/', include('apps.telephony.urls')),
]
