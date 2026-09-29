"""
Cliente de la WhatsApp Business Cloud API (Graph API de Meta).

Referencias:
  - Envío de mensajes:  POST /{PHONE_NUMBER_ID}/messages
  - Plantillas:         GET/POST/DELETE /{WABA_ID}/message_templates
  - Suscripción app:    POST /{WABA_ID}/subscribed_apps
  - Número:             GET /{PHONE_NUMBER_ID}
  - Media:              GET /{MEDIA_ID}  → url  (descarga con el mismo token)
"""
import logging
import re

import requests

logger = logging.getLogger(__name__)

GRAPH_URL = 'https://graph.facebook.com'
TIMEOUT = 20


class WhatsAppAPIError(Exception):
    def __init__(self, message, code=None, subcode=None, details=None, status=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.subcode = subcode
        self.details = details
        self.status = status

    def to_dict(self):
        return {
            'error': self.message,
            'code': self.code,
            'subcode': self.subcode,
            'details': self.details,
        }


# Mensajes de error de Meta más comunes, traducidos
_ERROR_HINTS = {
    131047: 'Han pasado más de 24 h desde el último mensaje del cliente: usa una plantilla aprobada.',
    131026: 'El número destino no tiene WhatsApp o no puede recibir mensajes.',
    131051: 'Tipo de mensaje no soportado.',
    132000: 'La cantidad de parámetros no coincide con la plantilla.',
    132001: 'La plantilla no existe o no está aprobada en ese idioma.',
    131030: 'El número destino no está en la lista de destinatarios permitidos (número de prueba).',
    190: 'El token de acceso es inválido o expiró.',
    100: 'Parámetro inválido (revisa Phone Number ID / WABA ID).',
    10: 'La app no tiene permisos suficientes (whatsapp_business_messaging / management).',
    80007: 'Límite de velocidad alcanzado, intenta en unos minutos.',
}


def normalize_wa_number(number: str) -> str:
    """WhatsApp espera el número en formato internacional sin '+' ni espacios."""
    return re.sub(r'\D', '', number or '')


class WhatsAppCloudClient:
    def __init__(self, access_token: str, api_version: str = 'v21.0'):
        if not access_token:
            raise WhatsAppAPIError('La línea no tiene token de acceso configurado en su proveedor.')
        self.token = access_token
        self.version = api_version or 'v21.0'

    @classmethod
    def for_provider(cls, provider):
        return cls(provider.access_token, provider.api_version)

    # ── HTTP ─────────────────────────────────────────────────────────────────
    def _url(self, path: str) -> str:
        return f"{GRAPH_URL}/{self.version}/{path.lstrip('/')}"

    def _request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {self.token}'
        url = path if path.startswith('http') else self._url(path)
        try:
            resp = requests.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
        except requests.RequestException as e:
            raise WhatsAppAPIError(f'No se pudo conectar con Meta: {e}')

        try:
            data = resp.json()
        except ValueError:
            data = {}

        if resp.status_code >= 400 or (isinstance(data, dict) and 'error' in data):
            err = (data or {}).get('error', {}) if isinstance(data, dict) else {}
            code = err.get('code')
            subcode = err.get('error_subcode')
            details = (err.get('error_data') or {}).get('details') or err.get('error_user_msg')
            message = _ERROR_HINTS.get(code) or err.get('message') or f'Error HTTP {resp.status_code}'
            logger.warning(f"[WhatsApp] {method} {path} → {resp.status_code} code={code} {err.get('message')}")
            raise WhatsAppAPIError(message, code=code, subcode=subcode, details=details, status=resp.status_code)
        return data

    # ── Cuenta / número ──────────────────────────────────────────────────────
    def me(self):
        """Identidad del token (Usuario del Sistema)."""
        return self._request('GET', 'me', params={'fields': 'id,name'})

    def get_phone_number(self, phone_number_id: str):
        return self._request('GET', phone_number_id, params={
            'fields': 'id,display_phone_number,verified_name,quality_rating,'
                      'code_verification_status,platform_type,throughput,name_status,messaging_limit_tier',
        })

    def list_phone_numbers(self, waba_id: str):
        data = self._request('GET', f'{waba_id}/phone_numbers', params={
            'fields': 'id,display_phone_number,verified_name,quality_rating,code_verification_status',
        })
        return data.get('data', [])

    def subscribe_app(self, waba_id: str):
        """Suscribe la app a los webhooks de la WABA (necesario para recibir mensajes)."""
        return self._request('POST', f'{waba_id}/subscribed_apps')

    def subscribed_apps(self, waba_id: str):
        return self._request('GET', f'{waba_id}/subscribed_apps').get('data', [])

    # ── Plantillas ───────────────────────────────────────────────────────────
    def list_templates(self, waba_id: str):
        results = []
        data = self._request('GET', f'{waba_id}/message_templates', params={
            'limit': 100,
            'fields': 'id,name,language,status,category,components,rejected_reason',
        })
        results.extend(data.get('data', []))
        next_url = (data.get('paging') or {}).get('next')
        pages = 0
        while next_url and pages < 20:
            data = self._request('GET', next_url)
            results.extend(data.get('data', []))
            next_url = (data.get('paging') or {}).get('next')
            pages += 1
        return results

    def create_template(self, waba_id: str, name: str, language: str, category: str, components: list):
        return self._request('POST', f'{waba_id}/message_templates', json={
            'name': name,
            'language': language,
            'category': category,
            'components': components,
        })

    def delete_template(self, waba_id: str, name: str):
        return self._request('DELETE', f'{waba_id}/message_templates', params={'name': name})

    # ── Envío ────────────────────────────────────────────────────────────────
    def send(self, phone_number_id: str, payload: dict):
        body = {'messaging_product': 'whatsapp', 'recipient_type': 'individual', **payload}
        return self._request('POST', f'{phone_number_id}/messages', json=body)

    def send_text(self, phone_number_id: str, to: str, text: str, preview_url: bool = True):
        return self.send(phone_number_id, {
            'to': normalize_wa_number(to),
            'type': 'text',
            'text': {'body': text, 'preview_url': preview_url},
        })

    def send_template(self, phone_number_id: str, to: str, name: str, language: str,
                      body_params=None, header_params=None):
        components = []
        if header_params:
            components.append({'type': 'header', 'parameters': [
                {'type': 'text', 'text': str(p)} for p in header_params
            ]})
        if body_params:
            components.append({'type': 'body', 'parameters': [
                {'type': 'text', 'text': str(p)} for p in body_params
            ]})
        template = {'name': name, 'language': {'code': language}}
        if components:
            template['components'] = components
        return self.send(phone_number_id, {
            'to': normalize_wa_number(to),
            'type': 'template',
            'template': template,
        })

    def send_media(self, phone_number_id: str, to: str, media_type: str, link: str,
                   caption: str = None, filename: str = None):
        media = {'link': link}
        if caption and media_type in ('image', 'video', 'document'):
            media['caption'] = caption
        if filename and media_type == 'document':
            media['filename'] = filename
        return self.send(phone_number_id, {
            'to': normalize_wa_number(to),
            'type': media_type,
            media_type: media,
        })

    def upload_media(self, phone_number_id: str, path: str, mime_type: str) -> str:
        """Sube un archivo local a Meta y devuelve el media_id (válido 30 días)."""
        import os
        try:
            with open(path, 'rb') as fh:
                resp = requests.post(
                    self._url(f'{phone_number_id}/media'),
                    headers={'Authorization': f'Bearer {self.token}'},
                    data={'messaging_product': 'whatsapp', 'type': mime_type},
                    files={'file': (os.path.basename(path), fh, mime_type)},
                    timeout=120,
                )
        except OSError as e:
            raise WhatsAppAPIError(f'No se pudo leer el archivo: {e}')
        except requests.RequestException as e:
            raise WhatsAppAPIError(f'No se pudo subir el archivo a Meta: {e}')
        try:
            data = resp.json()
        except ValueError:
            data = {}
        if resp.status_code >= 400 or 'error' in data:
            err = data.get('error', {}) if isinstance(data, dict) else {}
            code = err.get('code')
            raise WhatsAppAPIError(
                _ERROR_HINTS.get(code) or err.get('message') or f'Error subiendo archivo ({resp.status_code})',
                code=code, subcode=err.get('error_subcode'),
                details=(err.get('error_data') or {}).get('details'), status=resp.status_code,
            )
        return data.get('id', '')

    def send_media_id(self, phone_number_id: str, to: str, media_type: str, media_id: str,
                      caption: str = None, filename: str = None):
        media = {'id': media_id}
        if caption and media_type in ('image', 'video', 'document'):
            media['caption'] = caption
        if filename and media_type == 'document':
            media['filename'] = filename
        return self.send(phone_number_id, {
            'to': normalize_wa_number(to),
            'type': media_type,
            media_type: media,
        })

    def mark_read(self, phone_number_id: str, message_id: str):
        return self._request('POST', f'{phone_number_id}/messages', json={
            'messaging_product': 'whatsapp',
            'status': 'read',
            'message_id': message_id,
        })

    # ── Media entrante ───────────────────────────────────────────────────────
    def get_media_info(self, media_id: str):
        return self._request('GET', media_id)

    def download_media(self, url: str) -> bytes:
        try:
            resp = requests.get(url, headers={'Authorization': f'Bearer {self.token}'}, timeout=60)
        except requests.RequestException as e:
            raise WhatsAppAPIError(f'No se pudo descargar el archivo: {e}')
        if resp.status_code >= 400:
            raise WhatsAppAPIError(f'Error descargando archivo ({resp.status_code})', status=resp.status_code)
        return resp.content


def client_for_line(line) -> WhatsAppCloudClient:
    return WhatsAppCloudClient.for_provider(line.provider)


def extract_message_id(response: dict) -> str:
    msgs = (response or {}).get('messages') or []
    return msgs[0].get('id', '') if msgs else ''
