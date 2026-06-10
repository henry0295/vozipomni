#!/bin/sh
# Nginx entrypoint: si los certificados SSL no existen, elimina el bloque HTTPS
# del default.conf para que nginx arranque correctamente en modo solo-HTTP.
set -e

CONF="/etc/nginx/conf.d/default.conf"
CERT="/etc/nginx/ssl/vozipomni.crt"
KEY="/etc/nginx/ssl/vozipomni.key"

if [ ! -f "$CERT" ] || [ ! -f "$KEY" ]; then
    echo "=== [nginx-entrypoint] Certificados SSL no encontrados ==="
    echo "    WebRTC NO funcionará (requiere HTTPS para micrófono)"
    echo "    Para habilitar HTTPS: ./generate-dev-ssl.sh  o  .\generate-dev-ssl.ps1"
    # Eliminar el bloque 'server { listen 443 ssl; ... }' del conf
    # usando awk para quitar el segundo bloque server{}
    awk '
      /^server \{/{block++}
      block == 2 { next }
      /^\}$/ && block > 0 { block--; next }
      {print}
    ' "$CONF" > /tmp/default_nossl.conf
    cp /tmp/default_nossl.conf "$CONF"
    echo "    Bloque HTTPS desactivado — nginx iniciando en modo HTTP"
else
    echo "=== [nginx-entrypoint] Certificados SSL encontrados — HTTPS activo ==="
fi

exec nginx -g "daemon off;"
