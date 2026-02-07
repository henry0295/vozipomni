from django.db import models
from django.conf import settings


class Campaign(models.Model):
    """
    Campañas de contact center
    """
    CAMPAIGN_TYPES = [
        ('inbound', 'Entrante'),
        ('outbound', 'Saliente'),
        ('manual', 'Manual'),
        ('preview', 'Preview'),
    ]
    
    DIALER_TYPES = [
        ('predictive', 'Marcador Predictivo'),
        ('progressive', 'Marcador Progresivo'),
        ('preview', 'Marcador Preview'),
        ('manual', 'Marcación Manual'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Activa'),
        ('paused', 'Pausada'),
        ('finished', 'Finalizada'),
        ('draft', 'Borrador'),
    ]
    
    # Información básica
    name = models.CharField(max_length=200, unique=True, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES, verbose_name='Tipo de Campaña')
    dialer_type = models.CharField(max_length=20, choices=DIALER_TYPES, null=True, blank=True, verbose_name='Tipo de Marcador')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='Estado')
    
    # Configuración de campaña
    max_calls_per_agent = models.IntegerField(default=1, verbose_name='Máx. llamadas por agente')
    max_retries = models.IntegerField(default=3, verbose_name='Máx. reintentos')
    retry_delay = models.IntegerField(default=300, help_text="Segundos entre reintentos", verbose_name='Retardo entre reintentos')
    call_timeout = models.IntegerField(default=30, verbose_name='Timeout de llamada (seg)')
    
    # Horarios
    start_date = models.DateTimeField(verbose_name='Fecha inicio')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='Fecha fin')
    schedule_start_time = models.TimeField(null=True, blank=True, verbose_name='Hora inicio diario')
    schedule_end_time = models.TimeField(null=True, blank=True, verbose_name='Hora fin diario')
    
    # Relaciones
    queue = models.ForeignKey('queues.Queue', on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns')
    contact_list = models.ForeignKey('contacts.ContactList', on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns')
    
    # Scripts y formularios
    script_template = models.TextField(blank=True, verbose_name='Guión de llamada')
    form_fields = models.JSONField(default=dict, blank=True, verbose_name='Campos del formulario')
    
    # Métricas
    total_contacts = models.IntegerField(default=0, verbose_name='Total contactos')
    contacted = models.IntegerField(default=0, verbose_name='Contactados')
    successful = models.IntegerField(default=0, verbose_name='Exitosos')
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_campaigns')
    
    class Meta:
        db_table = 'campaigns'
        ordering = ['-created_at']
        verbose_name = 'Campaña'
        verbose_name_plural = 'Campañas'
    
    def __str__(self):
        return f"{self.name} ({self.get_campaign_type_display()})"
    
    @property
    def success_rate(self):
        if self.contacted == 0:
            return 0
        return round((self.successful / self.contacted) * 100, 2)


class CampaignDisposition(models.Model):
    """
    Calificaciones/Disposiciones posibles para una campaña
    """
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='dispositions')
    code = models.CharField(max_length=50, verbose_name='Código')
    name = models.CharField(max_length=200, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')
    is_success = models.BooleanField(default=False, verbose_name='¿Es exitosa?')
    requires_callback = models.BooleanField(default=False, verbose_name='¿Requiere rellamada?')
    order = models.IntegerField(default=0, verbose_name='Orden')
    
    class Meta:
        db_table = 'campaign_dispositions'
        ordering = ['campaign', 'order', 'name']
        unique_together = ['campaign', 'code']
        verbose_name = 'Calificación de Campaña'
        verbose_name_plural = 'Calificaciones de Campaña'
    
    def __str__(self):
        return f"{self.campaign.name} - {self.name}"
