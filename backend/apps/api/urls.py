from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.api import viewsets
from apps.api import views
from apps.api.supervisor_viewsets import SupervisorViewSet
from apps.api.extra_viewsets import AgentBreakReasonViewSet, AgentGroupViewSet, AuditViewSet
from apps.api.admin_viewsets import (
    UserAdminViewSet, BlacklistViewSet,
    EvaluationTemplateViewSet, RecordingEvaluationViewSet,
    PasswordResetRequestView, PasswordResetConfirmView, ChangePasswordView,
)
from apps.api.cc_viewsets import (
    CallbackViewSet, WebhookViewSet,
    ScreenPopView, ConsultiveTransferView, ConferenceView,
    DNCCheckView, BulkContactImportView, QualityStatsView,
)
from apps.telephony.views import SIPTrunkViewSet
from apps.messaging.views import MetaWebhookView
from apps.reports.views import ReportViewSet as ReportViewSetFull

router = DefaultRouter()
# Usuarios: gestión completa con contraseña y roles (solo admin)
router.register(r'users', UserAdminViewSet, basename='user')
# Lista negra DNC
router.register(r'blacklist', BlacklistViewSet, basename='blacklist')
# Calidad: plantillas y evaluaciones
router.register(r'evaluation-templates', EvaluationTemplateViewSet, basename='evaluationtemplate')
router.register(r'evaluations', RecordingEvaluationViewSet, basename='evaluation')
router.register(r'campaigns', viewsets.CampaignViewSet, basename='campaign')
router.register(r'campaign-forms', viewsets.CampaignFormViewSet, basename='campaignform')
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
# Contact Center features avanzados
router.register(r'callbacks', CallbackViewSet, basename='callback')
router.register(r'webhooks', WebhookViewSet, basename='webhook')

urlpatterns = [
    # Authentication
    path('auth/login/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.CurrentUserView.as_view(), name='current_user'),
    path('auth/logout/', views.LogoutView, name='logout'),
    path('auth/password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),

    # Webhook público de Meta (WhatsApp, Messenger, Instagram).
    # Va ANTES del router: /api/webhooks/ también lo usa WebhookViewSet (webhooks salientes).
    path('webhooks/whatsapp/<str:app_id>/', MetaWebhookView.as_view(), name='meta-webhook'),

    # ViewSets
    path('', include(router.urls)),

    # Telephony
    path('telephony/', include('apps.telephony.urls')),

    # Mensajería multicanal (WhatsApp, SMS, Email, Chat Web)
    path('messaging/', include('apps.messaging.urls')),

    # Contact Center - features avanzados
    path('cc/screen-pop/', ScreenPopView.as_view(), name='screen-pop'),
    path('cc/available-agents/', ConsultiveTransferView.as_view(), name='available-agents'),
    path('cc/consultive-transfer/', ConsultiveTransferView.as_view(), name='consultive-transfer'),
    path('cc/conference/', ConferenceView.as_view(), name='conference'),
    path('cc/dnc-check/', DNCCheckView.as_view(), name='dnc-check'),
    path('cc/bulk-import/', BulkContactImportView.as_view(), name='bulk-import'),
    path('cc/quality-stats/', QualityStatsView.as_view(), name='quality-stats'),
]
