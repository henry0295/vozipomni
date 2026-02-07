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


class Extension(models.Model):
    """
    Extensiones telefónicas
    """
    EXTENSION_TYPE_CHOICES = [
        ('SIP', 'SIP'),
        ('IAX2', 'IAX2'),
        ('PJSIP', 'PJSIP'),
    ]
    
    CONTEXT_CHOICES = [
        ('from-internal', 'from-internal'),
        ('from-external', 'from-external'),
        ('custom', 'custom'),
    ]
    
    extension = models.CharField(max_length=20, unique=True, verbose_name='Extensión')
    name = models.CharField(max_length=100, verbose_name='Nombre')
    extension_type = models.CharField(max_length=10, choices=EXTENSION_TYPE_CHOICES, default='SIP', verbose_name='Tipo')
    secret = models.CharField(max_length=100, verbose_name='Contraseña')
    context = models.CharField(max_length=50, choices=CONTEXT_CHOICES, default='from-internal', verbose_name='Contexto')
    callerid = models.CharField(max_length=100, blank=True, verbose_name='Caller ID')
    email = models.EmailField(blank=True, verbose_name='Email')
    voicemail_enabled = models.BooleanField(default=False, verbose_name='Buzón habilitado')
    
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'extensions'
        ordering = ['extension']
        verbose_name = 'Extensión'
        verbose_name_plural = 'Extensiones'
    
    def __str__(self):
        return f"{self.extension} - {self.name}"


class InboundRoute(models.Model):
    """
    Rutas entrantes (DIDs)
    """
    DESTINATION_TYPE_CHOICES = [
        ('ivr', 'IVR'),
        ('queue', 'Cola'),
        ('extension', 'Extensión'),
        ('voicemail', 'Buzón de Voz'),
        ('announcement', 'Anuncio'),
    ]
    
    did = models.CharField(max_length=50, unique=True, verbose_name='DID/Número')
    description = models.CharField(max_length=200, verbose_name='Descripción')
    destination_type = models.CharField(max_length=20, choices=DESTINATION_TYPE_CHOICES, verbose_name='Tipo destino')
    destination = models.CharField(max_length=100, verbose_name='Destino')
    priority = models.IntegerField(default=1, verbose_name='Prioridad')
    time_condition = models.CharField(max_length=100, blank=True, verbose_name='Condición horario')
    
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inbound_routes'
        ordering = ['priority', 'did']
        verbose_name = 'Ruta Entrante'
        verbose_name_plural = 'Rutas Entrantes'
    
    def __str__(self):
        return f"{self.did} - {self.description}"


class OutboundRoute(models.Model):
    """
    Rutas salientes
    """
    name = models.CharField(max_length=100, verbose_name='Nombre')
    pattern = models.CharField(max_length=50, verbose_name='Patrón')
    trunk = models.ForeignKey(SIPTrunk, on_delete=models.CASCADE, related_name='outbound_routes', verbose_name='Troncal')
    prepend = models.CharField(max_length=20, blank=True, verbose_name='Prefijo agregar')
    prefix = models.CharField(max_length=10, blank=True, verbose_name='Dígitos eliminar')
    callerid_prefix = models.CharField(max_length=50, blank=True, verbose_name='Prefijo Caller ID')
    
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'outbound_routes'
        ordering = ['name']
        verbose_name = 'Ruta Saliente'
        verbose_name_plural = 'Rutas Salientes'
    
    def __str__(self):
        return f"{self.name} ({self.pattern})"


class Voicemail(models.Model):
    """
    Buzones de voz
    """
    mailbox = models.CharField(max_length=20, unique=True, verbose_name='Buzón')
    name = models.CharField(max_length=100, verbose_name='Nombre')
    email = models.EmailField(verbose_name='Email')
    password = models.CharField(max_length=20, verbose_name='Contraseña')
    email_attach = models.BooleanField(default=True, verbose_name='Adjuntar audio')
    email_delete = models.BooleanField(default=False, verbose_name='Eliminar después de enviar')
    max_messages = models.IntegerField(default=100, verbose_name='Mensajes máximos')
    
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'voicemails'
        ordering = ['mailbox']
        verbose_name = 'Buzón de Voz'
        verbose_name_plural = 'Buzones de Voz'
    
    def __str__(self):
        return f"{self.mailbox} - {self.name}"


class MusicOnHold(models.Model):
    """
    Música en espera
    """
    MODE_CHOICES = [
        ('files', 'Archivos'),
        ('quietmp3', 'MP3 Silencioso'),
        ('custom', 'Aplicación Personalizada'),
    ]
    
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    description = models.CharField(max_length=200, verbose_name='Descripción')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='files', verbose_name='Modo')
    directory = models.CharField(max_length=500, blank=True, verbose_name='Directorio')
    application = models.CharField(max_length=500, blank=True, verbose_name='Aplicación')
    
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'music_on_hold'
        ordering = ['name']
        verbose_name = 'Música en Espera'
        verbose_name_plural = 'Música en Espera'
    
    def __str__(self):
        return self.name


class TimeCondition(models.Model):
    """
    Condiciones de horario
    """
    DESTINATION_TYPE_CHOICES = [
        ('ivr', 'IVR'),
        ('queue', 'Cola'),
        ('extension', 'Extensión'),
        ('voicemail', 'Buzón de Voz'),
        ('announcement', 'Anuncio'),
    ]
    
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    time_groups = models.JSONField(default=list, verbose_name='Grupos de horarios')
    
    # Si cumple la condición
    true_destination_type = models.CharField(max_length=20, choices=DESTINATION_TYPE_CHOICES, verbose_name='Tipo destino (true)')
    true_destination = models.CharField(max_length=100, verbose_name='Destino (true)')
    
    # Si NO cumple la condición
    false_destination_type = models.CharField(max_length=20, choices=DESTINATION_TYPE_CHOICES, verbose_name='Tipo destino (false)')
    false_destination = models.CharField(max_length=100, verbose_name='Destino (false)')
    
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'time_conditions'
        ordering = ['name']
        verbose_name = 'Condición de Horario'
        verbose_name_plural = 'Condiciones de Horario'
    
    def __str__(self):
        return self.name
