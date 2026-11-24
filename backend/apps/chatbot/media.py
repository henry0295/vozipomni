"""
Archivos dentro del bot: aceptar un archivo en una pregunta y el bloque «Analizar archivo».

Variable de archivo (la guarda el bloque Pregunta que acepta archivos):
  {"message_id": 123, "type": "image", "filename": "foto.jpg", "mime": "image/jpeg"}

Modos del bloque «Analizar archivo»:
  ocr       → texto del archivo (OCR / PDF / Office / transcripción), local
  extract   → texto local + IA de texto (datos ocultos) para extraer campos
  classify  → texto local + IA de texto para clasificar el documento en categorías
  vision    → IA de visión en la nube (la imagen sale del servidor; opcional)
"""
ACCEPTS = {
    'image': {'image', 'sticker'},
    'document': {'document'},
    'image_or_document': {'image', 'sticker', 'document'},
    'audio': {'audio'},
    'file': {'image', 'sticker', 'document', 'audio', 'video'},
}
MEDIA_TYPES = {'image', 'sticker', 'document', 'audio', 'video'}


class NotReady(Exception):
    """El adjunto aún no se ha descargado: reintentar."""


def accepts(accept: str, message_type: str) -> bool:
    return message_type in ACCEPTS.get(accept or '', set())


def file_info(message) -> dict:
    meta = message.metadata or {}
    return {'message_id': message.id, 'type': message.message_type,
            'filename': meta.get('filename') or '', 'mime': meta.get('mime_type') or '',
            'caption': message.body or ''}


def analyze(data: dict, info: dict, conversation_id=None):
    """Devuelve (status, result). status: success | unreadable | error. Lanza NotReady."""
    from apps.messaging.models import Message
    from apps.messaging.tasks import read_file_text
    from .ai import AIError, classify, vision
    from .models import AIProvider

    msg = Message.objects.filter(pk=(info or {}).get('message_id')).first()
    if not msg:
        return 'error', {'error': 'Archivo no encontrado'}
    path = (msg.metadata or {}).get('local_path')
    if not path:
        raise NotReady()
    mode = data.get('mode') or 'ocr'
    provider = None
    if mode in ('extract', 'classify', 'vision'):
        provider = AIProvider.objects.filter(pk=data.get('provider_id'), is_active=True).first()
        if not provider:
            return 'error', {'error': 'Proveedor de IA no disponible'}

    try:
        if mode == 'vision':
            if msg.message_type not in ('image', 'sticker'):
                return 'unreadable', {'error': 'La visión solo analiza imágenes'}
            r = vision(provider, path, data.get('instruction', ''), data.get('fields') or [],
                       conversation_id=conversation_id)
            return 'success', {'description': r['description'], **r['fields'], '_fields': r['fields']}

        try:
            read = read_file_text(msg)
        except Exception as e:
            return 'error', {'error': str(e)[:200]}
        text = read.get('text') or ''
        if len(text.strip()) < int(data.get('min_chars') or 10):
            return 'unreadable', {'text': text}
        if mode == 'ocr':
            return 'success', {'text': text[:4000], 'method': read.get('method')}

        categories = data.get('categories') or []
        intents = categories if mode == 'classify' and categories else [
            {'id': 'documento', 'name': 'Documento', 'description': 'Cualquier documento o texto'}]
        r = classify(provider, text[:4000], intents, data.get('fields') or [], purpose=f'file_{mode}',
                     conversation_id=conversation_id)
        return 'success', {'text': text[:1000], 'category': r['intent'], 'confidence': r['confidence'],
                           **r['fields'], '_fields': r['fields']}
    except AIError as e:
        return 'error', {'error': str(e)[:200]}


def local_path(info: dict):
    """Ruta en disco del archivo de una variable de archivo (para adjuntarlo a otro sistema)."""
    from apps.messaging.models import Message
    if not isinstance(info, dict) or not info.get('message_id'):
        return None, None
    msg = Message.objects.filter(pk=info['message_id']).first()
    if not msg:
        return None, None
    meta = msg.metadata or {}
    return meta.get('local_path'), meta.get('filename') or f"adjunto-{msg.id}"
