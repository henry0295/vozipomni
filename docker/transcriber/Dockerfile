# Transcripción local de audios (faster-whisper en CPU). No envía audio a terceros.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt && useradd -m -u 1000 transcriber && mkdir -p /models && chown 1000:1000 /models
COPY server.py .

USER transcriber
EXPOSE 9000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/health', timeout=4)" || exit 1
CMD ["python", "server.py"]
