from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CallViewSet, SIPTrunkViewSet, IVRViewSet, ExtensionViewSet,
    InboundRouteViewSet, OutboundRouteViewSet, VoicemailViewSet,
    MusicOnHoldViewSet, TimeConditionViewSet, CustomDestinationViewSet
)
from .security_views import (
    SecurityEventViewSet, SecurityPolicyApplyView, SecurityPolicyTestView,
    SecurityPolicyView, SecuritySummaryView,
)
from .webrtc_views import SipWsAuthView, WebRTCCredentialsView

router = DefaultRouter()
router.register(r'calls', CallViewSet, basename='call')
router.register(r'trunks', SIPTrunkViewSet, basename='siptrunk')
router.register(r'ivr', IVRViewSet, basename='ivr')
router.register(r'extensions', ExtensionViewSet, basename='extension')
router.register(r'inbound-routes', InboundRouteViewSet, basename='inbound-route')
router.register(r'outbound-routes', OutboundRouteViewSet, basename='outbound-route')
router.register(r'voicemail', VoicemailViewSet, basename='voicemail')
router.register(r'music-on-hold', MusicOnHoldViewSet, basename='music-on-hold')
router.register(r'time-conditions', TimeConditionViewSet, basename='time-condition')
router.register(r'custom-destinations', CustomDestinationViewSet, basename='custom-destination')
router.register(r'security/events', SecurityEventViewSet, basename='security-event')

urlpatterns = [
    # Softphone: TURN temporal + ticket del WebSocket SIP
    path('webrtc-credentials/', WebRTCCredentialsView.as_view(), name='webrtc-credentials'),
    path('sip-ws-auth/', SipWsAuthView.as_view(), name='sip-ws-auth'),
    # Seguridad y antifraude
    path('security/policy/', SecurityPolicyView.as_view(), name='security-policy'),
    path('security/policy/test/', SecurityPolicyTestView.as_view(), name='security-policy-test'),
    path('security/policy/apply/', SecurityPolicyApplyView.as_view(), name='security-policy-apply'),
    path('security/summary/', SecuritySummaryView.as_view(), name='security-summary'),
    path('', include(router.urls)),
]
