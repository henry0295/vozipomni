#!/bin/bash
set -e

echo "=== VoziPOmni Kamailio Entrypoint ==="

# ── 1. Certificados TLS ───────────────────────────────────────────────────
# IMPORTANTE: kamailio.cfg usa tls.cfg que referencia archivos SEPARADOS
# de clave y certificado. NO combinar en un solo archivo.
if [ ! -f /etc/kamailio/kamailio-selfsigned.pem ] || [ ! -f /etc/kamailio/kamailio-selfsigned.key ]; then
    echo "  [entrypoint] Generando certificados TLS autofirmados para Kamailio..."
    openssl req -x509 -newkey rsa:2048 \
        -keyout /etc/kamailio/kamailio-selfsigned.key \
        -out /etc/kamailio/kamailio-selfsigned.pem \
        -days 3650 -nodes \
        -subj "/C=CO/ST=Bogota/L=Bogota/O=VoziPOmni/CN=kamailio" 2>/dev/null
    chmod 600 /etc/kamailio/kamailio-selfsigned.key
    chmod 644 /etc/kamailio/kamailio-selfsigned.pem
    echo "  [entrypoint] Certificados TLS creados"
fi

# ── 2. Reemplazar placeholders en kamailio.cfg ────────────────────────────
# Con network_mode: host, los nombres de servicio Docker no resuelven.
# Todos los servicios escuchan en la misma IP del host (VOZIPOMNI_IPV4).
KAM_CFG="/etc/kamailio/kamailio.cfg"

RTPENGINE_ADDR="${RTPENGINE_HOST:-127.0.0.1}"
ASTERISK_ADDR="${ASTERISK_HOST:-${VOZIPOMNI_IPV4:-127.0.0.1}}"
REDIS_ADDR="${REDIS_HOST:-${VOZIPOMNI_IPV4:-127.0.0.1}}"
# sipping_from: usar la IP del servidor como "dominio" del ping SIP keepalive
VOZIPOMNI_HOST="${VOZIPOMNI_IPV4:-127.0.0.1}"

sed -i "s|RTPENGINE_HOST_PLACEHOLDER|${RTPENGINE_ADDR}|g"   "$KAM_CFG"
sed -i "s|ASTERISK_HOST_PLACEHOLDER|${ASTERISK_ADDR}|g"     "$KAM_CFG"
sed -i "s|REDIS_HOST_PLACEHOLDER|${REDIS_ADDR}|g"           "$KAM_CFG"
sed -i "s|VOZIPOMNI_HOST_PLACEHOLDER|${VOZIPOMNI_HOST}|g"   "$KAM_CFG"

echo "  [entrypoint] RTPEngine   → ${RTPENGINE_ADDR}:22222"
echo "  [entrypoint] Asterisk    → ${ASTERISK_ADDR}:5080"
echo "  [entrypoint] Redis       → ${REDIS_ADDR}:6379"
echo "  [entrypoint] Sipping-from → sip:keepalive@${VOZIPOMNI_HOST}"

echo "=== Iniciando Kamailio ==="
exec kamailio -DD -E
