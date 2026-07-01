from django.db import models
from django.conf import settings
from django.utils import timezone
from core.validators import validate_phone_number, validate_asterisk_pattern, validate_ip_address, validate_port_number


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
        ('voicemail', 'Buzón de Voz'),
        ('abandoned', 'Abandonada'),
        ('transferred', 'Transferida'),
    ]
    
    # Identificadores
    call_id = models.CharField(max_length=100, unique=True, verbose_name='ID Llamada')
    channel = models.CharField(max_length=200, blank=True, verbose_name='Canal')
    unique_id = models.CharField(max_length=100, blank=True, verbose_name='Unique ID')
    
    # Información de la llamada
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, verbose_name='Dirección')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated', verbose_name='Estado')
    
    # Números
    caller_id = models.CharField(max_length=50, verbose_name='Llamante', validators=[validate_phone_number])
    called_number = models.CharField(max_length=50, verbose_name='Número llamado', validators=[validate_phone_number])
    
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
    queue_enter_time = models.DateTimeField(null=True, blank=True, verbose_name='Hora entrada cola')
    
    # Duraciones (en segundos)
    wait_time = models.IntegerField(default=0, verbose_name='Tiempo espera')
    talk_time = models.IntegerField(default=0, verbose_name='Tiempo conversación')
    hold_time = models.IntegerField(default=0, verbose_name='Tiempo retención')
    
    # Grabación
    recording_file = models.CharField(max_length=500, blank=True, verbose_name='Archivo grabación')
    is_recorded = models.BooleanField(default=False, verbose_name='Grabada')
    
    # Transferencia
    transferred = models.BooleanField(default=False, verbose_name='Transferida')
    transfer_to = models.CharField(max_length=100, blank=True, verbose_name='Transferida a', validators=[validate_phone_number])
    
    # Datos adicionales
    notes = models.TextField(blank=True, verbose_name='Notas')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    
    class Meta:
        db_table = 'calls'
        ordering = ['-start_time']
        verbose_name = 'Llamada'
        verbose_name_plural = 'Llamadas'
        indexes = [
            # Índices originales (renombrados en migración 0004)
            models.Index(fields=['start_time'], name='calls_start_t_e6c81a_idx'),
            models.Index(fields=['agent', 'start_time'], name='calls_agent_i_3202a5_idx'),
            models.Index(fields=['campaign', 'start_time'], name='calls_campaig_d50e84_idx'),
            models.Index(fields=['status'], name='calls_status_79e8c6_idx'),
            models.Index(fields=['direction', 'status'], name='calls_directi_4d42f1_idx'),
        ]
    
    def __str__(self):
        return f"{self.caller_id} -> {self.called_number} ({self.get_status_display()})"
    
    @property
    def duration(self):
        """Calcular duración total de la llamada"""
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
        ('rfc2833', 'RFC2833 (legacy chan_sip — usar rfc4733 para PJSIP)'),
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
    host = models.CharField(max_length=200, verbose_name='Host/IP o FQDN', validators=[validate_ip_address])
    port = models.IntegerField(default=5060, verbose_name='Puerto', validators=[validate_port_number])
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
        default='rfc4733',  # rfc4733 es el nombre correcto para PJSIP (rfc2833 era chan_sip)
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
        indexes = [
            models.Index(fields=['is_active', 'is_registered'], name='trunks_active_reg_idx'),
            models.Index(fields=['trunk_type', 'is_active'], name='trunks_type_active_idx'),
        ]
    
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
    Extensiones telefónicas PJSIP
    Soporta tanto softphones SIP tradicionales como clientes WebRTC.
    """
    EXTENSION_TYPE_CHOICES = [
        ('PJSIP', 'SIP (Softphone)'),
        ('WEBRTC', 'WebRTC (Navegador)'),
    ]

    CONTEXT_CHOICES = [
        ('from-internal', 'from-internal'),
        ('from-external', 'from-external'),
        ('custom', 'custom'),
    ]

    TRANSPORT_CHOICES = [
        ('transport-udp', 'UDP (Softphone)'),
        ('transport-tcp', 'TCP'),
        ('transport-wss', 'WSS (WebRTC)'),
    ]

    extension = models.CharField(max_length=20, unique=True, verbose_name='Extensión')
    name = models.CharField(max_length=100, verbose_name='Nombre')
    extension_type = models.CharField(
        max_length=10,
        choices=EXTENSION_TYPE_CHOICES,
        default='PJSIP',
        verbose_name='Tipo',
        help_text='PJSIP para softphones (MicroSIP, Zoiper), WebRTC para navegador'
    )
    secret = models.CharField(max_length=100, verbose_name='Contraseña')
    context = models.CharField(max_length=50, choices=CONTEXT_CHOICES, default='from-internal', verbose_name='Contexto')
    transport = models.CharField(
        max_length=20,
        choices=TRANSPORT_CHOICES,
        default='transport-udp',
        verbose_name='Transporte',
        help_text='UDP para softphones, WSS para WebRTC'
    )
    callerid = models.CharField(max_length=100, blank=True, verbose_name='Caller ID')
    email = models.EmailField(blank=True, verbose_name='Email')
    voicemail_enabled = models.BooleanField(default=False, verbose_name='Buzón habilitado')
    max_contacts = models.IntegerField(default=1, verbose_name='Contactos máximos')
    codecs = models.CharField(
        max_length=100,
        default='ulaw,alaw,g722',
        blank=True,
        verbose_name='Códecs',
        help_text='Para WebRTC se agrega opus automáticamente'
    )

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
    priority = models.IntegerField(
        default=1, 
        verbose_name='Prioridad',
        help_text='Orden de evaluación (menor = mayor prioridad)'
    )
    ring_time = models.IntegerField(
        default=60, 
        verbose_name='Tiempo de timbre (seg)',
        help_text='Segundos a esperar antes de desistir'
    )
    dial_options = models.CharField(
        max_length=50, 
        default='trg', 
        blank=True,
        verbose_name='Opciones Dial',
        help_text='Opciones de Asterisk Dial: t=transfer, r=ring, g=continue, T=transfer caller, W=recording'
    )
    
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'outbound_routes'
        ordering = ['priority', 'name']
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


class CustomDestination(models.Model):
    """
    Destino personalizado de dialplan Asterisk.
    Permite definir nodos (context + extension + priority) invocables
    desde rutas entrantes, IVR, condiciones horarias, etc.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')

    # Triad Asterisk
    context = models.CharField(max_length=100, verbose_name='Context')
    extension = models.CharField(max_length=50, verbose_name='Extension', default='s')
    priority = models.PositiveIntegerField(default=1, verbose_name='Priority')

    # Destino de fallo (opcional)
    failover_context = models.CharField(max_length=100, blank=True, verbose_name='Context (fallo)')
    failover_extension = models.CharField(max_length=50, blank=True, verbose_name='Extension (fallo)')
    failover_priority = models.PositiveIntegerField(null=True, blank=True, verbose_name='Priority (fallo)')

    is_active = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'custom_destinations'
        ordering = ['name']
        verbose_name = 'Destino Personalizado'
        verbose_name_plural = 'Destinos Personalizados'

    def __str__(self):
        return f'{self.name} ({self.context},{self.extension},{self.priority})'


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
        ('custom_destination', 'Destino Personalizado'),
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


# ──────────────────────────────────────────────────────────────────────────────
# Callback Requests
# ──────────────────────────────────────────────────────────────────────────────

class CallbackRequest(models.Model):
    """
    Solicitud de devolución de llamada.
    Se crea cuando un contacto pide ser llamado más tarde o cuando
    una llamada no es contestada y el sistema programa reintento.
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('scheduled', 'Programado'),
        ('dialing', 'Marcando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('cancelled', 'Cancelado'),
    ]

    phone = models.CharField(max_length=30, verbose_name='Teléfono')
    contact_name = models.CharField(max_length=200, blank=True, verbose_name='Nombre contacto')
    notes = models.TextField(blank=True, verbose_name='Notas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Estado')
    priority = models.IntegerField(default=0, verbose_name='Prioridad')
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='Programado para')
    attempts = models.IntegerField(default=0, verbose_name='Intentos')
    max_attempts = models.IntegerField(default=3, verbose_name='Máx. intentos')

    # Relaciones opcionales
    call = models.ForeignKey('Call', on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='callbacks', verbose_name='Llamada origen')
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='callbacks', verbose_name='Campaña')
    agent = models.ForeignKey('agents.Agent', on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='callbacks_assigned', verbose_name='Agente asignado')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   verbose_name='Creado por')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'callback_requests'
        ordering = ['-priority', 'scheduled_at']
        verbose_name = 'Devolución de Llamada'
        verbose_name_plural = 'Devoluciones de Llamada'
        indexes = [
            models.Index(fields=['status', 'scheduled_at'], name='callback_status_sched_idx'),
            models.Index(fields=['phone'], name='callback_phone_idx'),
        ]

    def __str__(self):
        return f"Callback {self.phone} [{self.status}] @ {self.scheduled_at or 'ASAP'}"


# ──────────────────────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────────────────────

WEBHOOK_EVENTS = [
    ('call.initiated',    'Llamada iniciada'),
    ('call.answered',     'Llamada contestada'),
    ('call.completed',    'Llamada completada'),
    ('call.abandoned',    'Llamada abandonada'),
    ('agent.login',       'Agente conectado'),
    ('agent.logout',      'Agente desconectado'),
    ('agent.status',      'Cambio de estado agente'),
    ('campaign.started',  'Campaña iniciada'),
    ('campaign.paused',   'Campaña pausada'),
    ('campaign.finished', 'Campaña finalizada'),
    ('callback.created',  'Callback creado'),
    ('callback.completed','Callback completado'),
]


class WebhookEndpoint(models.Model):
    """Endpoint externo al que se notifican eventos del contact center."""

    name = models.CharField(max_length=200, verbose_name='Nombre')
    url = models.URLField(max_length=500, verbose_name='URL')
    secret = models.CharField(max_length=200, blank=True, verbose_name='Secret HMAC',
                              help_text='Si se establece, se firma el payload con HMAC-SHA256 en la cabecera X-Webhook-Signature.')
    events = models.JSONField(default=list, verbose_name='Eventos',
                              help_text='Lista de slugs de eventos a notificar (vacío = todos).')
    headers = models.JSONField(default=dict, blank=True, verbose_name='Headers adicionales')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    retry_on_failure = models.BooleanField(default=True, verbose_name='Reintentar en fallo')
    timeout_seconds = models.IntegerField(default=10, verbose_name='Timeout (seg)')

    last_triggered_at = models.DateTimeField(null=True, blank=True, verbose_name='Última ejecución')
    last_status_code = models.IntegerField(null=True, blank=True, verbose_name='Último código HTTP')
    total_deliveries = models.IntegerField(default=0, verbose_name='Entregas totales')
    failed_deliveries = models.IntegerField(default=0, verbose_name='Entregas fallidas')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'webhook_endpoints'
        ordering = ['name']
        verbose_name = 'Webhook'
        verbose_name_plural = 'Webhooks'

    def __str__(self):
        return f"{self.name} → {self.url}"

    def should_notify(self, event_type: str) -> bool:
        """Determina si este endpoint debe ser notificado para este evento."""
        return self.is_active and (not self.events or event_type in self.events)


class WebhookDelivery(models.Model):
    """Log de cada intento de entrega de un webhook."""

    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=100, verbose_name='Tipo de evento')
    payload = models.JSONField(verbose_name='Payload')
    status_code = models.IntegerField(null=True, blank=True, verbose_name='HTTP Status')
    response_body = models.TextField(blank=True, verbose_name='Respuesta')
    success = models.BooleanField(default=False, verbose_name='Exitoso')
    duration_ms = models.IntegerField(default=0, verbose_name='Duración (ms)')
    attempt = models.IntegerField(default=1, verbose_name='Intento')
    error_message = models.TextField(blank=True, verbose_name='Error')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'webhook_deliveries'
        ordering = ['-created_at']
        verbose_name = 'Entrega de Webhook'
        verbose_name_plural = 'Entregas de Webhook'
