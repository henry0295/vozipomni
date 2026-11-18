#!/bin/sh
# Genera la ACL de /admin/ (Django admin) según DJANGO_ADMIN_ALLOW.
# La ejecuta el entrypoint de nginx (docker-entrypoint.d/02-admin-acl.sh).
#
#   private (por defecto)  localhost y redes privadas RFC 1918
#   all                    sin restricción
#   off                    /admin/ bloqueado para todos
#   lista de CIDR          p. ej. "203.0.113.10,198.51.100.0/24" (solo IPv4)
#   cualquier otro valor   /admin/ bloqueado
#
# Siempre escribe el archivo, para que el include de nginx nunca quede roto.

ACL_DIR="/etc/nginx/vozipomni"
ACL_FILE="${ACL_DIR}/admin_acl.inc"
VALUE="$(printf '%s' "${DJANGO_ADMIN_ALLOW:-private}" | tr -d '[:space:]')"

mkdir -p "$ACL_DIR"

valid_ipv4_cidr() {
    printf '%s' "$1" | grep -Eq '^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(/(3[0-2]|[12]?[0-9]))?$'
}

TMP_FILE="${ACL_FILE}.tmp"
{
    echo "# Generado por admin-acl.sh (DJANGO_ADMIN_ALLOW=${VALUE})"
    case "$VALUE" in
        private)
            echo "allow 127.0.0.1;"
            echo "allow 10.0.0.0/8;"
            echo "allow 172.16.0.0/12;"
            echo "allow 192.168.0.0/16;"
            echo "deny all;"
            ;;
        all)
            echo "# sin restricción"
            ;;
        off)
            echo "deny all;"
            ;;
        *)
            if printf '%s' "$VALUE" | grep -Eq '^[0-9./,]+$'; then
                count=0
                OLD_IFS="$IFS"
                IFS=','
                for item in $VALUE; do
                    [ -z "$item" ] && continue
                    if valid_ipv4_cidr "$item"; then
                        echo "allow ${item};"
                        count=$((count + 1))
                    else
                        echo "[admin-acl] AVISO: valor descartado en DJANGO_ADMIN_ALLOW: ${item}" >&2
                    fi
                done
                IFS="$OLD_IFS"
                if [ "$count" -eq 0 ]; then
                    echo "[admin-acl] AVISO: DJANGO_ADMIN_ALLOW sin direcciones válidas: /admin/ bloqueado" >&2
                fi
                echo "deny all;"
            else
                echo "[admin-acl] AVISO: DJANGO_ADMIN_ALLOW desconocido: /admin/ bloqueado" >&2
                echo "deny all;"
            fi
            ;;
    esac
} > "$TMP_FILE"
mv -f "$TMP_FILE" "$ACL_FILE"

echo "[admin-acl] ✓ ACL de /admin/ generada (DJANGO_ADMIN_ALLOW=${VALUE})"
exit 0
