from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def update_agent_statistics():
    """
    Actualizar estadísticas de agentes basándose en el historial
    de estados generado por el AMI listener.
    Se ejecuta cada minuto como complemento al tracking en tiempo real.
    """
    from apps.agents.models import Agent, AgentStatusHistory

    now = timezone.now()
    agents = Agent.objects.exclude(status='offline')

    for agent in agents:
        # Buscar registro de historial abierto (sin ended_at)
        current_record = AgentStatusHistory.objects.filter(
            agent=agent, ended_at__isnull=True
        ).order_by('-started_at').first()

        if current_record:
            # Calcular duración acumulada del estado actual
            elapsed = int((now - current_record.started_at).total_seconds())

            # Solo acumular el incremento desde la última actualización
            # (evita doble conteo con el AMI listener)
            last_update = getattr(agent, '_last_stat_update', None)
            if last_update:
                increment = int((now - last_update).total_seconds())
            else:
                increment = min(elapsed, 60)  # máximo 1 minuto de incremento por ejecución

            if agent.status == 'available':
                agent.available_time_today += increment
            elif agent.status == 'break':
                agent.break_time_today += increment
            elif agent.status in ('oncall', 'busy'):
                agent.oncall_time_today += increment
            elif agent.status == 'wrapup':
                agent.wrapup_time_today += increment

            agent.save(update_fields=[
                'available_time_today', 'break_time_today',
                'oncall_time_today', 'wrapup_time_today',
            ])

    return f"Updated statistics for {agents.count()} agents"


@shared_task
def reset_daily_agent_metrics():
    """
    Reiniciar métricas diarias de agentes (ejecutar a medianoche).
    También cierra todos los registros de historial abiertos del día anterior.
    """
    from apps.agents.models import Agent, AgentStatusHistory

    now = timezone.now()

    # Cerrar registros abiertos del día anterior
    AgentStatusHistory.objects.filter(
        ended_at__isnull=True,
        started_at__lt=now.replace(hour=0, minute=0, second=0, microsecond=0),
    ).update(
        ended_at=now,
    )

    # Re-calcular duración en registros cerrados sin duración
    for record in AgentStatusHistory.objects.filter(duration=0, ended_at__isnull=False):
        record.duration = int((record.ended_at - record.started_at).total_seconds())
        record.save(update_fields=['duration'])

    # Resetear métricas diarias
    Agent.objects.all().update(
        calls_today=0,
        talk_time_today=0,
        available_time_today=0,
        break_time_today=0,
        oncall_time_today=0,
        wrapup_time_today=0,
    )

    # Crear nuevos registros de historial para agentes que siguen conectados
    online_agents = Agent.objects.exclude(status='offline')
    for agent in online_agents:
        AgentStatusHistory.objects.create(
            agent=agent,
            status=agent.status,
            started_at=now,
        )

    return f"Daily agent metrics reset. {online_agents.count()} agents still online."


@shared_task
def close_agent_status_history():
    """
    Cerrar registros de historial de estado abiertos de más de 24 horas.
    Esto es una red de seguridad para registros huérfanos.
    """
    from apps.agents.models import AgentStatusHistory

    cutoff_time = timezone.now() - timedelta(hours=24)
    open_records = AgentStatusHistory.objects.filter(
        ended_at__isnull=True,
        started_at__lt=cutoff_time
    )

    count = 0
    for record in open_records:
        record.ended_at = timezone.now()
        record.duration = int((record.ended_at - record.started_at).total_seconds())
        record.save(update_fields=['ended_at', 'duration'])
        count += 1

    return f"Closed {count} stale status history records"
