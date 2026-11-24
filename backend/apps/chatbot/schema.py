"""
Formato y validación de la definición de un flujo (lo que guarda el designer).

{
  "start": "n1",
  "nodes": [ {"id": "n1", "type": "message", "data": {...}, "position": {"x": 0, "y": 0}}, ... ],
  "edges": [ {"id": "e1", "source": "n1", "sourceHandle": "next", "target": "n2"}, ... ]
}

Salidas (sourceHandle) por tipo de bloque:
  message, question, set_variable, handoff(no tiene)  → next
  question                                            → next, invalid
  buttons / list                                      → opt:<id de la opción>
  dynamic_list                                        → next, empty
  condition                                           → true, false
  business_hours                                      → open, closed
  connector                                           → success, empty, error
  ai_intent                                           → intent:<id>, unknown, error
  end, handoff                                        → (ninguna)
"""
import re

NODE_TYPES = {
    'message': {'next'},
    'buttons': None,          # salidas dinámicas: opt:<id>
    'list': None,
    'question': {'next', 'invalid'},
    'condition': {'true', 'false'},
    'business_hours': {'open', 'closed'},
    'set_variable': {'next'},
    'connector': {'success', 'empty', 'error'},
    'dynamic_list': {'next', 'empty'},
    'ai_intent': None,        # salidas dinámicas: intent:<id> + unknown + error
    'analyze_file': None,     # success|unreadable|error  (classify: cat:<id> + unknown)
    'kb_answer': {'answered', 'not_found', 'error'},
    'handoff': set(),
    'end': set(),
}
WAITING_TYPES = {'buttons', 'list', 'question', 'dynamic_list'}
VALIDATIONS = {'text', 'number', 'email', 'phone', 'date', 'document', 'regex'}
ACCEPT_TYPES = {'text', 'image', 'document', 'image_or_document', 'audio', 'file'}
FILE_MODES = {'ocr', 'extract', 'classify', 'vision'}
OPERATORS = {'equals', 'not_equals', 'contains', 'empty', 'not_empty', 'gt', 'lt'}
VAR_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,40}$')
MAX_NODES = 200
MAX_TEXT = 1024


def node_map(definition: dict) -> dict:
    return {n.get('id'): n for n in (definition or {}).get('nodes', []) if n.get('id')}


def outgoing(definition: dict, node_id: str, handle: str):
    """Destino de la salida `handle` de un nodo, o None."""
    for e in (definition or {}).get('edges', []):
        if e.get('source') == node_id and (e.get('sourceHandle') or 'next') == handle:
            return e.get('target')
    return None


def option_handles(node: dict):
    data = node.get('data') or {}
    if node.get('type') == 'ai_intent':
        return {f"intent:{i.get('id')}" for i in data.get('intents', [])} | {'unknown', 'error'}
    if node.get('type') == 'analyze_file':
        if data.get('mode') == 'classify':
            return {f"cat:{c.get('id')}" for c in data.get('categories', [])} | {'unknown', 'unreadable', 'error'}
        return {'success', 'unreadable', 'error'}
    return {f"opt:{o.get('id')}" for o in data.get('options', [])}


def validate_definition(d: dict, *, connectors_ids=None, ai_ids=None) -> list:
    """Devuelve una lista de errores legibles (vacía = válido)."""
    errors = []
    if not isinstance(d, dict):
        return ['La definición debe ser un objeto JSON']
    nodes = d.get('nodes') or []
    edges = d.get('edges') or []
    if not nodes:
        return ['El flujo no tiene bloques']
    if len(nodes) > MAX_NODES:
        errors.append(f'Máximo {MAX_NODES} bloques por flujo')

    ids = [n.get('id') for n in nodes]
    if len(ids) != len(set(ids)):
        errors.append('Hay bloques con el mismo id')
    nmap = node_map(d)
    start = d.get('start')
    if not start or start not in nmap:
        errors.append('Falta el bloque de inicio')

    for n in nodes:
        nid, ntype, data = n.get('id'), n.get('type'), n.get('data') or {}
        label = data.get('title') or nid
        if ntype not in NODE_TYPES:
            errors.append(f'Bloque "{label}": tipo desconocido "{ntype}"')
            continue
        text = data.get('text', '')
        if text and len(text) > MAX_TEXT:
            errors.append(f'Bloque "{label}": el texto supera {MAX_TEXT} caracteres')
        if ntype in ('message', 'buttons', 'list', 'question', 'dynamic_list') and not (text or '').strip():
            errors.append(f'Bloque "{label}": falta el texto')

        if ntype in ('buttons', 'list'):
            opts = data.get('options') or []
            limit = 3 if ntype == 'buttons' else 10
            if not opts:
                errors.append(f'Bloque "{label}": agregue al menos una opción')
            if len(opts) > limit:
                errors.append(f'Bloque "{label}": máximo {limit} opciones')
            oids = [o.get('id') for o in opts]
            if len(oids) != len(set(oids)):
                errors.append(f'Bloque "{label}": opciones repetidas')
            for o in opts:
                if not (o.get('label') or '').strip():
                    errors.append(f'Bloque "{label}": hay una opción sin texto')

        if ntype in ('question', 'dynamic_list', 'set_variable') or (ntype in ('buttons', 'list') and data.get('variable')):
            var = data.get('variable') or ''
            if not VAR_RE.match(var):
                errors.append(f'Bloque "{label}": nombre de variable inválido "{var}"')
        if ntype == 'question' and data.get('validation', 'text') not in VALIDATIONS:
            errors.append(f'Bloque "{label}": validación desconocida')
        if ntype == 'question' and data.get('validation') == 'regex':
            try:
                re.compile(data.get('pattern') or '')
            except re.error:
                errors.append(f'Bloque "{label}": expresión regular inválida')
        if ntype == 'condition':
            rules = data.get('rules') or []
            if not rules:
                errors.append(f'Bloque "{label}": agregue al menos una regla')
            for r in rules:
                if r.get('operator') not in OPERATORS:
                    errors.append(f'Bloque "{label}": operador inválido')
        if ntype == 'connector':
            if not data.get('connector_id') or not data.get('action'):
                errors.append(f'Bloque "{label}": elija conector y acción')
            elif connectors_ids is not None and int(data['connector_id']) not in connectors_ids:
                errors.append(f'Bloque "{label}": el conector no existe o está inactivo')
            if data.get('output_variable') and not VAR_RE.match(data['output_variable']):
                errors.append(f'Bloque "{label}": variable de resultado inválida')
        if ntype == 'ai_intent':
            if not data.get('provider_id'):
                errors.append(f'Bloque "{label}": elija el proveedor de IA')
            elif ai_ids is not None and int(data['provider_id']) not in ai_ids:
                errors.append(f'Bloque "{label}": el proveedor de IA no existe o está inactivo')
            intents = data.get('intents') or []
            if not 1 <= len(intents) <= 20:
                errors.append(f'Bloque "{label}": defina entre 1 y 20 intenciones')
            iids = [i.get('id') for i in intents]
            if len(iids) != len(set(iids)) or any(not VAR_RE.match(str(i or '')) for i in iids):
                errors.append(f'Bloque "{label}": cada intención necesita un id único (letras, números y _)')
            for i in intents:
                if not (i.get('name') or '').strip():
                    errors.append(f'Bloque "{label}": hay una intención sin nombre')
            for f in data.get('fields') or []:
                if not VAR_RE.match(str(f.get('name') or '')):
                    errors.append(f'Bloque "{label}": nombre de dato a extraer inválido "{f.get("name")}"')
            if data.get('source') == 'variable' and not data.get('source_variable'):
                errors.append(f'Bloque "{label}": indique la variable con el texto a analizar')
            if not VAR_RE.match(data.get('output_variable') or ''):
                errors.append(f'Bloque "{label}": variable de resultado inválida')
            if data.get('source', 'wait') == 'wait' and not (data.get('text') or '').strip():
                errors.append(f'Bloque "{label}": falta la pregunta para el cliente')
        if ntype == 'kb_answer':
            if data.get('provider_id') and ai_ids is not None and int(data['provider_id']) not in ai_ids:
                errors.append(f'Bloque "{label}": el proveedor de IA no existe o está inactivo')
            if not isinstance(data.get('kb_ids') or [], list):
                errors.append(f'Bloque "{label}": bases de conocimiento inválidas')
            if data.get('source') == 'variable' and not data.get('source_variable'):
                errors.append(f'Bloque "{label}": indique la variable con la pregunta')
            if (data.get('source') or 'wait') == 'wait' and not (data.get('text') or '').strip():
                errors.append(f'Bloque "{label}": falta el texto que invita a preguntar')
            if not VAR_RE.match(data.get('output_variable') or ''):
                errors.append(f'Bloque "{label}": variable de resultado inválida')
        if ntype == 'question' and (data.get('accept') or 'text') not in ACCEPT_TYPES:
            errors.append(f'Bloque "{label}": tipo de respuesta desconocido')
        if ntype == 'analyze_file':
            mode = data.get('mode') or 'ocr'
            if mode not in FILE_MODES:
                errors.append(f'Bloque "{label}": modo de análisis desconocido')
            if not VAR_RE.match(data.get('source_variable') or ''):
                errors.append(f'Bloque "{label}": indique la variable del archivo (la de la Pregunta que lo pidió)')
            if mode in ('extract', 'classify', 'vision'):
                if not data.get('provider_id'):
                    errors.append(f'Bloque "{label}": elija el proveedor de IA')
                elif ai_ids is not None and int(data['provider_id']) not in ai_ids:
                    errors.append(f'Bloque "{label}": el proveedor de IA no existe o está inactivo')
            if mode == 'extract' and not data.get('fields'):
                errors.append(f'Bloque "{label}": indique qué datos extraer')
            if mode == 'classify':
                cats = data.get('categories') or []
                cids = [c.get('id') for c in cats]
                if not cats or len(cids) != len(set(cids)) or any(not VAR_RE.match(str(c or '')) for c in cids):
                    errors.append(f'Bloque "{label}": defina categorías con id único')
            for f in data.get('fields') or []:
                if not VAR_RE.match(str(f.get('name') or '')):
                    errors.append(f'Bloque "{label}": nombre de dato a extraer inválido "{f.get("name")}"')
            if not VAR_RE.match(data.get('output_variable') or ''):
                errors.append(f'Bloque "{label}": variable de resultado inválida')
        if ntype == 'dynamic_list' and not data.get('source_variable'):
            errors.append(f'Bloque "{label}": indique la variable con la lista')

        # Salidas
        allowed = NODE_TYPES[ntype] if NODE_TYPES[ntype] is not None else option_handles(n)
        used = {(e.get('sourceHandle') or 'next') for e in edges if e.get('source') == nid}
        for h in used - allowed:
            errors.append(f'Bloque "{label}": salida "{h}" no válida')
        required = {'next'} & allowed if ntype in ('message', 'set_variable') else set()
        if ntype in ('buttons', 'list'):
            required = allowed
        for h in required - used:
            errors.append(f'Bloque "{label}": la salida "{h.replace("opt:", "opción ")}" no está conectada')

    for e in edges:
        if e.get('source') not in nmap or e.get('target') not in nmap:
            errors.append('Hay una conexión hacia un bloque que no existe')
            break

    # Bloques inalcanzables desde el inicio
    if start in nmap:
        seen, stack = set(), [start]
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(e.get('target') for e in edges if e.get('source') == cur)
        orphans = [nmap[i].get('data', {}).get('title') or i for i in nmap if i not in seen]
        if orphans:
            errors.append('Bloques sin conexión desde el inicio: ' + ', '.join(orphans[:5]))

    # Bucles sin espera (el bot quedaría enviando mensajes sin fin)
    for nid in nmap:
        if _non_waiting_cycle(d, nmap, nid):
            errors.append(f'Hay un ciclo sin preguntas que pasa por "{nmap[nid].get("data", {}).get("title") or nid}"')
            break
    return errors


def _non_waiting_cycle(d, nmap, start):
    stack, seen = [(start, 0)], set()
    while stack:
        cur, depth = stack.pop()
        node = nmap.get(cur)
        if not node or node.get('type') in WAITING_TYPES or node.get('type') in ('connector', 'ai_intent', 'analyze_file', 'kb_answer'):
            continue
        for e in d.get('edges', []):
            if e.get('source') != cur:
                continue
            t = e.get('target')
            if t == start:
                return True
            if (t, depth) not in seen and depth < 60:
                seen.add((t, depth))
                stack.append((t, depth + 1))
    return False
