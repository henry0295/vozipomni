"""
Enrutamiento común a todos los canales (WhatsApp, email, chat web, Messenger, Instagram).

  config_for_channel(channel)        → objeto de configuración del canal (línea, cuenta, widget, página)
  auto_assign(conversation, config)  → asigna al agente conectado con menos chats abiertos
  get_or_create_conversation(...)    → conversación abierta del contacto (o nueva)
  ingest_inbound(...)                → registra un mensaje entrante y aplica bienvenida,
                                       asignación automática y respuesta fuera de horario
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import Conversation, Message
from .realtime import push

logger = logging.getLogger(__name__)

# No repetir el aviso de fuera de horario más de una vez cada N horas por conversación
AFTER_HOURS_REPEAT_HOURS = 4
# Una conversación cerrada por un envío masivo se reutiliza si el cliente responde dentro de este plazo
BROADCAST_REUSE_DAYS = 7


def config_for_channel(channel):
    for attr in ('whatsapp_line', 'email_account', 'webchat_widget', 'meta_page'):
        cfg = getattr(channel, attr, None)
        if cfg is not None:
            return cfg
    return None


def is_open_now(config) -> bool:
    from apps.telephony.time_utils import is_open
    return is_open(getattr(config, 'time_condition', None))


def auto_assign(conversation: Conversation, config=None):
    """Asigna la conversación al agente conectado con menos chats abiertos."""
    from apps.agents.models import Agent

    if conversation.agent_id:
        return conversation.agent
    config = config or config_for_channel(conversation.channel)
    if config is not None and not getattr(config, 'auto_assign', True):
        return None

    agents = Agent.objects.exclude(status='offline').filter(user__is_active=True)
    campaign_id = getattr(config, 'default_campaign_id', None) or conversation.campaign_id
    if campaign_id:
        in_campaign = agents.filter(campaigns__id=campaign_id)
        if in_campaign.exists():
            agents = in_campaign

    limit = getattr(config, 'max_chats_per_agent', 5) or 5
    candidate = agents.annotate(
        open_chats=Count('conversations', filter=Q(conversations__status__in=['open', 'waiting']))
    ).filter(open_chats__lt=limit).order_by('open_chats', 'id')
    agent = (candidate.filter(status='available').first()
             or candidate.exclude(status='break').first())
    if agent:
        conversation.agent = agent
        conversation.status = 'open'
        conversation.assigned_at = timezone.now()
        conversation.save(update_fields=['agent', 'status', 'assigned_at'])
        logger.info(f"[Messaging] Conversación {conversation.id} asignada a {agent.agent_id}")
    return agent


def get_or_create_conversation(channel, identifier: str, *, name: str = '', config=None,
                               contact=None, subject: str = '', metadata: dict | None = None):
    """Devuelve (conversación, creada)."""
    conv = Conversation.objects.filter(
        channel=channel, contact_identifier=identifier,
    ).exclude(status='closed').order_by('-started_at').first()

    if not conv:
        # Respuesta a un envío masivo: retomar esa conversación para conservar el contexto
        conv = Conversation.objects.filter(
            channel=channel, contact_identifier=identifier, status='closed',
            closed_reason='broadcast',
            closed_at__gte=timezone.now() - timedelta(days=BROADCAST_REUSE_DAYS),
        ).order_by('-closed_at').first()
        if conv:
            conv.status = 'waiting'
            conv.closed_at = None
            conv.closed_reason = ''
            conv.save(update_fields=['status', 'closed_at', 'closed_reason'])
            return conv, False

    if conv:
        updates = []
        if name and conv.contact_name != name:
            conv.contact_name = name
            updates.append('contact_name')
        if contact and not conv.contact_id:
            conv.contact = contact
            updates.append('contact')
        if updates:
            conv.save(update_fields=updates)
        return conv, False

    conv = Conversation.objects.create(
        channel=channel,
        contact_identifier=identifier,
        contact=contact,
        contact_name=name or '',
        campaign=getattr(config, 'default_campaign', None),
        status='waiting',
        subject=subject or '',
        metadata=metadata or {},
    )
    return conv, True


def ingest_inbound(channel, identifier: str, *, message_type: str = 'text', body: str = '',
                   metadata: dict | None = None, external_id: str | None = None, sent_at=None,
                   name: str = '', contact=None, config=None, subject: str = '',
                   conv_metadata: dict | None = None, auto_replies: bool = True):
    """
    Registra un mensaje entrante. Devuelve (conversación, mensaje, creada) o None si es duplicado.
    """
    if external_id and Message.objects.filter(conversation__channel=channel, external_id=external_id).exists():
        return None
    config = config if config is not None else config_for_channel(channel)
    sent_at = sent_at or timezone.now()

    with transaction.atomic():
        conv, created = get_or_create_conversation(
            channel, identifier, name=name, config=config, contact=contact,
            subject=subject, metadata=conv_metadata,
        )
        message = Message.objects.create(
            conversation=conv,
            direction='inbound',
            message_type=message_type,
            body=body or '',
            status='received',
            metadata=metadata or {},
            sent_at=sent_at,
            external_id=external_id,
        )
        conv.last_message_at = sent_at
        conv.last_inbound_at = sent_at
        fields = ['last_message_at', 'last_inbound_at']
        if conv.status == 'closed':
            conv.status = 'waiting'
            conv.closed_at = None
            fields += ['status', 'closed_at']
        if conv_metadata:
            conv.metadata = {**(conv.metadata or {}), **conv_metadata}
            fields.append('metadata')
        conv.save(update_fields=fields)

    if not conv.agent_id:
        auto_assign(conv, config)

    push(conv, 'message.new', {'message_id': message.id, 'direction': 'inbound',
                               'preview': (body or '')[:120], 'created': created,
                               'channel_type': channel.channel_type})

    if auto_replies and config is not None:
        send_auto_replies(conv, config, created)
    return conv, message, created


def send_auto_replies(conv: Conversation, config, created: bool):
    """Fuera de horario → aviso (máx. cada 4 h). Dentro de horario y conversación nueva → bienvenida."""
    from .whatsapp import create_outbound

    try:
        if not is_open_now(config):
            text = (getattr(config, 'after_hours_message', '') or '').strip()
            last = conv.after_hours_notified_at
            if text and (not last or timezone.now() - last > timedelta(hours=AFTER_HOURS_REPEAT_HOURS)):
                create_outbound(conv, body=text, sender=None, system=True, enforce_window=False)
                conv.after_hours_notified_at = timezone.now()
                conv.save(update_fields=['after_hours_notified_at'])
            return
        welcome = (getattr(config, 'welcome_message', '') or '').strip()
        if created and welcome:
            create_outbound(conv, body=welcome, sender=None, system=True, enforce_window=False)
    except Exception as e:
        logger.warning(f"[Messaging] Error enviando respuesta automática en conv {conv.id}: {e}")
