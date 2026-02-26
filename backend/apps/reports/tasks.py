from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import json
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_reports():
    """
    Generar reportes diarios programados automáticamente.
    Se ejecuta a la 1 AM via celery beat.
    Genera un reporte JSON con las estadísticas del día anterior.
    """
    from apps.reports.models import Report
    from apps.telephony.models import Call
    from apps.agents.models import Agent
    from django.db.models import Count, Avg, Sum, Q

    yesterday = timezone.now() - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

    calls_qs = Call.objects.filter(start_time__gte=start, start_time__lte=end)
    total = calls_qs.count()

    if total == 0:
        logger.info("No hay llamadas del día anterior para reportar")
        return "No calls yesterday"

    answered = calls_qs.filter(status='completed').count()
    missed = calls_qs.filter(status__in=['no_answer', 'busy', 'cancelled']).count()
    failed = calls_qs.filter(status='failed').count()
    inbound = calls_qs.filter(direction='inbound').count()
    outbound = calls_qs.filter(direction='outbound').count()

    agg = calls_qs.filter(status='completed').aggregate(
        avg_talk=Avg('talk_time'),
        avg_wait=Avg('wait_time'),
        total_talk=Sum('talk_time'),
    )

    answer_rate = round((answered / total * 100), 1) if total > 0 else 0

    # KPIs por agente
    agent_stats = []
    for agent in Agent.objects.all():
        agent_calls = calls_qs.filter(agent=agent)
        agent_total = agent_calls.count()
        if agent_total > 0:
            agent_answered = agent_calls.filter(status='completed').count()
            agent_agg = agent_calls.filter(status='completed').aggregate(
                avg_talk=Avg('talk_time'),
                total_talk=Sum('talk_time'),
            )
            agent_stats.append({
                'agent_id': agent.id,
                'agent_name': agent.user.get_full_name() or agent.agent_id,
                'total_calls': agent_total,
                'answered': agent_answered,
                'avg_talk_time': round(agent_agg['avg_talk'] or 0, 1),
                'total_talk_time': agent_agg['total_talk'] or 0,
            })

    report_data = {
        'date': yesterday.strftime('%Y-%m-%d'),
        'summary': {
            'total_calls': total,
            'answered': answered,
            'missed': missed,
            'failed': failed,
            'inbound': inbound,
            'outbound': outbound,
            'answer_rate': answer_rate,
            'avg_talk_time': round(agg['avg_talk'] or 0, 1),
            'avg_wait_time': round(agg['avg_wait'] or 0, 1),
            'total_talk_time': agg['total_talk'] or 0,
        },
        'agents': agent_stats,
    }

    # Crear el reporte en la BD
    report = Report.objects.create(
        name=f"Reporte Diario - {yesterday.strftime('%Y-%m-%d')}",
        report_type='calls',
        format='json',
        filters=report_data,
        date_from=start,
        date_to=end,
        status='completed',
        completed_at=timezone.now(),
    )

    logger.info(f"Reporte diario generado: {report.id} — {total} llamadas")
    return f"Daily report generated: {report.id} with {total} calls"


@shared_task
def generate_report(report_id):
    """
    Generar un reporte específico bajo demanda
    """
    from apps.reports.models import Report
    from apps.telephony.models import Call
    from django.db.models import Count, Avg, Sum, Q

    try:
        report = Report.objects.get(id=report_id)
        report.status = 'processing'
        report.save()

        calls_qs = Call.objects.filter(
            start_time__gte=report.date_from,
            start_time__lte=report.date_to,
        )

        total = calls_qs.count()
        answered = calls_qs.filter(status='completed').count()
        missed = calls_qs.filter(status__in=['no_answer', 'busy', 'cancelled']).count()

        agg = calls_qs.filter(status='completed').aggregate(
            avg_talk=Avg('talk_time'),
            avg_wait=Avg('wait_time'),
            total_talk=Sum('talk_time'),
        )

        report_data = {
            'total_calls': total,
            'answered': answered,
            'missed': missed,
            'answer_rate': round((answered / total * 100), 1) if total > 0 else 0,
            'avg_talk_time': round(agg['avg_talk'] or 0, 1),
            'avg_wait_time': round(agg['avg_wait'] or 0, 1),
            'total_talk_time': agg['total_talk'] or 0,
            'inbound': calls_qs.filter(direction='inbound').count(),
            'outbound': calls_qs.filter(direction='outbound').count(),
        }

        report.filters = report_data
        report.status = 'completed'
        report.completed_at = timezone.now()
        report.save()

        return f"Report {report_id} generated successfully"
    except Report.DoesNotExist:
        return f"Report {report_id} not found"
    except Exception as e:
        logger.error(f"Error generating report {report_id}: {str(e)}")
        if 'report' in dir():
            report.status = 'failed'
            report.error_message = str(e)
            report.save()
        return f"Error generating report {report_id}"
