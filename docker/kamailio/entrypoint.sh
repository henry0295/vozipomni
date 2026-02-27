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

# Sustituir placeholders en kamailio.cfg con las variables de entorno reales.
# Con network_mode: host los nombres de contenedor no resuelven;
# todos los servicios escuchan en la misma IP.
KAM_CFG="/etc/kamailio/kamailio.cfg"
RTPENGINE_ADDR="${RTPENGINE_HOST:-${VOZIPOMNI_IPV4:-127.0.0.1}}"
ASTERISK_ADDR="${ASTERISK_HOST:-${VOZIPOMNI_IPV4:-127.0.0.1}}"

sed -i "s|RTPENGINE_HOST_PLACEHOLDER|${RTPENGINE_ADDR}|g" "$KAM_CFG"
sed -i "s|ASTERISK_HOST_PLACEHOLDER|${ASTERISK_ADDR}|g"   "$KAM_CFG"

echo "  [entrypoint] RTPEngine  → ${RTPENGINE_ADDR}:22222"
echo "  [entrypoint] Asterisk   → ${ASTERISK_ADDR}:5060"

echo "=== Iniciando Kamailio ==="
exec kamailio -DD -E
