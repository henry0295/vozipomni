from django.db import models
from django.conf import settings
from django.utils import timezone


class CallDispositionAudit(models.Model):
    """
    Auditoría de gestiones de agentes.
    Un supervisor revisa las calificaciones que el agente asignó a las llamadas
    y puede aprobarlas, rechazarlas o corregirlas.

    Flujo:
      Agente califica llamada → AuditLog se crea con status 'pending'
      Supervisor revisa       → cambia a 'approved' / 'rejected' / 'corrected'
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente revisión'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
        ('corrected', 'Corregida'),
    ]

    # Qué se audita
    call = models.OneToOneField(
        'telephony.Call',
        on_delete=models.CASCADE,
        related_name='audit',
        verbose_name='Llamada',
    )
    agent = models.ForeignKey(
        'agents.Agent',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audits',
        verbose_name='Agente',
    )
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audits',
        verbose_name='Campaña',
    )

    # Calificación original del agente
    original_disposition = models.ForeignKey(
        'campaigns.CampaignDisposition',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='original_audits',
        verbose_name='Calificación original',
    )
    agent_notes = models.TextField(blank=True, verbose_name='Notas del agente')

    # Resultado de la auditoría
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Estado auditoría',
        db_index=True,
    )
    audited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_audits',
        verbose_name='Auditado por',
    )
    corrected_disposition = models.ForeignKey(
        'campaigns.CampaignDisposition',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corrected_audits',
        verbose_name='Calificación corregida',
    )
    supervisor_notes = models.TextField(blank=True, verbose_name='Notas del supervisor')

    # Puntuación de calidad (1-10)
    quality_score = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Puntuación calidad',
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    audited_at = models.DateTimeField(null=True, blank=True, verbose_name='Auditado')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'call_disposition_audits'
        ordering = ['-created_at']
        verbose_name = 'Auditoría de Gestión'
        verbose_name_plural = 'Auditorías de Gestiones'
        indexes = [
            models.Index(fields=['status', 'created_at'], name='audit_status_created_idx'),
            models.Index(fields=['agent', 'created_at'], name='audit_agent_created_idx'),
            models.Index(fields=['campaign', 'created_at'], name='audit_campaign_created_idx'),
        ]

    def __str__(self):
        return f"Auditoría #{self.pk} — {self.call.call_id} [{self.get_status_display()}]"

    def approve(self, supervisor, notes: str = ''):
        self.status = 'approved'
        self.audited_by = supervisor
        self.supervisor_notes = notes
        self.audited_at = timezone.now()
        self.save(update_fields=['status', 'audited_by', 'supervisor_notes', 'audited_at', 'updated_at'])

    def reject(self, supervisor, notes: str = ''):
        self.status = 'rejected'
        self.audited_by = supervisor
        self.supervisor_notes = notes
        self.audited_at = timezone.now()
        self.save(update_fields=['status', 'audited_by', 'supervisor_notes', 'audited_at', 'updated_at'])

    def correct(self, supervisor, new_disposition, notes: str = '', score=None):
        self.status = 'corrected'
        self.audited_by = supervisor
        self.corrected_disposition = new_disposition
        self.supervisor_notes = notes
        self.quality_score = score
        self.audited_at = timezone.now()
        self.save(update_fields=[
            'status', 'audited_by', 'corrected_disposition',
            'supervisor_notes', 'quality_score', 'audited_at', 'updated_at',
        ])
