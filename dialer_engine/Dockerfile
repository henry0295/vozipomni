FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY dialer.py .

# Variables de entorno
ENV REDIS_URL=redis://localhost:6379/0
ENV ASTERISK_HOST=asterisk
ENV ASTERISK_AMI_PORT=5038
ENV ASTERISK_AMI_USER=admin
ENV ASTERISK_AMI_PASSWORD=

CMD ["python", "dialer.py"]
