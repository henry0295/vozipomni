#!/bin/bash
set -e

echo "=== VoziPOmni RTPEngine Entrypoint ==="

# Obtener la IP de la interfaz o usar variable de entorno
INTERFACE_IP="${VOZIPOMNI_IPV4:-$(hostname -I | awk '{print $1}')}"

if [ -z "$INTERFACE_IP" ] || [ "$INTERFACE_IP" = "127.0.0.1" ]; then
    echo "ERROR: No se pudo determinar la IP de la interfaz"
    echo "  Usa la variable de entorno VOZIPOMNI_IPV4"
    exit 1
fi

echo "  [entrypoint] Configurando interfaz de red: $INTERFACE_IP"

# Reemplazar __INTERFACE_IP__ en la configuración
sed -i "s/__INTERFACE_IP__/$INTERFACE_IP/g" /etc/rtpengine/rtpengine.conf

echo "=== Iniciando RTPEngine ==="
cat /etc/rtpengine/rtpengine.conf

# Ejecutar rtpengine (puede estar en /usr/sbin o /usr/local/bin)
RTPENGINE_BIN=$(which rtpengine || echo "/usr/local/bin/rtpengine")

if [ ! -f "$RTPENGINE_BIN" ]; then
    echo "ERROR: rtpengine binary not found"
    exit 1
fi

exec "$RTPENGINE_BIN" --config-file=/etc/rtpengine/rtpengine.conf --foreground
