"""
Servicio local de transcripción (faster-whisper). No envía audio a terceros.

  GET  /health                       → {"status": "ok", "model": "...", "loaded": bool}
  POST /transcribe  (JSON)           → {"path": "/app/media/whatsapp/123_audio.ogg", "language": "es"}
  POST /transcribe  (multipart)      → campo "file" (+ "language")
     ← {"text": "...", "language": "es", "duration": 12.3, "elapsed": 4.1}

Solo es accesible dentro de la red interna de Docker (no publica puertos).
Variables: WHISPER_MODEL (small), WHISPER_COMPUTE (int8), WHISPER_THREADS (0=auto),
WHISPER_LANGUAGE (es), WHISPER_MAX_SECONDS (600), WHISPER_PRELOAD (false), ALLOWED_DIR (/app/media).
"""
import asyncio
import logging
import os
import tempfile
import time

from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s [transcriber] %(message)s')
log = logging.getLogger('transcriber')

MODEL_NAME = os.getenv('WHISPER_MODEL', 'small')
COMPUTE = os.getenv('WHISPER_COMPUTE', 'int8')
THREADS = int(os.getenv('WHISPER_THREADS', '0') or 0)
DEFAULT_LANG = os.getenv('WHISPER_LANGUAGE', 'es') or None
MAX_SECONDS = float(os.getenv('WHISPER_MAX_SECONDS', '600'))
ALLOWED_DIR = os.path.realpath(os.getenv('ALLOWED_DIR', '/app/media'))
MAX_UPLOAD = 25 * 1024 * 1024

_model = None
_lock = asyncio.Lock()


def _load():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        log.info(f'Cargando modelo {MODEL_NAME} ({COMPUTE})…')
        _model = WhisperModel(MODEL_NAME, device='cpu', compute_type=COMPUTE, cpu_threads=THREADS)
        log.info('Modelo cargado')
    return _model


def _transcribe(path, language):
    model = _load()
    t0 = time.monotonic()
    segments, info = model.transcribe(path, language=language or DEFAULT_LANG, vad_filter=True,
                                      beam_size=1, condition_on_previous_text=False)
    if info.duration and info.duration > MAX_SECONDS:
        raise ValueError(f'Audio demasiado largo ({int(info.duration)} s, máximo {int(MAX_SECONDS)} s)')
    text = ' '.join(s.text.strip() for s in segments).strip()
    return {'text': text, 'language': info.language, 'duration': round(info.duration or 0, 1),
            'elapsed': round(time.monotonic() - t0, 1)}


async def health(request):
    return web.json_response({'status': 'ok', 'model': MODEL_NAME, 'loaded': _model is not None})


async def transcribe(request):
    tmp = None
    try:
        if request.content_type.startswith('multipart/'):
            reader = await request.multipart()
            language, path = None, None
            async for part in reader:
                if part.name == 'language':
                    language = (await part.text()).strip() or None
                elif part.name == 'file':
                    fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(part.filename or '')[1])
                    size = 0
                    with os.fdopen(fd, 'wb') as fh:
                        while chunk := await part.read_chunk():
                            size += len(chunk)
                            if size > MAX_UPLOAD:
                                return web.json_response({'error': 'Archivo demasiado grande'}, status=413)
                            fh.write(chunk)
                    path = tmp
            if not path:
                return web.json_response({'error': 'Falta el archivo'}, status=400)
        else:
            body = await request.json()
            language = body.get('language')
            path = os.path.realpath(body.get('path') or '')
            if not path.startswith(ALLOWED_DIR + os.sep) or not os.path.isfile(path):
                return web.json_response({'error': 'Ruta no permitida o inexistente'}, status=400)
        async with _lock:  # un audio a la vez: el modelo usa todos los hilos de CPU
            result = await asyncio.get_running_loop().run_in_executor(None, _transcribe, path, language)
        log.info(f"Transcrito {result['duration']} s en {result['elapsed']} s")
        return web.json_response(result)
    except ValueError as e:
        return web.json_response({'error': str(e)}, status=422)
    except Exception as e:
        log.exception('Error transcribiendo')
        return web.json_response({'error': f'{type(e).__name__}: {e}'}, status=500)
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def main():
    if os.getenv('WHISPER_PRELOAD', 'false').lower() == 'true':
        _load()
    app = web.Application(client_max_size=MAX_UPLOAD + 1024 * 1024)
    app.router.add_get('/health', health)
    app.router.add_post('/transcribe', transcribe)
    web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT', '9000')), access_log=None)


if __name__ == '__main__':
    main()
