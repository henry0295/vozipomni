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
# Si NAT_IPV4 está definida y es distinta a la IP local, usar notación
# local!público para que RTPEngine anuncie la IP pública en el SDP (candidatos ICE)
# pero enlace en la IP privada (interfaz real del servidor).
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

# ── 3. Reemplazar placeholders en rtpengine.conf ───────────────────────────
# __INTERFACE_IP__  → IP de la interfaz (con o sin notación local!público)
# __REDIS_HOST__    → IP del servidor para Redis (en network_mode:host = VOZIPOMNI_IPV4)
# __REDIS_PASSWORD__ → Contraseña de Redis desde variable de entorno
REDIS_HOST="${VOZIPOMNI_IPV4:-127.0.0.1}"
REDIS_PASSWORD="${REDIS_PASSWORD:-vozipomni_redis_2026}"

sed -i "s|__INTERFACE_IP__|${NAT_INTERFACE}|g"   /etc/rtpengine/rtpengine.conf
sed -i "s|__REDIS_HOST__|${REDIS_HOST}|g"        /etc/rtpengine/rtpengine.conf
sed -i "s|__REDIS_PASSWORD__|${REDIS_PASSWORD}|g" /etc/rtpengine/rtpengine.conf

echo "  [entrypoint] Configuración RTPEngine:"
echo "  [entrypoint]   Interface: $NAT_INTERFACE"
echo "  [entrypoint]   Redis:     $REDIS_HOST:6379 (db=5)"
echo "  [entrypoint]   Puertos:   23000-23300/udp"
echo ""

# ── 4. Mostrar config final para diagnóstico ──────────────────────────────
cat /etc/rtpengine/rtpengine.conf

# ── 5. Buscar y ejecutar rtpengine ────────────────────────────────────────
RTPENGINE_BIN=$(which rtpengine 2>/dev/null || echo "/usr/local/bin/rtpengine")

if [ ! -f "$RTPENGINE_BIN" ]; then
    echo "ERROR: rtpengine binary not found at $RTPENGINE_BIN"
    echo "  Busca en: $(find /usr /usr/local -name rtpengine 2>/dev/null | head -5)"
    exit 1
fi

echo "=== Iniciando RTPEngine ($RTPENGINE_BIN) ==="
# table=-1: userspace-only — no requiere módulo kernel (necesario en Docker)
exec "$RTPENGINE_BIN" --config-file=/etc/rtpengine/rtpengine.conf --foreground --table=-1
