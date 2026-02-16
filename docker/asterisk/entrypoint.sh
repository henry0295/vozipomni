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
KEYS_DIR="${CONFIG_DIR}/keys"

echo "=== VoziPOmni Asterisk Entrypoint ==="

# -------------------------------------------------------
# 1. Archivos de inclusión dinámica (placeholders vacíos)
# -------------------------------------------------------
for conf in pjsip_extensions.conf pjsip_wizard.conf extensions_dynamic.conf; do
    if [ ! -f "${CONFIG_DIR}/${conf}" ]; then
        echo "; Auto-generated placeholder — managed by VoziPOmni backend" > "${CONFIG_DIR}/${conf}"
        echo "  [entrypoint] Creado ${conf} (placeholder)"
    fi
done

# -------------------------------------------------------
# 2. Inyectar IP pública en trunk-nat-transport
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
else
    if [ -z "${VOZIPOMNI_IPV4}" ]; then
        echo "  [entrypoint] AVISO: VOZIPOMNI_IPV4 no definido — trunk-nat-transport sin external_*"
    fi
fi

# -------------------------------------------------------
# 3. Certificados TLS para WebRTC (autofirmados)
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
# 4. Permisos
# -------------------------------------------------------
chown -R asterisk:asterisk "${CONFIG_DIR}" 2>/dev/null || true
chown -R asterisk:asterisk /var/log/asterisk 2>/dev/null || true
chown -R asterisk:asterisk /var/run/asterisk 2>/dev/null || true
chown -R asterisk:asterisk /var/spool/asterisk 2>/dev/null || true

echo "=== Iniciando Asterisk ==="
exec /usr/sbin/asterisk -f -vvv -U asterisk -G asterisk
