#!/bin/sh
# Selecciona automáticamente la configuración HTTPS si existen certificados SSL.
# Si no existen, los genera automáticamente con OpenSSL.
# Este script es ejecutado por el entrypoint de nginx (docker-entrypoint.d/).

SSL_DIR="/etc/nginx/ssl"
SSL_CERT="${SSL_DIR}/vozipomni.crt"
SSL_KEY="${SSL_DIR}/vozipomni.key"
HTTPS_CONF="/etc/nginx/conf.d/default.https.conf.bak"
ACTIVE_CONF="/etc/nginx/conf.d/default.conf"

# Obtener IP del servidor para el CN del certificado
SERVER_IP="${VOZIPOMNI_IPV4:-127.0.0.1}"

# Generar certificados autofirmados si no existen
if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
    echo "[SSL-switch] Certificados no encontrados — generando autofirmados..."
    mkdir -p "$SSL_DIR"

    # Generar certificado autofirmado válido 3650 días
    # Con SAN (subjectAltName) para la IP del servidor
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "$SSL_KEY" \
        -out    "$SSL_CERT" \
        -subj   "/C=CO/ST=Bogota/L=Bogota/O=VoziPOmni/CN=${SERVER_IP}" \
        -addext "subjectAltName=IP:${SERVER_IP},DNS:localhost" \
        2>/dev/null || \
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "$SSL_KEY" \
        -out    "$SSL_CERT" \
        -subj   "/C=CO/ST=Bogota/L=Bogota/O=VoziPOmni/CN=${SERVER_IP}" \
        2>/dev/null

    if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
        chmod 644 "$SSL_CERT"
        chmod 600 "$SSL_KEY"
        echo "[SSL-switch] ✓ Certificados SSL generados para IP: ${SERVER_IP}"
    else
        echo "[SSL-switch] ERROR: No se pudieron generar certificados SSL"
        echo "[SSL-switch] Nginx iniciará en modo HTTP sin WebRTC"
        exit 0
    fi
fi

# Activar configuración HTTPS
echo "[SSL-switch] Certificados encontrados → activando configuración HTTPS"
cp "$HTTPS_CONF" "$ACTIVE_CONF"
echo "[SSL-switch] ✓ Nginx configurado para HTTPS (wss:// disponible para WebRTC)"
echo "[SSL-switch]   Certificado: $SSL_CERT"
echo "[SSL-switch]   Clave:       $SSL_KEY"
echo ""
echo "[SSL-switch] IMPORTANTE: El certificado es autofirmado."
echo "[SSL-switch] El browser mostrará advertencia de seguridad."
echo "[SSL-switch] Acepta el certificado en:"
echo "[SSL-switch]   https://${SERVER_IP}"
