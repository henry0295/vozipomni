"""
Canal Email: lectura por IMAP (polling desde Celery) y envío por SMTP.

  poll_account(account)         → trae los correos nuevos (UID > last_uid) como mensajes entrantes
  send_email_message(message)   → envía un Message saliente; devuelve el Message-ID
  test_account(account)         → valida credenciales IMAP y SMTP
"""
import email
import email.header
import imaplib
import logging
import mimetypes
import os
import re
import smtplib
import ssl
import uuid
from datetime import timedelta
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, parseaddr, parsedate_to_datetime

from django.conf import settings
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

MEDIA_DIR = os.path.join(str(settings.MEDIA_ROOT), 'email')
MAX_PER_POLL = 50
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
IMAP_TIMEOUT = 30


class EmailChannelError(Exception):
    pass


# ── Utilidades ───────────────────────────────────────────────────────────────

def _decode(value) -> str:
    if not value:
        return ''
    try:
        return str(email.header.make_header(email.header.decode_header(value)))
    except Exception:
        return str(value)


def _safe_name(name: str) -> str:
    base = ''.join(ch for ch in (name or '') if ch.isalnum() or ch in '._- ')[:120].strip()
    return base or f'adjunto-{uuid.uuid4().hex[:8]}'


def _strip_quoted(text: str) -> str:
    """Quita el historial citado ("El ... escribió:" / líneas con >) para no duplicar el hilo."""
    lines = []
    for line in (text or '').splitlines():
        low = line.strip().lower()
        if re.match(r'^(el|on)\s.+(escribió|wrote):\s*$', low) or low.startswith('-----original message'):
            break
        if line.startswith('>'):
            continue
        lines.append(line)
    return '\n'.join(lines).strip()


def _extract(msg):
    """Devuelve (texto, adjuntos[(filename, mime, bytes)])."""
    text_plain, text_html, attachments = '', '', []
    for part in msg.walk():
        if part.is_multipart():
            continue
        disp = (part.get('Content-Disposition') or '').lower()
        ctype = part.get_content_type()
        filename = _decode(part.get_filename())
        payload = part.get_payload(decode=True) or b''
        if filename or 'attachment' in disp:
            if len(payload) <= MAX_ATTACHMENT_BYTES:
                attachments.append((filename or f'adjunto{mimetypes.guess_extension(ctype) or ""}', ctype, payload))
            continue
        charset = part.get_content_charset() or 'utf-8'
        try:
            decoded = payload.decode(charset, errors='replace')
        except LookupError:
            decoded = payload.decode('utf-8', errors='replace')
        if ctype == 'text/plain' and not text_plain:
            text_plain = decoded
        elif ctype == 'text/html' and not text_html:
            text_html = decoded
    text = text_plain or re.sub(r'\n{3,}', '\n\n', strip_tags(re.sub(r'<br\s*/?>', '\n', text_html or '')))
    return _strip_quoted(text), attachments


def _media_type_for(mime: str) -> str:
    if (mime or '').startswith('image/'):
        return 'image'
    if (mime or '').startswith('audio/'):
        return 'audio'
    if (mime or '').startswith('video/'):
        return 'video'
    return 'document'


def _save_attachment(filename: str, content: bytes) -> str:
    os.makedirs(MEDIA_DIR, exist_ok=True)
    path = os.path.join(MEDIA_DIR, f"{uuid.uuid4().hex}_{_safe_name(filename)}")
    with open(path, 'wb') as fh:
        fh.write(content)
    return path


def _find_contact(address: str):
    from apps.contacts.models import Contact
    if not address:
        return None
    return Contact.objects.filter(email__iexact=address).order_by('-updated_at').first()


# ── IMAP ─────────────────────────────────────────────────────────────────────

def _imap(account):
    if account.imap_ssl:
        conn = imaplib.IMAP4_SSL(account.imap_host, account.imap_port, timeout=IMAP_TIMEOUT)
    else:
        conn = imaplib.IMAP4(account.imap_host, account.imap_port, timeout=IMAP_TIMEOUT)
        try:
            conn.starttls(ssl_context=ssl.create_default_context())
        except Exception:
            pass
    conn.login(account.imap_username, account.imap_password)
    return conn


def poll_account(account) -> int:
    """Procesa los correos nuevos de la cuenta. Devuelve cuántos se registraron."""
    from .routing import ingest_inbound

    conn = _imap(account)
    created = 0
    try:
        status, _ = conn.select(f'"{account.imap_folder}"', readonly=True)
        if status != 'OK':
            raise EmailChannelError(f'No se pudo abrir la carpeta {account.imap_folder}')

        if account.last_uid:
            status, data = conn.uid('search', None, f'UID {account.last_uid + 1}:*')
        else:
            # Primera vez: no importar el histórico, solo lo no leído de los últimos 2 días
            since = (timezone.now() - timedelta(days=2)).strftime('%d-%b-%Y')
            status, data = conn.uid('search', None, f'(UNSEEN SINCE {since})')
        uids = sorted(int(u) for u in (data[0].split() if data and data[0] else []))
        uids = [u for u in uids if u > account.last_uid][:MAX_PER_POLL]

        own_address = account.email_address.lower()
        for uid in uids:
            status, parts = conn.uid('fetch', str(uid), '(RFC822)')
            if status != 'OK' or not parts or not isinstance(parts[0], tuple):
                account.last_uid = uid
                continue
            msg = email.message_from_bytes(parts[0][1])
            from_name, from_addr = parseaddr(_decode(msg.get('From')))
            from_addr = (from_addr or '').lower()
            # Ignorar correos propios, rebotes y auto-respuestas para no crear bucles
            auto = (msg.get('Auto-Submitted', 'no').lower() != 'no'
                    or msg.get('X-Autoreply') or msg.get('X-Autorespond')
                    or (msg.get('Precedence', '').lower() in ('bulk', 'auto_reply', 'junk')))
            if not from_addr or from_addr == own_address or 'mailer-daemon' in from_addr or auto:
                account.last_uid = uid
                continue

            subject = _decode(msg.get('Subject'))
            message_id = ((msg.get('Message-ID') or '').strip() or f'<imap-{account.id}-{uid}>')[:255]
            try:
                sent_at = parsedate_to_datetime(msg.get('Date'))
                if timezone.is_naive(sent_at):
                    sent_at = timezone.make_aware(sent_at)
            except Exception:
                sent_at = timezone.now()
            text, attachments = _extract(msg)
            meta = {
                'email_message_id': message_id,
                'subject': subject,
                'in_reply_to': (msg.get('In-Reply-To') or '').strip(),
                'references': (msg.get('References') or '').strip(),
                'from': from_addr,
            }
            result = ingest_inbound(
                account.channel, from_addr,
                message_type='text', body=text or (f'[{subject}]' if subject else ''),
                metadata=meta, external_id=message_id, sent_at=sent_at,
                name=from_name, contact=_find_contact(from_addr), config=account,
                subject=subject,
            )
            if result:
                conv, _message, _created = result
                for filename, mime, content in attachments:
                    from .models import Message
                    path = _save_attachment(filename, content)
                    Message.objects.create(
                        conversation=conv, direction='inbound', message_type=_media_type_for(mime),
                        body='', status='received', sent_at=sent_at,
                        metadata={'local_path': path, 'mime_type': mime, 'filename': filename,
                                  'size': len(content), 'email_message_id': message_id},
                    )
                created += 1
            account.last_uid = uid

        # Primera sincronización sin correos: fijar el UID actual para no leer el histórico después
        if not account.last_uid:
            status, data = conn.uid('search', None, 'ALL')
            all_uids = [int(u) for u in (data[0].split() if data and data[0] else [])]
            account.last_uid = max(all_uids) if all_uids else 0
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    account.last_polled_at = timezone.now()
    account.last_error = ''
    account.save(update_fields=['last_uid', 'last_polled_at', 'last_error'])
    return created


# ── SMTP ─────────────────────────────────────────────────────────────────────

def _smtp(account):
    if account.smtp_ssl:
        server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port, timeout=30,
                                  context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=30)
        server.ehlo()
        if account.smtp_starttls:
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
    user = account.smtp_username or account.imap_username
    password = account.smtp_password or account.imap_password
    if user:
        server.login(user, password)
    return server


def send_email_message(message) -> str:
    """Envía el mensaje como respuesta en el hilo del cliente. Devuelve el Message-ID."""
    from .models import Message

    conv = message.conversation
    account = conv.channel.email_account
    last_in = Message.objects.filter(conversation=conv, direction='inbound',
                                     metadata__has_key='email_message_id').order_by('-sent_at').first()
    last_meta = (last_in.metadata or {}) if last_in else {}

    subject = conv.subject or (message.metadata or {}).get('subject') or 'Seguimiento'
    if not subject.lower().startswith(('re:', 'rv:', 'fw:')) and last_in:
        subject = f'Re: {subject}'

    domain = account.email_address.split('@')[-1]
    message_id = make_msgid(domain=domain)
    mail = EmailMessage()
    mail['Subject'] = subject
    mail['From'] = formataddr((account.from_name or account.name, account.email_address))
    mail['To'] = conv.contact_identifier
    mail['Message-ID'] = message_id
    if last_meta.get('email_message_id'):
        mail['In-Reply-To'] = last_meta['email_message_id']
        refs = (last_meta.get('references', '') + ' ' + last_meta['email_message_id']).strip()
        mail['References'] = refs

    body = message.body or ''
    if account.signature and not (message.metadata or {}).get('system'):
        body = f"{body}\n\n--\n{account.signature}"
    mail.set_content(body or ' ')

    meta = message.metadata or {}
    if meta.get('local_path') and os.path.exists(meta['local_path']):
        mime = meta.get('mime_type') or 'application/octet-stream'
        maintype, _, subtype = mime.partition('/')
        with open(meta['local_path'], 'rb') as fh:
            mail.add_attachment(fh.read(), maintype=maintype or 'application',
                                subtype=subtype or 'octet-stream',
                                filename=meta.get('filename') or os.path.basename(meta['local_path']))

    server = _smtp(account)
    try:
        server.send_message(mail)
    finally:
        try:
            server.quit()
        except Exception:
            pass
    message.metadata = {**meta, 'email_message_id': message_id, 'subject': subject}
    message.save(update_fields=['metadata'])
    if not conv.subject:
        conv.subject = subject
        conv.save(update_fields=['subject'])
    return message_id


def test_account(account) -> dict:
    result = {'imap': False, 'smtp': False, 'errors': []}
    try:
        conn = _imap(account)
        status, _ = conn.select(f'"{account.imap_folder}"', readonly=True)
        result['imap'] = status == 'OK'
        if status != 'OK':
            result['errors'].append(f'IMAP: no existe la carpeta {account.imap_folder}')
        conn.logout()
    except Exception as e:
        result['errors'].append(f'IMAP: {e}')
    try:
        server = _smtp(account)
        server.quit()
        result['smtp'] = True
    except Exception as e:
        result['errors'].append(f'SMTP: {e}')
    return result
