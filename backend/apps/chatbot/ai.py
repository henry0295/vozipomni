"""
Inteligencia artificial para el bot.

  classify(provider, text, intents, fields, ...)  → intención + datos extraídos
  test_provider(provider)                         → prueba de conexión

Proveedores: OpenAI, Azure OpenAI y cualquier API compatible con OpenAI
(Ollama, vLLM, LM Studio, Gemini con su endpoint compatible).

Privacidad: si el proveedor tiene `mask_personal_data`, antes de enviar el texto
se reemplazan documentos, teléfonos, emails y tarjetas por marcadores
([DOC_1], [TEL_1]…). Los datos que la IA devuelva con esos marcadores se
restauran localmente: el valor real nunca sale del servidor.
"""
import json
import logging
import re
import time

import requests
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class AIError(Exception):
    pass


# ── enmascarado de datos personales ──────────────────────────────────────────

_PII = [
    ('EMAIL', re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')),
    ('TARJETA', re.compile(r'\b(?:\d[ -]?){13,19}\b')),
    ('TEL', re.compile(r'(?<!\d)(?:\+?57[ -]?)?3\d{2}[ -]?\d{3}[ -]?\d{4}(?!\d)')),
    ('DOC', re.compile(r'(?<!\d)\d{1,3}(?:[.\s]?\d{3}){1,3}(?!\d)|(?<!\d)\d{6,12}(?!\d)')),
]


def mask(text: str):
    mapping = {}
    counters = {}

    def repl(kind):
        def _r(m):
            value = m.group(0)
            for k, v in mapping.items():
                if v == value:
                    return k
            counters[kind] = counters.get(kind, 0) + 1
            key = f'[{kind}_{counters[kind]}]'
            mapping[key] = value
            return key
        return _r

    for kind, rx in _PII:
        text = rx.sub(repl(kind), text)
    return text, mapping


def unmask(value, mapping):
    if isinstance(value, str):
        for k, v in mapping.items():
            value = value.replace(k, v)
        return value
    if isinstance(value, dict):
        return {k: unmask(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [unmask(v, mapping) for v in value]
    return value


# ── cliente ──────────────────────────────────────────────────────────────────

def _endpoint(p):
    if p.provider_type == 'azure_openai':
        base = (p.base_url or '').rstrip('/')
        return (f'{base}/openai/deployments/{p.model}/chat/completions?api-version={p.api_version or "2024-06-01"}',
                {'api-key': p.api_key or ''})
    base = (p.base_url or 'https://api.openai.com/v1').rstrip('/')
    if not base.endswith('/v1') and p.provider_type == 'openai':
        base += '/v1'
    headers = {'Authorization': f'Bearer {p.api_key}'} if p.api_key else {}
    return f'{base}/chat/completions', headers


def _check_budget(p):
    if not p.monthly_token_limit:
        return
    start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = p.usage.filter(created_at__gte=start).aggregate(
        t=Sum('prompt_tokens') + Sum('completion_tokens'))['t'] or 0
    if used >= p.monthly_token_limit:
        raise AIError('Se alcanzó el límite mensual de tokens del proveedor')


def chat_json(p, system: str, user: str):
    """Llama al modelo pidiendo JSON. Devuelve (dict, usage)."""
    url, headers = _endpoint(p)
    body = {'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            'temperature': p.temperature, 'response_format': {'type': 'json_object'}}
    if p.provider_type != 'azure_openai':
        body['model'] = p.model
    resp = requests.post(url, json=body, headers={'Content-Type': 'application/json', **headers},
                         timeout=max(5, min(p.timeout_seconds or 30, 120)))
    if resp.status_code == 400 and 'response_format' in resp.text:
        body.pop('response_format')  # proveedores sin modo JSON
        resp = requests.post(url, json=body, headers={'Content-Type': 'application/json', **headers},
                             timeout=max(5, min(p.timeout_seconds or 30, 120)))
    if resp.status_code >= 400:
        raise AIError(f'HTTP {resp.status_code}: {resp.text[:300]}')
    data = resp.json()
    content = ((data.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
    match = re.search(r'\{.*\}', content, re.S)
    if not match:
        raise AIError('El modelo no devolvió JSON')
    try:
        parsed = json.loads(match.group(0))
    except ValueError:
        raise AIError('El modelo devolvió un JSON inválido')
    return parsed, data.get('usage') or {}


def _log(p, purpose, status, usage, t0, result='', error='', conversation_id=None):
    from .models import AIUsageLog
    try:
        AIUsageLog.objects.create(
            provider=p, purpose=purpose, status=status,
            prompt_tokens=int(usage.get('prompt_tokens') or 0),
            completion_tokens=int(usage.get('completion_tokens') or 0),
            duration_ms=int((time.monotonic() - t0) * 1000), result=result[:120], error=error[:1000],
            conversation_id=conversation_id)
    except Exception:
        logger.exception('[IA] No se pudo guardar el uso')


SYSTEM_PROMPT = """Eres el clasificador de un asistente de atención al cliente en español.
Tu única tarea es leer el mensaje del cliente y responder SOLO un objeto JSON:
{{"intent": "<id de la intención o null>", "confidence": <0 a 1>, "fields": {{...}}}}

Intenciones posibles:
{intents}

{fields_block}Reglas:
- Elige la intención que mejor describa lo que el cliente quiere. Si ninguna aplica, "intent": null.
- No inventes datos: si un campo no aparece en el mensaje, déjalo en null.
- Copia los marcadores como [DOC_1] o [TEL_1] exactamente como aparecen.
- No respondas al cliente ni agregues texto fuera del JSON."""


def classify(p, text, intents, fields=None, *, purpose='intent', conversation_id=None):
    """
    intents: [{"id","name","description","examples"}]   fields: [{"name","description"}]
    → {"intent": id|None, "confidence": float, "fields": {...}}
    """
    if not p or not p.is_active:
        raise AIError('Proveedor de IA inactivo')
    _check_budget(p)
    t0 = time.monotonic()
    original = (text or '').strip()[:2000]
    sent, mapping = mask(original) if p.mask_personal_data else (original, {})
    lines = []
    for it in intents:
        ex = '; '.join(e.strip() for e in str(it.get('examples') or '').splitlines() if e.strip())[:400]
        lines.append(f'- {it["id"]}: {it.get("name", "")}. {it.get("description", "")}'
                     + (f' Ejemplos: {ex}' if ex else ''))
    fields_block = ''
    if fields:
        fields_block = 'Campos a extraer (en "fields"):\n' + '\n'.join(
            f'- {f["name"]}: {f.get("description", "")}' for f in fields) + '\n\n'
    system = SYSTEM_PROMPT.format(intents='\n'.join(lines), fields_block=fields_block)
    usage = {}
    try:
        out, usage = chat_json(p, system, f'Mensaje del cliente: """{sent}"""')
        valid = {it['id'] for it in intents}
        intent = out.get('intent') if out.get('intent') in valid else None
        try:
            conf = max(0.0, min(1.0, float(out.get('confidence') or 0)))
        except (TypeError, ValueError):
            conf = 0.0
        names = {f['name'] for f in fields or []}
        extracted = {k: v for k, v in (out.get('fields') or {}).items() if k in names and v not in (None, '')}
        result = {'intent': intent, 'confidence': round(conf, 2), 'fields': unmask(extracted, mapping)}
        _log(p, purpose, 'success', usage, t0, result=intent or 'desconocida', conversation_id=conversation_id)
        return result
    except AIError as e:
        _log(p, purpose, 'error', usage, t0, error=str(e), conversation_id=conversation_id)
        raise
    except Exception as e:
        _log(p, purpose, 'error', usage, t0, error=f'{type(e).__name__}: {e}', conversation_id=conversation_id)
        raise AIError(f'{type(e).__name__}: {str(e)[:200]}')


def test_provider(p):
    t0 = time.monotonic()
    try:
        out, usage = chat_json(p, 'Responde solo JSON.', 'Devuelve {"ok": true}')
        _log(p, 'test', 'success', usage, t0, result='ok')
        return {'ok': bool(out.get('ok')), 'duration_ms': int((time.monotonic() - t0) * 1000)}
    except Exception as e:
        _log(p, 'test', 'error', {}, t0, error=str(e))
        raise AIError(str(e)[:300])


def offline_classify(text, intents, fields=None):
    """Clasificación aproximada sin IA (simulador sin conexión): coincidencia de palabras."""
    import unicodedata

    def words(s):
        s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().lower()
        return {w for w in re.findall(r'[a-z0-9]{3,}', s)}

    msg = words(text)
    best, score = None, 0
    for it in intents:
        vocab = words(f'{it.get("name", "")} {it.get("description", "")} {it.get("examples", "")}')
        s = len(msg & vocab)
        if s > score:
            best, score = it['id'], s
    return {'intent': best, 'confidence': min(1.0, 0.4 + 0.2 * score) if best else 0.0, 'fields': {}}
