#!/bin/bash
set -e

echo "=== VoziPOmni Kamailio Entrypoint ==="

# Crear certificados TLS autofirmados si no existen
if [ ! -f /etc/kamailio/cert.pem ]; then
    echo "  [entrypoint] Generando certificados TLS autofirmados para Kamailio..."
    openssl req -x509 -newkey rsa:2048 -keyout /etc/kamailio/cert.pem -out /etc/kamailio/cert.pem \
        -days 3650 -nodes -subj "/C=CO/ST=Bogota/L=Bogota/O=VoziPOmni/CN=kamailio" 2>/dev/null
    chmod 600 /etc/kamailio/cert.pem
    echo "  [entrypoint] Certificados TLS creados en /etc/kamailio/cert.pem"
fi

echo "=== Iniciando Kamailio ==="
exec kamailio -DD -E
