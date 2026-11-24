"""
Motor del bot.

  handle_inbound(conv, message, created) -> bool
      Enganchado en messaging.routing.ingest_inbound. True = el bot atendió el
      mensaje (no hay que asignar a un agente ni enviar autorrespuestas).

  continue_after_connector(session_id, node_id)
      Lo ejecuta la tarea Celery después de llamar a un sistema externo.

  simulate(definition, inputs, variables=None, live=False)
      Recorre el flujo sin enviar nada (simulador del designer).

El núcleo (`Runner`) no sabe de base de datos ni de canales: recibe un estado
(dict) y un "transporte" que envía las respuestas. Así el bot real y el
simulador ejecutan exactamente la misma lógica.
"""
import logging
import re
import unicodedata
from datetime import datetime, timedelta

from django.utils import timezone

from .schema import WAITING_TYPES, node_map, outgoing

logger = logging.getLogger(__name__)

MAX_STEPS_PER_TURN = 40
MAX_RETRIES = 3
TPL = re.compile(r'\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}')


# ── utilidades ───────────────────────────────────────────────────────────────

def _norm(text) -> str:
    text = unicodedata.normalize('NFD', str(text or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', text).strip().lower()


def _dig(data, path):
    cur = data
    for part in path.split('.'):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
    return cur


def render(text, variables: dict) -> str:
    def rep(m):
        v = _dig(variables, m.group(1))
        return '' if v is None else str(v)
    return TPL.sub(rep, str(text or ''))


def render_value(value, variables):
    if isinstance(value, str):
        full = TPL.fullmatch(value.strip())
        if full:
            v = _dig(variables, full.group(1))
            return '' if v is None else v
        return render(value, variables)
    return value


VALIDATORS = {
    'text': lambda v: bool(v.strip()),
    'number': lambda v: bool(re.fullmatch(r'-?\d+([.,]\d+)?', v.strip())),
    'email': lambda v: bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', v.strip())),
    'phone': lambda v: 7 <= len(re.sub(r'\D', '', v)) <= 15,
    'document': lambda v: bool(re.fullmatch(r'[A-Za-z0-9.\-]{4,20}', v.strip())),
}


def _valid_date(v):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            datetime.strptime(v.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def validate_input(data: dict, value: str) -> bool:
    kind = data.get('validation') or 'text'
    if kind == 'date':
        return _valid_date(value)
    if kind == 'regex':
        try:
            return bool(re.fullmatch(data.get('pattern') or '.*', value.strip()))
        except re.error:
            return False
    return VALIDATORS.get(kind, VALIDATORS['text'])(value)


def eval_rule(rule: dict, variables: dict) -> bool:
    raw = _dig(variables, rule.get('variable') or '')
    left = '' if raw is None else raw
    right = render(rule.get('value', ''), variables)
    op = rule.get('operator')
    if op == 'empty':
        return left in ('', None, [], {})
    if op == 'not_empty':
        return left not in ('', None, [], {})
    if op in ('gt', 'lt'):
        try:
            a, b = float(str(left).replace(',', '.')), float(str(right).replace(',', '.'))
        except ValueError:
            return False
        return a > b if op == 'gt' else a < b
    if op == 'contains':
        return _norm(right) in _norm(left)
    eq = _norm(left) == _norm(right)
    return eq if op == 'equals' else not eq


# ── transportes ──────────────────────────────────────────────────────────────

class Transport:
    """Envía respuestas del bot. Subclases: canal real o simulador."""

    def text(self, body): ...
    def choices(self, body, options, *, kind='buttons', button_label='Ver opciones'): ...
    def handoff(self, state, data): ...
    def end(self, state, data): ...
    def connector(self, state, node): ...
    def is_open(self, data) -> bool:
        return True


class SimTransport(Transport):
    def __init__(self, live=False):
        self.replies = []
        self.live = live

    def text(self, body):
        self.replies.append({'type': 'text', 'text': body})

    def choices(self, body, options, *, kind='buttons', button_label='Ver opciones'):
        self.replies.append({'type': kind, 'text': body, 'button': button_label,
                             'options': [{'id': o['id'], 'label': o['label'],
                                          'description': o.get('description', '')} for o in options]})

    def handoff(self, state, data):
        self.replies.append({'type': 'system', 'text': 'Conversación pasada a un asesor'
                             + (f" (campaña {data.get('campaign_id')})" if data.get('campaign_id') else '')})

    def end(self, state, data):
        self.replies.append({'type': 'system', 'text': 'Conversación cerrada por el bot'})

    def connector(self, state, node):
        """Simulador: ejecuta el conector en línea (live) o devuelve un resultado de prueba."""
        data = node.get('data') or {}
        if not self.live:
            self.replies.append({'type': 'system', 'text': f"[Conector] {data.get('action')} → éxito (simulado)"})
            return 'success', data.get('mock_result') or {}
        from .models import Connector
        from .connectors import get_connector
        try:
            conn = Connector.objects.get(pk=data.get('connector_id'), is_active=True)
        except Connector.DoesNotExist:
            return 'error', None
        params = {k: render_value(v, state['variables']) for k, v in (data.get('inputs') or {}).items()}
        res = get_connector(conn).execute(data['action'], params, source='simulator')
        self.replies.append({'type': 'system', 'text': f"[Conector] {data.get('action')} → {res.status}"
                             + (f": {res.error}" if res.error else '')})
        return res.status, res.data


# ── núcleo ───────────────────────────────────────────────────────────────────

class Runner:
    """
    state = {"current": id, "waiting": bool, "variables": {}, "path": [], "retries": 0,
             "status": "active|busy|handed_off|completed"}
    """

    def __init__(self, definition, state, transport: Transport):
        self.d = definition
        self.nodes = node_map(definition)
        self.state = state
        self.t = transport
        self.state.setdefault('variables', {})
        self.state.setdefault('path', [])
        self.state.setdefault('retries', 0)

    @property
    def vars(self):
        return self.state['variables']

    # Avanza desde un nodo hasta que haga falta esperar al cliente o se termine
    def run_from(self, node_id):
        steps = 0
        while node_id and steps < MAX_STEPS_PER_TURN:
            steps += 1
            node = self.nodes.get(node_id)
            if not node:
                break
            self.state['current'] = node_id
            self.state['waiting'] = False
            if not self.state['path'] or self.state['path'][-1] != node_id:
                self.state['path'] = (self.state['path'] + [node_id])[-50:]
            node_id = self._execute(node)
            if self.state.get('status') in ('handed_off', 'completed', 'busy') or self.state.get('waiting'):
                return
        if steps >= MAX_STEPS_PER_TURN:
            logger.warning('[Bot] Demasiados pasos seguidos: se pasa a un asesor')
            self._handoff({'text': ''})

    def start(self):
        self.state.update({'status': 'active', 'retries': 0})
        self.run_from(self.d.get('start'))

    def _out(self, node, handle='next'):
        return outgoing(self.d, node['id'], handle)

    def _execute(self, node):
        ntype, data = node.get('type'), node.get('data') or {}
        text = render(data.get('text', ''), self.vars)

        if ntype == 'message':
            if text:
                self.t.text(text)
            return self._out(node)

        if ntype in ('buttons', 'list'):
            opts = [{'id': f"opt:{o['id']}", 'label': render(o['label'], self.vars),
                     'description': render(o.get('description', ''), self.vars)}
                    for o in data.get('options') or []]
            self.t.choices(text, opts, kind=ntype, button_label=data.get('button_label') or 'Ver opciones')
            self.state['waiting'] = True
            self.state['options'] = opts
            return None

        if ntype == 'dynamic_list':
            items = _dig(self.vars, data.get('source_variable') or '') or []
            if isinstance(items, dict):
                items = [items]
            if not isinstance(items, list) or not items:
                return self._out(node, 'empty')
            label_f, desc_f = data.get('label_field') or 'name', data.get('description_field') or ''
            opts = []
            for i, it in enumerate(items[:10]):
                label = render(label_f, it) if '{{' in label_f else (it.get(label_f) if isinstance(it, dict) else it)
                desc = (render(desc_f, it) if '{{' in desc_f else (it.get(desc_f, '') if isinstance(it, dict) else '')) if desc_f else ''
                opts.append({'id': f'item:{i}', 'label': str(label or f'Opción {i + 1}'), 'description': str(desc or '')})
            self.state['items'] = items[:10]
            self.state['options'] = opts
            self.t.choices(text, opts, kind='list', button_label=data.get('button_label') or 'Ver opciones')
            self.state['waiting'] = True
            return None

        if ntype == 'question':
            self.t.text(text)
            self.state['waiting'] = True
            return None

        if ntype == 'condition':
            rules = data.get('rules') or []
            results = [eval_rule(r, self.vars) for r in rules]
            ok = all(results) if (data.get('match') or 'all') == 'all' else any(results)
            return self._out(node, 'true' if ok else 'false')

        if ntype == 'business_hours':
            return self._out(node, 'open' if self.t.is_open(data) else 'closed')

        if ntype == 'set_variable':
            self.vars[data['variable']] = render_value(data.get('value', ''), self.vars)
            return self._out(node)

        if ntype == 'connector':
            if text:
                self.t.text(text)
            res = self.t.connector(self.state, node)
            if res is None:            # ejecución asíncrona (Celery): se continúa después
                self.state['status'] = 'busy'
                return None
            status, result = res
            return self.apply_connector_result(node, status, result)

        if ntype == 'handoff':
            self._handoff(data, text)
            return None

        if ntype == 'end':
            if text:
                self.t.text(text)
            self.state['status'] = 'completed'
            self.t.end(self.state, data)
            return None
        return None

    def apply_connector_result(self, node, status, result):
        data = node.get('data') or {}
        if data.get('output_variable') and status != 'error':
            self.vars[data['output_variable']] = result
        self.vars['_last_error'] = '' if status != 'error' else 'error'
        self.state['status'] = 'active'
        target = self._out(node, status) or (self._out(node, 'success') if status == 'empty' else None)
        return target

    def _handoff(self, data, text=''):
        if text:
            self.t.text(text)
        self.state['status'] = 'handed_off'
        self.t.handoff(self.state, data)

    # Procesa la respuesta del cliente al nodo en espera
    def receive(self, value: str, reply_id: str = ''):
        node = self.nodes.get(self.state.get('current'))
        if not node or not self.state.get('waiting'):
            return self.start()
        ntype, data = node['type'], node.get('data') or {}

        if ntype in ('buttons', 'list', 'dynamic_list'):
            chosen = self._match_option(value, reply_id)
            if chosen is None:
                return self._retry(node, data.get('invalid_text') or 'Opción no válida. Elija una de la lista.')
            self.state['retries'] = 0
            if ntype == 'dynamic_list':
                idx = int(chosen['id'].split(':')[1])
                item = self.state.get('items', [])[idx] if idx < len(self.state.get('items', [])) else None
                self.vars[data['variable']] = item
                return self.run_from(self._out(node))
            if data.get('variable'):
                self.vars[data['variable']] = chosen['label']
            return self.run_from(self._out(node, chosen['id']))

        if ntype == 'question':
            if not validate_input(data, value or ''):
                return self._retry(node, data.get('error_text') or 'El dato no es válido, intente de nuevo.',
                                   handle='invalid')
            self.state['retries'] = 0
            self.vars[data['variable']] = (value or '').strip()
            return self.run_from(self._out(node))
        return self.start()

    def _match_option(self, value, reply_id):
        opts = self.state.get('options') or []
        if reply_id:
            for o in opts:
                if o['id'] == reply_id:
                    return o
        v = _norm(value)
        if v.isdigit() and 1 <= int(v) <= len(opts):
            return opts[int(v) - 1]
        for o in opts:
            if _norm(o['label']) == v:
                return o
        return None

    def _retry(self, node, msg, handle=None):
        self.state['retries'] = self.state.get('retries', 0) + 1
        limit = int((node.get('data') or {}).get('max_retries') or MAX_RETRIES)
        if self.state['retries'] >= limit:
            self.state['retries'] = 0
            target = self._out(node, handle) if handle else None
            if target:
                return self.run_from(target)
            return self._handoff({}, 'No logré entenderte. Te comunico con un asesor.')
        self.t.text(msg)
        # Repetir la pregunta / menú
        self.run_from(node['id'])


# ── transporte real (canales de messaging) ───────────────────────────────────

class ChannelTransport(Transport):
    def __init__(self, conversation, session):
        self.conv = conversation
        self.session = session
        self.pending_connector = None

    def _send(self, body, **kw):
        from apps.messaging.whatsapp import create_outbound
        create_outbound(self.conv, body=body, sender=None, system=True, enforce_window=False,
                        metadata={'bot': True, **(kw.pop('metadata', {}) or {})}, **kw)

    def text(self, body):
        if body:
            self._send(body)

    def choices(self, body, options, *, kind='buttons', button_label='Ver opciones'):
        if self.conv.channel.channel_type == 'whatsapp':
            interactive = build_whatsapp_interactive(body, options, kind, button_label)
            self._send(body, message_type='interactive',
                       metadata={'interactive': interactive, 'options': options})
        else:
            lines = [body, ''] + [f"{i}. {o['label']}" for i, o in enumerate(options, start=1)]
            self._send('\n'.join(lines), metadata={'options': options})

    def is_open(self, data):
        from apps.messaging.routing import config_for_channel, is_open_now
        from apps.telephony.time_utils import is_open
        tc_id = data.get('time_condition_id')
        if tc_id:
            try:
                from apps.telephony.models import TimeCondition
                return is_open(TimeCondition.objects.filter(pk=tc_id).first())
            except Exception:
                return True
        cfg = config_for_channel(self.conv.channel)
        return is_open_now(cfg) if cfg is not None else True

    def handoff(self, state, data):
        from apps.messaging.realtime import push
        from apps.messaging.routing import auto_assign, config_for_channel
        conv = self.conv
        meta = dict(conv.metadata or {})
        meta['bot'] = {
            'flow_id': self.session.flow_id, 'version': getattr(self.session.version, 'number', None),
            'path': state.get('path', [])[-20:],
            'variables': {k: v for k, v in state.get('variables', {}).items()
                          if not k.startswith('_') and not isinstance(v, (list, dict))},
            'note': render(data.get('note', ''), state.get('variables', {})),
        }
        conv.metadata = meta
        fields = ['metadata']
        if data.get('campaign_id'):
            conv.campaign_id = int(data['campaign_id'])
            fields.append('campaign')
        conv.save(update_fields=fields)
        auto_assign(conv)
        push(conv, 'conversation.bot_handoff', {'conversation_id': conv.id}, also_unassigned=True)

    def end(self, state, data):
        conv = self.conv
        conv.status = 'closed'
        conv.closed_at = timezone.now()
        conv.closed_reason = 'bot'
        conv.save(update_fields=['status', 'closed_at', 'closed_reason'])

    def connector(self, state, node):
        # Se ejecuta en Celery para no demorar el webhook del canal. El envío de la
        # tarea se hace en _persist(), DESPUÉS de guardar la sesión como "busy".
        self.pending_connector = node['id']
        return None


def build_whatsapp_interactive(body, options, kind, button_label):
    """Mensaje interactivo nativo de WhatsApp (botones: máx. 3 · lista: máx. 10)."""
    body = (body or ' ')[:1024]
    if kind == 'buttons' and len(options) <= 3:
        return {'type': 'button', 'body': {'text': body}, 'action': {'buttons': [
            {'type': 'reply', 'reply': {'id': o['id'][:256], 'title': o['label'][:20]}} for o in options
        ]}}
    return {'type': 'list', 'body': {'text': body}, 'action': {
        'button': (button_label or 'Ver opciones')[:20],
        'sections': [{'title': 'Opciones', 'rows': [
            {'id': o['id'][:200], 'title': o['label'][:24],
             **({'description': o['description'][:72]} if o.get('description') else {})}
            for o in options[:10]
        ]}],
    }}


# ── persistencia ─────────────────────────────────────────────────────────────

def _state_from(session):
    return {'current': session.current_node, 'waiting': session.waiting, 'variables': session.variables or {},
            'path': session.path or [], 'retries': session.retries, 'status': session.status,
            'options': (session.variables or {}).get('_options', []),
            'items': (session.variables or {}).get('_items', [])}


def _save_state(session, state):
    variables = dict(state.get('variables') or {})
    variables['_options'] = state.get('options', [])
    variables['_items'] = state.get('items', [])
    session.current_node = state.get('current') or ''
    session.waiting = bool(state.get('waiting'))
    session.variables = variables
    session.path = state.get('path', [])
    session.retries = state.get('retries', 0)
    session.status = state.get('status', 'active')
    session.last_activity_at = timezone.now()
    session.save()


def _persist(session, runner):
    """Guarda el estado y, si quedó un conector pendiente, lo envía a Celery."""
    _save_state(session, runner.state)
    pending = getattr(runner.t, 'pending_connector', None)
    if pending:
        runner.t.pending_connector = None
        from .tasks import run_connector_step
        try:
            run_connector_step.delay(session.id, pending)
        except Exception:
            logger.exception('[Bot] No se pudo encolar el conector: se ejecuta en línea')
            continue_after_connector(session.id, pending)


def _initial_variables(conv):
    contact = conv.contact
    return {
        'contact': {
            'name': conv.contact_name or (f'{contact.first_name} {contact.last_name}'.strip() if contact else ''),
            'phone': conv.contact_identifier if conv.channel.channel_type == 'whatsapp' else (contact.phone if contact else ''),
            'email': contact.email if contact else '',
            'id': contact.id if contact else None,
        },
        'channel': {'type': conv.channel.channel_type, 'name': conv.channel.name},
        'conversation_id': conv.id,
    }


def active_flow_for(channel):
    from .models import BotFlow
    return (BotFlow.objects.filter(is_active=True, channels=channel, published_version__isnull=False)
            .select_related('published_version').order_by('-updated_at').first())


def handle_inbound(conv, message, created) -> bool:
    """True si el bot atendió el mensaje."""
    from .models import BotSession
    try:
        if conv.agent_id:
            return False
        session = BotSession.objects.filter(conversation=conv).select_related('version', 'flow').first()

        if session and session.status in ('handed_off', 'error'):
            return False
        if session and session.status == 'busy':
            # Esperando a un sistema externo: no procesar otra entrada todavía
            if session.last_activity_at > timezone.now() - timedelta(minutes=2):
                return True
            session.status = 'active'

        flow = session.flow if session and session.flow_id else None
        timeout = (flow.session_timeout_minutes if flow else 30) or 30
        expired = session and session.last_activity_at < timezone.now() - timedelta(minutes=timeout)

        if not session or session.status in ('completed', 'timeout') or expired:
            flow = active_flow_for(conv.channel)
            if not flow:
                return False
            if session:
                session.delete()
            session = BotSession.objects.create(conversation=conv, flow=flow, version=flow.published_version,
                                                variables=_initial_variables(conv))
            runner = Runner(session.version.definition, _state_from(session), ChannelTransport(conv, session))
            runner.start()
            _persist(session, runner)
            return True

        if not session.version:
            return False
        if message.message_type not in ('text', 'interactive', 'button'):
            # Adjuntos, audios, ubicación: el bot no los entiende → asesor
            runner = Runner(session.version.definition, _state_from(session), ChannelTransport(conv, session))
            runner._handoff({}, 'Recibí tu archivo. Te comunico con un asesor.')
            _persist(session, runner)
            return True

        reply_id = (message.metadata or {}).get('reply_id') or (message.metadata or {}).get('payload') or ''
        runner = Runner(session.version.definition, _state_from(session), ChannelTransport(conv, session))
        runner.receive(message.body or '', reply_id)
        _persist(session, runner)
        return True
    except Exception:
        logger.exception(f'[Bot] Error en conversación {getattr(conv, "id", "?")}: se pasa a un asesor')
        try:
            from .models import BotSession
            BotSession.objects.filter(conversation=conv).update(status='error')
        except Exception:
            pass
        return False


def continue_after_connector(session_id, node_id):
    from apps.messaging.routing import auto_assign
    from .connectors import get_connector
    from .models import BotSession, Connector

    session = BotSession.objects.select_related('conversation', 'version', 'conversation__channel').filter(
        pk=session_id).first()
    if not session or not session.version or session.status != 'busy':
        return
    conv = session.conversation
    runner = Runner(session.version.definition, _state_from(session), ChannelTransport(conv, session))
    node = runner.nodes.get(node_id)
    if not node:
        return
    data = node.get('data') or {}
    status, result = 'error', None
    conn = Connector.objects.filter(pk=data.get('connector_id'), is_active=True).first()
    if conn:
        params = {k: render_value(v, runner.vars) for k, v in (data.get('inputs') or {}).items()}
        res = get_connector(conn).execute(data.get('action'), params, conversation_id=conv.id)
        status, result = res.status, res.data
    try:
        target = runner.apply_connector_result(node, status, result)
        if target:
            runner.run_from(target)
        elif status == 'error':
            runner._handoff({}, 'No pude consultar la información en este momento. Te comunico con un asesor.')
        _persist(session, runner)
    except Exception:
        logger.exception(f'[Bot] Error continuando tras conector en conv {conv.id}')
        session.status = 'error'
        session.save(update_fields=['status'])
        auto_assign(conv)


def simulate(definition, inputs, variables=None, live=False):
    """Devuelve la lista de turnos [{input, replies, state}] del simulador."""
    t = SimTransport(live=live)
    state = {'variables': {'contact': {'name': 'Cliente de prueba', 'phone': '573000000000', 'email': ''},
                           'channel': {'type': 'whatsapp', 'name': 'Simulador'}, **(variables or {})}}
    runner = Runner(definition, state, t)
    turns = []
    runner.start()
    turns.append({'input': None, 'replies': t.replies})
    for item in inputs or []:
        if runner.state.get('status') in ('handed_off', 'completed'):
            break
        t.replies = []
        value = item.get('text', '') if isinstance(item, dict) else str(item)
        reply_id = item.get('reply_id', '') if isinstance(item, dict) else ''
        runner.receive(value, reply_id)
        turns.append({'input': value, 'replies': t.replies})
    public = {k: v for k, v in runner.state['variables'].items() if not k.startswith('_')}
    return {'turns': turns, 'status': runner.state.get('status'), 'current': runner.state.get('current'),
            'waiting': runner.state.get('waiting'), 'variables': public,
            'options': runner.state.get('options') if runner.state.get('waiting') else []}
