#!/bin/sh
# ============================================================================
# VoziPOmni - Asterisk Container Entrypoint
# ============================================================================

set -e

CONFIG_DIR="/etc/asterisk"
DYNAMIC_DIR="/var/lib/asterisk/dynamic"
KEYS_DIR="${CONFIG_DIR}/keys"

echo "=== VoziPOmni Asterisk Entrypoint ==="

# -------------------------------------------------------
# 0. Crear directorios necesarios
# -------------------------------------------------------
mkdir -p "${DYNAMIC_DIR}"
mkdir -p /var/log/asterisk/cdr-csv
mkdir -p /var/log/asterisk/cdr-custom
echo "  [entrypoint] Directorios creados"

# -------------------------------------------------------
# 1. Placeholders vacíos para archivos dinámicos
#    (evita que #include/#tryinclude falle al primer arranque)
# -------------------------------------------------------
for conf in pjsip_extensions.conf pjsip_wizard.conf extensions_dynamic.conf \
            queues_dynamic.conf pjsip_agents.conf; do
    if [ ! -f "${DYNAMIC_DIR}/${conf}" ]; then
        echo "; Placeholder — gestionado por VoziPOmni backend" \
            > "${DYNAMIC_DIR}/${conf}"
        echo "  [entrypoint] Creado ${DYNAMIC_DIR}/${conf} (placeholder)"
    fi
done

# -------------------------------------------------------
# 2. Detectar y validar VOZIPOMNI_IPV4
# -------------------------------------------------------
if [ -z "${VOZIPOMNI_IPV4}" ]; then
    echo "  [entrypoint] VOZIPOMNI_IPV4 no definido — intentando auto-detectar..."
    VOZIPOMNI_IPV4=$(curl -4 -s --max-time 5 https://api.ipify.org 2>/dev/null || \
                     curl -4 -s --max-time 5 https://ifconfig.me  2>/dev/null || \
                     echo "")
    if [ -n "${VOZIPOMNI_IPV4}" ]; then
        echo "  [entrypoint] IP auto-detectada: ${VOZIPOMNI_IPV4}"
    else
        echo "  [entrypoint] ERROR: No se pudo detectar IP. Las troncales NAT NO funcionarán."
    fi
fi

EXTERNAL_IP="${NAT_IPV4:-${VOZIPOMNI_IPV4}}"

echo "  [entrypoint] IP local:    ${VOZIPOMNI_IPV4:-<no definida>}"
echo "  [entrypoint] IP externa:  ${EXTERNAL_IP:-<no definida>}"

# -------------------------------------------------------
# 3. Inyectar external_media/signaling_address en trunk-nat-transport
#
# pjsip.conf es un bind-mount de solo-lectura (del host).
# NO se puede modificar con sed de forma persistente porque
# el contenido del host se vuelve a montar en cada restart.
#
# SOLUCIÓN: trunk-nat-transport tiene las líneas comentadas
# ("; external_media_address= ..."). El entrypoint inyecta
# los valores en un archivo separado que pjsip.conf incluye
# via #tryinclude.
# -------------------------------------------------------
PJSIP_CONF="${CONFIG_DIR}/pjsip.conf"

if [ -n "${EXTERNAL_IP}" ]; then
    # El transport trunk-nat-transport NO soporta recarga parcial ni append ('+').
    # La única forma de inyectar external_media_address es via sed sobre una
    # COPIA del archivo en el directorio dinámico que Asterisk lee primero.
    # pjsip.conf estático tiene las líneas comentadas. En el siguiente reload,
    # Asterisk usará el archivo de /etc/asterisk/ (bind-mount del host).
    #
    # SOLUCIÓN: Copiar pjsip.conf a /tmp, inyectar la IP, y usar el path
    # alternativo. Pero como pjsip.conf es leído desde /etc/asterisk (bind-mount),
    # la única solución confiable es hacer sed en el archivo del CONTENEDOR
    # antes del primer arranque (no en reloads posteriores).
    #
    # El bind-mount monta el archivo HOST en el contenedor. sed -i modifica
    # la copia del contenedor. En el próximo arranque del contenedor, Docker
    # vuelve a montar el original del host. Para reloads dentro del mismo
    # contenedor, la copia modificada persiste.
    PJSIP_CONF="${CONFIG_DIR}/pjsip.conf"
    if [ -f "${PJSIP_CONF}" ]; then
        if grep -q "^external_media_address=" "${PJSIP_CONF}"; then
            sed -i "s|^external_media_address=.*|external_media_address=${EXTERNAL_IP}|" "${PJSIP_CONF}"
            sed -i "s|^external_signaling_address=.*|external_signaling_address=${EXTERNAL_IP}|" "${PJSIP_CONF}"
        else
            # Insertar después de bind=0.0.0.0:5162
            sed -i "/^bind=0\.0\.0\.0:5162$/a\\
external_media_address=${EXTERNAL_IP}\\
external_signaling_address=${EXTERNAL_IP}" "${PJSIP_CONF}"
        fi
        echo "  [entrypoint] ✓ trunk-nat-transport: external_*=${EXTERNAL_IP} inyectado en pjsip.conf"
    fi
    # Archivo de marca para saber que fue inyectado
    echo "${EXTERNAL_IP}" > "${DYNAMIC_DIR}/trunk_nat_address.conf"
else
    echo "; Sin IP externa" > "${DYNAMIC_DIR}/trunk_nat_address.conf"
    echo "  [entrypoint] ⚠ Sin IP externa — trunk-nat-transport sin NAT"
fi

# -------------------------------------------------------
# 4. Generar kamailio_identify.conf con la IP real del servidor
#
# PROBLEMA: res_pjsip_endpoint_identifier_ip NO interpreta ${ENV(...)}
# en pjsip.conf — solo el dialplan lo hace. Cada vez que Asterisk
# recarga pjsip.conf, el bind-mount restaura el ${ENV(...)} original
# y el identify falla con "Invalid IP address".
#
# SOLUCIÓN: Generar el identify en /var/lib/asterisk/dynamic/ con la
# IP real. pjsip.conf incluye este archivo via #tryinclude AL FINAL,
# lo que SOBREESCRIBE el identify estático (PJSIP fusiona secciones
# del mismo nombre — la última definición gana para 'identify').
# -------------------------------------------------------
if [ -n "${VOZIPOMNI_IPV4}" ]; then
    cat > "${DYNAMIC_DIR}/kamailio_identify.conf" <<EOF
; Auto-generado por entrypoint.sh — NO EDITAR MANUALMENTE
; Agrega match con la IP real del servidor al kamailio-endpoint-identify.
; PJSIP fusiona múltiples secciones con el mismo nombre, por eso
; este archivo AGREGA el match correcto al identify estático de pjsip.conf.

[kamailio-endpoint-identify]
type=identify
endpoint=kamailio-endpoint
match=${VOZIPOMNI_IPV4}/32
EOF
    echo "  [entrypoint] ✓ kamailio_identify.conf: match=${VOZIPOMNI_IPV4}/32"
else
    echo "; Sin VOZIPOMNI_IPV4 — usando solo fallbacks del pjsip.conf estático" \
        > "${DYNAMIC_DIR}/kamailio_identify.conf"
    echo "  [entrypoint] ⚠ kamailio_identify.conf sin IP pública"
fi

# -------------------------------------------------------
# 5. Certificados TLS para WebRTC (autofirmados)
# -------------------------------------------------------
if [ ! -f "${KEYS_DIR}/asterisk.pem" ]; then
    echo "  [entrypoint] Generando certificados TLS..."
    mkdir -p "${KEYS_DIR}"
    openssl req -x509 -nodes -days 3650 \
        -newkey rsa:2048 \
        -keyout "${KEYS_DIR}/asterisk.key" \
        -out    "${KEYS_DIR}/asterisk.pem" \
        -subj   "/CN=vozipomni-asterisk/O=VoziPOmni/C=CO" \
        2>/dev/null
    cat "${KEYS_DIR}/asterisk.key" "${KEYS_DIR}/asterisk.pem" \
        > "${KEYS_DIR}/asterisk-combined.pem"
    echo "  [entrypoint] ✓ Certificados TLS creados"
fi

# -------------------------------------------------------
# 6. Permisos
# -------------------------------------------------------
chown -R asterisk:asterisk "${CONFIG_DIR}"    2>/dev/null || true
chown -R asterisk:asterisk "${DYNAMIC_DIR}"   2>/dev/null || true
chmod -R 777 "${DYNAMIC_DIR}"                 2>/dev/null || true
chown -R asterisk:asterisk /var/log/asterisk  2>/dev/null || true
chown -R asterisk:asterisk /var/run/asterisk  2>/dev/null || true
chown -R asterisk:asterisk /var/spool/asterisk 2>/dev/null || true

# -------------------------------------------------------
# 7. Fix DNS: con network_mode:host el nombre "asterisk" no resuelve
# -------------------------------------------------------
if ! grep -qF "127.0.0.1 asterisk" /etc/hosts 2>/dev/null; then
    echo "127.0.0.1 asterisk" >> /etc/hosts
    echo "  [entrypoint] /etc/hosts → '127.0.0.1 asterisk' (fix DNS host network)"
fi

echo ""
echo "=== Iniciando Asterisk ==="
exec /usr/sbin/asterisk -f -vvv -U asterisk -G asterisk
