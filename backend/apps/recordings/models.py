from django.db import models
from django.conf import settings


class EvaluationTemplate(models.Model):
    """
    Plantilla de evaluación de calidad configurable.
    Permite definir criterios personalizados en lugar de los 5 fijos del modelo antiguo.

    Estructura de `criteria` (JSONField):
    [
      {"name": "greeting",        "label": "Saludo",          "weight": 20, "max_score": 5},
      {"name": "clarity",         "label": "Claridad",        "weight": 20, "max_score": 5},
      {"name": "professionalism", "label": "Profesionalismo", "weight": 20, "max_score": 5},
      {"name": "resolution",      "label": "Resolución",      "weight": 20, "max_score": 5},
      {"name": "closing",         "label": "Cierre",          "weight": 20, "max_score": 5},
    ]
    Los `weight` deben sumar 100. `max_score` es la puntuación máxima por criterio.
    """
    name = models.CharField(max_length=200, unique=True, verbose_name='Nombre de la plantilla')
    description = models.TextField(blank=True)
    criteria = models.JSONField(
        default=list,
        verbose_name='Criterios de evaluación',
        help_text='Lista de objetos {name, label, weight, max_score}',
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        verbose_name='Plantilla por defecto',
        help_text='Solo puede haber una plantilla por defecto.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_evaluation_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recording_evaluation_templates'
        ordering = ['-is_default', 'name']
        verbose_name = 'Plantilla de Evaluación'
        verbose_name_plural = 'Plantillas de Evaluación'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Solo una plantilla puede ser la por defecto
        if self.is_default:
            EvaluationTemplate.objects.exclude(pk=self.pk).filter(is_default=True).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    @property
    def max_total_score(self):
        """Puntuación máxima total de la plantilla."""
        return sum(c.get('max_score', 5) for c in (self.criteria or []))

    @classmethod
    def get_default(cls):
        """Obtener la plantilla por defecto, o None si no existe ninguna."""
        return cls.objects.filter(is_default=True, is_active=True).first()

    @classmethod
    def get_default_or_builtin(cls):
        """
        Obtener la plantilla activa por defecto.
        Si no existe ninguna, devuelve los criterios built-in para retrocompatibilidad.
        """
        default = cls.get_default()
        if default:
            return default
        # Built-in legacy (5 criterios fijos, max_score=5 cada uno)
        return None  # El caller usará RecordingEvaluation.get_legacy_criteria()


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
    Evaluación de calidad de grabaciones.

    Soporta dos modos:
    1. Legacy (retrocompatibilidad): usa los 5 criterios fijos del modelo original
       (greeting, clarity, professionalism, resolution, closing) con scores 0-5.
    2. Template: usa una EvaluationTemplate configurable; los scores se guardan
       en `scores_data` como JSON { "criteria_name": score }.
    """
    recording = models.OneToOneField(Recording, on_delete=models.CASCADE, related_name='evaluation')
    evaluator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    # ── Plantilla configurable ────────────────────────────────────────────────
    template = models.ForeignKey(
        EvaluationTemplate,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='evaluations',
        verbose_name='Plantilla de evaluación',
        help_text='Si se especifica, los scores se guardan en scores_data.',
    )
    # JSON con scores por criterio: {"greeting": 4, "clarity": 5, ...}
    scores_data = models.JSONField(
        default=dict, blank=True,
        verbose_name='Scores por criterio',
    )

    # ── Legacy (5 criterios fijos) ────────────────────────────────────────────
    # Se mantienen para retrocompatibilidad con evaluaciones existentes
    greeting        = models.IntegerField(default=0, verbose_name='Saludo')
    clarity         = models.IntegerField(default=0, verbose_name='Claridad')
    professionalism = models.IntegerField(default=0, verbose_name='Profesionalismo')
    resolution      = models.IntegerField(default=0, verbose_name='Resolución')
    closing         = models.IntegerField(default=0, verbose_name='Cierre')

    # ── Score total (calculado automáticamente) ───────────────────────────────
    total_score = models.FloatField(default=0.0, verbose_name='Puntuación total')

    # Comentarios y feedback
    comments = models.TextField(blank=True, verbose_name='Comentarios')
    feedback_sent = models.BooleanField(default=False, verbose_name='Feedback enviado')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recording_evaluations'
        verbose_name = 'Evaluación de Grabación'
        verbose_name_plural = 'Evaluaciones de Grabaciones'

    def __str__(self):
        return f"Evaluación - {self.recording.filename} - {self.total_score}"

    @classmethod
    def get_legacy_criteria(cls):
        """Criterios built-in para retrocompatibilidad."""
        return [
            {'name': 'greeting',        'label': 'Saludo',          'max_score': 5},
            {'name': 'clarity',         'label': 'Claridad',        'max_score': 5},
            {'name': 'professionalism', 'label': 'Profesionalismo', 'max_score': 5},
            {'name': 'resolution',      'label': 'Resolución',      'max_score': 5},
            {'name': 'closing',         'label': 'Cierre',          'max_score': 5},
        ]

    def _calculate_total(self) -> float:
        """Calcular puntuación total normalizada a 100."""
        if self.template and self.scores_data:
            criteria = self.template.criteria or []
            max_total = self.template.max_total_score or 1
            raw = sum(self.scores_data.get(c['name'], 0) for c in criteria)
            return round((raw / max_total) * 100, 2)

        # Legacy: suma de los 5 campos / 25 * 100
        raw = self.greeting + self.clarity + self.professionalism + self.resolution + self.closing
        return round((raw / 25) * 100, 2)

    def save(self, *args, **kwargs):
        # Sincronizar campos legacy desde scores_data si se usa template
        if self.template and self.scores_data:
            legacy_fields = ['greeting', 'clarity', 'professionalism', 'resolution', 'closing']
            for field in legacy_fields:
                if field in self.scores_data:
                    setattr(self, field, self.scores_data[field])

        self.total_score = self._calculate_total()
        super().save(*args, **kwargs)
