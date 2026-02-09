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
    Troncales SIP - Configuración completa PJSIP Wizard
    """
    TRUNK_TYPE_CHOICES = [
        ('nat_provider', 'Proveedor con NAT'),
        ('no_nat_provider', 'Proveedor sin NAT'),
        ('pbx_lan', 'PBX en LAN'),
        ('corporate', 'Troncal Corporativa'),
        ('custom', 'Personalizado'),
    ]
    
    PROTOCOL_CHOICES = [
        ('udp', 'UDP'),
        ('tcp', 'TCP'),
        ('tls', 'TLS'),
    ]
    
    DTMF_CHOICES = [
        ('rfc4733', 'RFC4733 (Recomendado)'),
        ('rfc2833', 'RFC2833'),
        ('inband', 'Inband'),
        ('info', 'SIP INFO'),
        ('auto', 'Auto'),
    ]
    
    CONTEXT_CHOICES = [
        ('from-pstn', 'Desde PSTN'),
        ('from-pbx', 'Desde PBX'),
        ('from-trunk', 'Desde Troncal'),
        ('custom', 'Personalizado'),
    ]
    
    # Información Básica
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')
    trunk_type = models.CharField(
        max_length=20, 
        choices=TRUNK_TYPE_CHOICES, 
        default='nat_provider', 
        verbose_name='Tipo de Troncal'
    )
    
    # Conexión
    host = models.CharField(max_length=200, verbose_name='Host/IP o FQDN')
    port = models.IntegerField(default=5060, verbose_name='Puerto')
    protocol = models.CharField(max_length=10, choices=PROTOCOL_CHOICES, default='udp', verbose_name='Protocolo')
    
    # Autenticación Saliente (desde VoziPOmni hacia el proveedor)
    outbound_auth_username = models.CharField(max_length=100, blank=True, verbose_name='Usuario Saliente')
    outbound_auth_password = models.CharField(max_length=100, blank=True, verbose_name='Contraseña Saliente')
    from_user = models.CharField(max_length=100, blank=True, verbose_name='From User')
    from_domain = models.CharField(max_length=200, blank=True, verbose_name='From Domain')
    
    # Autenticación Entrante (desde el proveedor hacia VoziPOmni)
    inbound_auth_username = models.CharField(max_length=100, blank=True, verbose_name='Usuario Entrante')
    inbound_auth_password = models.CharField(max_length=100, blank=True, verbose_name='Contraseña Entrante')
    
    # Registro
    sends_registration = models.BooleanField(default=True, verbose_name='Enviar Registro')
    registration_server_uri = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name='Server URI para Registro',
        help_text='Ej: sip:proveedor.com o sip:proveedor.com:5060'
    )
    registration_client_uri = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name='Client URI para Registro',
        help_text='Ej: sip:usuario@proveedor.com'
    )
    registration_retry_interval = models.IntegerField(
        default=60, 
        verbose_name='Intervalo de Reintento (seg)'
    )
    registration_expiration = models.IntegerField(
        default=3600, 
        verbose_name='Expiración Registro (seg)'
    )
    
    # Comportamiento SIP
    sends_auth = models.BooleanField(default=True, verbose_name='Enviar Autenticación')
    accepts_auth = models.BooleanField(default=False, verbose_name='Aceptar Autenticación')
    accepts_registrations = models.BooleanField(default=False, verbose_name='Aceptar Registros')
    
    # Configuración RTP/Media
    rtp_symmetric = models.BooleanField(default=True, verbose_name='RTP Simétrico')
    force_rport = models.BooleanField(default=True, verbose_name='Forzar RPORT')
    rewrite_contact = models.BooleanField(default=True, verbose_name='Reescribir Contact')
    direct_media = models.BooleanField(default=False, verbose_name='Media Directa')
    
    # Códecs y DTMF
    codec = models.CharField(
        max_length=100, 
        default='ulaw,alaw,g729', 
        verbose_name='Códecs',
        help_text='Separados por coma'
    )
    dtmf_mode = models.CharField(
        max_length=20, 
        choices=DTMF_CHOICES, 
        default='rfc4733', 
        verbose_name='Modo DTMF'
    )
    
    # Context y Timers
    context = models.CharField(
        max_length=50, 
        choices=CONTEXT_CHOICES, 
        default='from-pstn', 
        verbose_name='Contexto Dialplan'
    )
    custom_context = models.CharField(max_length=50, blank=True, verbose_name='Contexto Personalizado')
    timers = models.BooleanField(default=True, verbose_name='Session Timers')
    timers_min_se = models.IntegerField(default=90, verbose_name='Min SE (seg)')
    timers_sess_expires = models.IntegerField(default=1800, verbose_name='Session Expires (seg)')
    
    # Qualify (Monitoreo)
    qualify_enabled = models.BooleanField(default=True, verbose_name='Habilitar Qualify')
    qualify_frequency = models.IntegerField(default=60, verbose_name='Frecuencia Qualify (seg)')
    qualify_timeout = models.FloatField(default=3.0, verbose_name='Timeout Qualify (seg)')
    
    # Canales y Caller ID
    max_channels = models.IntegerField(default=10, verbose_name='Canales Máximos')
    caller_id = models.CharField(max_length=50, blank=True, verbose_name='Caller ID')
    caller_id_name = models.CharField(max_length=100, blank=True, verbose_name='Nombre Caller ID')
    
    # NAT y Red
    local_net = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Red Local',
        help_text='Ej: 192.168.0.0/16, 10.0.0.0/8'
    )
    external_media_address = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='IP Externa Media',
        help_text='IP pública para RTP cuando está detrás de NAT'
    )
    external_signaling_address = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='IP Externa Señalización',
        help_text='IP pública para SIP cuando está detrás de NAT'
    )
    
    # Opciones Avanzadas
    language = models.CharField(max_length=10, default='es', verbose_name='Idioma')
    trust_id_inbound = models.BooleanField(default=False, verbose_name='Confiar en ID Entrante')
    trust_id_outbound = models.BooleanField(default=False, verbose_name='Confiar en ID Saliente')
    send_pai = models.BooleanField(default=False, verbose_name='Enviar P-Asserted-Identity')
    send_rpid = models.BooleanField(default=False, verbose_name='Enviar Remote-Party-ID')
    
    # Estado
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    is_registered = models.BooleanField(default=False, verbose_name='Registrado')
    last_registration_time = models.DateTimeField(null=True, blank=True, verbose_name='Última Registro')
    
    # Estadísticas
    calls_total = models.IntegerField(default=0, verbose_name='Total llamadas')
    calls_active = models.IntegerField(default=0, verbose_name='Llamadas activas')
    calls_successful = models.IntegerField(default=0, verbose_name='Llamadas exitosas')
    calls_failed = models.IntegerField(default=0, verbose_name='Llamadas fallidas')
    
    # Configuración Raw (para tipo "custom")
    pjsip_config_custom = models.TextField(
        blank=True, 
        verbose_name='Configuración PJSIP Personalizada',
        help_text='Solo para tipo "Personalizado". Configuración PJSIP Wizard raw.'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sip_trunks'
        verbose_name = 'Troncal SIP'
        verbose_name_plural = 'Troncales SIP'
    
    def __str__(self):
        return f"{self.name} ({self.host}:{self.port})"
    
    # Backward compatibility
    @property
    def username(self):
        """Alias para compatibilidad con código existente"""
        return self.outbound_auth_username
    
    @property
    def password(self):
        """Alias para compatibilidad con código existente"""
        return self.outbound_auth_password
    
    def get_context_value(self):
        """Obtener el valor real del contexto"""
        if self.context == 'custom' and self.custom_context:
            return self.custom_context
        return self.context
    
    def needs_registration(self):
        """Verificar si esta troncal necesita/debe registrarse"""
        return self.sends_registration and bool(self.registration_server_uri)


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
