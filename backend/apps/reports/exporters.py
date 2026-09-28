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
}

STATUS_LABELS = {
    'initiated': 'Iniciada', 'ringing': 'Timbrando', 'answered': 'Contestada',
    'completed': 'Completada', 'busy': 'Ocupado', 'no_answer': 'No contestada',
    'failed': 'Fallida', 'cancelled': 'Cancelada', 'voicemail': 'Buzón',
    'abandoned': 'Abandonada', 'transferred': 'Transferida',
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


BUILDERS = {
    'calls': build_calls,
    'agents': build_agents,
    'daily': build_daily,
    'queues': build_queues,
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
