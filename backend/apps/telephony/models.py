from django.db import models
from django.conf import settings
from django.utils import timezone


class Call(models.Model):
    """
    Registro de llamadas
    """
    DIRECTION_CHOICES = [
        ('inbound', 'Entrante'),
        ('outbound', 'Saliente'),
    ]
    
    STATUS_CHOICES = [
        ('initiated', 'Iniciada'),
        ('ringing', 'Timbrando'),
        ('answered', 'Contestada'),
        ('completed', 'Completada'),
        ('busy', 'Ocupado'),
        ('no_answer', 'No Contestada'),
        ('failed', 'Fallida'),
        ('cancelled', 'Cancelada'),
    ]
    
    # Identificadores
    call_id = models.CharField(max_length=100, unique=True, verbose_name='ID Llamada')
    channel = models.CharField(max_length=200, blank=True, verbose_name='Canal')
    unique_id = models.CharField(max_length=100, blank=True, verbose_name='Unique ID')
    
    # Información de la llamada
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, verbose_name='Dirección')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated', verbose_name='Estado')
    
    # Números
    caller_id = models.CharField(max_length=50, verbose_name='Llamante')
    called_number = models.CharField(max_length=50, verbose_name='Número llamado')
    
    # Relaciones
    agent = models.ForeignKey('agents.Agent', on_delete=models.SET_NULL, null=True, blank=True, related_name='calls')
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True, blank=True, related_name='calls')
    contact = models.ForeignKey('contacts.Contact', on_delete=models.SET_NULL, null=True, blank=True, related_name='calls')
    queue = models.ForeignKey('queues.Queue', on_delete=models.SET_NULL, null=True, blank=True, related_name='calls')
    disposition = models.ForeignKey('campaigns.CampaignDisposition', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Tiempos
    start_time = models.DateTimeField(default=timezone.now, verbose_name='Hora inicio')
    answer_time = models.DateTimeField(null=True, blank=True, verbose_name='Hora respuesta')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Hora fin')
    
    # Duraciones (en segundos)
    wait_time = models.IntegerField(default=0, verbose_name='Tiempo espera')
    talk_time = models.IntegerField(default=0, verbose_name='Tiempo conversación')
    hold_time = models.IntegerField(default=0, verbose_name='Tiempo retención')
    
    # Grabación
    recording_file = models.CharField(max_length=500, blank=True, verbose_name='Archivo grabación')
    is_recorded = models.BooleanField(default=False, verbose_name='Grabada')
    
    # Transferencia
    transferred = models.BooleanField(default=False, verbose_name='Transferida')
    transfer_to = models.CharField(max_length=100, blank=True, verbose_name='Transferida a')
    
    # Datos adicionales
    notes = models.TextField(blank=True, verbose_name='Notas')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    
    class Meta:
        db_table = 'calls'
        ordering = ['-start_time']
        verbose_name = 'Llamada'
        verbose_name_plural = 'Llamadas'
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['agent', 'start_time']),
            models.Index(fields=['campaign', 'start_time']),
        ]
    
    def __str__(self):
        return f"{self.call_id} - {self.caller_id} -> {self.called_number}"
    
    @property
    def duration(self):
        """Duración total de la llamada"""
        if self.end_time and self.start_time:
            return int((self.end_time - self.start_time).total_seconds())
        return 0


class SIPTrunk(models.Model):
    """
    Troncales SIP
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    host = models.CharField(max_length=200, verbose_name='Host/IP')
    port = models.IntegerField(default=5060, verbose_name='Puerto')
    username = models.CharField(max_length=100, blank=True, verbose_name='Usuario')
    password = models.CharField(max_length=100, blank=True, verbose_name='Contraseña')
    
    # Configuración
    codec = models.CharField(max_length=50, default='ulaw,alaw,gsm', verbose_name='Códecs')
    max_channels = models.IntegerField(default=10, verbose_name='Canales máximos')
    dtmf_mode = models.CharField(max_length=20, default='rfc2833', verbose_name='Modo DTMF')
    
    # Estado
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    is_registered = models.BooleanField(default=False, verbose_name='Registrado')
    
    # Estadísticas
    calls_total = models.IntegerField(default=0, verbose_name='Total llamadas')
    calls_active = models.IntegerField(default=0, verbose_name='Llamadas activas')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sip_trunks'
        verbose_name = 'Troncal SIP'
        verbose_name_plural = 'Troncales SIP'
    
    def __str__(self):
        return f"{self.name} ({self.host}:{self.port})"


class IVR(models.Model):
    """
    Sistema IVR (Interactive Voice Response)
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')
    extension = models.CharField(max_length=20, unique=True, verbose_name='Extensión')
    
    # Audio de bienvenida
    welcome_message = models.CharField(max_length=500, blank=True, verbose_name='Mensaje bienvenida')
    invalid_message = models.CharField(max_length=500, blank=True, verbose_name='Mensaje opción inválida')
    timeout_message = models.CharField(max_length=500, blank=True, verbose_name='Mensaje timeout')
    
    # Configuración
    timeout = models.IntegerField(default=5, verbose_name='Timeout (seg)')
    max_attempts = models.IntegerField(default=3, verbose_name='Intentos máximos')
    
    # Opciones (JSON)
    menu_options = models.JSONField(default=dict, verbose_name='Opciones menú')
    
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ivr_menus'
        verbose_name = 'IVR'
        verbose_name_plural = 'IVRs'
    
    def __str__(self):
        return f"{self.name} ({self.extension})"
