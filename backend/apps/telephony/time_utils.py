"""
Evaluación de condiciones horarias (TimeCondition) desde Python.

time_groups: [{name, days, start_time, end_time}]
  days: 'mon-fri' | 'mon-sat' | 'sat-sun' | 'mon-sun' | 'mon,wed,fri' | 'mon' | 'mon-thu' (rango genérico)
  start_time / end_time: 'HH:MM'. Si end < start el rango cruza la medianoche (ej: 22:00-06:00).

Usa la zona horaria de Django (TIME_ZONE), no la hora del servidor.
"""
from django.utils import timezone

_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


def _expand_days(spec: str):
    spec = (spec or '').strip().lower()
    if not spec or spec in ('all', '*', 'mon-sun'):
        return set(_DAYS)
    result = set()
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            a, b = [p.strip()[:3] for p in part.split('-', 1)]
            if a in _DAYS and b in _DAYS:
                i, j = _DAYS.index(a), _DAYS.index(b)
                rng = _DAYS[i:j + 1] if i <= j else _DAYS[i:] + _DAYS[:j + 1]
                result.update(rng)
        elif part[:3] in _DAYS:
            result.add(part[:3])
    return result


def _hm(value, default):
    try:
        h, m = str(value or default).split(':')[:2]
        return int(h) * 60 + int(m)
    except (ValueError, TypeError):
        h, m = default.split(':')
        return int(h) * 60 + int(m)


def group_matches(group: dict, now=None) -> bool:
    now = timezone.localtime(now or timezone.now())
    day = _DAYS[now.weekday()]
    prev_day = _DAYS[(now.weekday() - 1) % 7]
    days = _expand_days(group.get('days', ''))
    start = _hm(group.get('start_time'), '00:00')
    end = _hm(group.get('end_time'), '23:59')
    minute = now.hour * 60 + now.minute
    if start <= end:
        return day in days and start <= minute <= end
    # Cruza medianoche: la parte de la madrugada pertenece al día anterior
    return (day in days and minute >= start) or (prev_day in days and minute <= end)


def is_open(time_condition, now=None) -> bool:
    """True si ahora está dentro de algún grupo horario. Sin condición o inactiva = abierto."""
    if not time_condition or not getattr(time_condition, 'is_active', True):
        return True
    groups = time_condition.time_groups or []
    if not groups:
        return True
    return any(group_matches(g, now) for g in groups)
