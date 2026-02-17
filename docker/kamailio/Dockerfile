# Dockerfile para Kamailio - WebRTC SIP Proxy
FROM debian:bookworm-slim

# Instalar Kamailio desde paquetes Debian
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg2 \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.kamailio.org/kamailiodebkey.gpg | gpg --dearmor -o /usr/share/keyrings/kamailio.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/kamailio.gpg] http://deb.kamailio.org/kamailio57 bookworm main" > /etc/apt/sources.list.d/kamailio.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    kamailio \
    kamailio-tls-modules \
    kamailio-websocket-modules \
    kamailio-json-modules \
    kamailio-redis-modules \
    kamailio-extra-modules \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorios necesarios
RUN mkdir -p /etc/kamailio /var/run/kamailio

# Copiar configuraciones
COPY kamailio.cfg /etc/kamailio/kamailio.cfg
COPY kamailio-local.cfg /etc/kamailio/kamailio-local.cfg

# Copiar entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5060/udp 5060/tcp 5061/tcp 8080/tcp

ENTRYPOINT ["/entrypoint.sh"]
