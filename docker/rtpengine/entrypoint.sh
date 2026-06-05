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

# Soporte NAT: si NAT_IPV4 está definida y es distinta a la IP local,
# usar notación local!público para que RTPEngine anuncie la IP pública en el SDP
# pero enlace en la IP privada (interfaz real del servidor).
# Equivalente al parámetro --nat-ip de rtpengine.
PUBLIC_IP="${NAT_IPV4:-}"
if [ -n "$PUBLIC_IP" ] && [ "$PUBLIC_IP" != "$INTERFACE_IP" ]; then
    NAT_INTERFACE="${INTERFACE_IP}!${PUBLIC_IP}"
    echo "  [entrypoint] NAT detectado — bind: $INTERFACE_IP  anuncio SDP: $PUBLIC_IP"
else
    NAT_INTERFACE="$INTERFACE_IP"
    echo "  [entrypoint] Configurando interfaz de red: $INTERFACE_IP"
fi

# Reemplazar __INTERFACE_IP__ en la configuración
sed -i "s/__INTERFACE_IP__/$NAT_INTERFACE/g" /etc/rtpengine/rtpengine.conf

echo "=== Iniciando RTPEngine ==="
cat /etc/rtpengine/rtpengine.conf

# Ejecutar rtpengine (puede estar en /usr/sbin o /usr/local/bin)
RTPENGINE_BIN=$(which rtpengine || echo "/usr/local/bin/rtpengine")

if [ ! -f "$RTPENGINE_BIN" ]; then
    echo "ERROR: rtpengine binary not found"
    exit 1
fi

exec "$RTPENGINE_BIN" --config-file=/etc/rtpengine/rtpengine.conf --foreground
