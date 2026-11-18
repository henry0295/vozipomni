"""
VozipCX — Descargas protegidas.

Ningún archivo subido, recibido o generado se sirve por una URL pública. Las vistas
autenticadas llaman a `protected_file_response()`, que comprueba que la ruta esté dentro
de una raíz permitida (`settings.PROTECTED_FILE_ROOTS`) y delega el envío a nginx con
`X-Accel-Redirect` hacia una ubicación `internal` (`/_protected/...`). Sin nginx
(`USE_X_ACCEL_REDIRECT=False`, por defecto con `DEBUG=True`) el archivo lo envía Django.
"""
import logging
import mimetypes
import os
from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse

logger = logging.getLogger(__name__)


def _resolve(path: str):
    """Devuelve (ruta_real, raíz_real, prefijo_interno) o None si la ruta no está permitida."""
    real = os.path.realpath(path)
    for root, prefix in (getattr(settings, 'PROTECTED_FILE_ROOTS', None) or {}).items():
        real_root = os.path.realpath(str(root))
        if real.startswith(real_root + os.sep):
            return real, real_root, prefix
    return None


def _content_disposition(filename: str, as_attachment: bool) -> str:
    kind = 'attachment' if as_attachment else 'inline'
    # Respaldo ASCII para clientes antiguos + filename* (RFC 6266/5987) con el nombre real
    ascii_name = ''.join(ch if 32 <= ord(ch) < 127 and ch not in '"\\' else '_' for ch in filename) or 'archivo'
    return f'{kind}; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename, safe="")}'


def protected_file_response(path: str, *, filename: str | None = None,
                            content_type: str | None = None,
                            as_attachment: bool = True):
    """
    Respuesta para descargar `path` de forma autenticada.

    Lanza `Http404` si la ruta está fuera de las raíces permitidas o el archivo no existe.
    """
    if not path:
        raise Http404('El archivo no está disponible')
    resolved = _resolve(str(path))
    if resolved is None:
        logger.warning('Descarga rechazada: ruta fuera de las raíces protegidas (%s)', path)
        raise Http404('El archivo no está disponible')
    real, real_root, prefix = resolved
    if not os.path.isfile(real):
        raise Http404('El archivo no está disponible')

    name = filename or os.path.basename(real)
    ctype = content_type or mimetypes.guess_type(real)[0] or 'application/octet-stream'

    if getattr(settings, 'USE_X_ACCEL_REDIRECT', False):
        relpath = os.path.relpath(real, real_root).replace(os.sep, '/')
        response = HttpResponse(status=200, content_type=ctype)
        response['X-Accel-Redirect'] = quote(prefix.rstrip('/') + '/' + relpath)
    else:
        response = FileResponse(open(real, 'rb'), content_type=ctype)

    response['Content-Disposition'] = _content_disposition(name, as_attachment)
    response['Cache-Control'] = 'private, no-store'
    return response
