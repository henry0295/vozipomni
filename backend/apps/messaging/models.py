"""
Modelos de mensajería multicanal.

Arquitectura:
  Channel → tipo de canal (whatsapp, sms, email, chat)
  Conversation → hilo de conversación entre agente y contacto
  Message → mensaje individual en una conversación
"""
from django.db import models
from django.utils import timezone


class Channel(models.Model):
    """Canal de comunicación configurado (ej: número WhatsApp Business)."""

    CHANNEL_TYPES = [
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('chat', 'Chat Web'),
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

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    body = models.TextField(verbose_name='Cuerpo del mensaje')
    media_url = models.URLField(null=True, blank=True, verbose_name='Adjunto')
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(default=timezone.now)
    external_id = models.CharField(
        max_length=255, null=True, blank=True,
        help_text='ID del mensaje en la plataforma externa (WhatsApp, Twilio, etc.)'
    )

    class Meta:
        db_table = 'messaging_messages'
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'
        ordering = ['sent_at']
        indexes = [models.Index(fields=['conversation', 'sent_at'], name='messaging_m_conv_idx')]

    def __str__(self):
        return f"[{self.direction}] {self.body[:60]}"
