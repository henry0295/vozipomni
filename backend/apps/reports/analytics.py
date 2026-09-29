"""
Analítica del contact center por período (todo calculado en la base de datos).

Convenciones de KPIs (estándar de la industria, COPC / ICMI):
  Ofrecidas        = llamadas entrantes
  Nivel de servicio (SL) = entrantes contestadas en ≤ T s / (ofrecidas − abandonos cortos < 5 s)
  ASA              = espera promedio de las entrantes contestadas
  AHT (TMO)        = (conversación + retención + post-llamada) / llamadas atendidas
  Abandono         = abandonadas / ofrecidas
  Ocupación        = (en llamada + post-llamada) / (tiempo conectado − pausas)
  Utilización      = (en llamada + post-llamada) / tiempo conectado
  FCR estimado     = 100 − % de clientes que llamaron más de una vez en el período
  Contactabilidad  = salientes contestadas / salientes
  Conversión       = llamadas tipificadas como exitosas / atendidas

Filtros comunes (dict): campaign, agent, queue, direction.
"""
from datetime import timedelta

from django.db.models import (
    Avg, Count, DurationField, ExpressionWrapper, F, Max, Min, OuterRef, Q, Subquery, Sum,
)
from django.db.models.functions import ExtractHour, ExtractWeekDay, Right, TruncDate
from django.utils import timezone

MISSED = ['no_answer', 'busy', 'cancelled']
DEFAULT_SLA = 20          # segundos
SHORT_ABANDON = 5         # abandonos < 5 s no penalizan el nivel de servicio
SHORT_CALL = 10           # llamadas contestadas < 10 s (posibles cortes / errores)
CHAT_FRT_TARGET = 300     # primera respuesta en chats ≤ 5 min

WAIT_BUCKETS = [(0, 10), (10, 20), (20, 30), (30, 60), (60, 120), (120, None)]
TALK_BUCKETS = [(0, 30), (30, 60), (60, 180), (180, 300), (300, 600), (600, None)]
TALK_LABELS = ['< 30 s', '30 s – 1 min', '1 – 3 min', '3 – 5 min', '5 – 10 min', '> 10 min']

STATUS_LABELS = {
    'initiated': 'Iniciada', 'ringing': 'Timbrando', 'answered': 'En curso',
    'completed': 'Contestada', 'busy': 'Ocupado', 'no_answer': 'No contestada',
    'failed': 'Fallida', 'cancelled': 'Cancelada', 'voicemail': 'Buzón',
    'machine': 'Contestador', 'abandoned': 'Abandonada', 'transferred': 'Transferida',
}
WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────

def pct(part, total):
    return round(part / total * 100, 1) if total else 0


def rnd(value, digits=1):
    return round(value or 0, digits)


def secs(delta):
    """timedelta (Avg sobre DurationField) → segundos."""
    return round(delta.total_seconds(), 1) if delta else 0


def previous_range(start, end):
    """Período anterior de la misma duración (para comparar)."""
    span = end - start
    return start - span - timedelta(seconds=1), start - timedelta(seconds=1)


def calls_qs(start, end, filters=None):
    from apps.telephony.models import Call
    qs = Call.objects.filter(start_time__gte=start, start_time__lte=end)
    f = filters or {}
    if f.get('campaign'):
        qs = qs.filter(campaign_id=f['campaign'])
    if f.get('agent'):
        qs = qs.filter(agent_id=f['agent'])
    if f.get('queue'):
        qs = qs.filter(queue_id=f['queue'])
    if f.get('direction'):
        qs = qs.filter(direction=f['direction'])
    return qs


def _bucket_label(lo, hi):
    if hi is None:
        return f'> {lo} s'
    return f'{lo}–{hi} s'


def _bucket_aggs(field, buckets, base_q, prefix):
    aggs = {}
    for i, (lo, hi) in enumerate(buckets):
        q = base_q & Q(**{f'{field}__gte': lo})
        if hi is not None:
            q &= Q(**{f'{field}__lt': hi})
        aggs[f'{prefix}{i}'] = Count('id', filter=q)
    return aggs


def agent_times(start, end, agent_ids=None):
    """
    Segundos por estado y agente según AgentStatusHistory en el período.
    → {agent_id: {'available': s, 'oncall': s, 'wrapup': s, 'break': s, 'logged': s, ...}}
    """
    from apps.agents.models import AgentStatusHistory
    qs = AgentStatusHistory.objects.filter(started_at__gte=start, started_at__lte=end)
    if agent_ids is not None:
        qs = qs.filter(agent_id__in=agent_ids)
    out = {}

    def add(agent_id, status, seconds):
        d = out.setdefault(agent_id, {})
        d[status] = d.get(status, 0) + max(0, int(seconds or 0))

    for row in qs.filter(ended_at__isnull=False).values('agent_id', 'status').annotate(s=Sum('duration')).order_by():
        add(row['agent_id'], row['status'], row['s'])
    limit = min(timezone.now(), end)
    for rec in qs.filter(ended_at__isnull=True).only('agent_id', 'status', 'started_at'):
        add(rec.agent_id, rec.status, (limit - rec.started_at).total_seconds())

    for d in out.values():
        d['oncall_total'] = d.get('oncall', 0) + d.get('busy', 0)
        d['logged'] = sum(v for k, v in d.items() if k not in ('offline', 'oncall_total'))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Resumen general
# ─────────────────────────────────────────────────────────────────────────────

def kpi_block(start, end, filters=None, sla=DEFAULT_SLA):
    """KPIs principales de un período (se usa también para el período anterior)."""
    qs = calls_qs(start, end, filters)
    done = Q(status='completed')
    inbound = Q(direction='inbound')
    a = qs.aggregate(
        total=Count('id'),
        inbound=Count('id', filter=inbound),
        outbound=Count('id', filter=Q(direction='outbound')),
        answered=Count('id', filter=done),
        in_answered=Count('id', filter=inbound & done),
        out_answered=Count('id', filter=Q(direction='outbound') & done),
        abandoned=Count('id', filter=Q(status='abandoned')),
        short_abandoned=Count('id', filter=Q(status='abandoned', wait_time__lt=SHORT_ABANDON)),
        missed=Count('id', filter=Q(status__in=MISSED)),
        failed=Count('id', filter=Q(status='failed')),
        voicemail=Count('id', filter=Q(status='voicemail')),
        machine=Count('id', filter=Q(status='machine')),
        transferred=Count('id', filter=Q(transferred=True)),
        in_sla=Count('id', filter=inbound & done & Q(wait_time__lte=sla)),
        short_calls=Count('id', filter=done & Q(talk_time__lt=SHORT_CALL)),
        talk=Sum('talk_time', filter=done),
        hold=Sum('hold_time', filter=done),
        avg_talk=Avg('talk_time', filter=done),
        avg_hold=Avg('hold_time', filter=done),
        asa=Avg('wait_time', filter=inbound & done),
        max_wait=Max('wait_time', filter=inbound),
        avg_abandon_wait=Avg('wait_time', filter=Q(status='abandoned')),
        typed=Count('id', filter=Q(disposition__isnull=False)),
        success=Count('id', filter=Q(disposition__is_success=True)),
        recorded=Count('id', filter=Q(is_recorded=True)),
    )

    in_qs = qs.filter(direction='inbound').exclude(caller_id__in=['', 'unknown']).order_by()
    unique_callers = in_qs.values('caller_id').distinct().count()
    repeat_callers = in_qs.values('caller_id').annotate(n=Count('id')).filter(n__gt=1).count()

    agent_ids = [int(filters['agent'])] if filters and filters.get('agent') else None
    times = agent_times(start, end, agent_ids)
    tot = {}
    for d in times.values():
        for k, v in d.items():
            tot[k] = tot.get(k, 0) + v
    logged = tot.get('logged', 0)
    wrapup = tot.get('wrapup', 0)
    breaks = tot.get('break', 0)
    productive = max(tot.get('oncall_total', 0), (a['talk'] or 0) + (a['hold'] or 0)) + wrapup

    answered = a['answered']
    offered_sl = max(0, a['inbound'] - a['short_abandoned'])
    handle = (a['talk'] or 0) + (a['hold'] or 0) + wrapup

    return {
        'totalCalls': a['total'],
        'inboundCalls': a['inbound'],
        'outboundCalls': a['outbound'],
        'answeredCalls': answered,
        'inboundAnswered': a['in_answered'],
        'outboundAnswered': a['out_answered'],
        'abandonedCalls': a['abandoned'],
        'shortAbandoned': a['short_abandoned'],
        'missedCalls': a['missed'],
        'failedCalls': a['failed'],
        'voicemailCalls': a['voicemail'],
        'machineCalls': a['machine'],
        'transferredCalls': a['transferred'],
        'shortCalls': a['short_calls'],
        'answerRate': pct(answered, a['total']),
        'inboundAnswerRate': pct(a['in_answered'], a['inbound']),
        'abandonRate': pct(a['abandoned'], a['inbound']),
        'serviceLevel': pct(a['in_sla'], offered_sl),
        'slaThreshold': sla,
        'contactRate': pct(a['out_answered'], a['outbound']),
        'transferRate': pct(a['transferred'], answered),
        'shortCallRate': pct(a['short_calls'], answered),
        'asa': rnd(a['asa']),
        'maxWaitTime': a['max_wait'] or 0,
        'avgAbandonWait': rnd(a['avg_abandon_wait']),
        'avgTalkTime': rnd(a['avg_talk']),
        'avgHoldTime': rnd(a['avg_hold']),
        'avgWrapupTime': rnd(wrapup / answered) if answered else 0,
        'aht': rnd(handle / answered) if answered else 0,
        'totalTalkTime': a['talk'] or 0,
        'totalHandleTime': handle,
        'uniqueCallers': unique_callers,
        'repeatCallers': repeat_callers,
        'repeatRate': pct(repeat_callers, unique_callers),
        'fcr': round(100 - pct(repeat_callers, unique_callers), 1) if unique_callers else 0,
        'typedCalls': a['typed'],
        'typingRate': pct(a['typed'], answered),
        'successCalls': a['success'],
        'conversionRate': pct(a['success'], answered),
        'recordedCalls': a['recorded'],
        'loggedTime': logged,
        'breakTime': breaks,
        'wrapupTime': wrapup,
        'occupancy': pct(productive, max(0, logged - breaks)),
        'utilization': pct(productive, logged),
        'agentsWorked': len([1 for d in times.values() if d.get('logged')]),
        'callsPerAgentHour': round(answered / (logged / 3600), 1) if logged >= 60 else 0,
    }


def summary(start, end, filters=None, sla=DEFAULT_SLA):
    """KPIs + comparación con el período anterior + tendencias para la pestaña Resumen."""
    qs = calls_qs(start, end, filters)
    prev_start, prev_end = previous_range(start, end)
    done = Q(status='completed')

    # Tendencia diaria
    daily = []
    for d in qs.annotate(date=TruncDate('start_time')).values('date').annotate(
        total=Count('id'),
        inbound=Count('id', filter=Q(direction='inbound')),
        outbound=Count('id', filter=Q(direction='outbound')),
        answered=Count('id', filter=done),
        abandoned=Count('id', filter=Q(status='abandoned')),
        missed=Count('id', filter=Q(status__in=MISSED)),
        short_ab=Count('id', filter=Q(status='abandoned', wait_time__lt=SHORT_ABANDON)),
        in_sla=Count('id', filter=Q(direction='inbound', wait_time__lte=sla) & done),
        talk=Sum('talk_time', filter=done),
        hold=Sum('hold_time', filter=done),
        asa=Avg('wait_time', filter=Q(direction='inbound') & done),
    ).order_by('date'):
        daily.append({
            'date': d['date'].isoformat() if d['date'] else '',
            'total': d['total'], 'inbound': d['inbound'], 'outbound': d['outbound'],
            'answered': d['answered'], 'abandoned': d['abandoned'], 'missed': d['missed'],
            'answerRate': pct(d['answered'], d['total']),
            'abandonRate': pct(d['abandoned'], d['inbound']),
            'serviceLevel': pct(d['in_sla'], max(0, d['inbound'] - d['short_ab'])),
            'aht': rnd(((d['talk'] or 0) + (d['hold'] or 0)) / d['answered']) if d['answered'] else 0,
            'asa': rnd(d['asa']),
        })

    # Por hora
    hours = {h['hour']: h for h in qs.order_by().annotate(hour=ExtractHour('start_time')).values('hour').annotate(
        total=Count('id'),
        answered=Count('id', filter=done),
        abandoned=Count('id', filter=Q(status='abandoned')),
        missed=Count('id', filter=Q(status__in=MISSED)),
        inbound=Count('id', filter=Q(direction='inbound')),
        in_sla=Count('id', filter=Q(direction='inbound', wait_time__lte=sla) & done),
        asa=Avg('wait_time', filter=Q(direction='inbound') & done),
    )}
    hourly = []
    for h in range(24):
        d = hours.get(h, {})
        hourly.append({
            'hour': h, 'label': f'{h:02d}:00',
            'total': d.get('total', 0), 'answered': d.get('answered', 0),
            'abandoned': d.get('abandoned', 0), 'missed': d.get('missed', 0),
            'serviceLevel': pct(d.get('in_sla', 0), d.get('inbound', 0)),
            'asa': rnd(d.get('asa')),
        })

    # Mapa de calor día × hora (ExtractWeekDay: 1=domingo … 7=sábado → 0=lunes)
    matrix = [[0] * 24 for _ in range(7)]
    for row in qs.order_by().annotate(dow=ExtractWeekDay('start_time'), hour=ExtractHour('start_time')) \
            .values('dow', 'hour').annotate(n=Count('id')):
        matrix[(row['dow'] + 5) % 7][row['hour']] = row['n']

    # Distribución por estado
    by_status = [
        {'status': r['status'], 'label': STATUS_LABELS.get(r['status'], r['status']), 'count': r['n']}
        for r in qs.values('status').annotate(n=Count('id')).order_by('-n')
    ]

    # Distribución de conversación
    talk_aggs = qs.aggregate(**_bucket_aggs('talk_time', TALK_BUCKETS, done, 't'))
    talk_dist = [{'label': label, 'count': talk_aggs[f't{i}']} for i, label in enumerate(TALK_LABELS)]

    return {
        'current': kpi_block(start, end, filters, sla),
        'previous': kpi_block(prev_start, prev_end, filters, sla),
        'previousPeriod': {'start': prev_start.isoformat(), 'end': prev_end.isoformat()},
        'daily': daily,
        'hourly': hourly,
        'heatmap': {'days': WEEKDAYS, 'matrix': matrix, 'max': max(max(r) for r in matrix)},
        'byStatus': by_status,
        'talkDistribution': talk_dist,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Agentes
# ─────────────────────────────────────────────────────────────────────────────

def agents_report(start, end, filters=None):
    from apps.agents.models import Agent
    from apps.recordings.models import RecordingEvaluation

    done = Q(status='completed')
    stats = {r['agent_id']: r for r in calls_qs(start, end, filters).exclude(agent__isnull=True)
             .values('agent_id').annotate(
                 total=Count('id'),
                 inbound=Count('id', filter=Q(direction='inbound')),
                 outbound=Count('id', filter=Q(direction='outbound')),
                 answered=Count('id', filter=done),
                 missed=Count('id', filter=Q(status__in=MISSED)),
                 transferred=Count('id', filter=Q(transferred=True)),
                 short=Count('id', filter=done & Q(talk_time__lt=SHORT_CALL)),
                 talk=Sum('talk_time', filter=done),
                 hold=Sum('hold_time', filter=done),
                 avg_talk=Avg('talk_time', filter=done),
                 max_talk=Max('talk_time', filter=done),
                 typed=Count('id', filter=Q(disposition__isnull=False)),
                 success=Count('id', filter=Q(disposition__is_success=True)),
             ).order_by()}

    agent_filter = [int(filters['agent'])] if filters and filters.get('agent') else None
    times = agent_times(start, end, agent_filter)

    ev_qs = RecordingEvaluation.objects.filter(created_at__gte=start, created_at__lte=end,
                                               recording__agent__isnull=False)
    quality = {r['recording__agent_id']: r for r in ev_qs.values('recording__agent_id')
               .annotate(n=Count('id'), avg=Avg('total_score')).order_by()}

    from apps.messaging.models import Conversation
    chats = {r['agent_id']: r['n'] for r in Conversation.objects.filter(
        started_at__gte=start, started_at__lte=end, agent__isnull=False
    ).values('agent_id').annotate(n=Count('id')).order_by()}

    ids = set(stats) | {k for k, v in times.items() if v.get('logged')} | set(chats)
    if agent_filter:
        ids &= set(agent_filter)
    rows = []
    for agent in Agent.objects.select_related('user').filter(id__in=ids):
        s = stats.get(agent.id, {})
        t = times.get(agent.id, {})
        q = quality.get(agent.id, {})
        answered = s.get('answered', 0)
        talk, hold, wrapup = s.get('talk') or 0, s.get('hold') or 0, t.get('wrapup', 0)
        logged, breaks = t.get('logged', 0), t.get('break', 0)
        productive = max(t.get('oncall_total', 0), talk + hold) + wrapup
        rows.append({
            'agentId': agent.id,
            'agentName': agent.user.get_full_name() or agent.user.username or agent.agent_id,
            'extension': agent.sip_extension,
            'status': agent.status,
            'totalCalls': s.get('total', 0),
            'inboundCalls': s.get('inbound', 0),
            'outboundCalls': s.get('outbound', 0),
            'answeredCalls': answered,
            'missedCalls': s.get('missed', 0),
            'transferredCalls': s.get('transferred', 0),
            'shortCalls': s.get('short', 0),
            'chats': chats.get(agent.id, 0),
            'avgTalkTime': rnd(s.get('avg_talk')),
            'maxTalkTime': s.get('max_talk') or 0,
            'avgHoldTime': rnd(hold / answered) if answered else 0,
            'avgWrapupTime': rnd(wrapup / answered) if answered else 0,
            'aht': rnd((talk + hold + wrapup) / answered) if answered else 0,
            'totalTalkTime': talk,
            'loggedTime': logged,
            'availableTime': t.get('available', 0),
            'oncallTime': t.get('oncall_total', 0),
            'wrapupTime': wrapup,
            'breakTime': breaks,
            'occupancy': pct(productive, max(0, logged - breaks)),
            'utilization': pct(productive, logged),
            'callsPerHour': round(answered / (logged / 3600), 1) if logged >= 60 else 0,
            'transferRate': pct(s.get('transferred', 0), answered),
            'typingRate': pct(s.get('typed', 0), answered),
            'successCalls': s.get('success', 0),
            'conversionRate': pct(s.get('success', 0), answered),
            'qualityScore': rnd(q.get('avg')),
            'evaluations': q.get('n', 0),
        })

    # Puntaje compuesto (0-100) para el ranking: productividad, calidad y adherencia
    max_cph = max([r['callsPerHour'] for r in rows] or [0]) or 1
    for r in rows:
        parts = [(r['callsPerHour'] / max_cph * 100, 0.35), (min(r['occupancy'], 100), 0.25)]
        if r['evaluations']:
            parts.append((r['qualityScore'], 0.3))
        parts.append((100 - min(r['transferRate'], 100), 0.1))
        weight = sum(w for _, w in parts)
        r['score'] = round(sum(v * w for v, w in parts) / weight, 1) if weight else 0
    rows.sort(key=lambda r: (r['score'], r['answeredCalls']), reverse=True)
    for i, r in enumerate(rows, 1):
        r['rank'] = i
    return rows


def breaks_report(start, end, filters=None):
    """Pausas por motivo y por agente, incluidas las que exceden la duración máxima configurada."""
    from apps.agents.models import AgentBreakReason, AgentStatusHistory

    qs = AgentStatusHistory.objects.filter(status='break', started_at__gte=start, started_at__lte=end) \
        .select_related('agent__user')
    if filters and filters.get('agent'):
        qs = qs.filter(agent_id=filters['agent'])
    limits = {}
    for r in AgentBreakReason.objects.all():
        if r.max_duration:
            limits[r.name.lower()] = r.max_duration * 60
            limits[r.code.lower()] = r.max_duration * 60

    now = min(timezone.now(), end)
    by_reason, by_agent, exceeded = {}, {}, []
    for rec in qs:
        dur = rec.duration or (int(((rec.ended_at or now) - rec.started_at).total_seconds()))
        reason = (rec.reason or '').strip() or 'Sin motivo'
        agent_name = rec.agent.user.get_full_name() or rec.agent.user.username
        r = by_reason.setdefault(reason, {'reason': reason, 'count': 0, 'total': 0, 'max': 0, 'exceeded': 0})
        a = by_agent.setdefault(rec.agent_id, {'agentId': rec.agent_id, 'agentName': agent_name,
                                               'count': 0, 'total': 0, 'exceeded': 0, 'reasons': {}})
        r['count'] += 1
        r['total'] += dur
        r['max'] = max(r['max'], dur)
        a['count'] += 1
        a['total'] += dur
        ar = a['reasons'].setdefault(reason, {'count': 0, 'total': 0, 'exceeded': 0})
        ar['count'] += 1
        ar['total'] += dur
        limit = limits.get(reason.lower())
        if limit and dur > limit:
            r['exceeded'] += 1
            a['exceeded'] += 1
            ar['exceeded'] += 1
            exceeded.append({
                'agentName': agent_name, 'reason': reason, 'duration': dur, 'limit': limit,
                'excess': dur - limit, 'start': timezone.localtime(rec.started_at).isoformat(),
            })
    for r in by_reason.values():
        r['avg'] = round(r['total'] / r['count']) if r['count'] else 0
        r['limit'] = limits.get(r['reason'].lower())
    total = sum(r['total'] for r in by_reason.values())
    for r in by_reason.values():
        r['share'] = pct(r['total'], total)
    exceeded.sort(key=lambda x: x['excess'], reverse=True)
    return {
        'totalBreaks': sum(r['count'] for r in by_reason.values()),
        'totalTime': total,
        'exceededCount': len(exceeded),
        'byReason': sorted(by_reason.values(), key=lambda x: x['total'], reverse=True),
        'byAgent': sorted(by_agent.values(), key=lambda x: x['total'], reverse=True),
        'exceeded': exceeded[:100],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Colas
# ─────────────────────────────────────────────────────────────────────────────

def queues_report(start, end, filters=None):
    from apps.queues.models import Queue

    qs = calls_qs(start, end, filters).filter(direction='inbound')
    done = Q(status='completed')
    thresholds = {q.id: (q.service_level or DEFAULT_SLA) for q in Queue.objects.all()}
    rows = []
    for r in qs.values('queue_id', 'queue__name').annotate(
        offered=Count('id'),
        answered=Count('id', filter=done),
        abandoned=Count('id', filter=Q(status='abandoned')),
        short_ab=Count('id', filter=Q(status='abandoned', wait_time__lt=SHORT_ABANDON)),
        voicemail=Count('id', filter=Q(status='voicemail')),
        missed=Count('id', filter=Q(status__in=MISSED)),
        asa=Avg('wait_time', filter=done),
        max_wait=Max('wait_time'),
        ab_wait=Avg('wait_time', filter=Q(status='abandoned')),
        talk=Sum('talk_time', filter=done),
        hold=Sum('hold_time', filter=done),
        transferred=Count('id', filter=Q(transferred=True)),
    ).order_by('-offered'):
        threshold = thresholds.get(r['queue_id'], DEFAULT_SLA)
        in_sla = qs.filter(queue_id=r['queue_id'], status='completed', wait_time__lte=threshold).count()
        answered = r['answered']
        rows.append({
            'queueId': r['queue_id'],
            'queueName': r['queue__name'] or 'Directas (sin cola)',
            'offered': r['offered'],
            'answered': answered,
            'abandoned': r['abandoned'],
            'shortAbandoned': r['short_ab'],
            'voicemail': r['voicemail'],
            'missed': r['missed'],
            'transferred': r['transferred'],
            'answerRate': pct(answered, r['offered']),
            'abandonRate': pct(r['abandoned'], r['offered']),
            'serviceLevel': pct(in_sla, max(0, r['offered'] - r['short_ab'])),
            'slaThreshold': threshold,
            'asa': rnd(r['asa']),
            'maxWait': r['max_wait'] or 0,
            'avgAbandonWait': rnd(r['ab_wait']),
            'aht': rnd(((r['talk'] or 0) + (r['hold'] or 0)) / answered) if answered else 0,
        })

    # Distribución de espera: contestadas vs abandonadas (curva de abandono)
    aggs = qs.aggregate(
        **_bucket_aggs('wait_time', WAIT_BUCKETS, done, 'a'),
        **_bucket_aggs('wait_time', WAIT_BUCKETS, Q(status='abandoned'), 'b'),
    )
    dist = [{'label': _bucket_label(lo, hi), 'answered': aggs[f'a{i}'], 'abandoned': aggs[f'b{i}']}
            for i, (lo, hi) in enumerate(WAIT_BUCKETS)]
    return {'queues': rows, 'waitDistribution': dist}


def abandoned_report(start, end, filters=None, limit=300):
    """
    Llamadas entrantes perdidas (abandonadas / no contestadas / buzón) y si se devolvieron:
    alguna llamada posterior saliente a ese número o entrante contestada del mismo número.
    Se comparan los últimos 10 dígitos para tolerar prefijos (57, 0, +).
    """
    from apps.telephony.models import Call

    base = calls_qs(start, end, filters).filter(
        direction='inbound', status__in=['abandoned', 'no_answer', 'voicemail', 'cancelled'],
    ).exclude(caller_id__in=['', 'unknown'])
    attempts = {r['caller_id']: r['n'] for r in base.order_by().values('caller_id').annotate(n=Count('id'))}

    tail = Right(OuterRef('caller_id'), 10)
    later = Call.objects.filter(start_time__gt=OuterRef('start_time')).filter(
        Q(direction='outbound', called_number__endswith=tail) |
        Q(direction='inbound', status='completed', caller_id__endswith=tail)
    ).order_by('start_time')
    lost = base.annotate(
        returned_at=Subquery(later.values('start_time')[:1]),
        returned_by=Subquery(later.values('agent__user__first_name')[:1]),
    ).select_related('queue').order_by('-start_time')

    rows, returned, delays = [], 0, []
    for c in lost[:2000]:
        if c.returned_at:
            returned += 1
            delays.append((c.returned_at - c.start_time).total_seconds())
        if len(rows) < limit:
            rows.append({
                'callId': c.call_id,
                'start': timezone.localtime(c.start_time).isoformat(),
                'caller': c.caller_id,
                'queue': c.queue.name if c.queue else '',
                'status': c.status,
                'statusLabel': STATUS_LABELS.get(c.status, c.status),
                'waitTime': c.wait_time,
                'attempts': attempts.get(c.caller_id, 1),
                'returned': bool(c.returned_at),
                'returnedAt': timezone.localtime(c.returned_at).isoformat() if c.returned_at else None,
                'returnDelay': int((c.returned_at - c.start_time).total_seconds()) if c.returned_at else None,
                'returnedBy': c.returned_by or '',
            })
    total = base.count()
    return {
        'total': total,
        'uniqueNumbers': len(attempts),
        'returned': returned,
        'pending': max(0, min(total, 2000) - returned),
        'returnRate': pct(returned, min(total, 2000)),
        'avgReturnDelay': round(sum(delays) / len(delays)) if delays else 0,
        'rows': rows,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Campañas y tipificaciones
# ─────────────────────────────────────────────────────────────────────────────

def campaigns_report(start, end, filters=None):
    from apps.campaigns.models import Campaign
    from apps.contacts.models import Contact
    from apps.messaging.models import Conversation

    done = Q(status='completed')
    calls = calls_qs(start, end, {k: v for k, v in (filters or {}).items() if k != 'queue'})
    stats = {r['campaign_id']: r for r in calls.exclude(campaign__isnull=True).values('campaign_id').annotate(
        total=Count('id'),
        answered=Count('id', filter=done),
        machine=Count('id', filter=Q(status='machine')),
        no_answer=Count('id', filter=Q(status__in=MISSED + ['failed'])),
        abandoned=Count('id', filter=Q(status='abandoned')),
        typed=Count('id', filter=Q(disposition__isnull=False)),
        success=Count('id', filter=Q(disposition__is_success=True)),
        callbacks=Count('id', filter=Q(disposition__requires_callback=True)),
        talk=Sum('talk_time', filter=done),
        avg_talk=Avg('talk_time', filter=done),
        agents=Count('agent_id', distinct=True),
    ).order_by()}
    chats = {r['campaign_id']: r for r in Conversation.objects.filter(
        started_at__gte=start, started_at__lte=end, campaign__isnull=False
    ).values('campaign_id').annotate(
        n=Count('id'), success=Count('id', filter=Q(disposition__is_success=True))).order_by()}

    camps = Campaign.objects.select_related('contact_list')
    if filters and filters.get('campaign'):
        camps = camps.filter(id=filters['campaign'])
    else:
        camps = camps.filter(Q(id__in=set(stats) | set(chats)) | Q(status='active'))

    rows = []
    for c in camps:
        s = stats.get(c.id, {})
        ch = chats.get(c.id, {})
        contacts = {'total': 0, 'touched': 0, 'pending': 0, 'avg_attempts': 0, 'success': 0}
        if c.contact_list_id:
            ca = Contact.objects.filter(contact_list_id=c.contact_list_id).aggregate(
                total=Count('id'),
                touched=Count('id', filter=Q(attempts__gt=0)),
                pending=Count('id', filter=Q(status__in=['new', 'pending', 'callback'])),
                success=Count('id', filter=Q(status='success')),
                avg_attempts=Avg('attempts', filter=Q(attempts__gt=0)),
            )
            contacts = {k: (v or 0) for k, v in ca.items()}
        answered = s.get('answered', 0)
        rows.append({
            'campaignId': c.id,
            'campaignName': c.name,
            'type': c.campaign_type,
            'dialer': c.dialer_type or '',
            'status': c.status,
            'calls': s.get('total', 0),
            'answered': answered,
            'machine': s.get('machine', 0),
            'noAnswer': s.get('no_answer', 0),
            'abandoned': s.get('abandoned', 0),
            'contactRate': pct(answered, s.get('total', 0)),
            'typed': s.get('typed', 0),
            'typingRate': pct(s.get('typed', 0), answered),
            'success': s.get('success', 0) + ch.get('success', 0),
            'conversionRate': pct(s.get('success', 0), answered),
            'callbacks': s.get('callbacks', 0),
            'avgTalkTime': rnd(s.get('avg_talk')),
            'totalTalkTime': s.get('talk') or 0,
            'agents': s.get('agents', 0),
            'chats': ch.get('n', 0),
            'contactsTotal': contacts['total'],
            'contactsTouched': contacts['touched'],
            'contactsPending': contacts['pending'],
            'contactsSuccess': contacts['success'],
            'penetration': pct(contacts['touched'], contacts['total']),
            'avgAttempts': rnd(contacts['avg_attempts']),
        })
    rows.sort(key=lambda r: r['calls'] + r['chats'], reverse=True)
    return rows


def dispositions_report(start, end, filters=None):
    """Tipificaciones de llamadas y conversaciones en el período."""
    from apps.messaging.models import Conversation

    merged = {}
    call_rows = calls_qs(start, end, filters).filter(disposition__isnull=False).order_by().values(
        'disposition__name', 'disposition__is_success', 'disposition__campaign__name').annotate(n=Count('id'))
    chat_qs = Conversation.objects.filter(started_at__gte=start, started_at__lte=end, disposition__isnull=False)
    if filters and filters.get('campaign'):
        chat_qs = chat_qs.filter(campaign_id=filters['campaign'])
    if filters and filters.get('agent'):
        chat_qs = chat_qs.filter(agent_id=filters['agent'])
    chat_rows = chat_qs.order_by().values('disposition__name', 'disposition__is_success',
                               'disposition__campaign__name').annotate(n=Count('id'))
    for kind, rows in (('calls', call_rows), ('chats', chat_rows)):
        for r in rows:
            key = (r['disposition__campaign__name'] or '', r['disposition__name'])
            d = merged.setdefault(key, {
                'campaign': key[0], 'name': key[1], 'isSuccess': bool(r['disposition__is_success']),
                'calls': 0, 'chats': 0,
            })
            d[kind] += r['n']
    total = sum(d['calls'] + d['chats'] for d in merged.values())
    out = []
    for d in merged.values():
        d['total'] = d['calls'] + d['chats']
        d['share'] = pct(d['total'], total)
        out.append(d)
    out.sort(key=lambda d: d['total'], reverse=True)
    answered = calls_qs(start, end, filters).filter(status='completed').count()
    typed = sum(d['calls'] for d in out)
    return {
        'total': total,
        'success': sum(d['total'] for d in out if d['isSuccess']),
        'untypedCalls': max(0, answered - typed),
        'typingRate': pct(typed, answered),
        'rows': out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Omnicanal y calidad
# ─────────────────────────────────────────────────────────────────────────────

def omnichannel_report(start, end, filters=None):
    from apps.messaging.models import Channel, Conversation

    qs = Conversation.objects.filter(started_at__gte=start, started_at__lte=end) \
        .exclude(closed_reason='broadcast', last_inbound_at__isnull=True)
    f = filters or {}
    if f.get('campaign'):
        qs = qs.filter(campaign_id=f['campaign'])
    if f.get('agent'):
        qs = qs.filter(agent_id=f['agent'])

    frt = ExpressionWrapper(F('first_response_at') - F('started_at'), output_field=DurationField())
    res = ExpressionWrapper(F('closed_at') - F('started_at'), output_field=DurationField())
    aggs = dict(
        total=Count('id', distinct=True),
        closed=Count('id', filter=Q(status='closed'), distinct=True),
        open=Count('id', filter=Q(status__in=['open', 'waiting']), distinct=True),
        unassigned=Count('id', filter=Q(agent__isnull=True, status__in=['open', 'waiting']), distinct=True),
        responded=Count('id', filter=Q(first_response_at__isnull=False), distinct=True),
        frt_ok=Count('id', filter=Q(first_response_at__lte=F('started_at') + timedelta(seconds=CHAT_FRT_TARGET)),
                     distinct=True),
        typed=Count('id', filter=Q(disposition__isnull=False), distinct=True),
        success=Count('id', filter=Q(disposition__is_success=True), distinct=True),
    )
    types = dict(Channel.CHANNEL_TYPES)

    def build(row, frt_avg, res_avg, msgs):
        return {
            'total': row['total'], 'closed': row['closed'], 'open': row['open'],
            'unassigned': row['unassigned'], 'responded': row['responded'],
            'responseRate': pct(row['responded'], row['total']),
            'frtWithinTarget': pct(row['frt_ok'], row['responded']),
            'avgFirstResponse': secs(frt_avg),
            'avgResolution': secs(res_avg),
            'resolutionRate': pct(row['closed'], row['total']),
            'typingRate': pct(row['typed'], row['closed']),
            'success': row['success'],
            'inboundMessages': msgs.get('in', 0), 'outboundMessages': msgs.get('out', 0),
        }

    def msg_counts(q):
        return q.aggregate(**{'in': Count('messages', filter=Q(messages__direction='inbound')),
                              'out': Count('messages', filter=Q(messages__direction='outbound'))})

    by_channel = []
    for r in qs.values('channel__channel_type').annotate(**aggs).order_by('-total'):
        ctype = r['channel__channel_type']
        sub = qs.filter(channel__channel_type=ctype)
        times = sub.aggregate(frt=Avg(frt, filter=Q(first_response_at__isnull=False)),
                              res=Avg(res, filter=Q(closed_at__isnull=False)))
        item = build(r, times['frt'], times['res'], msg_counts(sub))
        item.update({'channel': ctype, 'label': types.get(ctype, ctype)})
        by_channel.append(item)

    total_row = qs.aggregate(**aggs)
    times = qs.aggregate(frt=Avg(frt, filter=Q(first_response_at__isnull=False)),
                         res=Avg(res, filter=Q(closed_at__isnull=False)))
    totals = build(total_row, times['frt'], times['res'], msg_counts(qs))

    by_agent = []
    for r in qs.exclude(agent__isnull=True).values(
            'agent_id', 'agent__user__first_name', 'agent__user__last_name', 'agent__user__username'
    ).annotate(n=Count('id'), closed=Count('id', filter=Q(status='closed')),
               frt=Avg(frt, filter=Q(first_response_at__isnull=False)),
               res=Avg(res, filter=Q(closed_at__isnull=False))).order_by('-n')[:50]:
        name = f"{r['agent__user__first_name'] or ''} {r['agent__user__last_name'] or ''}".strip()
        by_agent.append({
            'agentId': r['agent_id'], 'agentName': name or r['agent__user__username'],
            'total': r['n'], 'closed': r['closed'],
            'avgFirstResponse': secs(r['frt']), 'avgResolution': secs(r['res']),
        })

    hours = {h['hour']: h['n'] for h in qs.order_by().annotate(hour=ExtractHour('started_at'))
             .values('hour').annotate(n=Count('id'))}
    return {
        'totals': totals, 'frtTarget': CHAT_FRT_TARGET, 'byChannel': by_channel, 'byAgent': by_agent,
        'hourly': [{'hour': h, 'label': f'{h:02d}:00', 'total': hours.get(h, 0)} for h in range(24)],
    }


def quality_report(start, end, filters=None):
    from apps.recordings.models import RecordingEvaluation

    qs = RecordingEvaluation.objects.filter(created_at__gte=start, created_at__lte=end)
    f = filters or {}
    if f.get('agent'):
        qs = qs.filter(recording__agent_id=f['agent'])
    if f.get('campaign'):
        qs = qs.filter(recording__campaign_id=f['campaign'])
    a = qs.aggregate(
        n=Count('id'), avg=Avg('total_score'), min=Min('total_score'), max=Max('total_score'),
        b0=Count('id', filter=Q(total_score__lt=60)),
        b1=Count('id', filter=Q(total_score__gte=60, total_score__lt=80)),
        b2=Count('id', filter=Q(total_score__gte=80, total_score__lt=90)),
        b3=Count('id', filter=Q(total_score__gte=90)),
        feedback=Count('id', filter=Q(feedback_sent=True)),
    )
    recorded = calls_qs(start, end, filters).filter(is_recorded=True).count()
    by_agent = []
    for r in qs.exclude(recording__agent__isnull=True).values(
            'recording__agent_id', 'recording__agent__user__first_name',
            'recording__agent__user__last_name', 'recording__agent__user__username'
    ).annotate(n=Count('id'), avg=Avg('total_score'), min=Min('total_score'), max=Max('total_score'),
               below=Count('id', filter=Q(total_score__lt=60))).order_by('-avg'):
        name = f"{r['recording__agent__user__first_name'] or ''} {r['recording__agent__user__last_name'] or ''}"
        by_agent.append({
            'agentId': r['recording__agent_id'],
            'agentName': name.strip() or r['recording__agent__user__username'],
            'evaluations': r['n'], 'avgScore': rnd(r['avg']),
            'minScore': rnd(r['min']), 'maxScore': rnd(r['max']), 'belowTarget': r['below'],
        })
    by_evaluator = [
        {'evaluator': (r['evaluator__first_name'] or r['evaluator__username'] or '—'),
         'evaluations': r['n'], 'avgScore': rnd(r['avg'])}
        for r in qs.values('evaluator__first_name', 'evaluator__username')
        .annotate(n=Count('id'), avg=Avg('total_score')).order_by('-n')
    ]
    return {
        'evaluations': a['n'], 'avgScore': rnd(a['avg']), 'minScore': rnd(a['min']), 'maxScore': rnd(a['max']),
        'recordedCalls': recorded, 'coverage': pct(a['n'], recorded),
        'feedbackRate': pct(a['feedback'], a['n']),
        'distribution': [
            {'label': '< 60', 'count': a['b0']}, {'label': '60–79', 'count': a['b1']},
            {'label': '80–89', 'count': a['b2']}, {'label': '≥ 90', 'count': a['b3']},
        ],
        'byAgent': by_agent, 'byEvaluator': by_evaluator,
    }
