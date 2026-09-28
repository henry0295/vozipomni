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

from django.db import transaction
from django.db.models import Count, Q
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
    """Asigna la conversación al agente conectado con menos chats abiertos."""
    from apps.agents.models import Agent

    if conversation.agent_id:
        return conversation.agent
    line = line or getattr(conversation.channel, 'whatsapp_line', None)
    if line and not line.auto_assign:
        return None

    agents = Agent.objects.exclude(status='offline').filter(user__is_active=True)
    if line and line.default_campaign_id:
        in_campaign = agents.filter(campaigns__id=line.default_campaign_id)
        if in_campaign.exists():
            agents = in_campaign

    limit = line.max_chats_per_agent if line else 5
    candidate = agents.annotate(
        open_chats=Count('conversations', filter=Q(conversations__status__in=['open', 'waiting']))
    ).filter(open_chats__lt=limit).order_by('open_chats', 'id')
    # Preferir agentes en estado "disponible"; si no hay, cualquier conectado (no en pausa)
    agent = (candidate.filter(status='available').first()
             or candidate.exclude(status='break').first())
    if agent:
        conversation.agent = agent
        conversation.status = 'open'
        conversation.save(update_fields=['agent', 'status'])
        logger.info(f"[WhatsApp] Conversación {conversation.id} asignada a {agent.agent_id}")
    return agent


def _get_or_create_conversation(line: WhatsAppLine, wa_id: str, profile_name: str):
    conv = Conversation.objects.filter(
        channel=line.channel, contact_identifier=wa_id,
    ).exclude(status='closed').order_by('-started_at').first()
    created = False
    if not conv:
        conv = Conversation.objects.create(
            channel=line.channel,
            contact_identifier=wa_id,
            contact=_find_contact(wa_id),
            contact_name=profile_name or '',
            campaign=line.default_campaign,
            status='waiting',
        )
        created = True
    elif profile_name and conv.contact_name != profile_name:
        conv.contact_name = profile_name
        conv.save(update_fields=['contact_name'])
    return conv, created


def _handle_inbound(line: WhatsAppLine, msg: dict, profiles: dict):
    external_id = msg.get('id')
    if external_id and Message.objects.filter(external_id=external_id).exists():
        return  # Meta reintenta webhooks: evitar duplicados

    wa_id = msg.get('from', '')
    mtype, body, meta = _parse_inbound(msg)

    with transaction.atomic():
        conv, created = _get_or_create_conversation(line, wa_id, profiles.get(wa_id, ''))
        sent_at = _ts(msg.get('timestamp'))
        message = Message.objects.create(
            conversation=conv,
            direction='inbound',
            message_type=mtype,
            body=body,
            status='received',
            metadata=meta,
            sent_at=sent_at,
            external_id=external_id,
        )
        conv.last_message_at = sent_at
        conv.last_inbound_at = sent_at
        fields = ['last_message_at', 'last_inbound_at']
        if conv.status == 'closed':
            conv.status = 'waiting'
            fields.append('status')
        conv.save(update_fields=fields)

    if not conv.agent_id:
        auto_assign(conv, line)

    # Descargar media en segundo plano
    if meta.get('media_id'):
        try:
            from .tasks import download_whatsapp_media
            download_whatsapp_media.delay(message.id)
        except Exception as e:
            logger.warning(f"[WhatsApp] No se pudo encolar descarga de media: {e}")

    push(conv, 'message.new', {'message_id': message.id, 'direction': 'inbound',
                               'preview': body[:120], 'created': created})

    if created and line.welcome_message:
        try:
            create_outbound(conv, body=line.welcome_message, sender=None, system=True)
        except Exception as e:
            logger.warning(f"[WhatsApp] Error enviando bienvenida: {e}")


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
    push(msg.conversation, 'message.status', {'message_id': msg.id, 'message_status': new_status,
                                              'error': msg.error_message})


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


def send_outbound(message: Message) -> Message:
    """Envía un Message saliente ya creado. Actualiza status/external_id/error."""
    conv = message.conversation
    line = getattr(conv.channel, 'whatsapp_line', None)
    if conv.channel.channel_type != 'whatsapp' or not line:
        # Otros canales aún sin proveedor: se registra el mensaje localmente
        message.status = 'sent'
        message.save(update_fields=['status'])
        return message

    client = client_for_line(line)
    to = conv.contact_identifier
    meta = message.metadata or {}
    try:
        if message.message_type == 'template':
            resp = client.send_template(
                line.phone_number_id, to,
                name=meta.get('template_name'),
                language=meta.get('language', 'es'),
                body_params=meta.get('body_params') or [],
                header_params=meta.get('header_params') or [],
            )
        elif message.message_type in ('image', 'video', 'audio', 'document') and message.media_url:
            resp = client.send_media(line.phone_number_id, to, message.message_type, message.media_url,
                                     caption=message.body or None, filename=meta.get('filename'))
        else:
            resp = client.send_text(line.phone_number_id, to, message.body)
        message.external_id = extract_message_id(resp)
        message.status = 'sent'
        message.error_message = ''
    except WhatsAppAPIError as e:
        message.status = 'failed'
        message.error_message = e.message + (f" — {e.details}" if e.details else '')
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
    """Crea y envía un mensaje saliente respetando la ventana de 24 h de WhatsApp."""
    if (enforce_window and message_type != 'template'
            and conversation.channel.channel_type == 'whatsapp'
            and not conversation.is_window_open):
        raise WindowClosedError(
            'Han pasado más de 24 h desde el último mensaje del cliente. '
            'Para escribirle debes usar una plantilla aprobada por Meta.'
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
