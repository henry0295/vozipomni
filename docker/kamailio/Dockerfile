# Dockerfile para Kamailio - WebRTC SIP Proxy
FROM kamailio/kamailio:5.7-alpine

# Instalar módulos necesarios
RUN apk add --no-cache \
    kamailio-tls \
    kamailio-websocket \
    kamailio-json \
    kamailio-redis \
    openssl

# Crear directorios necesarios
RUN mkdir -p /etc/kamailio /var/run/kamailio

# Copiar configuraciones
COPY kamailio.cfg /etc/kamailio/kamailio.cfg
COPY kamailio-local.cfg /etc/kamailio/kamailio-local.cfg

# Crear certificados auto-firmados si no existen
RUN if [ ! -f /etc/kamailio/kamailio-selfsigned.pem ]; then \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/kamailio/kamailio-selfsigned.key \
    -out /etc/kamailio/kamailio-selfsigned.pem \
    -subj "/C=CO/ST=Bogota/L=Bogota/O=VozipOmni/CN=kamailio"; \
    fi

EXPOSE 5060/udp 5060/tcp 5061/tcp 8080/tcp

CMD ["kamailio", "-DD", "-E"]
