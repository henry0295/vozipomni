"""
Tareas Celery de reportes.

  generate_report(report_id)          → genera el archivo (CSV/XLSX) de un Report
  generate_campaign_report(campaign)  → reporte de cierre al detener una campaña
  run_scheduled_reports()             → ejecuta los reportes programados (diario/semanal/mensual)
  generate_daily_reports()            → snapshot JSON del día anterior (histórico)
"""
import logging
import os
import re
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(str(settings.MEDIA_ROOT), 'reports')


def _slug(text):
    return re.sub(r'[^a-zA-Z0-9_-]+', '_', text or 'reporte').strip('_')[:60] or 'reporte'


def _summary(start, end, filters):
    """Resumen corto que se guarda junto al reporte (se muestra en la UI)."""
    from django.db.models import Avg, Sum
    from apps.reports.exporters import _calls_qs
    qs = _calls_qs(start, end, filters)
    total = qs.count()
    answered = qs.filter(status='completed').count()
    agg = qs.filter(status='completed').aggregate(avg_talk=Avg('talk_time'), total_talk=Sum('talk_time'))
    return {
        'total_calls': total,
        'answered': answered,
        'missed': qs.filter(status__in=['no_answer', 'busy', 'cancelled']).count(),
        'abandoned': qs.filter(status='abandoned').count(),
        'answer_rate': round(answered / total * 100, 1) if total else 0,
        'avg_talk_time': round(agg['avg_talk'] or 0, 1),
        'total_talk_time': agg['total_talk'] or 0,
    }


@shared_task
def generate_report(report_id):
    """Genera el archivo de un Report según su tipo y formato."""
    from apps.reports.exporters import REPORT_TYPE_DATASET, build_dataset, render_table
    from apps.reports.models import Report

    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return f"Report {report_id} not found"

    report.status = 'processing'
    report.error_message = ''
    report.save(update_fields=['status', 'error_message'])

    try:
        filters = {k: v for k, v in (report.filters or {}).items() if not k.startswith('_')}
        dataset = filters.pop('dataset', None) or REPORT_TYPE_DATASET.get(report.report_type, 'calls')
        fmt = report.format
        if fmt == 'pdf':
            fmt = 'excel'  # PDF no soportado: se entrega Excel

        summary = _summary(report.date_from, report.date_to, filters)

        if fmt == 'json':
            report.filters = {**(report.filters or {}), '_summary': summary}
            report.status = 'completed'
            report.completed_at = timezone.now()
            report.save(update_fields=['filters', 'status', 'completed_at'])
            return f"Report {report_id} (json) generated"

        headers, rows = build_dataset(dataset, report.date_from, report.date_to, filters)
        content, _ctype, ext = render_table(headers, rows, fmt, report.name)

        os.makedirs(REPORTS_DIR, exist_ok=True)
        path = os.path.join(REPORTS_DIR, f"{report.id}_{_slug(report.name)}.{ext}")
        with open(path, 'wb') as fh:
            fh.write(content)

        report.file_path = path
        report.file_size = len(content)
        report.filters = {**(report.filters or {}), '_summary': summary, '_rows': len(rows)}
        report.status = 'completed'
        report.completed_at = timezone.now()
        report.save(update_fields=['file_path', 'file_size', 'filters', 'status', 'completed_at'])
        logger.info(f"[Reports] Reporte {report_id} generado: {path} ({len(rows)} filas)")
        return f"Report {report_id} generated ({len(rows)} rows)"

    except Exception as e:
        logger.exception(f"[Reports] Error generando reporte {report_id}")
        report.status = 'failed'
        report.error_message = str(e)[:2000]
        report.save(update_fields=['status', 'error_message'])
        return f"Error generating report {report_id}: {e}"


@shared_task
def generate_campaign_report(campaign_id):
    """Reporte de cierre de campaña (se llama al detener la campaña)."""
    from apps.campaigns.models import Campaign
    from apps.reports.models import Report

    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return f"Campaign {campaign_id} not found"

    report = Report.objects.create(
        name=f"Cierre campaña {campaign.name}",
        report_type='campaign',
        format='excel',
        filters={'campaign': campaign.id, 'dataset': 'calls'},
        date_from=campaign.start_date,
        date_to=campaign.end_date or timezone.now(),
        created_by=campaign.created_by,
    )
    return generate_report(report.id)


def _period_for(frequency, now):
    """Rango del período anterior según la frecuencia."""
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if frequency == 'weekly':
        return today - timedelta(days=7), today - timedelta(microseconds=1)
    if frequency == 'monthly':
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(microseconds=1)
        return last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0), last_month_end
    return today - timedelta(days=1), today - timedelta(microseconds=1)


def _is_due(frequency, now):
    if frequency == 'weekly':
        return now.weekday() == 0      # lunes
    if frequency == 'monthly':
        return now.day == 1
    return frequency == 'daily'


def _email_report(report):
    """Enviar el archivo generado al creador del reporte programado (si hay email)."""
    from django.core.mail import EmailMessage
    user = report.created_by
    if not user or not user.email or not report.file_path or not os.path.exists(report.file_path):
        return
    try:
        msg = EmailMessage(
            subject=f"VozipOmni — {report.name}",
            body=f"Adjunto el reporte programado «{report.name}».",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_file(report.file_path)
        msg.send(fail_silently=False)
    except Exception as e:
        logger.warning(f"[Reports] No se pudo enviar reporte {report.id} por email: {e}")


@shared_task
def run_scheduled_reports():
    """
    Ejecuta los reportes marcados como programados (is_scheduled=True).
    Cada reporte programado actúa como plantilla: se crea una copia con el
    período anterior, se genera y se envía por correo al creador.
    """
    from apps.reports.models import Report

    now = timezone.localtime()
    generated = 0
    for tpl in Report.objects.filter(is_scheduled=True):
        freq = (tpl.schedule_frequency or 'daily').lower()
        if not _is_due(freq, now):
            continue
        start, end = _period_for(freq, now)
        filters = {k: v for k, v in (tpl.filters or {}).items() if not k.startswith('_')}
        run = Report.objects.create(
            name=f"{tpl.name} ({start.strftime('%Y-%m-%d')})",
            report_type=tpl.report_type,
            format=tpl.format,
            filters=filters,
            date_from=start,
            date_to=end,
            created_by=tpl.created_by,
        )
        generate_report(run.id)
        run.refresh_from_db()
        if run.status == 'completed':
            _email_report(run)
        generated += 1
    return f"{generated} reportes programados generados"


@shared_task
def generate_daily_reports():
    """Snapshot JSON del día anterior (histórico, se mantiene por compatibilidad)."""
    from apps.reports.models import Report

    start, end = _period_for('daily', timezone.localtime())
    summary = _summary(start, end, {})
    if not summary['total_calls']:
        return "No calls yesterday"
    report = Report.objects.create(
        name=f"Reporte Diario - {start.strftime('%Y-%m-%d')}",
        report_type='calls',
        format='json',
        filters={'_summary': summary},
        date_from=start,
        date_to=end,
        status='completed',
        completed_at=timezone.now(),
    )
    return f"Daily report generated: {report.id}"
