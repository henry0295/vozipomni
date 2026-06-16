#!/bin/bash
set -e

echo "=== VoziPOmni RTPEngine Entrypoint ==="

# ── 1. IP de la interfaz de red ────────────────────────────────────────────
INTERFACE_IP="${VOZIPOMNI_IPV4:-$(hostname -I | awk '{print $1}')}"

if [ -z "$INTERFACE_IP" ] || [ "$INTERFACE_IP" = "127.0.0.1" ]; then
    echo "ERROR: No se pudo determinar la IP de la interfaz"
    echo "  Usa la variable de entorno VOZIPOMNI_IPV4"
    exit 1
fi

# ── 2. Soporte NAT ────────────────────────────────────────────────────────
PUBLIC_IP="${NAT_IPV4:-}"
if [ -n "$PUBLIC_IP" ] && [ "$PUBLIC_IP" != "$INTERFACE_IP" ]; then
    NAT_INTERFACE="${INTERFACE_IP}!${PUBLIC_IP}"
    echo "  [entrypoint] NAT detectado"
    echo "  [entrypoint]   bind (privada):   $INTERFACE_IP"
    echo "  [entrypoint]   ICE SDP (pública): $PUBLIC_IP"
else
    NAT_INTERFACE="$INTERFACE_IP"
    echo "  [entrypoint] IP directa: $INTERFACE_IP"
fi

# ── 3. Restaurar config desde plantilla (evita corrupción por sed en restarts) ─
ORIG="/etc/rtpengine/rtpengine.conf.orig"
CONF="/etc/rtpengine/rtpengine.conf"
if [ -f "$ORIG" ]; then
    cp "$ORIG" "$CONF"
fi

sed -i "s|__INTERFACE_IP__|${NAT_INTERFACE}|g" "$CONF"

echo "  [entrypoint] Configuración RTPEngine:"
echo "  [entrypoint]   Interface: $NAT_INTERFACE"
echo "  [entrypoint]   listen-ng: 127.0.0.1:22222"
echo "  [entrypoint]   Puertos:   23000-23300/udp"
echo ""

# ── 4. Buscar binario ─────────────────────────────────────────────────────
RTPENGINE_BIN=$(command -v rtpengine 2>/dev/null || echo "/usr/local/bin/rtpengine")

if [ ! -x "$RTPENGINE_BIN" ]; then
    echo "ERROR: rtpengine binary not found"
    find /usr /usr/local -name rtpengine -type f 2>/dev/null | head -5
    exit 1
fi

echo "  [entrypoint] Binario: $RTPENGINE_BIN"
"$RTPENGINE_BIN" --version 2>&1 || true
echo ""

# ── 5. Arrancar con args CLI explícitos (más fiable que solo config file) ─
# table=-1: userspace-only, sin módulo kernel (requerido en Docker/host)
echo "=== Iniciando RTPEngine ==="
exec "$RTPENGINE_BIN" \
    --config-file="$CONF" \
    --foreground \
    --table=-1 \
    --interface="${NAT_INTERFACE}" \
    --listen-ng=127.0.0.1:22222 \
    --port-min=23000 \
    --port-max=23300 \
    --log-level=6 \
    --log-stderr
