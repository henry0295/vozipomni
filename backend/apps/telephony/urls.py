from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CallViewSet, SIPTrunkViewSet, IVRViewSet, ExtensionViewSet,
    InboundRouteViewSet, OutboundRouteViewSet, VoicemailViewSet,
    MusicOnHoldViewSet, TimeConditionViewSet
)

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

urlpatterns = [
    path('', include(router.urls)),
]
