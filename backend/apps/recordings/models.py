from django.db import models
from django.conf import settings


class Recording(models.Model):
    """
    Grabaciones de llamadas
    """
    STATUS_CHOICES = [
        ('recording', 'Grabando'),
        ('completed', 'Completada'),
        ('failed', 'Fallida'),
        ('archived', 'Archivada'),
    ]
    
    # Información básica
    call = models.OneToOneField('telephony.Call', on_delete=models.CASCADE, related_name='recording_detail')
    filename = models.CharField(max_length=500, verbose_name='Nombre archivo')
    file_path = models.CharField(max_length=1000, verbose_name='Ruta archivo')
    file_size = models.BigIntegerField(default=0, help_text="Bytes", verbose_name='Tamaño')
    
    # Formato
    format = models.CharField(max_length=10, default='wav', verbose_name='Formato')
    duration = models.IntegerField(default=0, help_text="Segundos", verbose_name='Duración')
    codec = models.CharField(max_length=50, blank=True, verbose_name='Códec')
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='recording', verbose_name='Estado')
    
    # Metadatos
    agent = models.ForeignKey('agents.Agent', on_delete=models.SET_NULL, null=True, blank=True)
    campaign = models.ForeignKey('campaigns.Campaign', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Transcripción
    transcription = models.TextField(blank=True, verbose_name='Transcripción')
    transcription_status = models.CharField(max_length=20, blank=True, verbose_name='Estado transcripción')
    
    # Control de acceso
    is_public = models.BooleanField(default=False, verbose_name='Público')
    access_count = models.IntegerField(default=0, verbose_name='Reproducciones')
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'recordings'
        ordering = ['-created_at']
        verbose_name = 'Grabación'
        verbose_name_plural = 'Grabaciones'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['agent', 'created_at']),
            models.Index(fields=['campaign', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.filename} - {self.call.call_id}"
    
    @property
    def file_size_mb(self):
        """Tamaño en MB"""
        return round(self.file_size / (1024 * 1024), 2)


class RecordingNote(models.Model):
    """
    Notas sobre grabaciones
    """
    recording = models.ForeignKey(Recording, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField(verbose_name='Nota')
    timestamp = models.IntegerField(default=0, help_text="Segundo de la grabación", verbose_name='Timestamp')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'recording_notes'
        ordering = ['timestamp', 'created_at']
        verbose_name = 'Nota de Grabación'
        verbose_name_plural = 'Notas de Grabaciones'
    
    def __str__(self):
        return f"Nota @ {self.timestamp}s - {self.recording.filename}"


class RecordingEvaluation(models.Model):
    """
    Evaluación de calidad de grabaciones
    """
    recording = models.OneToOneField(Recording, on_delete=models.CASCADE, related_name='evaluation')
    evaluator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    # Criterios de evaluación (1-5)
    greeting = models.IntegerField(default=0, verbose_name='Saludo')
    clarity = models.IntegerField(default=0, verbose_name='Claridad')
    professionalism = models.IntegerField(default=0, verbose_name='Profesionalismo')
    resolution = models.IntegerField(default=0, verbose_name='Resolución')
    closing = models.IntegerField(default=0, verbose_name='Cierre')
    
    # Puntuación total
    total_score = models.IntegerField(default=0, verbose_name='Puntuación total')
    
    # Comentarios
    comments = models.TextField(blank=True, verbose_name='Comentarios')
    feedback_sent = models.BooleanField(default=False, verbose_name='Feedback enviado')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'recording_evaluations'
        verbose_name = 'Evaluación de Grabación'
        verbose_name_plural = 'Evaluaciones de Grabaciones'
    
    def __str__(self):
        return f"Evaluación - {self.recording.filename} - {self.total_score}/25"
    
    def save(self, *args, **kwargs):
        # Calcular puntuación total
        self.total_score = (
            self.greeting + 
            self.clarity + 
            self.professionalism + 
            self.resolution + 
            self.closing
        )
        super().save(*args, **kwargs)
