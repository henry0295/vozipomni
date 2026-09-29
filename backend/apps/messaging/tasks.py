"""Tareas Celery de mensajería / WhatsApp."""
import logging
import mimetypes
import os

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

MEDIA_DIR = os.path.join(str(settings.MEDIA_ROOT), 'whatsapp')


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def download_whatsapp_media(self, message_id: int):
    """Descarga el adjunto de un mensaje entrante y lo guarda en MEDIA_ROOT/whatsapp/."""
    from .models import Message
    from .whatsapp_service import WhatsAppAPIError, client_for_line

    try:
        msg = Message.objects.select_related('conversation__channel__whatsapp_line__provider').get(id=message_id)
    except Message.DoesNotExist:
        return
    media_id = (msg.metadata or {}).get('media_id')
    line = getattr(msg.conversation.channel, 'whatsapp_line', None)
    if not media_id or not line:
        return

    try:
        client = client_for_line(line)
        info = client.get_media_info(media_id)
        content = client.download_media(info['url'])
    except WhatsAppAPIError as e:
        logger.warning(f"[WhatsApp] Descarga de media {media_id} falló: {e.message}")
        raise self.retry(exc=e)

    mime = info.get('mime_type') or (msg.metadata or {}).get('mime_type') or ''
    ext = mimetypes.guess_extension(mime.split(';')[0].strip()) or ''
    filename = (msg.metadata or {}).get('filename') or f"{media_id}{ext}"
    safe = ''.join(ch for ch in filename if ch.isalnum() or ch in '._-')[:120] or f"{media_id}{ext}"

    os.makedirs(MEDIA_DIR, exist_ok=True)
    path = os.path.join(MEDIA_DIR, f"{msg.id}_{safe}")
    with open(path, 'wb') as fh:
        fh.write(content)

    msg.metadata = {**(msg.metadata or {}), 'local_path': path, 'mime_type': mime,
                    'size': len(content), 'filename': filename}
    msg.save(update_fields=['metadata'])

    from .realtime import push
    push(msg.conversation, 'message.media', {'message_id': msg.id})


@shared_task
def send_whatsapp_message(message_id: int):
    """Reintento asíncrono de un mensaje saliente pendiente/fallido."""
    from .models import Message
    from .whatsapp import send_outbound
    msg = Message.objects.select_related('conversation__channel').filter(id=message_id).first()
    if msg and msg.direction == 'outbound' and msg.status in ('pending', 'failed'):
        send_outbound(msg)


def sync_line_templates(line) -> dict:
    """Sincroniza las plantillas de Meta de una línea. Devuelve contadores."""
    from .models import WhatsAppTemplate
    from .whatsapp_service import client_for_line

    client = client_for_line(line)
    remote = client.list_templates(line.waba_id)
    seen = set()
    created = updated = 0
    for t in remote:
        key = (t.get('name'), t.get('language'))
        seen.add(key)
        obj, was_created = WhatsAppTemplate.objects.update_or_create(
            line=line, name=t.get('name'), language=t.get('language', 'es'),
            defaults={
                'meta_id': t.get('id', ''),
                'category': t.get('category', ''),
                'status': t.get('status', ''),
                'rejected_reason': (t.get('rejected_reason') or '')[:200],
                'components': t.get('components') or [],
            },
        )
        created += int(was_created)
        updated += int(not was_created)

    removed = 0
    for tpl in WhatsAppTemplate.objects.filter(line=line):
        if (tpl.name, tpl.language) not in seen:
            if tpl.broadcasts.exists():
                # Usada por envíos masivos (PROTECT): conservarla marcada como eliminada
                if tpl.status != 'DELETED':
                    tpl.status = 'DELETED'
                    tpl.save(update_fields=['status'])
                continue
            tpl.delete()
            removed += 1

    line.last_sync_at = timezone.now()
    line.save(update_fields=['last_sync_at'])
    return {'total': len(remote), 'created': created, 'updated': updated, 'removed': removed}


@shared_task
def sync_all_whatsapp_templates():
    """Periódica: refresca estado de aprobación de plantillas en todas las líneas activas."""
    from .models import WhatsAppLine
    ok = failed = 0
    for line in WhatsAppLine.objects.filter(is_active=True, provider__is_active=True).select_related('provider'):
        try:
            sync_line_templates(line)
            ok += 1
        except Exception as e:
            failed += 1
            logger.warning(f"[WhatsApp] Sync plantillas línea {line.id} falló: {e}")
    return f"{ok} líneas sincronizadas, {failed} con error"


# ══════════════════════════════════════════════════════════════════════════════
# Adjuntos remotos (Messenger / Instagram: URL de CDN que expira)
# ══════════════════════════════════════════════════════════════════════════════

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def download_remote_media(self, message_id: int):
    import requests
    from .models import Message

    msg = Message.objects.select_related('conversation').filter(id=message_id).first()
    url = (msg.metadata or {}).get('remote_url') if msg else None
    if not url:
        return
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise self.retry(exc=e)

    mime = (resp.headers.get('Content-Type') or 'application/octet-stream').split(';')[0].strip()
    ext = mimetypes.guess_extension(mime) or ''
    directory = os.path.join(str(settings.MEDIA_ROOT), 'meta')
    os.makedirs(directory, exist_ok=True)
    filename = f"{msg.id}{ext}"
    path = os.path.join(directory, filename)
    with open(path, 'wb') as fh:
        fh.write(resp.content)
    msg.metadata = {**(msg.metadata or {}), 'local_path': path, 'mime_type': mime,
                    'size': len(resp.content), 'filename': filename}
    msg.save(update_fields=['metadata'])

    from .realtime import push
    push(msg.conversation, 'message.media', {'message_id': msg.id})


# ══════════════════════════════════════════════════════════════════════════════
# Email (IMAP polling)
# ══════════════════════════════════════════════════════════════════════════════

@shared_task
def poll_email_accounts():
    """Periódica (cada minuto): trae correos nuevos de todas las cuentas activas."""
    from django.core.cache import cache
    from .email_channel import poll_account
    from .models import EmailAccount

    # Evitar solapamiento si un buzón tarda más de un minuto
    if not cache.add('messaging:poll_email:lock', 1, timeout=300):
        return 'Polling en curso, omitido'
    total = errors = 0
    try:
        for account in EmailAccount.objects.filter(is_active=True).select_related('channel'):
            try:
                total += poll_account(account)
            except Exception as e:
                errors += 1
                account.last_error = str(e)[:500]
                account.last_polled_at = timezone.now()
                account.save(update_fields=['last_error', 'last_polled_at'])
                logger.warning(f"[Email] Error leyendo {account.email_address}: {e}")
    finally:
        cache.delete('messaging:poll_email:lock')
    return f"{total} correos nuevos, {errors} cuentas con error"


# ══════════════════════════════════════════════════════════════════════════════
# Envíos masivos
# ══════════════════════════════════════════════════════════════════════════════

@shared_task
def process_broadcast_batch(broadcast_id: int):
    """Envía un lote (rate_per_minute) y se reprograma cada 60 s hasta terminar."""
    from .broadcasts import send_batch
    result = send_batch(broadcast_id)
    if result.get('status') == 'running' and result.get('remaining', 0) > 0:
        process_broadcast_batch.apply_async((broadcast_id,), countdown=60)
    return result


@shared_task
def dispatch_scheduled_broadcasts():
    """Periódica (cada minuto): inicia los envíos programados cuya hora llegó."""
    from .broadcasts import start_broadcast
    from .models import WhatsAppBroadcast

    started = 0
    for b in WhatsAppBroadcast.objects.filter(status='scheduled', scheduled_at__lte=timezone.now()) \
            .select_related('template', 'line'):
        try:
            start_broadcast(b)
            process_broadcast_batch.delay(b.id)
            started += 1
        except Exception as e:
            b.status = 'failed'
            b.last_error = str(e)[:500]
            b.save(update_fields=['status', 'last_error'])
            logger.warning(f"[Broadcast {b.id}] No se pudo iniciar: {e}")
    return f"{started} envíos iniciados"
