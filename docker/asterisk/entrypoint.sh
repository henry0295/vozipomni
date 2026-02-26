#!/bin/sh
# ============================================================================
# VoziPOmni - Asterisk Container Entrypoint
# ============================================================================
# 1. Crea archivos de configuración vacíos si no existen
#    (evita que #include falle al iniciar Asterisk por primera vez)
# 2. Inyecta la IP pública (VOZIPOMNI_IPV4) en trunk-nat-transport
# 3. Genera certificados TLS autofirmados para WebRTC si no existen
# 4. Fija permisos y ejecuta Asterisk en foreground
# ============================================================================

set -e

CONFIG_DIR="/etc/asterisk"
DYNAMIC_DIR="/var/lib/asterisk/dynamic"
KEYS_DIR="${CONFIG_DIR}/keys"

echo "=== VoziPOmni Asterisk Entrypoint ==="

# -------------------------------------------------------
# 0. Crear directorio para configuraciones dinámicas
# -------------------------------------------------------
mkdir -p "${DYNAMIC_DIR}"
echo "  [entrypoint] Directorio de configs dinámicas: ${DYNAMIC_DIR}"

# -------------------------------------------------------
# 1. Ajustar maxload según cores disponibles del sistema
# -------------------------------------------------------
CORES=$(nproc 2>/dev/null || echo 1)
# maxload = cores * 0.9 (permite usar ~90% de la capacidad del sistema)
if command -v bc >/dev/null 2>&1; then
    MAXLOAD=$(echo "$CORES * 0.9" | bc)
else
    # Fallback sin bc: usar el número de cores directamente
    MAXLOAD=$CORES
fi
echo "  [entrypoint] CPUs detectados: ${CORES} → maxload = ${MAXLOAD}"

# Reemplazar placeholder o valor existente en asterisk.conf
ASTERISK_CONF="${CONFIG_DIR}/asterisk.conf"
if [ -f "${ASTERISK_CONF}" ]; then
    sed -i "s/^maxload.*/maxload = ${MAXLOAD}/" "${ASTERISK_CONF}"
    echo "  [entrypoint] asterisk.conf → maxload = ${MAXLOAD}"
fi

# -------------------------------------------------------
# 2. Archivos de inclusión dinámica (placeholders vacíos)
# -------------------------------------------------------
for conf in pjsip_extensions.conf pjsip_wizard.conf extensions_dynamic.conf queues_dynamic.conf; do
    if [ ! -f "${DYNAMIC_DIR}/${conf}" ]; then
        echo "; Auto-generated placeholder — managed by VoziPOmni backend" > "${DYNAMIC_DIR}/${conf}"
        echo "  [entrypoint] Creado ${DYNAMIC_DIR}/${conf} (placeholder)"
    fi
done

# -------------------------------------------------------
# 2b. Crear directorios CDR
# -------------------------------------------------------
mkdir -p /var/log/asterisk/cdr-csv
mkdir -p /var/log/asterisk/cdr-custom
chown -R asterisk:asterisk /var/log/asterisk/cdr-csv 2>/dev/null || true
chown -R asterisk:asterisk /var/log/asterisk/cdr-custom 2>/dev/null || true
echo "  [entrypoint] Directorios CDR creados"

# -------------------------------------------------------
# 3. Auto-detección y validación de IP pública
# -------------------------------------------------------
if [ -z "${VOZIPOMNI_IPV4}" ]; then
    echo "  [entrypoint] VOZIPOMNI_IPV4 no definido — intentando auto-detectar..."
    VOZIPOMNI_IPV4=$(curl -4 -s --max-time 5 https://api.ipify.org 2>/dev/null || \
                     curl -4 -s --max-time 5 https://ifconfig.me 2>/dev/null || \
                     curl -4 -s --max-time 5 https://icanhazip.com 2>/dev/null || \
                     echo "")
    if [ -n "${VOZIPOMNI_IPV4}" ]; then
        echo "  [entrypoint] IP pública auto-detectada: ${VOZIPOMNI_IPV4}"
    else
        echo "  [entrypoint] ERROR: No se pudo detectar IP pública. Las troncales con NAT NO funcionarán."
    fi
fi

# Validar que la IP no sea privada
if [ -n "${VOZIPOMNI_IPV4}" ]; then
    case "${VOZIPOMNI_IPV4}" in
        10.*|172.1[6-9].*|172.2[0-9].*|172.3[0-1].*|192.168.*)
            echo "  [entrypoint] ⚠ AVISO: IP detectada es PRIVADA (${VOZIPOMNI_IPV4})"
            echo "  [entrypoint]   Las llamadas SIP con NAT probablemente NO tendrán audio."
            echo "  [entrypoint]   Configure VOZIPOMNI_IPV4 con la IP pública real del servidor."
            ;;
    esac
fi

# -------------------------------------------------------
# 4. Inyectar IP pública en trunk-nat-transport
# -------------------------------------------------------
PJSIP_CONF="${CONFIG_DIR}/pjsip.conf"
if [ -n "${VOZIPOMNI_IPV4}" ] && [ -f "${PJSIP_CONF}" ]; then
    echo "  [entrypoint] Inyectando VOZIPOMNI_IPV4=${VOZIPOMNI_IPV4} en trunk-nat-transport"

    # Si ya existen líneas external_*, reemplazarlas; si no, agregarlas después de bind
    if grep -q "^external_media_address=" "${PJSIP_CONF}"; then
        sed -i "s|^external_media_address=.*|external_media_address=${VOZIPOMNI_IPV4}|" "${PJSIP_CONF}"
        sed -i "s|^external_signaling_address=.*|external_signaling_address=${VOZIPOMNI_IPV4}|" "${PJSIP_CONF}"
    else
        # Insertar después de "bind=0.0.0.0:5162"
        sed -i "/^\[trunk-nat-transport\]/,/^\[/ {
            /^bind=0\.0\.0\.0:5162/a\\
external_media_address=${VOZIPOMNI_IPV4}\\
external_signaling_address=${VOZIPOMNI_IPV4}
        }" "${PJSIP_CONF}"
    fi
    echo "  [entrypoint] ✓ trunk-nat-transport configurado con IP ${VOZIPOMNI_IPV4}"
else
    if [ -z "${VOZIPOMNI_IPV4}" ]; then
        echo "  [entrypoint] ⚠ AVISO: VOZIPOMNI_IPV4 no definido — trunk-nat-transport sin external_*"
        echo "  [entrypoint]   Las llamadas salientes por troncales NAT NO tendrán audio."
    fi
fi

# -------------------------------------------------------
# 5. Certificados TLS para WebRTC (autofirmados)
# -------------------------------------------------------
if [ ! -f "${KEYS_DIR}/asterisk.pem" ]; then
    echo "  [entrypoint] Generando certificados TLS autofirmados para WebRTC..."
    mkdir -p "${KEYS_DIR}"
    openssl req -x509 -nodes -days 3650 \
        -newkey rsa:2048 \
        -keyout "${KEYS_DIR}/asterisk.key" \
        -out "${KEYS_DIR}/asterisk.pem" \
        -subj "/CN=vozipomni-asterisk/O=VoziPOmni/C=CO" \
        2>/dev/null
    # Combinar key + cert para transports que lo requieran
    cat "${KEYS_DIR}/asterisk.key" "${KEYS_DIR}/asterisk.pem" > "${KEYS_DIR}/asterisk-combined.pem"
    echo "  [entrypoint] Certificados creados en ${KEYS_DIR}"
fi

# -------------------------------------------------------
# 6. Permisos
# -------------------------------------------------------
chown -R asterisk:asterisk "${CONFIG_DIR}" 2>/dev/null || true
chown -R asterisk:asterisk "${DYNAMIC_DIR}" 2>/dev/null || true
chmod -R 777 "${DYNAMIC_DIR}" 2>/dev/null || true  # Permitir escritura desde backend
chown -R asterisk:asterisk /var/log/asterisk 2>/dev/null || true
chown -R asterisk:asterisk /var/run/asterisk 2>/dev/null || true
chown -R asterisk:asterisk /var/spool/asterisk 2>/dev/null || true

echo "=== Iniciando Asterisk ==="
exec /usr/sbin/asterisk -f -vvv -U asterisk -G asterisk
