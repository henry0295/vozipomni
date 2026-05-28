from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.api import viewsets
from apps.api import views
from apps.api.supervisor_viewsets import SupervisorViewSet
from apps.api.extra_viewsets import AgentBreakReasonViewSet, AgentGroupViewSet, AuditViewSet
from apps.telephony.views import SIPTrunkViewSet
from apps.reports.views import ReportViewSet as ReportViewSetFull

router = DefaultRouter()
router.register(r'users', viewsets.UserViewSet, basename='user')
router.register(r'campaigns', viewsets.CampaignViewSet, basename='campaign')
router.register(r'agents', viewsets.AgentViewSet, basename='agent')
router.register(r'contacts', viewsets.ContactViewSet, basename='contact')
router.register(r'contact-lists', viewsets.ContactListViewSet, basename='contactlist')
router.register(r'queues', viewsets.QueueViewSet, basename='queue')
router.register(r'calls', viewsets.CallViewSet, basename='call')
router.register(r'recordings', viewsets.RecordingViewSet, basename='recording')
router.register(r'reports', ReportViewSetFull, basename='report')
router.register(r'trunks', SIPTrunkViewSet, basename='trunk')
# Supervisor (spy, barge, whisper, dashboard)
router.register(r'supervisor', SupervisorViewSet, basename='supervisor')
# Gestión de grupos y razones de pausa
router.register(r'agent-groups', AgentGroupViewSet, basename='agentgroup')
router.register(r'break-reasons', AgentBreakReasonViewSet, basename='breakreason')
# Auditoría de gestiones
router.register(r'audits', AuditViewSet, basename='audit')

urlpatterns = [
    # Authentication
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('auth/logout/', views.LogoutView, name='logout'),

    # ViewSets
    path('', include(router.urls)),

    # Telephony
    path('telephony/', include('apps.telephony.urls')),
]
