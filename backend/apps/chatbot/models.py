"""
Bot de autoatención (WhatsApp, chat web, Messenger/Instagram) y conectores
con sistemas externos (GLPI, APIs HTTP).

  Connector        → sistema externo con sus credenciales cifradas
  ConnectorLog     → auditoría de cada llamada (sin datos sensibles)
  BotFlow          → flujo editable en el designer (borrador + versión publicada)
  BotFlowVersion   → copia inmutable de un flujo publicado
  BotSession       → estado del bot dentro de una conversación
"""
import json

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.fields import EncryptedTextField


class Connector(models.Model):
    TYPE_CHOICES = [
        ('glpi', 'GLPI (mesa de ayuda)'),
        ('http', 'API HTTP genérica'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    connector_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Tipo')
    base_url = models.URLField(max_length=500, verbose_name='URL base')
    # Configuración no secreta (por tipo). HTTP: headers, acciones. GLPI: ids por defecto.
    config = models.JSONField(default=dict, blank=True)
    # JSON con credenciales (tokens, contraseñas). Se guarda cifrado y nunca se devuelve por la API.
    secrets = EncryptedTextField(blank=True, default='')
    timeout_seconds = models.PositiveIntegerField(default=15)
    verify_ssl = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chatbot_connectors'
        ordering = ['name']
        verbose_name = 'Conector'
        verbose_name_plural = 'Conectores'

    def __str__(self):
        return f"{self.name} ({self.get_connector_type_display()})"

    @property
    def secret_values(self) -> dict:
        try:
            return json.loads(self.secrets or '{}') or {}
        except (TypeError, ValueError):
            return {}

    def set_secret_values(self, values: dict):
        self.secrets = json.dumps(values or {})


class ConnectorLog(models.Model):
    STATUS_CHOICES = [('success', 'Éxito'), ('empty', 'Sin resultados'), ('error', 'Error')]

    connector = models.ForeignKey(Connector, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    duration_ms = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True, default='')
    conversation_id = models.BigIntegerField(null=True, blank=True)
    source = models.CharField(max_length=20, default='bot')  # bot | test | simulator | agent
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'chatbot_connector_logs'
        ordering = ['-created_at']


class BotFlow(models.Model):
    name = models.CharField(max_length=150, verbose_name='Nombre')
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=False, verbose_name='Activo')
    channels = models.ManyToManyField('messaging.Channel', blank=True, related_name='bot_flows')
    # Borrador que edita el designer: {"start": id, "nodes": [...], "edges": [...]}
    draft = models.JSONField(default=dict, blank=True)
    published_version = models.ForeignKey('BotFlowVersion', null=True, blank=True,
                                          on_delete=models.SET_NULL, related_name='+')
    session_timeout_minutes = models.PositiveIntegerField(default=30)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chatbot_flows'
        ordering = ['name']
        verbose_name = 'Flujo de bot'
        verbose_name_plural = 'Flujos de bot'

    def __str__(self):
        return self.name


class BotFlowVersion(models.Model):
    flow = models.ForeignKey(BotFlow, on_delete=models.CASCADE, related_name='versions')
    number = models.PositiveIntegerField()
    definition = models.JSONField(default=dict)
    notes = models.CharField(max_length=300, blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chatbot_flow_versions'
        ordering = ['-number']
        unique_together = [('flow', 'number')]

    def __str__(self):
        return f"{self.flow.name} v{self.number}"


class BotSession(models.Model):
    STATUS_CHOICES = [
        ('active', 'Activa'),
        ('busy', 'Consultando sistema externo'),
        ('handed_off', 'Pasada a asesor'),
        ('completed', 'Terminada'),
        ('timeout', 'Expirada'),
        ('error', 'Error'),
    ]

    conversation = models.OneToOneField('messaging.Conversation', on_delete=models.CASCADE,
                                        related_name='bot_session')
    flow = models.ForeignKey(BotFlow, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='sessions')
    version = models.ForeignKey(BotFlowVersion, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name='sessions')
    current_node = models.CharField(max_length=64, blank=True, default='')
    waiting = models.BooleanField(default=False)  # True: espera respuesta del cliente
    variables = models.JSONField(default=dict, blank=True)
    path = models.JSONField(default=list, blank=True)
    retries = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(default=timezone.now)
    last_activity_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'chatbot_sessions'
        ordering = ['-last_activity_at']

    def __str__(self):
        return f"Bot conv #{self.conversation_id} [{self.status}]"
