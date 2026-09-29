"""
Envíos masivos de plantillas de WhatsApp.

Flujo:
  start_broadcast(b)      → arma destinatarios desde la lista de contactos (opt-in, DNC, sin duplicados)
                            y deja el envío en 'running'
  send_batch(b)           → envía hasta rate_per_minute destinatarios pendientes (tarea cada 60 s)

Cada envío crea (o reutiliza) la conversación del contacto y la deja cerrada con
closed_reason='broadcast': si el cliente responde, routing la reabre con el historial.
"""
import logging
import re

from django.db import transaction
from django.utils import timezone

from .models import Conversation, WhatsAppBroadcast, WhatsAppBroadcastRecipient

logger = logging.getLogger(__name__)

PLACEHOLDER = re.compile(r'\{([a-z_]+(?:\.[\w-]+)?)\}')


def render_param(template: str, contact) -> str:
    """Sustituye {first_name}, {last_name}, {full_name}, {company}, {city}, {phone}, {custom.campo}."""
    def repl(m):
        key = m.group(1)
        if contact is None:
            return ''
        if key.startswith('custom.'):
            return str((contact.custom_fields or {}).get(key[7:], '') or '')
        if key == 'full_name':
            return contact.full_name
        return str(getattr(contact, key, '') or '')
    return PLACEHOLDER.sub(repl, str(template or '')).strip()


def _normalize(phone: str) -> str:
    return re.sub(r'\D', '', phone or '')


def start_broadcast(broadcast: WhatsAppBroadcast) -> dict:
    """Genera los destinatarios y pone el envío en marcha. Idempotente para destinatarios."""
    from apps.contacts.models import Blacklist, Contact

    if broadcast.status not in ('draft', 'scheduled', 'paused'):
        raise ValueError(f'No se puede iniciar un envío en estado {broadcast.status}')
    if str(broadcast.template.status).upper() != 'APPROVED':
        raise ValueError('La plantilla no está aprobada por Meta.')

    if not broadcast.recipients.exists():
        if not broadcast.contact_list_id:
            raise ValueError('Selecciona una lista de contactos.')
        blocked = {_normalize(p)[-10:] for p in Blacklist.objects.filter(is_active=True).values_list('phone', flat=True)}
        qs = Contact.objects.filter(contact_list_id=broadcast.contact_list_id, dnc_opt_out=False) \
            .exclude(status='blacklisted')
        eligible, skipped, seen = [], 0, set()
        for c in qs.iterator():
            phone = _normalize(c.phone or c.phone2 or c.phone3)
            if len(phone) < 8 or phone in seen or phone[-10:] in blocked:
                skipped += 1
                continue
            if broadcast.require_opt_in and not c.whatsapp_opt_in:
                skipped += 1
                continue
            seen.add(phone)
            eligible.append(WhatsAppBroadcastRecipient(broadcast=broadcast, contact=c, phone=phone))
        WhatsAppBroadcastRecipient.objects.bulk_create(eligible, batch_size=1000, ignore_conflicts=True)
        broadcast.total_recipients = len(eligible)
        broadcast.skipped_count = skipped

    broadcast.status = 'running'
    broadcast.started_at = broadcast.started_at or timezone.now()
    broadcast.last_error = ''
    broadcast.save(update_fields=['status', 'started_at', 'total_recipients', 'skipped_count', 'last_error'])
    return {'total': broadcast.total_recipients, 'skipped': broadcast.skipped_count}


def _conversation_for(broadcast, recipient):
    channel = broadcast.line.channel
    conv = Conversation.objects.filter(channel=channel, contact_identifier=recipient.phone) \
        .exclude(status='closed').order_by('-started_at').first()
    if conv:
        return conv, False
    conv = Conversation.objects.create(
        channel=channel, contact_identifier=recipient.phone, contact=recipient.contact,
        contact_name=recipient.contact.full_name if recipient.contact else '',
        campaign=broadcast.line.default_campaign, status='closed', closed_at=timezone.now(),
        closed_reason='broadcast', metadata={'broadcast_id': broadcast.id},
    )
    return conv, True


def send_to_recipient(broadcast, recipient):
    from .whatsapp import create_outbound, render_template_preview

    contact = recipient.contact
    body_params = [render_param(p, contact) for p in (broadcast.body_params or [])]
    header_params = [render_param(p, contact) for p in (broadcast.header_params or [])]
    if any(not p for p in body_params + header_params):
        recipient.status = 'failed'
        recipient.error = 'Faltan datos del contacto para completar las variables de la plantilla.'
        recipient.save(update_fields=['status', 'error'])
        return recipient

    conv, _ = _conversation_for(broadcast, recipient)
    tpl = broadcast.template
    msg = create_outbound(
        conv,
        body=render_template_preview(tpl, body_params, header_params),
        sender=broadcast.created_by,
        message_type='template',
        system=True,  # no cuenta como primera respuesta del agente
        metadata={'template_name': tpl.name, 'language': tpl.language,
                  'body_params': body_params, 'header_params': header_params,
                  'broadcast_id': broadcast.id},
    )
    # create_outbound reabre la conversación si tiene agente: mantenerla cerrada hasta que respondan
    if conv.status != 'closed' and conv.closed_reason == 'broadcast':
        conv.status = 'closed'
        conv.save(update_fields=['status'])
    recipient.message = msg
    recipient.sent_at = timezone.now()
    recipient.status = 'failed' if msg.status == 'failed' else 'sent'
    recipient.error = msg.error_message or ''
    recipient.save(update_fields=['message', 'sent_at', 'status', 'error'])
    return recipient


def send_batch(broadcast_id: int) -> dict:
    """Envía un lote. Devuelve {'sent', 'failed', 'remaining', 'status'}."""
    with transaction.atomic():
        broadcast = WhatsAppBroadcast.objects.select_for_update().select_related(
            'line__channel', 'line__provider', 'template', 'created_by',
        ).filter(id=broadcast_id).first()
        if not broadcast or broadcast.status != 'running':
            return {'status': getattr(broadcast, 'status', 'missing'), 'sent': 0, 'failed': 0, 'remaining': 0}
        batch = list(broadcast.recipients.filter(status='pending').select_related('contact')
                     .order_by('id')[:max(1, broadcast.rate_per_minute)])

    sent = failed = 0
    for recipient in batch:
        try:
            send_to_recipient(broadcast, recipient)
            if recipient.status == 'failed':
                failed += 1
            else:
                sent += 1
        except Exception as e:
            failed += 1
            recipient.status = 'failed'
            recipient.error = str(e)[:500]
            recipient.save(update_fields=['status', 'error'])
            logger.warning(f"[Broadcast {broadcast_id}] Error con {recipient.phone}: {e}")
        # Si el token es inválido o la cuenta está bloqueada, todos fallarán: detener
        if failed >= 10 and sent == 0:
            broadcast.status = 'paused'
            broadcast.last_error = recipient.error or 'Demasiados errores consecutivos.'
            broadcast.save(update_fields=['status', 'last_error'])
            return {'status': 'paused', 'sent': sent, 'failed': failed,
                    'remaining': broadcast.recipients.filter(status='pending').count()}

    remaining = broadcast.recipients.filter(status='pending').count()
    if remaining == 0:
        broadcast.status = 'completed'
        broadcast.finished_at = timezone.now()
        broadcast.save(update_fields=['status', 'finished_at'])
    return {'status': broadcast.status, 'sent': sent, 'failed': failed, 'remaining': remaining}


def stats(broadcast) -> dict:
    from django.db.models import Count
    counts = dict(broadcast.recipients.values_list('status').annotate(n=Count('id')))
    replied = Conversation.objects.filter(
        metadata__broadcast_id=broadcast.id, last_inbound_at__isnull=False,
        last_inbound_at__gte=broadcast.started_at or broadcast.created_at,
    ).count() if broadcast.started_at else 0
    return {
        'pending': counts.get('pending', 0),
        'sent': counts.get('sent', 0) + counts.get('delivered', 0) + counts.get('read', 0),
        'delivered': counts.get('delivered', 0) + counts.get('read', 0),
        'read': counts.get('read', 0),
        'failed': counts.get('failed', 0),
        'replied': replied,
    }
