"""
Lógica de negocio de WhatsApp (independiente del transporte HTTP):

  process_webhook_payload(provider, payload) → procesa mensajes y estados entrantes de Meta
  send_outbound(message)                      → envía un Message saliente por la Cloud API
  create_outbound(conversation, ...)          → crea y envía un mensaje saliente
  auto_assign(conversation)                   → asigna al agente disponible con menos chats
"""
import logging
import re
from datetime import datetime, timezone as dt_timezone

from django.db.models import Q
from django.utils import timezone

from .models import Channel, Conversation, Message, WhatsAppLine
from .realtime import push
from .whatsapp_service import WhatsAppAPIError, client_for_line, extract_message_id

logger = logging.getLogger(__name__)

# Orden de estados de entrega (no se retrocede: read no vuelve a delivered)
_STATUS_RANK = {'pending': 0, 'sent': 1, 'delivered': 2, 'read': 3, 'failed': 4}


def _ts(value):
    try:
        return datetime.fromtimestamp(int(value), tz=dt_timezone.utc)
    except (TypeError, ValueError):
        return timezone.now()


def _find_contact(wa_id: str):
    from apps.contacts.models import Contact
    tail = re.sub(r'\D', '', wa_id)[-10:]
    if not tail:
        return None
    return Contact.objects.filter(
        Q(phone__endswith=tail) | Q(phone2__endswith=tail) | Q(phone3__endswith=tail)
    ).order_by('-updated_at').first()


def _parse_inbound(msg: dict):
    """Devuelve (message_type, body, metadata) a partir del payload de Meta."""
    mtype = msg.get('type', 'unknown')
    meta = {}
    body = ''

    if mtype == 'text':
        body = (msg.get('text') or {}).get('body', '')
    elif mtype in ('image', 'video', 'audio', 'document', 'sticker'):
        media = msg.get(mtype) or {}
        body = media.get('caption', '') or ''
        meta = {
            'media_id': media.get('id'),
            'mime_type': media.get('mime_type'),
            'filename': media.get('filename'),
            'voice': media.get('voice', False),
        }
    elif mtype == 'location':
        loc = msg.get('location') or {}
        body = loc.get('name') or loc.get('address') or 'Ubicación compartida'
        meta = {k: loc.get(k) for k in ('latitude', 'longitude', 'name', 'address', 'url')}
    elif mtype == 'contacts':
        contacts = msg.get('contacts') or []
        names = [((c.get('name') or {}).get('formatted_name') or '') for c in contacts]
        body = 'Contacto compartido: ' + ', '.join(n for n in names if n)
        meta = {'contacts': contacts}
    elif mtype == 'interactive':
        inter = msg.get('interactive') or {}
        reply = inter.get('button_reply') or inter.get('list_reply') or {}
        body = reply.get('title', '')
        meta = {'reply_id': reply.get('id'), 'interactive_type': inter.get('type')}
    elif mtype == 'button':
        btn = msg.get('button') or {}
        body = btn.get('text', '')
        meta = {'payload': btn.get('payload')}
    elif mtype == 'reaction':
        reaction = msg.get('reaction') or {}
        body = reaction.get('emoji', '')
        meta = {'reacted_message_id': reaction.get('message_id')}
    else:
        mtype = 'unknown'
        errors = msg.get('errors') or []
        body = (errors[0].get('title') if errors else '') or 'Mensaje no soportado'

    if msg.get('context'):
        meta['reply_to'] = msg['context'].get('id')
    return mtype, body, meta


def auto_assign(conversation: Conversation, line: WhatsAppLine | None = None):
    """Compatibilidad: la lógica vive en routing.auto_assign (común a todos los canales)."""
    from .routing import auto_assign as _auto_assign
    return _auto_assign(conversation, line)


def _keywords(value: str):
    return {k.strip().upper() for k in (value or '').split(',') if k.strip()}


def _handle_opt_keywords(line: WhatsAppLine, conv: Conversation, body: str) -> bool:
    """
    Palabras clave de baja/alta (ej: BAJA / ALTA). Actualiza el consentimiento de
    WhatsApp de los contactos con ese número y confirma al cliente.
    Devuelve True si el mensaje era una palabra clave.
    """
    from apps.contacts.models import Contact

    word = (body or '').strip().upper().rstrip('.!')
    if not word:
        return False
    opt_out = word in _keywords(line.opt_out_keywords)
    opt_in = word in _keywords(line.opt_in_keywords)
    if not (opt_out or opt_in):
        return False

    tail = re.sub(r'\D', '', conv.contact_identifier)[-10:]
    contacts = Contact.objects.filter(
        Q(phone__endswith=tail) | Q(phone2__endswith=tail) | Q(phone3__endswith=tail)
    ) if tail else Contact.objects.none()
    now = timezone.now()
    if opt_out:
        contacts.update(whatsapp_opt_in=False, whatsapp_opt_in_at=now, whatsapp_opt_in_source='keyword_out')
    else:
        contacts.update(whatsapp_opt_in=True, whatsapp_opt_in_at=now, whatsapp_opt_in_source='keyword')
    conv.metadata = {**(conv.metadata or {}), 'whatsapp_opt_in': bool(opt_in), 'opt_changed_at': now.isoformat()}
    conv.save(update_fields=['metadata'])

    reply = (line.opt_out_reply if opt_out else line.opt_in_reply) or ''
    if reply.strip():
        try:
            create_outbound(conv, body=reply.strip(), sender=None, system=True)
        except Exception as e:
            logger.warning(f"[WhatsApp] No se pudo confirmar opt-in/out: {e}")
    logger.info(f"[WhatsApp] {'Opt-out' if opt_out else 'Opt-in'} de {conv.contact_identifier} "
                f"({contacts.count()} contacto/s)")
    return True


def _handle_inbound(line: WhatsAppLine, msg: dict, profiles: dict):
    from .routing import ingest_inbound, send_auto_replies

    wa_id = msg.get('from', '')
    mtype, body, meta = _parse_inbound(msg)

    result = ingest_inbound(
        line.channel, wa_id,
        message_type=mtype, body=body, metadata=meta,
        external_id=msg.get('id'), sent_at=_ts(msg.get('timestamp')),
        name=profiles.get(wa_id, ''), contact=_find_contact(wa_id), config=line,
        auto_replies=False,
    )
    if result is None:
        return  # Meta reintenta webhooks: duplicado
    conv, message, created = result

    # Descargar media en segundo plano
    if meta.get('media_id'):
        try:
            from .tasks import download_whatsapp_media
            download_whatsapp_media.delay(message.id)
        except Exception as e:
            logger.warning(f"[WhatsApp] No se pudo encolar descarga de media: {e}")

    # Palabra clave de baja/alta: se confirma y no se envían otras respuestas automáticas
    if mtype == 'text' and _handle_opt_keywords(line, conv, body):
        return
    send_auto_replies(conv, line, created)


def _handle_status(line: WhatsAppLine, st: dict):
    external_id = st.get('id')
    new_status = st.get('status')
    if not external_id or new_status not in _STATUS_RANK:
        return
    msg = Message.objects.select_related('conversation').filter(external_id=external_id).first()
    if not msg:
        return
    current = _STATUS_RANK.get(msg.status, 0)
    if new_status != 'failed' and _STATUS_RANK[new_status] <= current:
        return
    msg.status = new_status
    fields = ['status']
    if new_status == 'failed':
        errors = st.get('errors') or []
        if errors:
            e = errors[0]
            msg.error_message = f"{e.get('code', '')} {e.get('title', '')} {(e.get('error_data') or {}).get('details', '')}".strip()
            fields.append('error_message')
    msg.save(update_fields=fields)
    _sync_broadcast_recipient(msg)
    push(msg.conversation, 'message.status', {'message_id': msg.id, 'message_status': new_status,
                                              'error': msg.error_message})


def _sync_broadcast_recipient(msg: Message):
    """Refleja el estado de entrega en el destinatario del envío masivo (si aplica)."""
    try:
        from .models import WhatsAppBroadcastRecipient
        WhatsAppBroadcastRecipient.objects.filter(message=msg).update(
            status=msg.status if msg.status in ('sent', 'delivered', 'read', 'failed') else 'sent',
            error=msg.error_message or '',
        )
    except Exception as e:
        logger.debug(f"[WhatsApp] No se pudo actualizar destinatario de envío masivo: {e}")


def process_webhook_payload(provider, payload: dict):
    """Procesa el cuerpo de un webhook de Meta (objeto whatsapp_business_account)."""
    if payload.get('object') != 'whatsapp_business_account':
        return
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') != 'messages':
                continue
            value = change.get('value') or {}
            phone_number_id = (value.get('metadata') or {}).get('phone_number_id')
            line = WhatsAppLine.objects.select_related('channel', 'provider').filter(
                phone_number_id=phone_number_id, provider=provider, is_active=True,
            ).first()
            if not line:
                logger.warning(f"[WhatsApp] Webhook para phone_number_id={phone_number_id} sin línea configurada")
                continue
            profiles = {
                c.get('wa_id'): (c.get('profile') or {}).get('name', '')
                for c in value.get('contacts', [])
            }
            for msg in value.get('messages', []):
                try:
                    _handle_inbound(line, msg, profiles)
                except Exception:
                    logger.exception("[WhatsApp] Error procesando mensaje entrante")
            for st in value.get('statuses', []):
                try:
                    _handle_status(line, st)
                except Exception:
                    logger.exception("[WhatsApp] Error procesando estado")


# ── Salientes ────────────────────────────────────────────────────────────────

class WindowClosedError(Exception):
    """Fuera de la ventana de 24 h: solo se permiten plantillas."""


MEDIA_TYPES = ('image', 'video', 'audio', 'document', 'sticker')


def _send_whatsapp(message: Message, line: WhatsAppLine):
    client = client_for_line(line)
    to = message.conversation.contact_identifier
    meta = message.metadata or {}
    if message.message_type == 'template':
        return client.send_template(
            line.phone_number_id, to,
            name=meta.get('template_name'),
            language=meta.get('language', 'es'),
            body_params=meta.get('body_params') or [],
            header_params=meta.get('header_params') or [],
        )
    if message.message_type in MEDIA_TYPES:
        media_id = meta.get('wa_media_id')
        if not media_id and meta.get('local_path'):
            # Subir el archivo a Meta (queda disponible 30 días) y enviar por ID
            media_id = client.upload_media(line.phone_number_id, meta['local_path'],
                                           meta.get('mime_type') or 'application/octet-stream')
            message.metadata = {**meta, 'wa_media_id': media_id}
            message.save(update_fields=['metadata'])
        if media_id:
            return client.send_media_id(line.phone_number_id, to, message.message_type, media_id,
                                        caption=message.body or None, filename=meta.get('filename'))
        if message.media_url:
            return client.send_media(line.phone_number_id, to, message.message_type, message.media_url,
                                     caption=message.body or None, filename=meta.get('filename'))
    return client.send_text(line.phone_number_id, to, message.body)


def send_outbound(message: Message) -> Message:
    """
    Envía un Message saliente ya creado por el canal de su conversación.
    Actualiza status / external_id / error y notifica por WebSocket.
    """
    conv = message.conversation
    channel = conv.channel
    ctype = channel.channel_type
    try:
        if ctype == 'whatsapp' and getattr(channel, 'whatsapp_line', None):
            message.external_id = extract_message_id(_send_whatsapp(message, channel.whatsapp_line))
        elif ctype == 'email' and getattr(channel, 'email_account', None):
            from .email_channel import send_email_message
            message.external_id = send_email_message(message)
        elif ctype in ('messenger', 'instagram') and getattr(channel, 'meta_page', None):
            from .meta_pages import send_page_message
            message.external_id = send_page_message(message)
        # webchat / otros: el visitante lo recoge por la API pública (no hay envío externo)
        message.status = 'sent'
        message.error_message = ''
    except WhatsAppAPIError as e:
        message.status = 'failed'
        message.error_message = e.message + (f" — {e.details}" if e.details else '')
    except Exception as e:
        logger.exception(f"[Messaging] Error enviando mensaje {message.id} por {ctype}")
        message.status = 'failed'
        message.error_message = str(e)[:500]
    message.save(update_fields=['external_id', 'status', 'error_message'])
    push(conv, 'message.status', {'message_id': message.id, 'message_status': message.status,
                                  'error': message.error_message})
    return message


def render_template_preview(template, body_params=None, header_params=None) -> str:
    """Texto legible de la plantilla con los parámetros sustituidos."""
    def fill(text, params):
        for i, p in enumerate(params or [], start=1):
            text = text.replace('{{%d}}' % i, str(p))
        return text
    parts = []
    if template.header_text:
        parts.append(fill(template.header_text, header_params))
    parts.append(fill(template.body_text, body_params))
    return '\n'.join(p for p in parts if p)


def create_outbound(conversation: Conversation, body: str = '', sender=None, *,
                    message_type: str = 'text', metadata: dict | None = None,
                    media_url: str | None = None, system: bool = False,
                    enforce_window: bool = True) -> Message:
    """Crea y envía un mensaje saliente respetando la ventana de mensajería del canal."""
    ctype = conversation.channel.channel_type
    if enforce_window and message_type != 'template' and not conversation.is_window_open:
        if ctype == 'whatsapp':
            raise WindowClosedError(
                'Han pasado más de 24 h desde el último mensaje del cliente. '
                'Para escribirle debes usar una plantilla aprobada por Meta.'
            )
        if ctype in ('messenger', 'instagram'):
            raise WindowClosedError(
                'Han pasado más de 7 días desde el último mensaje del cliente. '
                'Meta no permite escribirle hasta que vuelva a escribir.'
            )

    now = timezone.now()
    message = Message.objects.create(
        conversation=conversation,
        direction='outbound',
        message_type=message_type,
        body=body,
        media_url=media_url,
        status='pending',
        sender=sender,
        metadata={**(metadata or {}), **({'system': True} if system else {})},
        is_read=True,
        sent_at=now,
    )
    updates = {'last_message_at': now}
    if conversation.status != 'open' and conversation.agent_id:
        updates['status'] = 'open'
    # Métrica: primera respuesta humana (no cuentan bienvenida / fuera de horario / masivos)
    if sender is not None and not system and not conversation.first_response_at:
        updates['first_response_at'] = now
    for k, v in updates.items():
        setattr(conversation, k, v)
    conversation.save(update_fields=list(updates))

    push(conversation, 'message.new', {'message_id': message.id, 'direction': 'outbound',
                                       'preview': (body or '')[:120]})
    return send_outbound(message)


def channel_for_line_defaults(provider, name: str, display_number: str = '') -> Channel:
    return Channel.objects.create(
        name=name,
        channel_type='whatsapp',
        identifier=display_number or name,
        is_active=True,
    )
