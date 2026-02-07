from django.db import models
from django.conf import settings


class Report(models.Model):
    """
    Reportes generados
    """
    REPORT_TYPES = [
        ('campaign', 'Campaña'),
        ('agent', 'Agente'),
        ('queue', 'Cola'),
        ('calls', 'Llamadas'),
        ('custom', 'Personalizado'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    # Información básica
    name = models.CharField(max_length=200, verbose_name='Nombre')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name='Tipo')
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, verbose_name='Formato')
    
    # Filtros y parámetros
    filters = models.JSONField(default=dict, verbose_name='Filtros')
    date_from = models.DateTimeField(verbose_name='Desde')
    date_to = models.DateTimeField(verbose_name='Hasta')
    
    # Archivo generado
    file_path = models.CharField(max_length=1000, blank=True, verbose_name='Archivo')
    file_size = models.BigIntegerField(default=0, verbose_name='Tamaño')
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Estado')
    error_message = models.TextField(blank=True, verbose_name='Mensaje error')
    
    # Programación
    is_scheduled = models.BooleanField(default=False, verbose_name='Programado')
    schedule_frequency = models.CharField(max_length=20, blank=True, verbose_name='Frecuencia')
    
    # Auditoría
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        verbose_name = 'Reporte'
        verbose_name_plural = 'Reportes'
    
    def __str__(self):
        return f"{self.name} - {self.get_report_type_display()} ({self.created_at.date()})"
