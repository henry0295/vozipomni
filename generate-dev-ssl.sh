#!/bin/bash
# =============================================================================
# VoziPOmni - Generador de Certificados SSL para Desarrollo
# =============================================================================
# WebRTC REQUIERE HTTPS. Este script genera certificados autofirmados para
# poder usar el softphone WebRTC durante el desarrollo local.
#
# Uso: ./generate-dev-ssl.sh [IP_DEL_SERVIDOR]
# =============================================================================

set -e

SSL_DIR="docker/nginx/ssl"
IP="${1:-}"

mkdir -p "$SSL_DIR"

# Leer VOZIPOMNI_IPV4 del .env si no se pasó IP como argumento
if [ -z "$IP" ] && [ -f ".env" ]; then
    IP=$(grep "^VOZIPOMNI_IPV4=" .env | cut -d= -f2 | tr -d ' ')
fi
if [ -z "$IP" ]; then
    IP="localhost"
fi

echo "=== Generando certificados SSL para desarrollo ==="
echo "  IP/CN: $IP"
echo "  Destino: $SSL_DIR"

# Config para SAN (Subject Alternative Names) — Chrome requiere SAN
cat > "$SSL_DIR/san.cfg" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no
[req_distinguished_name]
C  = CO
ST = Bogota
L  = Bogota
O  = VozipOmni
CN = $IP
[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
IP.1  = $IP
DNS.1 = localhost
DNS.2 = vozipomni
EOF

openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout "$SSL_DIR/vozipomni.key" \
    -out    "$SSL_DIR/vozipomni.crt" \
    -config "$SSL_DIR/san.cfg" \
    -extensions v3_req 2>/dev/null

rm -f "$SSL_DIR/san.cfg"
chmod 644 "$SSL_DIR/vozipomni.crt"
chmod 600 "$SSL_DIR/vozipomni.key"

echo ""
echo "✓ Certificados generados:"
echo "  $SSL_DIR/vozipomni.crt"
echo "  $SSL_DIR/vozipomni.key"
echo ""
echo "SIGUIENTE PASO:"
echo "  1. Reinicia nginx:  docker compose restart nginx"
echo "  2. Accede via HTTPS: https://$IP"
echo "  3. Acepta la advertencia del certificado autofirmado en el browser"
echo "  4. El softphone WebRTC ya podrá acceder al micrófono"
