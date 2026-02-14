FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY server.py .

# Variables de entorno por defecto
ENV WS_HOST=0.0.0.0
ENV WS_PORT=8765
ENV REDIS_URL=redis://localhost:6379/0

EXPOSE 8765

CMD ["python", "server.py"]
