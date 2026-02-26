"""
Vistas de Reportes y KPIs del Contact Center.

Endpoints:
  GET /api/reports/kpis/                  — KPIs en tiempo real
  GET /api/reports/calls-by-hour/         — Llamadas por hora
  GET /api/reports/calls-by-queue/        — Distribución por cola
  GET /api/reports/agent-performance/     — Rendimiento de agentes
  GET /api/reports/call-summary/          — Resumen de llamadas (filtrable por fecha)
"""
from datetime import timedelta, datetime

from django.db.models import (
    Count, Avg, Sum, Q, F, ExpressionWrapper,
    FloatField, IntegerField, Case, When, Value,
)
from django.db.models.functions import (
    TruncHour, TruncDate, ExtractHour,
)
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.telephony.models import Call
from apps.agents.models import Agent
from apps.queues.models import Queue
from apps.reports.models import Report
from apps.api.serializers import ReportSerializer


def _parse_date_range(request):
    """Parsea parámetros period / start_date / end_date del request."""
    period = request.query_params.get('period', 'today')
    now = timezone.now()

    if period == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == 'yesterday':
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period == 'last7days':
        start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == 'last30days':
        start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == 'thismonth':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == 'custom':
        try:
            start = timezone.make_aware(
                datetime.strptime(request.query_params.get('start_date', ''), '%Y-%m-%d')
            )
            end_raw = request.query_params.get('end_date', '')
            end = timezone.make_aware(
                datetime.strptime(end_raw, '%Y-%m-%d')
            ).replace(hour=23, minute=59, second=59) if end_raw else now
        except (ValueError, TypeError):
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now

    return start, end


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet básico para CRUD de reportes guardados."""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generar un reporte específico."""
        report = self.get_object()
        from apps.reports.tasks import generate_report
        generate_report.delay(report.id)
        return Response({'status': 'generating report'})

    # ─────────────────────────────────────────────────────────────
    # KPIs en Tiempo Real
    # ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='kpis')
    def kpis(self, request):
        """
        KPIs principales del contact center.

        Retorna:
          totalCalls, answeredCalls, missedCalls, abandonedCalls,
          answerRate, abandonRate, avgTalkTime, avgWaitTime,
          avgHandleTime (AHT), serviceLevel (SLA),
          inboundCalls, outboundCalls, totalTalkTime,
          activeAgents, availableAgents
        """
        start, end = _parse_date_range(request)
        qs = Call.objects.filter(start_time__gte=start, start_time__lte=end)

        total = qs.count()
        answered = qs.filter(status='completed').count()
        no_answer = qs.filter(status='no_answer').count()
        busy = qs.filter(status='busy').count()
        failed = qs.filter(status='failed').count()
        cancelled = qs.filter(status='cancelled').count()
        missed = no_answer + busy + cancelled

        # AHT (Average Handle Time) = talk_time + wrapup (usamos talk_time como aproximación)
        agg = qs.filter(status='completed').aggregate(
            avg_talk=Avg('talk_time'),
            avg_wait=Avg('wait_time'),
            avg_hold=Avg('hold_time'),
            total_talk=Sum('talk_time'),
        )
        avg_talk = agg['avg_talk'] or 0
        avg_wait = agg['avg_wait'] or 0
        avg_hold = agg['avg_hold'] or 0
        total_talk = agg['total_talk'] or 0
        aht = avg_talk + avg_hold  # AHT = talk + hold

        # SLA: porcentaje de llamadas contestadas dentro de X segundos (ej: 20s)
        SLA_THRESHOLD = 20  # segundos
        answered_in_sla = qs.filter(
            status='completed',
            wait_time__lte=SLA_THRESHOLD,
        ).count()
        sla = round((answered_in_sla / total * 100), 1) if total > 0 else 0

        answer_rate = round((answered / total * 100), 1) if total > 0 else 0
        abandon_rate = round((missed / total * 100), 1) if total > 0 else 0

        inbound = qs.filter(direction='inbound').count()
        outbound = qs.filter(direction='outbound').count()

        # Agentes
        active_agents = Agent.objects.exclude(status='offline').count()
        available_agents = Agent.objects.filter(status='available').count()

        return Response({
            'totalCalls': total,
            'answeredCalls': answered,
            'missedCalls': missed,
            'abandonedCalls': cancelled,
            'failedCalls': failed,
            'answerRate': answer_rate,
            'abandonRate': abandon_rate,
            'avgTalkTime': round(avg_talk, 1),
            'avgWaitTime': round(avg_wait, 1),
            'avgHoldTime': round(avg_hold, 1),
            'avgHandleTime': round(aht, 1),
            'serviceLevel': sla,
            'slaThreshold': SLA_THRESHOLD,
            'inboundCalls': inbound,
            'outboundCalls': outbound,
            'totalTalkTime': total_talk,
            'activeAgents': active_agents,
            'availableAgents': available_agents,
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat(),
            },
        })

    # ─────────────────────────────────────────────────────────────
    # Llamadas por Hora
    # ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='calls-by-hour')
    def calls_by_hour(self, request):
        """
        Distribución de llamadas por hora del día.
        Retorna array de {hour, total, answered, missed, inbound, outbound}.
        """
        start, end = _parse_date_range(request)
        qs = Call.objects.filter(start_time__gte=start, start_time__lte=end)

        hours_data = (
            qs
            .annotate(hour=ExtractHour('start_time'))
            .values('hour')
            .annotate(
                total=Count('id'),
                answered=Count('id', filter=Q(status='completed')),
                missed=Count('id', filter=Q(status__in=['no_answer', 'busy', 'cancelled'])),
                inbound=Count('id', filter=Q(direction='inbound')),
                outbound=Count('id', filter=Q(direction='outbound')),
            )
            .order_by('hour')
        )

        # Rellenar horas vacías
        hours_map = {item['hour']: item for item in hours_data}
        result = []
        for h in range(24):
            data = hours_map.get(h, {
                'hour': h,
                'total': 0,
                'answered': 0,
                'missed': 0,
                'inbound': 0,
                'outbound': 0,
            })
            data['label'] = f"{h:02d}:00"
            result.append(data)

        return Response(result)

    # ─────────────────────────────────────────────────────────────
    # Distribución por Cola
    # ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='calls-by-queue')
    def calls_by_queue(self, request):
        """
        Distribución de llamadas por cola.
        Retorna array de {queue_id, queue_name, total, answered, missed, avgWait}.
        """
        start, end = _parse_date_range(request)
        qs = Call.objects.filter(
            start_time__gte=start,
            start_time__lte=end,
            queue__isnull=False,
        )

        queue_data = (
            qs
            .values('queue__id', 'queue__name')
            .annotate(
                total=Count('id'),
                answered=Count('id', filter=Q(status='completed')),
                missed=Count('id', filter=Q(status__in=['no_answer', 'busy', 'cancelled'])),
                avg_wait=Avg('wait_time'),
                avg_talk=Avg('talk_time'),
            )
            .order_by('-total')
        )

        result = []
        for item in queue_data:
            result.append({
                'queueId': item['queue__id'],
                'queueName': item['queue__name'] or 'Sin cola',
                'total': item['total'],
                'answered': item['answered'],
                'missed': item['missed'],
                'avgWait': round(item['avg_wait'] or 0, 1),
                'avgTalk': round(item['avg_talk'] or 0, 1),
            })

        # También incluir llamadas sin cola
        no_queue = Call.objects.filter(
            start_time__gte=start,
            start_time__lte=end,
            queue__isnull=True,
        ).aggregate(
            total=Count('id'),
            answered=Count('id', filter=Q(status='completed')),
            missed=Count('id', filter=Q(status__in=['no_answer', 'busy', 'cancelled'])),
            avg_wait=Avg('wait_time'),
        )
        if no_queue['total']:
            result.append({
                'queueId': None,
                'queueName': 'Directas (sin cola)',
                'total': no_queue['total'],
                'answered': no_queue['answered'],
                'missed': no_queue['missed'],
                'avgWait': round(no_queue['avg_wait'] or 0, 1),
                'avgTalk': 0,
            })

        return Response(result)

    # ─────────────────────────────────────────────────────────────
    # Rendimiento de Agentes
    # ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='agent-performance')
    def agent_performance(self, request):
        """
        Rendimiento por agente.
        Retorna array con KPIs individuales por agente.
        """
        start, end = _parse_date_range(request)

        agents = Agent.objects.all()
        result = []

        for agent in agents:
            calls_qs = Call.objects.filter(
                agent=agent,
                start_time__gte=start,
                start_time__lte=end,
            )
            total = calls_qs.count()
            answered = calls_qs.filter(status='completed').count()
            missed = calls_qs.filter(status__in=['no_answer', 'busy', 'cancelled']).count()

            agg = calls_qs.filter(status='completed').aggregate(
                avg_talk=Avg('talk_time'),
                avg_wait=Avg('wait_time'),
                total_talk=Sum('talk_time'),
            )

            answer_rate = round((answered / total * 100), 1) if total > 0 else 0

            result.append({
                'agentId': agent.id,
                'agentName': agent.user.get_full_name() or agent.agent_id,
                'extension': agent.sip_extension,
                'status': agent.status,
                'totalCalls': total,
                'answeredCalls': answered,
                'missedCalls': missed,
                'answerRate': answer_rate,
                'avgTalkTime': round(agg['avg_talk'] or 0, 1),
                'avgWaitTime': round(agg['avg_wait'] or 0, 1),
                'totalTalkTime': agg['total_talk'] or 0,
                'callsToday': agent.calls_today,
                'talkTimeToday': agent.talk_time_today,
            })

        # Ordenar por total de llamadas descendente
        result.sort(key=lambda x: x['totalCalls'], reverse=True)
        return Response(result)

    # ─────────────────────────────────────────────────────────────
    # Resumen de Llamadas por Día
    # ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='call-summary')
    def call_summary(self, request):
        """
        Resumen diario de llamadas.
        Retorna array de {date, total, answered, missed, inbound, outbound, avgTalk}.
        """
        start, end = _parse_date_range(request)
        qs = Call.objects.filter(start_time__gte=start, start_time__lte=end)

        daily = (
            qs
            .annotate(date=TruncDate('start_time'))
            .values('date')
            .annotate(
                total=Count('id'),
                answered=Count('id', filter=Q(status='completed')),
                missed=Count('id', filter=Q(status__in=['no_answer', 'busy', 'cancelled'])),
                inbound=Count('id', filter=Q(direction='inbound')),
                outbound=Count('id', filter=Q(direction='outbound')),
                avg_talk=Avg('talk_time', filter=Q(status='completed')),
                total_talk=Sum('talk_time', filter=Q(status='completed')),
            )
            .order_by('date')
        )

        result = []
        for item in daily:
            result.append({
                'date': item['date'].isoformat() if item['date'] else '',
                'total': item['total'],
                'answered': item['answered'],
                'missed': item['missed'],
                'inbound': item['inbound'],
                'outbound': item['outbound'],
                'avgTalkTime': round(item['avg_talk'] or 0, 1),
                'totalTalkTime': item['total_talk'] or 0,
            })

        return Response(result)

    # ─────────────────────────────────────────────────────────────
    # Dashboard Stats (endpoint dedicado)
    # ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'], url_path='dashboard-stats')
    def dashboard_stats(self, request):
        """
        Estadísticas principales para el dashboard.
        Calcula todo server-side para evitar traer miles de registros al frontend.
        """
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        calls_today = Call.objects.filter(start_time__gte=today_start)
        total_today = calls_today.count()
        answered_today = calls_today.filter(status='completed').count()
        missed_today = calls_today.filter(
            status__in=['no_answer', 'busy', 'cancelled']
        ).count()

        agg = calls_today.filter(status='completed').aggregate(
            avg_talk=Avg('talk_time'),
            avg_wait=Avg('wait_time'),
            total_talk=Sum('talk_time'),
        )

        # Llamadas activas
        active_calls = Call.objects.filter(
            status__in=['initiated', 'ringing', 'answered']
        ).count()

        # Agentes
        active_agents = Agent.objects.exclude(status='offline').count()
        available_agents = Agent.objects.filter(status='available').count()
        busy_agents = Agent.objects.filter(status__in=['busy', 'oncall']).count()

        # Llamadas en espera (en cola / ringing)
        queued_calls = Call.objects.filter(status='ringing').count()

        # Inbound/outbound hoy
        inbound_today = calls_today.filter(direction='inbound').count()
        outbound_today = calls_today.filter(direction='outbound').count()

        answer_rate = round((answered_today / total_today * 100), 1) if total_today > 0 else 0

        return Response({
            'callsToday': total_today,
            'answeredToday': answered_today,
            'missedToday': missed_today,
            'activeCalls': active_calls,
            'queuedCalls': queued_calls,
            'inboundToday': inbound_today,
            'outboundToday': outbound_today,
            'answerRate': answer_rate,
            'avgTalkTime': round(agg['avg_talk'] or 0, 1),
            'avgWaitTime': round(agg['avg_wait'] or 0, 1),
            'totalTalkTime': agg['total_talk'] or 0,
            'activeAgents': active_agents,
            'availableAgents': available_agents,
            'busyAgents': busy_agents,
        })
