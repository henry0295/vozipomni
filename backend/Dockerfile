FROM python:3.11-slim

LABEL maintainer="VoziPOmni Team"
LABEL description="Backend Django para VoziPOmni Contact Center"

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    postgresql-client \
    libpq-dev \
    gettext \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
# En producción se usa requirements/prod.txt (excluye herramientas de dev/test)
COPY requirements.txt requirements.txt
COPY requirements/ requirements/
RUN pip install --upgrade pip && \
    pip install -r requirements/prod.txt

# Copiar código de la aplicación
COPY . .

# Crear directorios necesarios con permisos correctos
RUN mkdir -p static media recordings logs && \
    chmod 755 static media recordings logs

# Crear usuario no-root para ejecutar la aplicación
RUN useradd -m -u 1000 vozipomni && \
    chown -R vozipomni:vozipomni /app && \
    chmod -R 755 /app/logs

USER vozipomni

# Exponer puerto
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=15s --timeout=10s --start-period=120s --retries=10 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

# Comando por defecto
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
