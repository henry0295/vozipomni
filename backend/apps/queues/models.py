from django.db import models
from django.conf import settings


class Queue(models.Model):
    """
    Cola de llamadas (ACD)
    """
    STRATEGY_CHOICES = [
        ('ringall', 'Ring All - Timbran todos'),
        ('leastrecent', 'Least Recent - Menos reciente'),
        ('fewestcalls', 'Fewest Calls - Menos llamadas'),
        ('random', 'Random - Aleatorio'),
        ('rrmemory', 'Round Robin Memory'),
        ('linear', 'Linear - Lineal'),
    ]
    
    name = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    extension = models.CharField(max_length=20, unique=True, verbose_name='Extensión')
    description = models.TextField(blank=True, verbose_name='Descripción')
    strategy = models.CharField(max_length=20, choices=STRATEGY_CHOICES, default='ringall', verbose_name='Estrategia')
    
    # Configuración de timers
    timeout = models.IntegerField(default=30, verbose_name='Timeout (seg)')
    retry = models.IntegerField(default=5, verbose_name='Reintentar después de (seg)')
    max_wait_time = models.IntegerField(default=300, verbose_name='Tiempo máx. espera (seg)')
    
    # Anuncios y mensajes
    announce_frequency = models.IntegerField(default=30, verbose_name='Frecuencia anuncio (seg)')
    announce_holdtime = models.BooleanField(default=True, verbose_name='Anunciar tiempo espera')
    periodic_announce_frequency = models.IntegerField(default=60, verbose_name='Anuncio periódico (seg)')
    
    # Música en espera
    music_on_hold = models.CharField(max_length=100, default='default', verbose_name='Música en espera')
    
    # Configuración avanzada
    max_callers = models.IntegerField(default=0, help_text="0 = ilimitado", verbose_name='Máx. llamadas')
    service_level = models.IntegerField(default=60, help_text="Segundos", verbose_name='Nivel de servicio')
    wrap_up_time = models.IntegerField(default=0, verbose_name='Tiempo post-llamada (seg)')
    
    # Estado
    is_active = models.BooleanField(default=True, verbose_name='Activa')
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'queues'
        verbose_name = 'Cola'
        verbose_name_plural = 'Colas'
    
    def __str__(self):
        return f"{self.name} ({self.extension})"


class QueueMember(models.Model):
    """
    Miembros de una cola
    """
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, related_name='members')
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='queue_memberships')
    penalty = models.IntegerField(default=0, verbose_name='Penalización')
    paused = models.BooleanField(default=False, verbose_name='Pausado')
    
    # Estadísticas
    calls_taken = models.IntegerField(default=0, verbose_name='Llamadas atendidas')
    last_call = models.DateTimeField(null=True, blank=True, verbose_name='Última llamada')
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'queue_members'
        unique_together = ['queue', 'agent']
        verbose_name = 'Miembro de Cola'
        verbose_name_plural = 'Miembros de Colas'
    
    def __str__(self):
        return f"{self.queue.name} - {self.agent}"


class QueueStats(models.Model):
    """
    Estadísticas de colas en tiempo real
    """
    queue = models.OneToOneField(Queue, on_delete=models.CASCADE, related_name='stats')
    
    # Llamadas
    calls_waiting = models.IntegerField(default=0, verbose_name='En espera')
    calls_completed = models.IntegerField(default=0, verbose_name='Completadas')
    calls_abandoned = models.IntegerField(default=0, verbose_name='Abandonadas')
    
    # Tiempos
    avg_wait_time = models.IntegerField(default=0, help_text="Segundos", verbose_name='Tiempo espera promedio')
    avg_talk_time = models.IntegerField(default=0, help_text="Segundos", verbose_name='Tiempo conversación promedio')
    max_wait_time = models.IntegerField(default=0, help_text="Segundos", verbose_name='Tiempo espera máximo')
    
    # Agentes
    agents_available = models.IntegerField(default=0, verbose_name='Agentes disponibles')
    agents_busy = models.IntegerField(default=0, verbose_name='Agentes ocupados')
    
    # Nivel de servicio
    service_level_met = models.IntegerField(default=0, verbose_name='Nivel servicio cumplido')
    service_level_percentage = models.FloatField(default=0.0, verbose_name='% Nivel servicio')
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'queue_stats'
        verbose_name = 'Estadísticas de Cola'
        verbose_name_plural = 'Estadísticas de Colas'
    
    def __str__(self):
        return f"Stats: {self.queue.name}"
