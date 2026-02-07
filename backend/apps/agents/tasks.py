from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_agent_statistics():
    """
    Actualizar estadísticas de agentes
    """
    from apps.agents.models import Agent, AgentStatusHistory
    
    agents = Agent.objects.exclude(status='offline')
    
    for agent in agents:
        # Calcular tiempo en estado actual
        if agent.last_status_change:
            current_status_duration = (timezone.now() - agent.last_status_change).total_seconds()
            
            if agent.status == 'available':
                agent.available_time_today += int(current_status_duration)
            elif agent.status == 'break':
                agent.break_time_today += int(current_status_duration)
            
            agent.save()
    
    return f"Updated statistics for {agents.count()} agents"


@shared_task
def reset_daily_agent_metrics():
    """
    Reiniciar métricas diarias de agentes (ejecutar a medianoche)
    """
    from apps.agents.models import Agent
    
    Agent.objects.all().update(
        calls_today=0,
        talk_time_today=0,
        available_time_today=0,
        break_time_today=0
    )
    
    return "Daily agent metrics reset"


@shared_task
def close_agent_status_history():
    """
    Cerrar registros de historial de estado abiertos
    """
    from apps.agents.models import AgentStatusHistory
    
    # Cerrar registros abiertos de más de 24 horas
    cutoff_time = timezone.now() - timedelta(hours=24)
    open_records = AgentStatusHistory.objects.filter(
        ended_at__isnull=True,
        started_at__lt=cutoff_time
    )
    
    for record in open_records:
        record.ended_at = timezone.now()
        record.duration = int((record.ended_at - record.started_at).total_seconds())
        record.save()
    
    return f"Closed {open_records.count()} status history records"
