from django.db import models
from django.conf import settings
from django.utils import timezone


class Agent(models.Model):
    """
    Agente de contact center
    """
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('busy', 'Ocupado'),
        ('oncall', 'En Llamada'),
        ('break', 'En Descanso'),
        ('offline', 'Desconectado'),
        ('wrapup', 'Post-Llamada'),
    ]
    
    # Información básica
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='agent_profile')
    agent_id = models.CharField(max_length=50, unique=True, verbose_name='ID Agente')
    sip_extension = models.CharField(max_length=20, unique=True, verbose_name='Extensión SIP')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline', verbose_name='Estado')
    
    # Configuración
    webrtc_enabled = models.BooleanField(default=True, verbose_name='WebRTC habilitado')
    max_concurrent_calls = models.IntegerField(default=1, verbose_name='Llamadas concurrentes máx')
    auto_answer = models.BooleanField(default=False, verbose_name='Auto-respuesta')
    recording_enabled = models.BooleanField(default=True, verbose_name='Grabación habilitada')
    
    # Estado en tiempo real
    current_calls = models.IntegerField(default=0, verbose_name='Llamadas actuales')
    last_call_time = models.DateTimeField(null=True, blank=True, verbose_name='Última llamada')
    logged_in_at = models.DateTimeField(null=True, blank=True, verbose_name='Conectado desde')
    last_status_change = models.DateTimeField(auto_now=True, verbose_name='Último cambio estado')
    
    # Métricas del día
    calls_today = models.IntegerField(default=0, verbose_name='Llamadas hoy')
    talk_time_today = models.IntegerField(default=0, help_text="Segundos", verbose_name='Tiempo hablado hoy')
    available_time_today = models.IntegerField(default=0, help_text="Segundos", verbose_name='Tiempo disponible hoy')
    break_time_today = models.IntegerField(default=0, help_text="Segundos", verbose_name='Tiempo descanso hoy')
    oncall_time_today = models.IntegerField(default=0, help_text="Segundos", verbose_name='Tiempo en llamada hoy')
    wrapup_time_today = models.IntegerField(default=0, help_text="Segundos", verbose_name='Tiempo post-llamada hoy')
    
    # Relaciones
    campaigns = models.ManyToManyField('campaigns.Campaign', related_name='agents', blank=True)
    current_campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True, blank=True, related_name='current_agents')
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agents'
        verbose_name = 'Agente'
        verbose_name_plural = 'Agentes'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.sip_extension}"
    
    def login(self):
        """Marcar agente como conectado"""
        self.status = 'available'
        self.logged_in_at = timezone.now()
        self.save()
    
    def logout(self):
        """Marcar agente como desconectado"""
        self.status = 'offline'
        self.logged_in_at = None
        self.current_calls = 0
        self.save()
    
    @property
    def is_available(self):
        """Verificar si el agente está disponible"""
        return self.status == 'available' and self.current_calls < self.max_concurrent_calls

    @property
    def session_duration(self):
        """Duración de la sesión actual en segundos."""
        if self.logged_in_at:
            return int((timezone.now() - self.logged_in_at).total_seconds())
        return 0

    @property
    def occupancy(self):
        """Porcentaje de ocupación (tiempo productivo / tiempo sesión)."""
        session = self.session_duration
        if session > 0:
            productive = self.oncall_time_today + self.talk_time_today + self.wrapup_time_today
            return round((productive / session * 100), 1)
        return 0.0


class AgentStatusHistory(models.Model):
    """
    Historial de cambios de estado de agentes
    """
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Segundos")
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'agent_status_history'
        ordering = ['-started_at']
        verbose_name = 'Historial Estado Agente'
        verbose_name_plural = 'Historial Estados Agentes'
    
    def __str__(self):
        return f"{self.agent.user.username} - {self.status} - {self.started_at}"


class AgentBreakReason(models.Model):
    """
    Razones de descanso para agentes
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_paid = models.BooleanField(default=True, verbose_name='¿Es pagado?')
    max_duration = models.IntegerField(null=True, blank=True, help_text="Minutos máximos", verbose_name='Duración máxima')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'agent_break_reasons'
        verbose_name = 'Razón de Descanso'
        verbose_name_plural = 'Razones de Descanso'
    
    def __str__(self):
        return self.name
