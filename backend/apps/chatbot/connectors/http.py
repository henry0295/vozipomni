"""
Conector HTTP genérico para cualquier API REST (agendas, CRM, ERP…).

config = {
  "headers": {"Authorization": "Bearer {{secret.token}}"},
  "actions": [
    {"name": "consultar_citas", "label": "Consultar citas",
     "method": "GET", "path": "/pacientes/{{documento}}/citas",
     "query": {"estado": "activa"},
     "body": null,                       # dict/lista con {{variables}} para POST/PUT/PATCH
     "inputs": ["documento"],            # parámetros que pide el bloque del bot
     "result_path": "data.citas",        # parte de la respuesta que se guarda
     "returns_list": true}
  ]
}
secrets = {"token": "..."}   → se usan como {{secret.token}} en headers, query y body
"""
import json
import re

import requests

from .base import ActionSpec, BaseConnector, ConnectorError, ConnectorResult, dig, is_empty

TPL = re.compile(r'\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}')
METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}


def render(value, ctx: dict):
    """Sustituye {{x}} en strings dentro de estructuras JSON."""
    if isinstance(value, str):
        full = TPL.fullmatch(value.strip())
        if full:  # "{{x}}" completo conserva el tipo (número, lista…)
            v = dig(ctx, full.group(1))
            return '' if v is None else v
        return TPL.sub(lambda m: '' if dig(ctx, m.group(1)) is None else str(dig(ctx, m.group(1))), value)
    if isinstance(value, dict):
        return {k: render(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, ctx) for v in value]
    return value


class HttpConnector(BaseConnector):

    @classmethod
    def actions(cls, connector=None) -> list:
        out = []
        for a in ((connector.config or {}).get('actions') or []) if connector else []:
            if not a.get('name'):
                continue
            inputs = [i if isinstance(i, dict) else {'name': i, 'label': i, 'required': False}
                      for i in (a.get('inputs') or [])]
            out.append(ActionSpec(a['name'], a.get('label') or a['name'], inputs,
                                  a.get('outputs', ''), bool(a.get('returns_list'))))
        return out

    def _action(self, name):
        for a in self.config.get('actions') or []:
            if a.get('name') == name:
                return a
        raise ConnectorError(f'Acción desconocida: {name}')

    def _request(self, method, path, params, body=None, query=None):
        ctx = {**params, 'secret': self.secrets}
        url = self.base_url + '/' + render(path or '', ctx).lstrip('/')
        if not url.lower().startswith(('http://', 'https://')):
            raise ConnectorError('URL inválida')
        headers = {'Accept': 'application/json', **render(self.config.get('headers') or {}, ctx)}
        kwargs = {'headers': headers, 'timeout': self.timeout, 'verify': self.verify,
                  'params': render(query or {}, ctx) or None}
        if body is not None and method in ('POST', 'PUT', 'PATCH'):
            kwargs['json'] = render(body, ctx)
        resp = requests.request(method, url, **kwargs)
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise ConnectorError(f'HTTP {resp.status_code}: {resp.text[:200]}')
        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {'text': resp.text[:2000]}

    def run(self, action, params):
        a = self._action(action)
        method = (a.get('method') or 'GET').upper()
        if method not in METHODS:
            raise ConnectorError(f'Método no permitido: {method}')
        data = self._request(method, a.get('path', ''), params, a.get('body'), a.get('query'))
        data = dig(data, a.get('result_path', '')) if data is not None else None
        return ConnectorResult('empty' if is_empty(data) else 'success', data)

    def test(self):
        resp = requests.get(self.base_url, timeout=self.timeout, verify=self.verify,
                            headers=render(self.config.get('headers') or {}, {'secret': self.secrets}))
        return ConnectorResult('success' if resp.status_code < 500 else 'error',
                               {'http_status': resp.status_code},
                               '' if resp.status_code < 500 else f'HTTP {resp.status_code}')


def parse_json_field(value, default):
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value) if value else default
    except ValueError:
        return default
