"""
Conector GLPI (API REST legacy /apirest.php — GLPI 9.5, 10 y 11).

base_url  = https://soporte.empresa.com/apirest.php
secrets   = {"app_token": "...", "user_token": "..."}     (usuario técnico del bot)
config    = {
  "default_type": 1,                # 1 Incidente · 2 Solicitud
  "default_urgency": 3,             # 1 Muy baja … 5 Muy alta
  "default_category_id": null,      # itilcategories_id
  "requesttype_id": null,           # origen "WhatsApp" (Configuración > Desplegables > Orígenes)
  "entity_id": null                 # entidad por defecto (opcional)
}

En GLPI: Configuración > General > API → habilitar la API REST, permitir
"inicio de sesión con token externo" y crear un cliente de API (App-Token).
El usuario del bot necesita un perfil que pueda crear tickets y ver usuarios.
"""
import base64

import requests

from .base import ActionSpec, BaseConnector, ConnectorError, ConnectorResult, is_empty

TICKET_STATUS = {1: 'Nuevo', 2: 'En curso (asignado)', 3: 'En curso (planificado)',
                 4: 'En espera', 5: 'Resuelto', 6: 'Cerrado'}
URGENCY = {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, 'muy baja': 1, 'baja': 2, 'media': 3,
           'alta': 4, 'muy alta': 5}
TYPES = {'1': 1, '2': 2, 'incidente': 1, 'incidencia': 1, 'solicitud': 2, 'requerimiento': 2}

# Opciones de búsqueda estándar de GLPI (search options)
U_ID, U_LOGIN, U_EMAIL, U_PHONE, U_MOBILE, U_FIRSTNAME, U_REALNAME = '2', '1', '5', '6', '11', '9', '34'
T_ID, T_NAME, T_STATUS, T_DATE, T_REQUESTER, T_TECH = '2', '1', '12', '15', '4', '5'


class GlpiConnector(BaseConnector):

    @classmethod
    def actions(cls, connector=None):
        return [
            ActionSpec('find_requester', 'Buscar solicitante',
                       [{'name': 'email', 'label': 'Email', 'required': False},
                        {'name': 'phone', 'label': 'Teléfono', 'required': False}],
                       'id, nombre, email, teléfono del usuario de GLPI'),
            ActionSpec('create_ticket', 'Crear ticket',
                       [{'name': 'title', 'label': 'Título', 'required': True},
                        {'name': 'description', 'label': 'Descripción', 'required': True},
                        {'name': 'requester_id', 'label': 'Id del solicitante', 'required': False},
                        {'name': 'category_id', 'label': 'Id de categoría', 'required': False},
                        {'name': 'urgency', 'label': 'Urgencia (1-5 o baja/media/alta)', 'required': False},
                        {'name': 'type', 'label': 'Tipo (incidente/solicitud)', 'required': False}],
                       'id del ticket y enlace'),
            ActionSpec('get_ticket', 'Consultar ticket',
                       [{'name': 'ticket_id', 'label': 'Número de ticket', 'required': True}],
                       'id, título, estado, fecha, técnico, último seguimiento'),
            ActionSpec('my_tickets', 'Tickets abiertos del solicitante',
                       [{'name': 'requester_id', 'label': 'Id del solicitante', 'required': True}],
                       'lista de tickets abiertos (id, título, estado)', returns_list=True),
            ActionSpec('add_followup', 'Agregar seguimiento',
                       [{'name': 'ticket_id', 'label': 'Número de ticket', 'required': True},
                        {'name': 'content', 'label': 'Texto', 'required': True}],
                       'id del seguimiento'),
            ActionSpec('list_categories', 'Categorías ITIL',
                       [], 'lista de categorías (id, nombre)', returns_list=True),
        ]

    # ── sesión ──
    def _headers(self, session=None):
        h = {'Content-Type': 'application/json', 'App-Token': self.secrets.get('app_token', '')}
        if session:
            h['Session-Token'] = session
        return h

    def _init_session(self):
        h = self._headers()
        if self.secrets.get('user_token'):
            h['Authorization'] = f"user_token {self.secrets['user_token']}"
        elif self.secrets.get('login'):
            raw = f"{self.secrets['login']}:{self.secrets.get('password', '')}".encode()
            h['Authorization'] = 'Basic ' + base64.b64encode(raw).decode()
        else:
            raise ConnectorError('Faltan credenciales de GLPI (user_token o login/password)')
        r = requests.get(f'{self.base_url}/initSession', headers=h, timeout=self.timeout, verify=self.verify)
        if r.status_code >= 400:
            raise ConnectorError(f'GLPI rechazó el inicio de sesión (HTTP {r.status_code}): {r.text[:200]}')
        token = (r.json() or {}).get('session_token')
        if not token:
            raise ConnectorError('GLPI no devolvió session_token')
        if self.config.get('entity_id'):
            requests.post(f'{self.base_url}/changeActiveEntities', headers=self._headers(token),
                          json={'entities_id': int(self.config['entity_id']), 'is_recursive': True},
                          timeout=self.timeout, verify=self.verify)
        return token

    def _kill(self, token):
        try:
            requests.get(f'{self.base_url}/killSession', headers=self._headers(token),
                         timeout=self.timeout, verify=self.verify)
        except Exception:
            pass

    def _call(self, token, method, path, **kw):
        r = requests.request(method, f'{self.base_url}/{path.lstrip("/")}', headers=self._headers(token),
                             timeout=self.timeout, verify=self.verify, **kw)
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise ConnectorError(f'GLPI HTTP {r.status_code}: {r.text[:200]}')
        return r.json() if r.content else {}

    def _search(self, token, itemtype, criteria, display):
        params = {'forcedisplay[]': display, 'range': '0-49'}
        for i, c in enumerate(criteria):
            if i:
                params[f'criteria[{i}][link]'] = c.get('link', 'AND')
            params[f'criteria[{i}][field]'] = c['field']
            params[f'criteria[{i}][searchtype]'] = c.get('searchtype', 'contains')
            params[f'criteria[{i}][value]'] = c['value']
        data = self._call(token, 'GET', f'search/{itemtype}', params=params) or {}
        return data.get('data') or []

    def ticket_url(self, ticket_id):
        front = self.config.get('front_url') or self.base_url.replace('/apirest.php', '')
        return f"{front.rstrip('/')}/front/ticket.form.php?id={ticket_id}"

    # ── acciones ──
    def run(self, action, params):
        token = self._init_session()
        try:
            return getattr(self, f'_a_{action}')(token, params)
        finally:
            self._kill(token)

    def _a_find_requester(self, token, p):
        email = (p.get('email') or '').strip()
        phone = ''.join(ch for ch in str(p.get('phone') or '') if ch.isdigit())
        rows = []
        if email:
            rows = self._search(token, 'User', [{'field': U_EMAIL, 'value': email, 'searchtype': 'contains'}],
                                [U_ID, U_LOGIN, U_FIRSTNAME, U_REALNAME, U_EMAIL, U_PHONE])
        if not rows and phone:
            tail = phone[-10:]  # sin indicativo de país
            rows = self._search(token, 'User', [
                {'field': U_PHONE, 'value': tail},
                {'field': U_MOBILE, 'value': tail, 'link': 'OR'},
            ], [U_ID, U_LOGIN, U_FIRSTNAME, U_REALNAME, U_EMAIL, U_PHONE])
        if not rows:
            return ConnectorResult('empty', None)
        u = rows[0]
        name = f"{u.get(U_FIRSTNAME) or ''} {u.get(U_REALNAME) or ''}".strip() or u.get(U_LOGIN)
        return ConnectorResult('success', {'id': u.get(U_ID), 'name': name, 'login': u.get(U_LOGIN),
                                           'email': u.get(U_EMAIL), 'phone': u.get(U_PHONE)})

    def _a_create_ticket(self, token, p):
        title = (p.get('title') or '').strip()[:250]
        desc = (p.get('description') or '').strip()
        if not title or not desc:
            raise ConnectorError('El título y la descripción son obligatorios')
        urgency = URGENCY.get(str(p.get('urgency') or '').strip().lower(), self.config.get('default_urgency', 3))
        ttype = TYPES.get(str(p.get('type') or '').strip().lower(), self.config.get('default_type', 1))
        data = {'name': title, 'content': desc.replace('\n', '<br>'), 'urgency': urgency, 'type': ttype}
        cat = p.get('category_id') or self.config.get('default_category_id')
        if cat:
            data['itilcategories_id'] = int(cat)
        if self.config.get('requesttype_id'):
            data['requesttypes_id'] = int(self.config['requesttype_id'])
        if p.get('requester_id'):
            data['_users_id_requester'] = int(p['requester_id'])
        res = self._call(token, 'POST', 'Ticket', json={'input': data}) or {}
        tid = res.get('id')
        if not tid:
            raise ConnectorError(f'GLPI no creó el ticket: {res}')
        return ConnectorResult('success', {'id': tid, 'url': self.ticket_url(tid), 'title': title})

    def _a_get_ticket(self, token, p):
        tid = ''.join(ch for ch in str(p.get('ticket_id') or '') if ch.isdigit())
        if not tid:
            return ConnectorResult('empty', None)
        t = self._call(token, 'GET', f'Ticket/{tid}', params={'expand_dropdowns': 'true'})
        if not t:
            return ConnectorResult('empty', None)
        follow = self._call(token, 'GET', f'Ticket/{tid}/ITILFollowup',
                            params={'range': '0-0', 'sort': 'date', 'order': 'DESC'}) or []
        last = ''
        if isinstance(follow, list) and follow:
            import re
            last = re.sub(r'<[^>]+>', ' ', follow[0].get('content') or '').strip()[:300]
        status = t.get('status')
        return ConnectorResult('success', {
            'id': t.get('id'), 'title': t.get('name'),
            'status': TICKET_STATUS.get(status, str(status)), 'status_code': status,
            'date': t.get('date'), 'category': t.get('itilcategories_id'),
            'last_followup': last, 'url': self.ticket_url(t.get('id')),
        })

    def _a_my_tickets(self, token, p):
        rid = p.get('requester_id')
        if not rid:
            return ConnectorResult('empty', [])
        rows = self._search(token, 'Ticket', [
            {'field': T_REQUESTER, 'value': str(rid), 'searchtype': 'equals'},
            {'field': T_STATUS, 'value': 'notold', 'searchtype': 'equals'},
        ], [T_ID, T_NAME, T_STATUS, T_DATE])
        items = [{'id': r.get(T_ID), 'title': r.get(T_NAME),
                  'status': TICKET_STATUS.get(r.get(T_STATUS), str(r.get(T_STATUS))),
                  'date': r.get(T_DATE)} for r in rows]
        return ConnectorResult('empty' if not items else 'success', items)

    def _a_add_followup(self, token, p):
        tid = ''.join(ch for ch in str(p.get('ticket_id') or '') if ch.isdigit())
        content = (p.get('content') or '').strip()
        if not tid or not content:
            raise ConnectorError('Número de ticket y texto son obligatorios')
        res = self._call(token, 'POST', 'ITILFollowup', json={'input': {
            'itemtype': 'Ticket', 'items_id': int(tid), 'content': content.replace('\n', '<br>'),
        }}) or {}
        return ConnectorResult('success', {'id': res.get('id'), 'ticket_id': int(tid)})

    def _a_list_categories(self, token, p):
        rows = self._call(token, 'GET', 'ITILCategory', params={'range': '0-99', 'is_helpdeskvisible': 1}) or []
        items = [{'id': r.get('id'), 'name': r.get('completename') or r.get('name')}
                 for r in rows if isinstance(r, dict)]
        return ConnectorResult('empty' if is_empty(items) else 'success', items)

    def test(self):
        token = self._init_session()
        try:
            me = self._call(token, 'GET', 'getFullSession') or {}
            name = (me.get('session') or {}).get('glpiname')
            return ConnectorResult('success', {'message': f'Conectado a GLPI como {name or "usuario API"}'})
        finally:
            self._kill(token)
