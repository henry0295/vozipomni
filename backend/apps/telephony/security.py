"""
Antifraude de llamadas salientes.

  outbound_policy_dialplan(policy)   → contexto [vozip-outbound-policy] (GoSub desde cada ruta saliente)
  route_policy_gosub(route, policy)  → línea GoSub para una ruta saliente
  publish_policy()                   → copia la política en Redis (telephony:dial_policy) para el marcador
  record_event(...)                  → registra un evento de seguridad y avisa por WebSocket
  apply_policy()                     → regenera dialplan + recarga Asterisk + publica en Redis
  check_alerts()                     → umbrales de fraude (tarea periódica) → eventos + correo

Lo que se controla (todas las llamadas que usan una ruta saliente: WebRTC, click-to-call,
callbacks, conferencias; el marcador aplica la misma política antes de originar):
  - Internacionales (00… o +<otro país>), prefijos bloqueados, lista blanca opcional, longitud máxima
  - Canales simultáneos por troncal (SIPTrunk.max_channels) y total
  - Llamadas por extensión por hora
"""
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

REDIS_POLICY_KEY = 'telephony:dial_policy'
POLICY_CONTEXT = 'vozip-outbound-policy'

REASONS = ('international', 'blocked_prefix', 'not_allowed', 'too_long',
           'trunk_full', 'global_limit', 'extension_rate')


def _policy():
    from .models import TelephonySecurityPolicy
    try:
        return TelephonySecurityPolicy.get()
    except Exception as e:  # tabla aún no migrada
        logger.warning(f"[Seguridad] Política no disponible: {e}")
        return None


def outbound_policy_dialplan(policy=None):
    """Contexto de validación. ARG1=marcado ARG2=número final ARG3=troncal ARG4=máx. canales troncal."""
    policy = policy or _policy()
    lines = [
        '',
        '; ====== POLÍTICA ANTIFRAUDE DE LLAMADAS SALIENTES (generada desde Seguridad y antifraude) ======',
        f'[{POLICY_CONTEXT}]',
        'exten => s,1,NoOp(Politica saliente: ${ARG1} -> ${ARG2} via ${ARG3})',
        ' same => n,Set(LOCAL(raw)=${FILTER(0123456789+,${ARG1})})',
        ' same => n,Set(LOCAL(digits)=${FILTER(0123456789,${ARG1})})',
        ' same => n,Set(LOCAL(final)=${FILTER(0123456789,${ARG2})})',
        ' same => n,Set(LOCAL(src)=${CALLERID(num)})',
    ]
    if policy is None:
        lines += [' same => n,Return()']
    else:
        if policy.max_number_length:
            lines.append(f' same => n,GotoIf($[${{LEN(${{digits}})}} > {int(policy.max_number_length)}]?deny_too_long,1)')
        if policy.block_international:
            cc = ''.join(ch for ch in (policy.home_country_code or '') if ch.isdigit())
            lines.append(' same => n,GotoIf($["${raw:0:2}" = "00"]?deny_international,1)')
            if cc:
                lines.append(f' same => n,GotoIf($["${{raw:0:1}}" = "+" & "${{raw:1:{len(cc)}}}" != "{cc}"]'
                             f'?deny_international,1)')
            else:
                lines.append(' same => n,GotoIf($["${raw:0:1}" = "+"]?deny_international,1)')
        for p in policy.blocked_list:
            n = len(p)
            lines.append(f' same => n,GotoIf($["${{digits:0:{n}}}" = "{p}" | "${{final:0:{n}}}" = "{p}"]'
                         f'?deny_blocked_prefix,1)')
        allowed = policy.allowed_list
        if allowed:
            lines.append(' same => n,Set(LOCAL(ok)=0)')
            for p in allowed:
                lines.append(f' same => n,ExecIf($["${{digits:0:{len(p)}}}" = "{p}"]?Set(LOCAL(ok)=1))')
            lines.append(' same => n,GotoIf($[${ok} = 0]?deny_not_allowed,1)')
        if policy.max_calls_per_extension_hour:
            lines += [
                ' same => n,Set(LOCAL(hk)=${src}_${STRFTIME(${EPOCH},,%Y%m%d%H)})',
                ' same => n,Set(DB(vozip_rate/${hk})=$[0${DB(vozip_rate/${hk})} + 1])',
                f' same => n,GotoIf($[${{DB(vozip_rate/${{hk}})}} > {int(policy.max_calls_per_extension_hour)}]'
                f'?deny_extension_rate,1)',
            ]
        # Canales: GROUP en el canal que marca; se libera al colgar
        lines += [
            ' same => n,Set(GROUP(vozip_trunk)=${ARG3})',
            ' same => n,GotoIf($[0${ARG4} > 0 & ${GROUP_COUNT(${ARG3}@vozip_trunk)} > 0${ARG4}]?deny_trunk_full,1)',
            ' same => n,Set(GROUP(vozip_out)=total)',
        ]
        if policy.max_concurrent_outbound:
            lines.append(f' same => n,GotoIf($[${{GROUP_COUNT(total@vozip_out)}} > {int(policy.max_concurrent_outbound)}]'
                         f'?deny_global_limit,1)')
        lines.append(' same => n,Return()')

    for reason in REASONS:
        lines += [
            f'exten => deny_{reason},1,Set(LOCAL(reason)={reason})',
            ' same => n,Goto(deny,1)',
        ]
    lines += [
        'exten => deny,1,NoOp(LLAMADA BLOQUEADA ${reason}: ${ARG1} via ${ARG3} desde ${src})',
        ' same => n,UserEvent(VozipFraud,Reason: ${reason},Number: ${ARG1},Dialed: ${ARG2},Trunk: ${ARG3},Source: ${src})',
        ' same => n,GotoIf($["${reason}" = "trunk_full" | "${reason}" = "global_limit" | "${reason}" = "extension_rate"]?busy)',
        # Sin contestar la llamada: locución como early media (183) y rechazo con código SIP
        # (21 → 403 bloqueada, 34 → 503 sin canales) para que el softphone muestre el motivo.
        ' same => n,Progress()',
        ' same => n,Playback(ss-noservice,noanswer)',
        ' same => n,Hangup(21)',
        ' same => n(busy),Progress()',
        ' same => n,Playback(all-circuits-busy-now,noanswer)',
        ' same => n,Hangup(34)',
        '',
    ]
    return lines


def route_policy_gosub(route, policy=None):
    policy = policy or _policy()
    max_ch = 0
    if policy is None or policy.enforce_trunk_channels:
        max_ch = int(getattr(route.trunk, 'max_channels', 0) or 0)
    return f" same => n,GoSub({POLICY_CONTEXT},s,1(${{EXTEN}},${{dial_number}},{route.trunk.name},{max_ch}))"


def policy_payload(policy=None):
    from .models import SIPTrunk
    policy = policy or _policy()
    if policy is None:
        return {}
    return {
        'block_international': policy.block_international,
        'home_country_code': policy.home_country_code,
        'blocked_prefixes': policy.blocked_list,
        'allowed_prefixes': policy.allowed_list,
        'max_number_length': policy.max_number_length,
        'max_concurrent_outbound': policy.max_concurrent_outbound,
        'enforce_trunk_channels': policy.enforce_trunk_channels,
        'trunk_limits': {t.name: t.max_channels for t in SIPTrunk.objects.filter(is_active=True)},
        'updated_at': timezone.now().isoformat(),
    }


def publish_policy(policy=None):
    """Guarda la política en Redis para que el marcador la aplique sin consultar la base de datos."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.set(REDIS_POLICY_KEY, json.dumps(policy_payload(policy)))
        return True
    except Exception as e:
        logger.warning(f"[Seguridad] No se pudo publicar la política en Redis: {e}")
        return False


def apply_policy():
    """Regenera el dialplan, recarga Asterisk y publica la política para el marcador."""
    from .asterisk_ami import AsteriskAMI
    from .asterisk_config import AsteriskConfigGenerator
    result = {'dialplan': False, 'reloaded': False, 'published': publish_policy()}
    try:
        AsteriskConfigGenerator().write_all_configs()
        result['dialplan'] = True
        ami = AsteriskAMI()
        if ami.connect():
            result['reloaded'] = bool(ami.reload_dialplan())
            ami.disconnect()
    except Exception as e:
        logger.error(f"[Seguridad] Error aplicando la política: {e}")
        result['error'] = str(e)
    return result


def _push(event):
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer:
            # RealtimeDashboardConsumer.dashboard_update reenvía el evento tal cual al navegador
            async_to_sync(layer.group_send)('dashboard', {
                'type': 'dashboard_update',
                'event': 'security.event',
                'data': {'id': event.id, 'type': event.event_type, 'severity': event.severity,
                         'number': event.number, 'trunk': event.trunk, 'source': event.source},
            })
    except Exception as e:
        logger.debug(f"[Seguridad] No se pudo notificar por WebSocket: {e}")


def record_event(event_type, number='', trunk='', source='', detail='', severity='warning'):
    from .models import TelephonySecurityEvent
    event = TelephonySecurityEvent.objects.create(
        event_type=event_type, number=str(number)[:50], trunk=str(trunk)[:100],
        source=str(source)[:100], detail=str(detail)[:2000], severity=severity,
    )
    logger.warning(f"[Seguridad] {event_type} número={number} troncal={trunk} origen={source} {detail}")
    _push(event)
    return event


def _alert_recipients(policy):
    emails = [e.strip() for e in (policy.alert_emails or '').replace(',', '\n').splitlines() if e.strip()]
    if emails:
        return emails
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return list(User.objects.filter(is_active=True, role='admin').exclude(email='')
                .values_list('email', flat=True)) + \
        list(User.objects.filter(is_active=True, is_superuser=True).exclude(email='')
             .values_list('email', flat=True))


def _notify(policy, event, subject, body):
    from django.core.mail import send_mail
    recipients = sorted(set(_alert_recipients(policy)))
    if not recipients:
        logger.warning(f"[Seguridad] Alerta sin destinatarios: {subject}")
        return
    try:
        send_mail(f'[VozipOmni] {subject}', body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
        event.notified = True
        event.save(update_fields=['notified'])
    except Exception as e:
        logger.error(f"[Seguridad] No se pudo enviar la alerta por correo: {e}")


def _drain_dialer_events(limit=500):
    """El marcador deja sus bloqueos en Redis (telephony:security_events); pasarlos a la base de datos."""
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        for _ in range(limit):
            raw = r.lpop('telephony:security_events')
            if not raw:
                break
            try:
                data = json.loads(raw)
            except ValueError:
                continue
            record_event(data.get('event_type', 'dialer_blocked'), number=data.get('number', ''),
                         trunk=data.get('trunk', ''), source=data.get('source', 'marcador'),
                         detail=data.get('detail', ''), severity='warning')
    except Exception as e:
        logger.warning(f"[Seguridad] No se pudieron leer eventos del marcador: {e}")


def check_alerts():
    """Umbrales de fraude. Cada tipo de alerta se envía como máximo cada 30 minutos."""
    from .models import Call, TelephonySecurityEvent
    policy = _policy()
    if policy is None:
        return 'Sin política'
    publish_policy(policy)  # mantener al marcador con la política vigente

    _drain_dialer_events()

    now = timezone.now()
    fired = []
    outbound = Call.objects.filter(direction='outbound')

    def fire(kind, severity, subject, body):
        if not cache.add(f'telephony:alert:{kind}', 1, timeout=30 * 60):
            return
        event = record_event(kind, detail=body, severity=severity, source='monitor')
        _notify(policy, event, subject, body)
        fired.append(kind)

    if policy.alert_calls_per_10min:
        n = outbound.filter(start_time__gte=now - timedelta(minutes=10)).count()
        if n > policy.alert_calls_per_10min:
            fire('alert_spike', 'critical', 'Pico de llamadas salientes',
                 f'Se registraron {n} llamadas salientes en los últimos 10 minutos '
                 f'(umbral {policy.alert_calls_per_10min}). Revisa si hay uso no autorizado.')

    if policy.alert_international_per_hour:
        recent = outbound.filter(start_time__gte=now - timedelta(hours=1)).values_list('called_number', flat=True)
        intl = [num for num in recent if policy.is_international(num)]
        if len(intl) > policy.alert_international_per_hour:
            sample = ', '.join(sorted(set(intl))[:10])
            fire('alert_international', 'critical', 'Llamadas internacionales',
                 f'{len(intl)} llamadas internacionales en la última hora '
                 f'(umbral {policy.alert_international_per_hour}). Destinos: {sample}')

    if policy.alert_blocked_per_10min:
        blocked = TelephonySecurityEvent.objects.filter(
            created_at__gte=now - timedelta(minutes=10), event_type__in=REASONS + ('dialer_blocked',))
        n = blocked.count()
        if n >= policy.alert_blocked_per_10min:
            sources = ', '.join(sorted({s for s in blocked.values_list('source', flat=True) if s})[:10])
            fire('alert_blocked', 'warning', 'Muchos intentos de llamada bloqueados',
                 f'{n} intentos bloqueados por la política en los últimos 10 minutos. Orígenes: {sources or "—"}')

    return f"Alertas: {', '.join(fired) or 'ninguna'}"
