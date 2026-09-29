"""
Modelos de mensajería multicanal.

Arquitectura:
  Channel → tipo de canal (whatsapp, sms, email, chat)
  Conversation → hilo de conversación entre agente y contacto
  Message → mensaje individual en una conversación
"""
from django.db import models
from django.utils import timezone

from core.fields import EncryptedCharField, EncryptedTextField


class Channel(models.Model):
    """Canal de comunicación configurado (ej: número WhatsApp Business)."""

    CHANNEL_TYPES = [
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('chat', 'Chat Web (legacy)'),
        ('webchat', 'Chat Web'),
        ('messenger', 'Facebook Messenger'),
        ('instagram', 'Instagram'),
    ]

    name = models.CharField(max_length=100, verbose_name='Nombre')
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES, verbose_name='Tipo')
    identifier = models.CharField(
        max_length=200, verbose_name='Identificador',
        help_text='Número de teléfono, dirección de email o URL del canal'
    )
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'messaging_channels'
        verbose_name = 'Canal'
        verbose_name_plural = 'Canales'
        ordering = ['channel_type', 'name']

    def __str__(self):
        return f"{self.get_channel_type_display()} — {self.name}"


class Conversation(models.Model):
    """Hilo de conversación entre un agente y un contacto."""

    STATUS_CHOICES = [
        ('open', 'Abierta'),
        ('waiting', 'En espera'),
        ('closed', 'Cerrada'),
    ]

    channel = models.ForeignKey(Channel, on_delete=models.PROTECT, related_name='conversations')
    agent = models.ForeignKey(
        'agents.Agent', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='conversations'
    )
    contact = models.ForeignKey(
        'contacts.Contact', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='conversations'
    )
    contact_identifier = models.CharField(
        max_length=200, verbose_name='Identificador del contacto',
        help_text='Número/email del contacto en este canal'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    started_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    campaign = models.ForeignKey(
        'campaigns.Campaign', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='conversations'
    )
    # Nombre de perfil del contacto en el canal (ej: nombre de WhatsApp)
    contact_name = models.CharField(max_length=200, blank=True, default='')
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # Último mensaje ENTRANTE: define la ventana de 24 h de WhatsApp para texto libre
    last_inbound_at = models.DateTimeField(null=True, blank=True)

    # Tipificación al cerrar
    disposition = models.ForeignKey(
        'campaigns.CampaignDisposition', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='conversations', verbose_name='Tipificación'
    )
    tags = models.ManyToManyField('ConversationTag', blank=True, related_name='conversations')
    close_notes = models.TextField(blank=True, default='', verbose_name='Notas de cierre')
    # agent | broadcast | system
    closed_reason = models.CharField(max_length=20, blank=True, default='')

    # Métricas
    assigned_at = models.DateTimeField(null=True, blank=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    after_hours_notified_at = models.DateTimeField(null=True, blank=True)

    # Email: asunto del hilo · Webchat: datos del visitante, etc.
    subject = models.CharField(max_length=300, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)

    WHATSAPP_WINDOW_HOURS = 24
    # Messenger/Instagram: 24 h estándar + etiqueta HUMAN_AGENT hasta 7 días
    META_HUMAN_AGENT_DAYS = 7

    @property
    def window_hours(self):
        ctype = self.channel.channel_type
        if ctype == 'whatsapp':
            return self.WHATSAPP_WINDOW_HOURS
        if ctype in ('messenger', 'instagram'):
            return self.META_HUMAN_AGENT_DAYS * 24
        return None

    @property
    def is_window_open(self):
        """
        WhatsApp: texto libre solo dentro de 24 h desde el último mensaje del cliente.
        Messenger/Instagram: hasta 7 días (etiqueta HUMAN_AGENT después de 24 h).
        Email / chat web: sin ventana.
        """
        hours = self.window_hours
        if hours is None:
            return True
        if not self.last_inbound_at:
            return False
        from datetime import timedelta
        return timezone.now() - self.last_inbound_at < timedelta(hours=hours)

    @property
    def needs_human_agent_tag(self):
        """Messenger/Instagram fuera de las 24 h estándar (pero dentro de 7 días)."""
        if self.channel.channel_type not in ('messenger', 'instagram') or not self.last_inbound_at:
            return False
        from datetime import timedelta
        return timezone.now() - self.last_inbound_at >= timedelta(hours=24)

    class Meta:
        db_table = 'messaging_conversations'
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status', 'agent'], name='messaging_c_status_idx'),
            models.Index(fields=['channel', 'contact_identifier'], name='messaging_c_channel_idx'),
        ]

    def __str__(self):
        return f"Conv #{self.pk} [{self.get_status_display()}]"


class Message(models.Model):
    """Mensaje individual dentro de una conversación."""

    DIRECTION_CHOICES = [
        ('inbound', 'Entrante'),
        ('outbound', 'Saliente'),
    ]

    TYPE_CHOICES = [
        ('text', 'Texto'),
        ('template', 'Plantilla'),
        ('image', 'Imagen'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('document', 'Documento'),
        ('sticker', 'Sticker'),
        ('location', 'Ubicación'),
        ('contacts', 'Contactos'),
        ('interactive', 'Interactivo'),
        ('button', 'Botón'),
        ('reaction', 'Reacción'),
        ('system', 'Sistema'),
        ('unknown', 'Desconocido'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('sent', 'Enviado'),
        ('delivered', 'Entregado'),
        ('read', 'Leído'),
        ('failed', 'Fallido'),
        ('received', 'Recibido'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    message_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text')
    body = models.TextField(verbose_name='Cuerpo del mensaje', blank=True)
    media_url = models.URLField(null=True, blank=True, verbose_name='Adjunto')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    error_message = models.TextField(blank=True, default='')
    sender = models.ForeignKey(
        'users.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sent_messages', help_text='Usuario que envió el mensaje (salientes)'
    )
    # Datos extra: media_id, mime_type, filename, caption, template, parámetros, payload crudo
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(default=timezone.now)
    external_id = models.CharField(
        max_length=255, null=True, blank=True, db_index=True,
        help_text='ID del mensaje en la plataforma externa (WhatsApp, Twilio, etc.)'
    )

    class Meta:
        db_table = 'messaging_messages'
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'
        ordering = ['sent_at']
        indexes = [models.Index(fields=['conversation', 'sent_at'], name='messaging_m_conv_idx')]

    def __str__(self):
        return f"[{self.direction}] {(self.body or self.message_type)[:60]}"


# ══════════════════════════════════════════════════════════════════════════════
# WhatsApp Business — integración directa con Meta (Cloud API)
#
# Modelo inspirado en OMniLeads: Proveedor (App de Meta) → Líneas (números)
#   • WhatsAppProvider: App de Meta for Developers + token de Usuario del Sistema.
#     El webhook se configura en Meta con la URL /api/messaging/webhooks/meta/<app_id>/
#     y el verify_token generado aquí.
#   • WhatsAppLine: número de WhatsApp Business (Phone Number ID + WABA ID),
#     vinculado 1:1 a un Channel para reutilizar Conversation/Message.
#   • WhatsAppTemplate: plantillas aprobadas por Meta (necesarias para iniciar
#     conversación o escribir fuera de la ventana de 24 h).
# ══════════════════════════════════════════════════════════════════════════════

def _generate_verify_token():
    import secrets
    return secrets.token_urlsafe(24)


class WhatsAppProvider(models.Model):
    """App de Meta que da acceso a la WhatsApp Cloud API."""

    name = models.CharField(max_length=100, verbose_name='Nombre')
    app_id = models.CharField(max_length=64, unique=True, verbose_name='App ID')
    app_secret = EncryptedCharField(
        max_length=255, blank=True, default='', verbose_name='App Secret',
        help_text='Se usa para validar la firma X-Hub-Signature-256 de los webhooks.'
    )
    access_token = EncryptedTextField(
        blank=True, default='', verbose_name='Token de acceso',
        help_text='Token permanente del Usuario del Sistema (Business Manager) con permisos '
                  'whatsapp_business_messaging y whatsapp_business_management.'
    )
    verify_token = models.CharField(
        max_length=100, default=_generate_verify_token, verbose_name='Token de verificación',
        help_text='Se ingresa en Meta al configurar el webhook.'
    )
    api_version = models.CharField(max_length=10, default='v21.0', verbose_name='Versión Graph API')
    business_id = models.CharField(max_length=64, blank=True, default='', verbose_name='Business Portfolio ID')
    is_active = models.BooleanField(default=True)

    webhook_verified = models.BooleanField(default=False)
    webhook_verified_at = models.DateTimeField(null=True, blank=True)
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'whatsapp_providers'
        verbose_name = 'Proveedor WhatsApp (Meta)'
        verbose_name_plural = 'Proveedores WhatsApp (Meta)'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (App {self.app_id})"


class WhatsAppLine(models.Model):
    """Número de WhatsApp Business conectado vía Cloud API."""

    STATUS_CHOICES = [
        ('pending', 'Pendiente de verificación'),
        ('connected', 'Conectada'),
        ('error', 'Error'),
        ('disabled', 'Deshabilitada'),
    ]

    provider = models.ForeignKey(WhatsAppProvider, on_delete=models.PROTECT, related_name='lines')
    channel = models.OneToOneField(Channel, on_delete=models.CASCADE, related_name='whatsapp_line')
    name = models.CharField(max_length=100, verbose_name='Nombre de la línea')
    waba_id = models.CharField(max_length=64, verbose_name='WhatsApp Business Account ID')
    phone_number_id = models.CharField(max_length=64, unique=True, verbose_name='Phone Number ID')

    # Datos informativos obtenidos de Meta
    display_phone_number = models.CharField(max_length=30, blank=True, default='')
    verified_name = models.CharField(max_length=200, blank=True, default='')
    quality_rating = models.CharField(max_length=20, blank=True, default='')
    messaging_limit = models.CharField(max_length=40, blank=True, default='')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_detail = models.TextField(blank=True, default='')
    webhook_subscribed = models.BooleanField(default=False)

    # Enrutamiento
    default_campaign = models.ForeignKey(
        'campaigns.Campaign', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='whatsapp_lines', verbose_name='Campaña por defecto'
    )
    auto_assign = models.BooleanField(
        default=True, verbose_name='Asignación automática',
        help_text='Asignar las conversaciones nuevas al agente disponible con menos chats abiertos.'
    )
    max_chats_per_agent = models.PositiveIntegerField(default=5, verbose_name='Chats simultáneos por agente')
    welcome_message = models.TextField(
        blank=True, default='', verbose_name='Mensaje de bienvenida',
        help_text='Respuesta automática al primer mensaje de una conversación nueva.'
    )
    # Horario de atención
    time_condition = models.ForeignKey(
        'telephony.TimeCondition', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='whatsapp_lines', verbose_name='Horario de atención'
    )
    after_hours_message = models.TextField(
        blank=True, default='', verbose_name='Mensaje fuera de horario'
    )
    # Opt-in / opt-out por palabra clave (separadas por coma, sin distinguir mayúsculas)
    opt_out_keywords = models.CharField(max_length=200, blank=True, default='BAJA,STOP,CANCELAR')
    opt_in_keywords = models.CharField(max_length=200, blank=True, default='ALTA,SUSCRIBIR')
    opt_out_reply = models.TextField(
        blank=True, default='Listo, no volverás a recibir mensajes promocionales. Escribe ALTA para suscribirte de nuevo.'
    )
    opt_in_reply = models.TextField(blank=True, default='¡Gracias! Quedaste suscrito a nuestras novedades.')
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'whatsapp_lines'
        verbose_name = 'Línea WhatsApp'
        verbose_name_plural = 'Líneas WhatsApp'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.display_phone_number or self.phone_number_id})"


class WhatsAppTemplate(models.Model):
    """Plantilla de mensaje registrada en la WABA (sincronizada desde Meta)."""

    line = models.ForeignKey(WhatsAppLine, on_delete=models.CASCADE, related_name='templates')
    meta_id = models.CharField(max_length=64, blank=True, default='')
    name = models.CharField(max_length=512)
    language = models.CharField(max_length=15, default='es')
    category = models.CharField(max_length=30, blank=True, default='')
    status = models.CharField(max_length=30, blank=True, default='')
    rejected_reason = models.CharField(max_length=200, blank=True, default='')
    components = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'whatsapp_templates'
        verbose_name = 'Plantilla WhatsApp'
        verbose_name_plural = 'Plantillas WhatsApp'
        ordering = ['name', 'language']
        unique_together = [('line', 'name', 'language')]

    def __str__(self):
        return f"{self.name} [{self.language}] {self.status}"

    def _component(self, ctype):
        for c in self.components or []:
            if str(c.get('type', '')).upper() == ctype:
                return c
        return None

    @property
    def body_text(self):
        c = self._component('BODY')
        return c.get('text', '') if c else ''

    @property
    def header_text(self):
        c = self._component('HEADER')
        return c.get('text', '') if c and c.get('format', '').upper() == 'TEXT' else ''

    @property
    def body_param_count(self):
        import re
        return len(set(re.findall(r'\{\{(\d+)\}\}', self.body_text)))

    @property
    def header_param_count(self):
        import re
        return len(set(re.findall(r'\{\{(\d+)\}\}', self.header_text)))


# ══════════════════════════════════════════════════════════════════════════════
# Gestión de conversaciones: etiquetas y respuestas rápidas
# ══════════════════════════════════════════════════════════════════════════════

class ConversationTag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Etiqueta')
    color = models.CharField(max_length=20, default='gray')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'messaging_tags'
        ordering = ['name']
        verbose_name = 'Etiqueta de conversación'
        verbose_name_plural = 'Etiquetas de conversación'

    def __str__(self):
        return self.name


class QuickReply(models.Model):
    """Respuesta rápida. campaign vacío = disponible en todas las campañas."""

    title = models.CharField(max_length=100, verbose_name='Título')
    shortcut = models.CharField(max_length=30, blank=True, default='', help_text='Ej: /saludo')
    body = models.TextField(verbose_name='Texto')
    campaign = models.ForeignKey(
        'campaigns.Campaign', null=True, blank=True, on_delete=models.CASCADE,
        related_name='quick_replies'
    )
    channel_type = models.CharField(max_length=20, blank=True, default='',
                                    help_text='Vacío = todos los canales')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messaging_quick_replies'
        ordering = ['order', 'title']
        verbose_name = 'Respuesta rápida'
        verbose_name_plural = 'Respuestas rápidas'

    def __str__(self):
        return self.title


# ══════════════════════════════════════════════════════════════════════════════
# Envíos masivos de plantillas WhatsApp
# ══════════════════════════════════════════════════════════════════════════════

class WhatsAppBroadcast(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('scheduled', 'Programado'),
        ('running', 'Enviando'),
        ('paused', 'Pausado'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
        ('failed', 'Fallido'),
    ]

    name = models.CharField(max_length=200)
    line = models.ForeignKey(WhatsAppLine, on_delete=models.PROTECT, related_name='broadcasts')
    template = models.ForeignKey(WhatsAppTemplate, on_delete=models.PROTECT, related_name='broadcasts')
    contact_list = models.ForeignKey(
        'contacts.ContactList', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='whatsapp_broadcasts'
    )
    # Parámetros con marcadores: {first_name}, {last_name}, {full_name}, {company}, {city}, {custom.campo}
    body_params = models.JSONField(default=list, blank=True)
    header_params = models.JSONField(default=list, blank=True)
    require_opt_in = models.BooleanField(
        default=True, help_text='Solo enviar a contactos con consentimiento (opt-in) de WhatsApp.'
    )
    rate_per_minute = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_recipients = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default='')
    created_by = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'whatsapp_broadcasts'
        ordering = ['-created_at']
        verbose_name = 'Envío masivo WhatsApp'
        verbose_name_plural = 'Envíos masivos WhatsApp'

    def __str__(self):
        return self.name


class WhatsAppBroadcastRecipient(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('sent', 'Enviado'),
        ('delivered', 'Entregado'),
        ('read', 'Leído'),
        ('failed', 'Fallido'),
    ]

    broadcast = models.ForeignKey(WhatsAppBroadcast, on_delete=models.CASCADE, related_name='recipients')
    contact = models.ForeignKey('contacts.Contact', null=True, blank=True, on_delete=models.SET_NULL)
    phone = models.CharField(max_length=30)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    message = models.ForeignKey(Message, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='broadcast_recipients')
    error = models.TextField(blank=True, default='')
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'whatsapp_broadcast_recipients'
        unique_together = [('broadcast', 'phone')]
        indexes = [models.Index(fields=['broadcast', 'status'], name='wa_bc_rcpt_status_idx')]


# ══════════════════════════════════════════════════════════════════════════════
# Otros canales: Email, Chat web, Messenger/Instagram
# ══════════════════════════════════════════════════════════════════════════════

class RoutingSettings(models.Model):
    """Campos comunes de enrutamiento y horario para cada canal."""

    default_campaign = models.ForeignKey(
        'campaigns.Campaign', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='Campaña por defecto'
    )
    auto_assign = models.BooleanField(default=True)
    max_chats_per_agent = models.PositiveIntegerField(default=5)
    welcome_message = models.TextField(blank=True, default='')
    time_condition = models.ForeignKey(
        'telephony.TimeCondition', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name='Horario de atención'
    )
    after_hours_message = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EmailAccount(RoutingSettings):
    """Buzón de correo atendido como canal (IMAP entrada + SMTP salida)."""

    channel = models.OneToOneField(Channel, on_delete=models.CASCADE, related_name='email_account')
    name = models.CharField(max_length=100)
    email_address = models.EmailField(unique=True)
    from_name = models.CharField(max_length=100, blank=True, default='')
    signature = models.TextField(blank=True, default='')

    imap_host = models.CharField(max_length=200)
    imap_port = models.PositiveIntegerField(default=993)
    imap_ssl = models.BooleanField(default=True)
    imap_username = models.CharField(max_length=200)
    imap_password = EncryptedCharField(max_length=500, blank=True, default='')
    imap_folder = models.CharField(max_length=100, default='INBOX')

    smtp_host = models.CharField(max_length=200)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_starttls = models.BooleanField(default=True)
    smtp_ssl = models.BooleanField(default=False)
    smtp_username = models.CharField(max_length=200, blank=True, default='')
    smtp_password = EncryptedCharField(max_length=500, blank=True, default='')

    last_uid = models.BigIntegerField(default=0)
    last_polled_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'messaging_email_accounts'
        verbose_name = 'Cuenta de email'
        verbose_name_plural = 'Cuentas de email'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} <{self.email_address}>"


def _generate_widget_key():
    import secrets
    return secrets.token_urlsafe(16)


class WebChatWidget(RoutingSettings):
    """Widget de chat para incrustar en un sitio web."""

    channel = models.OneToOneField(Channel, on_delete=models.CASCADE, related_name='webchat_widget')
    name = models.CharField(max_length=100)
    widget_key = models.CharField(max_length=64, unique=True, default=_generate_widget_key)
    allowed_origins = models.TextField(
        blank=True, default='',
        help_text='Un dominio por línea (ej: https://www.miempresa.com). Vacío = cualquier sitio.'
    )
    title = models.CharField(max_length=100, default='¿Hablamos?')
    subtitle = models.CharField(max_length=200, blank=True, default='Te respondemos en minutos')
    primary_color = models.CharField(max_length=20, default='#16a34a')
    position = models.CharField(max_length=10, default='right')  # right | left
    require_name = models.BooleanField(default=True)
    require_email = models.BooleanField(default=False)
    intro_text = models.TextField(blank=True, default='Déjanos tus datos y cuéntanos en qué te ayudamos.')

    class Meta:
        db_table = 'messaging_webchat_widgets'
        verbose_name = 'Widget de chat web'
        verbose_name_plural = 'Widgets de chat web'
        ordering = ['name']

    def __str__(self):
        return self.name

    def origin_allowed(self, origin: str) -> bool:
        allowed = [o.strip().rstrip('/').lower() for o in (self.allowed_origins or '').splitlines() if o.strip()]
        if not allowed:
            return True
        return (origin or '').rstrip('/').lower() in allowed


class MetaPage(RoutingSettings):
    """Página de Facebook (Messenger) o cuenta de Instagram conectada vía la App de Meta."""

    PLATFORM_CHOICES = [('messenger', 'Facebook Messenger'), ('instagram', 'Instagram')]

    provider = models.ForeignKey(WhatsAppProvider, on_delete=models.PROTECT, related_name='pages')
    channel = models.OneToOneField(Channel, on_delete=models.CASCADE, related_name='meta_page')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    name = models.CharField(max_length=200)
    page_id = models.CharField(max_length=64, help_text='ID de la página de Facebook')
    instagram_account_id = models.CharField(
        max_length=64, blank=True, default='',
        help_text='ID de la cuenta profesional de Instagram (solo para Instagram)'
    )
    page_access_token = EncryptedTextField(blank=True, default='')
    subscribed = models.BooleanField(default=False)
    last_error = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'messaging_meta_pages'
        verbose_name = 'Página Messenger / Instagram'
        verbose_name_plural = 'Páginas Messenger / Instagram'
        ordering = ['platform', 'name']
        unique_together = [('platform', 'page_id')]

    def __str__(self):
        return f"{self.get_platform_display()} · {self.name}"

    @property
    def webhook_account_id(self):
        """ID que llega en entry.id del webhook: página (Messenger) o cuenta IG (Instagram)."""
        return self.instagram_account_id if self.platform == 'instagram' else self.page_id
