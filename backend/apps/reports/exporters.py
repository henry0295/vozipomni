"""
Generación de datasets tabulares y exportación a CSV / Excel.

Datasets disponibles:
  calls   → detalle de llamadas
  agents  → rendimiento por agente
  daily   → resumen diario
  queues  → resumen por cola

Uso:
  headers, rows = build_dataset('calls', start, end, {'campaign': 3})
  content, content_type, ext = render_table(headers, rows, 'xlsx', 'Llamadas')
"""
import csv
import io
from datetime import datetime

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

MAX_ROWS = 100_000

DATASETS = {
    'calls': 'Detalle de llamadas',
    'agents': 'Rendimiento de agentes',
    'daily': 'Resumen diario',
    'queues': 'Resumen por cola',
    'chats': 'Conversaciones (WhatsApp, email, chat web, redes)',
}

STATUS_LABELS = {
    'initiated': 'Iniciada', 'ringing': 'Timbrando', 'answered': 'Contestada',
    'completed': 'Completada', 'busy': 'Ocupado', 'no_answer': 'No contestada',
    'failed': 'Fallida', 'cancelled': 'Cancelada', 'voicemail': 'Buzón',
    'machine': 'Contestador', 'abandoned': 'Abandonada', 'transferred': 'Transferida',
}

MISSED = ['no_answer', 'busy', 'cancelled']


def _calls_qs(start, end, filters):
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
    if f.get('status'):
        qs = qs.filter(status=f['status'])
    return qs


def _fmt_dt(value):
    if not value:
        return ''
    return timezone.localtime(value).strftime('%Y-%m-%d %H:%M:%S')


def _pct(part, total):
    return round(part / total * 100, 1) if total else 0


def build_calls(start, end, filters):
    headers = [
        'ID llamada', 'Inicio', 'Contestada', 'Fin', 'Dirección', 'Estado',
        'Origen', 'Destino', 'Agente', 'Extensión', 'Campaña', 'Cola',
        'Espera (s)', 'Conversación (s)', 'Retención (s)', 'Calificación',
        'Transferida', 'Grabada', 'Notas',
    ]
    qs = _calls_qs(start, end, filters).select_related(
        'agent__user', 'campaign', 'queue', 'disposition'
    ).order_by('start_time')[:MAX_ROWS]
    rows = []
    for c in qs:
        agent_name = ''
        if c.agent and c.agent.user:
            agent_name = c.agent.user.get_full_name() or c.agent.user.username
        rows.append([
            c.call_id, _fmt_dt(c.start_time), _fmt_dt(c.answer_time), _fmt_dt(c.end_time),
            'Entrante' if c.direction == 'inbound' else 'Saliente',
            STATUS_LABELS.get(c.status, c.status),
            c.caller_id, c.called_number, agent_name,
            c.agent.sip_extension if c.agent else '',
            c.campaign.name if c.campaign else '',
            c.queue.name if c.queue else '',
            c.wait_time, c.talk_time, c.hold_time,
            c.disposition.name if c.disposition else '',
            'Sí' if c.transferred else 'No',
            'Sí' if c.is_recorded else 'No',
            (c.notes or '').replace('\n', ' ')[:500],
        ])
    return headers, rows


def build_agents(start, end, filters):
    from apps.agents.models import Agent
    headers = [
        'Agente', 'ID agente', 'Extensión', 'Total llamadas', 'Contestadas',
        'Perdidas', 'Abandonadas', 'Transferidas', '% respuesta',
        'Conversación total (s)', 'TMO (s)', 'Espera prom. (s)', 'Retención prom. (s)',
    ]
    calls = _calls_qs(start, end, filters)
    stats = {
        row['agent_id']: row for row in calls.exclude(agent__isnull=True).values('agent_id').annotate(
            total=Count('id'),
            answered=Count('id', filter=Q(status='completed')),
            missed=Count('id', filter=Q(status__in=MISSED)),
            abandoned=Count('id', filter=Q(status='abandoned')),
            transferred=Count('id', filter=Q(transferred=True)),
            talk=Sum('talk_time', filter=Q(status='completed')),
            avg_talk=Avg('talk_time', filter=Q(status='completed')),
            avg_wait=Avg('wait_time', filter=Q(status='completed')),
            avg_hold=Avg('hold_time', filter=Q(status='completed')),
        )
    }
    rows = []
    agents = Agent.objects.select_related('user').filter(id__in=stats.keys()).order_by('agent_id')
    for a in agents:
        s = stats[a.id]
        rows.append([
            a.user.get_full_name() or a.user.username, a.agent_id, a.sip_extension,
            s['total'], s['answered'], s['missed'], s['abandoned'], s['transferred'],
            _pct(s['answered'], s['total']), s['talk'] or 0,
            round(s['avg_talk'] or 0, 1), round(s['avg_wait'] or 0, 1), round(s['avg_hold'] or 0, 1),
        ])
    rows.sort(key=lambda r: r[3], reverse=True)
    return headers, rows


def build_daily(start, end, filters):
    headers = [
        'Fecha', 'Total', 'Entrantes', 'Salientes', 'Contestadas', 'Perdidas',
        'Abandonadas', 'Buzón', '% respuesta', 'Conversación total (s)', 'TMO (s)',
    ]
    qs = _calls_qs(start, end, filters).annotate(date=TruncDate('start_time')).values('date').annotate(
        total=Count('id'),
        inbound=Count('id', filter=Q(direction='inbound')),
        outbound=Count('id', filter=Q(direction='outbound')),
        answered=Count('id', filter=Q(status='completed')),
        missed=Count('id', filter=Q(status__in=MISSED)),
        abandoned=Count('id', filter=Q(status='abandoned')),
        voicemail=Count('id', filter=Q(status='voicemail')),
        talk=Sum('talk_time', filter=Q(status='completed')),
        avg_talk=Avg('talk_time', filter=Q(status='completed')),
    ).order_by('date')
    rows = [[
        d['date'].isoformat() if d['date'] else '', d['total'], d['inbound'], d['outbound'],
        d['answered'], d['missed'], d['abandoned'], d['voicemail'],
        _pct(d['answered'], d['total']), d['talk'] or 0, round(d['avg_talk'] or 0, 1),
    ] for d in qs]
    return headers, rows


def build_queues(start, end, filters):
    headers = [
        'Cola', 'Total', 'Contestadas', 'Abandonadas', 'Perdidas', '% respuesta',
        '% abandono', 'Espera prom. (s)', 'Espera máx. (s)', 'TMO (s)',
    ]
    from django.db.models import Max
    qs = _calls_qs(start, end, filters).exclude(queue__isnull=True).values('queue__name').annotate(
        total=Count('id'),
        answered=Count('id', filter=Q(status='completed')),
        abandoned=Count('id', filter=Q(status='abandoned')),
        missed=Count('id', filter=Q(status__in=MISSED)),
        avg_wait=Avg('wait_time'),
        max_wait=Max('wait_time'),
        avg_talk=Avg('talk_time', filter=Q(status='completed')),
    ).order_by('-total')
    rows = [[
        q['queue__name'], q['total'], q['answered'], q['abandoned'], q['missed'],
        _pct(q['answered'], q['total']), _pct(q['abandoned'], q['total']),
        round(q['avg_wait'] or 0, 1), q['max_wait'] or 0, round(q['avg_talk'] or 0, 1),
    ] for q in qs]
    return headers, rows


def build_chats(start, end, filters):
    from django.db.models import Count, Q
    from apps.messaging.models import Channel, Conversation

    headers = [
        'ID', 'Canal', 'Contacto', 'Identificador', 'Agente', 'Campaña', 'Estado',
        'Inicio', 'Asignada', 'Primera respuesta (s)', 'Cierre', 'Duración (s)',
        'Tipificación', 'Etiquetas', 'Mensajes entrantes', 'Mensajes salientes', 'Notas de cierre',
    ]
    f = filters or {}
    qs = Conversation.objects.filter(started_at__gte=start, started_at__lte=end) \
        .exclude(closed_reason='broadcast', last_inbound_at__isnull=True)
    if f.get('campaign'):
        qs = qs.filter(campaign_id=f['campaign'])
    if f.get('agent'):
        qs = qs.filter(agent_id=f['agent'])
    if f.get('channel_type'):
        qs = qs.filter(channel__channel_type=f['channel_type'])
    qs = qs.select_related('channel', 'agent__user', 'contact', 'campaign', 'disposition') \
        .prefetch_related('tags').annotate(
            n_in=Count('messages', filter=Q(messages__direction='inbound')),
            n_out=Count('messages', filter=Q(messages__direction='outbound')),
        ).order_by('started_at')[:MAX_ROWS]
    types = dict(Channel.CHANNEL_TYPES)
    status_labels = {'open': 'Abierta', 'waiting': 'En espera', 'closed': 'Cerrada'}
    rows = []
    for c in qs:
        agent_name = ''
        if c.agent and c.agent.user:
            agent_name = c.agent.user.get_full_name() or c.agent.user.username
        frt = int((c.first_response_at - c.started_at).total_seconds()) if c.first_response_at else ''
        aht = int((c.closed_at - c.started_at).total_seconds()) if c.closed_at else ''
        rows.append([
            c.id, types.get(c.channel.channel_type, c.channel.channel_type),
            c.contact.full_name if c.contact else (c.contact_name or ''), c.contact_identifier,
            agent_name, c.campaign.name if c.campaign else '', status_labels.get(c.status, c.status),
            _fmt_dt(c.started_at), _fmt_dt(c.assigned_at), frt, _fmt_dt(c.closed_at), aht,
            c.disposition.name if c.disposition else '', ', '.join(t.name for t in c.tags.all()),
            c.n_in, c.n_out, c.close_notes,
        ])
    return headers, rows


# ─── Datasets de la analítica (apps/reports/analytics.py) ───────────────────

def build_hourly(start, end, filters):
    from apps.reports import analytics
    data = analytics.summary(start, end, filters)
    headers = ['Hora', 'Total', 'Contestadas', 'Abandonadas', 'Perdidas', 'Nivel de servicio (%)', 'ASA (s)']
    return headers, [[h['label'], h['total'], h['answered'], h['abandoned'], h['missed'],
                      h['serviceLevel'], h['asa']] for h in data['hourly']]


def build_agent_kpis(start, end, filters):
    from apps.reports import analytics
    headers = [
        'Ranking', 'Agente', 'Extensión', 'Puntaje', 'Llamadas', 'Atendidas', 'Entrantes', 'Salientes',
        'Chats', 'AHT (s)', 'Conversación prom. (s)', 'Retención prom. (s)', 'Post-llamada prom. (s)',
        'Conectado (s)', 'Disponible (s)', 'En llamada (s)', 'Pausa (s)', 'Ocupación (%)', 'Utilización (%)',
        'Llamadas/hora', 'Transferencias (%)', 'Tipificación (%)', 'Conversión (%)', 'Calidad', 'Evaluaciones',
    ]
    rows = [[
        r['rank'], r['agentName'], r['extension'], r['score'], r['totalCalls'], r['answeredCalls'],
        r['inboundCalls'], r['outboundCalls'], r['chats'], r['aht'], r['avgTalkTime'], r['avgHoldTime'],
        r['avgWrapupTime'], r['loggedTime'], r['availableTime'], r['oncallTime'], r['breakTime'],
        r['occupancy'], r['utilization'], r['callsPerHour'], r['transferRate'], r['typingRate'],
        r['conversionRate'], r['qualityScore'], r['evaluations'],
    ] for r in analytics.agents_report(start, end, filters)]
    return headers, rows


def build_breaks(start, end, filters):
    from apps.reports import analytics
    data = analytics.breaks_report(start, end, filters)
    headers = ['Agente', 'Motivo', 'Pausas', 'Tiempo (s)', 'Excedidas']
    rows = []
    for a in data['byAgent']:
        for reason, r in sorted(a['reasons'].items(), key=lambda x: -x[1]['total']):
            rows.append([a['agentName'], reason, r['count'], r['total'], r['exceeded']])
        rows.append([a['agentName'], 'TOTAL', a['count'], a['total'], a['exceeded']])
    return headers, rows


def build_queue_sla(start, end, filters):
    from apps.reports import analytics
    headers = [
        'Cola', 'Ofrecidas', 'Atendidas', 'Abandonadas', 'Abandono corto (<5 s)', '% atención',
        '% abandono', 'Nivel de servicio (%)', 'Umbral SL (s)', 'ASA (s)', 'Espera máx. (s)',
        'Espera prom. abandono (s)', 'AHT (s)',
    ]
    rows = [[
        q['queueName'], q['offered'], q['answered'], q['abandoned'], q['shortAbandoned'], q['answerRate'],
        q['abandonRate'], q['serviceLevel'], q['slaThreshold'], q['asa'], q['maxWait'],
        q['avgAbandonWait'], q['aht'],
    ] for q in analytics.queues_report(start, end, filters)['queues']]
    return headers, rows


def build_abandoned(start, end, filters):
    from apps.reports import analytics
    headers = ['Fecha', 'Número', 'Cola', 'Estado', 'Espera (s)', 'Intentos del número',
               'Devuelta', 'Devuelta en (s)', 'Devuelta por']
    data = analytics.abandoned_report(start, end, filters, limit=MAX_ROWS)
    rows = [[
        r['start'][:19].replace('T', ' '), r['caller'], r['queue'], r['statusLabel'], r['waitTime'],
        r['attempts'], 'Sí' if r['returned'] else 'No', r['returnDelay'] if r['returnDelay'] is not None else '',
        r['returnedBy'],
    ] for r in data['rows']]
    return headers, rows


def build_campaign_kpis(start, end, filters):
    from apps.reports import analytics
    headers = [
        'Campaña', 'Tipo', 'Estado', 'Llamadas', 'Contactadas', 'Contactabilidad (%)', 'Contestador',
        'No contesta/ocupado', 'Tipificadas (%)', 'Éxitos', 'Conversión (%)', 'Rellamadas',
        'Conversación prom. (s)', 'Agentes', 'Chats', 'Contactos base', 'Contactos trabajados',
        'Penetración (%)', 'Pendientes', 'Intentos prom.',
    ]
    rows = [[
        c['campaignName'], c['type'], c['status'], c['calls'], c['answered'], c['contactRate'], c['machine'],
        c['noAnswer'], c['typingRate'], c['success'], c['conversionRate'], c['callbacks'], c['avgTalkTime'],
        c['agents'], c['chats'], c['contactsTotal'], c['contactsTouched'], c['penetration'],
        c['contactsPending'], c['avgAttempts'],
    ] for c in analytics.campaigns_report(start, end, filters)]
    return headers, rows


def build_dispositions(start, end, filters):
    from apps.reports import analytics
    headers = ['Campaña', 'Tipificación', 'Exitosa', 'Llamadas', 'Chats', 'Total', '% del total']
    rows = [[d['campaign'], d['name'], 'Sí' if d['isSuccess'] else 'No', d['calls'], d['chats'],
             d['total'], d['share']] for d in analytics.dispositions_report(start, end, filters)['rows']]
    return headers, rows


def build_omnichannel(start, end, filters):
    from apps.reports import analytics
    headers = ['Canal', 'Conversaciones', 'Cerradas', 'Abiertas', 'Sin asignar', '% respondidas',
               f'% 1ª respuesta ≤ {analytics.CHAT_FRT_TARGET // 60} min', '1ª respuesta prom. (s)',
               'Resolución prom. (s)', 'Mensajes entrantes', 'Mensajes salientes']
    data = analytics.omnichannel_report(start, end, filters)
    rows = [[c['label'], c['total'], c['closed'], c['open'], c['unassigned'], c['responseRate'],
             c['frtWithinTarget'], c['avgFirstResponse'], c['avgResolution'], c['inboundMessages'],
             c['outboundMessages']] for c in data['byChannel']]
    return headers, rows


def build_quality(start, end, filters):
    from apps.reports import analytics
    headers = ['Agente', 'Evaluaciones', 'Promedio', 'Mínimo', 'Máximo', 'Bajo 60']
    rows = [[a['agentName'], a['evaluations'], a['avgScore'], a['minScore'], a['maxScore'], a['belowTarget']]
            for a in analytics.quality_report(start, end, filters)['byAgent']]
    return headers, rows


DATASETS.update({
    'hourly': 'Llamadas por hora (nivel de servicio / ASA)',
    'agent_kpis': 'KPIs y ranking de agentes (AHT, ocupación, calidad)',
    'breaks': 'Pausas por agente y motivo',
    'queue_sla': 'Nivel de servicio y abandono por cola',
    'abandoned': 'Llamadas perdidas y devoluciones',
    'campaign_kpis': 'KPIs de campañas (contactabilidad, conversión)',
    'dispositions': 'Tipificaciones',
    'omnichannel': 'Omnicanal por canal (primera respuesta, resolución)',
    'quality': 'Calidad por agente',
})

BUILDERS = {
    'calls': build_calls,
    'agents': build_agents,
    'daily': build_daily,
    'queues': build_queues,
    'chats': build_chats,
    'hourly': build_hourly,
    'agent_kpis': build_agent_kpis,
    'breaks': build_breaks,
    'queue_sla': build_queue_sla,
    'abandoned': build_abandoned,
    'campaign_kpis': build_campaign_kpis,
    'dispositions': build_dispositions,
    'omnichannel': build_omnichannel,
    'quality': build_quality,
}

# report_type del modelo Report → dataset
REPORT_TYPE_DATASET = {
    'calls': 'calls',
    'agent': 'agents',
    'queue': 'queues',
    'campaign': 'calls',
    'custom': 'daily',
}


def build_dataset(dataset, start, end, filters=None):
    builder = BUILDERS.get(dataset)
    if not builder:
        raise ValueError(f"Dataset desconocido: {dataset}")
    return builder(start, end, filters or {})


def render_table(headers, rows, fmt, title='Reporte'):
    """Devuelve (bytes, content_type, extensión)."""
    fmt = (fmt or 'csv').lower()
    if fmt in ('xlsx', 'excel'):
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = title[:31] or 'Reporte'
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='0EA5E9')
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        for row in rows:
            ws.append(row)
        ws.freeze_panes = 'A2'
        for idx, header in enumerate(headers, start=1):
            sample = [len(str(header))] + [len(str(r[idx - 1])) for r in rows[:500] if idx - 1 < len(r)]
            ws.column_dimensions[get_column_letter(idx)].width = min(max(sample) + 2, 50)
        buf = io.BytesIO()
        wb.save(buf)
        return (
            buf.getvalue(),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'xlsx',
        )

    # CSV con BOM para que Excel respete UTF-8 y separador ';' (configuración regional es-CO)
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=';')
    writer.writerow(headers)
    writer.writerows(rows)
    return ('\ufeff' + buf.getvalue()).encode('utf-8'), 'text/csv; charset=utf-8', 'csv'


def export_filename(dataset, start, end, ext):
    s = start.strftime('%Y%m%d') if isinstance(start, datetime) else str(start)
    e = end.strftime('%Y%m%d') if isinstance(end, datetime) else str(end)
    return f"vozipomni_{dataset}_{s}_{e}.{ext}"
