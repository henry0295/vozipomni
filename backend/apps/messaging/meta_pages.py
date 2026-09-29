"""
Facebook Messenger e Instagram Direct vía la misma App de Meta del proveedor de WhatsApp.

  list_pages(provider)                 → páginas (y cuentas de Instagram) accesibles con el token del proveedor
  subscribe_page(page)                 → suscribe la página a la App (webhooks de mensajes)
  test_page(page)                      → valida el token de la página
  process_page_webhook(provider, data) → procesa webhooks object=page | instagram
  send_page_message(message)           → envía un Message saliente; devuelve el mid

Requisitos en Meta: productos "Messenger" (e "Instagram") en la App, permisos
pages_messaging (+ instagram_manage_messages) y, para responder entre 24 h y 7 días,
la función "Human Agent" aprobada.
"""
import logging
import os
from datetime import datetime, timezone as dt_timezone

import requests
from django.utils import timezone

from .whatsapp_service import GRAPH_URL, TIMEOUT, WhatsAppAPIError

logger = logging.getLogger(__name__)

SUBSCRIBED_FIELDS = 'messages,messaging_postbacks,message_deliveries,message_reads'


def _graph(method: str, path: str, token: str, version: str = 'v21.0', **kwargs):
    url = f"{GRAPH_URL}/{version or 'v21.0'}/{path.lstrip('/')}"
    params = kwargs.pop('params', {}) or {}
    params['access_token'] = token
    try:
        resp = requests.request(method, url, params=params, timeout=kwargs.pop('timeout', TIMEOUT), **kwargs)
    except requests.RequestException as e:
        raise WhatsAppAPIError(f'No se pudo conectar con Meta: {e}')
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if resp.status_code >= 400 or (isinstance(data, dict) and 'error' in data):
        err = (data or {}).get('error', {}) if isinstance(data, dict) else {}
        code = err.get('code')
        hints = {
            10: 'La app no tiene permiso para esta acción (pages_messaging / instagram_manage_messages).',
            190: 'El token de la página es inválido o expiró.',
            200: 'Permisos insuficientes en la página.',
            551: 'El usuario no está disponible para recibir mensajes.',
            2018278: 'Fuera de la ventana de mensajería: el cliente debe escribir de nuevo.',
        }
        message = hints.get(code) or hints.get(err.get('error_subcode')) or err.get('message') \
            or f'Error HTTP {resp.status_code}'
        raise WhatsAppAPIError(message, code=code, subcode=err.get('error_subcode'),
                               details=err.get('error_user_msg'), status=resp.status_code)
    return data


# ── Configuración ────────────────────────────────────────────────────────────

def list_pages(provider):
    data = _graph('GET', 'me/accounts', provider.access_token, provider.api_version, params={
        'fields': 'id,name,access_token,instagram_business_account{id,username,name}',
        'limit': 100,
    })
    pages = []
    for p in data.get('data', []):
        ig = p.get('instagram_business_account') or {}
        pages.append({
            'page_id': p.get('id'),
            'name': p.get('name'),
            'has_token': bool(p.get('access_token')),
            'access_token': p.get('access_token', ''),
            'instagram_account_id': ig.get('id', ''),
            'instagram_username': ig.get('username', ''),
        })
    return pages


def subscribe_page(page):
    _graph('POST', f'{page.page_id}/subscribed_apps', page.page_access_token, page.provider.api_version,
           params={'subscribed_fields': SUBSCRIBED_FIELDS})
    page.subscribed = True
    page.last_error = ''
    page.save(update_fields=['subscribed', 'last_error'])
    return True


def test_page(page):
    if page.platform == 'instagram' and page.instagram_account_id:
        return _graph('GET', page.instagram_account_id, page.page_access_token, page.provider.api_version,
                      params={'fields': 'id,username,name'})
    return _graph('GET', page.page_id, page.page_access_token, page.provider.api_version,
                  params={'fields': 'id,name'})


def _profile_name(page, user_id: str) -> str:
    try:
        if page.platform == 'instagram':
            data = _graph('GET', user_id, page.page_access_token, page.provider.api_version,
                          params={'fields': 'name,username'})
            return data.get('name') or (f"@{data['username']}" if data.get('username') else '')
        data = _graph('GET', user_id, page.page_access_token, page.provider.api_version,
                      params={'fields': 'first_name,last_name'})
        return f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    except WhatsAppAPIError as e:
        logger.debug(f"[Meta] No se pudo obtener perfil {user_id}: {e.message}")
        return ''


# ── Webhook ──────────────────────────────────────────────────────────────────

_ATTACHMENT_TYPES = {'image': 'image', 'video': 'video', 'audio': 'audio', 'file': 'document',
                     'sticker': 'sticker', 'animated_image': 'image'}


def _find_page(provider, platform: str, account_id: str):
    from django.db.models import Q
    from .models import MetaPage
    return MetaPage.objects.select_related('channel', 'provider').filter(
        provider=provider, platform=platform, is_active=True,
    ).filter(Q(page_id=account_id) | Q(instagram_account_id=account_id)).first()


def _ts_ms(value):
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=dt_timezone.utc)
    except (TypeError, ValueError):
        return timezone.now()


def _handle_message(page, event: dict):
    from .models import Conversation, Message
    from .routing import ingest_inbound

    msg = event.get('message') or {}
    if msg.get('is_echo'):
        return  # mensajes enviados por la propia página (incluidos los nuestros)
    sender_id = (event.get('sender') or {}).get('id', '')
    if not sender_id:
        return
    sent_at = _ts_ms(event.get('timestamp'))

    existing = Conversation.objects.filter(channel=page.channel, contact_identifier=sender_id) \
        .exclude(contact_name='').order_by('-started_at').first()
    name = existing.contact_name if existing else _profile_name(page, sender_id)

    text = msg.get('text', '')
    attachments = msg.get('attachments') or []
    meta = {'mid': msg.get('mid')}
    if msg.get('reply_to'):
        meta['reply_to'] = (msg['reply_to'] or {}).get('mid')
    if (msg.get('quick_reply') or {}).get('payload'):
        meta['quick_reply_payload'] = msg['quick_reply']['payload']

    result = ingest_inbound(
        page.channel, sender_id,
        message_type='text' if text or not attachments else _ATTACHMENT_TYPES.get(attachments[0].get('type'), 'document'),
        body=text, metadata=meta, external_id=msg.get('mid'), sent_at=sent_at,
        name=name, config=page,
    )
    if not result:
        return
    conv, first, _created = result

    from .tasks import download_remote_media
    for idx, att in enumerate(attachments):
        mtype = _ATTACHMENT_TYPES.get(att.get('type'), 'document')
        url = (att.get('payload') or {}).get('url')
        if not url:
            continue
        if idx == 0 and not text:
            target = first
            target.metadata = {**(target.metadata or {}), 'remote_url': url}
            target.save(update_fields=['metadata'])
        else:
            target = Message.objects.create(
                conversation=conv, direction='inbound', message_type=mtype, body='',
                status='received', sent_at=sent_at, metadata={'remote_url': url, 'mid': msg.get('mid')},
            )
        download_remote_media.delay(target.id)


def _handle_postback(page, event: dict):
    from .routing import ingest_inbound
    pb = event.get('postback') or {}
    sender_id = (event.get('sender') or {}).get('id', '')
    if not sender_id:
        return
    ingest_inbound(
        page.channel, sender_id, message_type='button', body=pb.get('title', ''),
        metadata={'payload': pb.get('payload')}, external_id=pb.get('mid'),
        sent_at=_ts_ms(event.get('timestamp')), config=page,
    )


def _handle_delivery_read(page, event: dict):
    from .models import Message
    from .realtime import push
    sender_id = (event.get('sender') or {}).get('id', '')
    qs = Message.objects.filter(conversation__channel=page.channel,
                                conversation__contact_identifier=sender_id, direction='outbound')
    if 'delivery' in event:
        mids = (event['delivery'] or {}).get('mids') or []
        targets = qs.filter(external_id__in=mids, status='sent') if mids else \
            qs.filter(status='sent', sent_at__lte=_ts_ms((event['delivery'] or {}).get('watermark')))
        new_status = 'delivered'
    else:
        targets = qs.filter(status__in=['sent', 'delivered'],
                            sent_at__lte=_ts_ms((event.get('read') or {}).get('watermark')))
        new_status = 'read'
    for m in list(targets.select_related('conversation')[:200]):
        m.status = new_status
        m.save(update_fields=['status'])
        push(m.conversation, 'message.status', {'message_id': m.id, 'message_status': new_status})


def process_page_webhook(provider, payload: dict):
    obj = payload.get('object')
    if obj not in ('page', 'instagram'):
        return
    platform = 'instagram' if obj == 'instagram' else 'messenger'
    for entry in payload.get('entry', []):
        page = _find_page(provider, platform, str(entry.get('id', '')))
        if not page:
            logger.warning(f"[Meta] Webhook {obj} para cuenta {entry.get('id')} sin página configurada")
            continue
        for event in entry.get('messaging', []) or []:
            try:
                if 'message' in event:
                    _handle_message(page, event)
                elif 'postback' in event:
                    _handle_postback(page, event)
                elif 'delivery' in event or 'read' in event:
                    _handle_delivery_read(page, event)
            except Exception:
                logger.exception(f"[Meta] Error procesando evento {obj}")


# ── Envío ────────────────────────────────────────────────────────────────────

def send_page_message(message) -> str:
    conv = message.conversation
    page = conv.channel.meta_page
    body = {'recipient': {'id': conv.contact_identifier}}
    if conv.needs_human_agent_tag:
        body.update({'messaging_type': 'MESSAGE_TAG', 'tag': 'HUMAN_AGENT'})
    else:
        body['messaging_type'] = 'RESPONSE'

    meta = message.metadata or {}
    local_path = meta.get('local_path')
    if message.message_type in ('image', 'video', 'audio', 'document') and local_path:
        if page.platform == 'instagram':
            raise WhatsAppAPIError('Instagram solo permite enviar texto desde VozipOmni por ahora.')
        att_type = 'file' if message.message_type == 'document' else message.message_type
        import json
        form = {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in body.items()}
        form['message'] = json.dumps({'attachment': {'type': att_type, 'payload': {'is_reusable': False}}})
        mime = meta.get('mime_type') or 'application/octet-stream'
        with open(local_path, 'rb') as fh:
            data = _graph('POST', f'{page.page_id}/messages', page.page_access_token, page.provider.api_version,
                          data=form, files={'filedata': (meta.get('filename') or os.path.basename(local_path), fh, mime)},
                          timeout=120)
        mid = data.get('message_id', '')
        # El texto que acompaña al adjunto se envía como mensaje aparte
        if message.body:
            _graph('POST', f'{page.page_id}/messages', page.page_access_token, page.provider.api_version,
                   json={**body, 'message': {'text': message.body}})
        return mid

    data = _graph('POST', f'{page.page_id}/messages', page.page_access_token, page.provider.api_version,
                  json={**body, 'message': {'text': message.body or ' '}})
    return data.get('message_id', '')
