"""
Credenciales para el softphone WebRTC.

  GET /api/telephony/webrtc-credentials/   (autenticado)
      → ice_servers: STUN + TURN con credencial temporal (coturn use-auth-secret, RFC 7635/TURN REST)
      → ws_ticket:   ticket firmado para abrir wss://<host>/sip/ws?ticket=...

  GET /api/telephony/sip-ws-auth/          (solo nginx, auth_request)
      → 204 si el ticket de X-Original-URI es válido, 401 si no.

Así ni la clave TURN ni el acceso al WebSocket SIP quedan expuestos en el JavaScript público:
sin sesión válida en VozipOmni no se puede registrar una extensión ni marcar.
"""
import base64
import hashlib
import hmac
import logging
import time
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.http import HttpResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

WS_TICKET_SALT = 'vozipomni.sip-ws'
STUN_SERVERS = ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302']


def turn_credentials(user_id, ttl=None):
    """Usuario/clave temporales que coturn valida con el mismo TURN_SECRET."""
    ttl = ttl or settings.TURN_CREDENTIAL_TTL
    username = f"{int(time.time()) + ttl}:{user_id}"
    digest = hmac.new(settings.TURN_SECRET.encode(), username.encode(), hashlib.sha1).digest()
    return username, base64.b64encode(digest).decode(), ttl


def _turn_host(request):
    if settings.TURN_HOST:
        return settings.TURN_HOST
    base = getattr(settings, 'PUBLIC_BASE_URL', '')
    if base:
        return urlparse(base).hostname
    return request.get_host().split(':')[0]


class WebRTCCredentialsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ice_servers = [{'urls': STUN_SERVERS}]
        turn_ttl = None
        if settings.TURN_SECRET:
            host = _turn_host(request)
            username, credential, turn_ttl = turn_credentials(request.user.pk)
            ice_servers.append({
                'urls': [
                    f'turn:{host}:{settings.TURN_PORT}?transport=udp',
                    f'turn:{host}:{settings.TURN_PORT}?transport=tcp',
                ],
                'username': username,
                'credential': credential,
            })
        ticket = signing.dumps({'u': request.user.pk}, salt=WS_TICKET_SALT)
        return Response({
            'ice_servers': ice_servers,
            'turn_enabled': bool(settings.TURN_SECRET),
            'turn_ttl': turn_ttl,
            'ws_ticket': ticket,
            'ws_ticket_ttl': settings.SIP_WS_TICKET_TTL,
        })


def validate_ws_ticket(ticket: str):
    """Devuelve el usuario activo del ticket o None."""
    if not ticket:
        return None
    try:
        data = signing.loads(ticket, salt=WS_TICKET_SALT, max_age=settings.SIP_WS_TICKET_TTL)
    except signing.BadSignature:
        return None
    user = get_user_model().objects.filter(pk=data.get('u'), is_active=True).first()
    return user


class SipWsAuthView(APIView):
    """
    Llamado por nginx (auth_request) en cada handshake de /sip/ws y /asterisk/ws.
    nginx envía la URI original en X-Original-URI.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []  # todas las peticiones llegan desde nginx (127.0.0.1)

    def get(self, request):
        original = request.headers.get('X-Original-URI', '')
        ticket = (parse_qs(urlparse(original).query).get('ticket') or [''])[0] \
            or request.query_params.get('ticket', '')
        user = validate_ws_ticket(ticket)
        if not user:
            logger.warning(f"[SIP-WS] Handshake rechazado desde {request.headers.get('X-Real-IP', '?')}")
            return HttpResponse(status=401)
        resp = HttpResponse(status=204)
        resp['X-Vozip-User'] = str(user.pk)
        return resp
