#!/bin/bash
# Respaldo de VozipCX: base de datos, grabaciones, media y configuración.
#
# Uso:  sudo bash /opt/vozipomni/backup-production.sh
# deploy.sh lo programa a diario en /etc/cron.d/vozipomni-backup (03:30).
#
# Variables opcionales (en /opt/vozipomni/.env o en el entorno):
#   BACKUP_DIR             Carpeta local (default /var/backups/vozipomni)
#   BACKUP_RETENTION_DAYS  Días que se conservan los respaldos locales (default 14)
#   BACKUP_REMOTE          Destino remoto opcional:
#                            rsync:  usuario@host:/ruta   (requiere clave SSH)
#                            S3:     s3://bucket/ruta     (requiere aws cli configurado)
#   BACKUP_PASSPHRASE      Si se define, la copia de .env se cifra con openssl (AES-256)
#
# El .env contiene FIELD_ENCRYPTION_KEY: sin él no se pueden descifrar las claves
# SIP guardadas. Guarde los respaldos en un lugar seguro.
set -Eeuo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/vozipomni}"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.prod.yml"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

env_value() { grep "^$1=" "$INSTALL_DIR/.env" 2>/dev/null | tail -1 | cut -d= -f2- || true; }

BACKUP_DIR="${BACKUP_DIR:-$(env_value BACKUP_DIR)}";               BACKUP_DIR="${BACKUP_DIR:-/var/backups/vozipomni}"
RETENTION="${BACKUP_RETENTION_DAYS:-$(env_value BACKUP_RETENTION_DAYS)}"; RETENTION="${RETENTION:-14}"
REMOTE="${BACKUP_REMOTE:-$(env_value BACKUP_REMOTE)}"
PASSPHRASE="${BACKUP_PASSPHRASE:-$(env_value BACKUP_PASSPHRASE)}"
DB_USER="$(env_value POSTGRES_USER)"; DB_USER="${DB_USER:-vozipomni_user}"
DB_NAME="$(env_value POSTGRES_DB)";   DB_NAME="${DB_NAME:-vozipomni}"

log() { echo "[$(date '+%F %T')] $*"; }

DEST="$BACKUP_DIR/$STAMP"
mkdir -p "$DEST"
chmod 700 "$BACKUP_DIR" "$DEST"
cd "$INSTALL_DIR"

# Nombre real de un volumen del proyecto (vozipomni_<nombre>)
volume_path() {
    local v
    for v in "vozipomni_$1" "$1"; do
        docker volume inspect -f '{{.Mountpoint}}' "$v" 2>/dev/null && return 0
    done
    return 1
}

# 1. Base de datos
log "Respaldando PostgreSQL ($DB_NAME)..."
docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U "$DB_USER" -d "$DB_NAME" --format=custom \
    > "$DEST/postgres.dump"

# 2. Volúmenes con datos: grabaciones reales de Asterisk (spool), grabaciones
#    procesadas, media (adjuntos) y configuración dinámica de Asterisk
for vol in asterisk_spool recordings_volume media_volume asterisk_config; do
    if path="$(volume_path "$vol")"; then
        log "Respaldando volumen $vol..."
        tar --create --gzip --file "$DEST/$vol.tar.gz" -C "$path" . 2>/dev/null \
            || log "AVISO: no se pudo empaquetar $vol"
    fi
done

# 3. Configuración: .env (cifrado si hay BACKUP_PASSPHRASE), credenciales y certificados
if [ -n "$PASSPHRASE" ]; then
    export PASSPHRASE_ENV="$PASSPHRASE"
    tar --create --gzip -C "$INSTALL_DIR" .env backend/.env credentials.txt docker/nginx/ssl 2>/dev/null \
        | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:PASSPHRASE_ENV -out "$DEST/config.tar.gz.enc" \
        || log "AVISO: no se pudo cifrar la configuración"
    unset PASSPHRASE_ENV
    # Descifrar: openssl enc -d -aes-256-cbc -pbkdf2 -in config.tar.gz.enc | tar xz
else
    tar --create --gzip --file "$DEST/config.tar.gz" -C "$INSTALL_DIR" .env backend/.env credentials.txt docker/nginx/ssl 2>/dev/null \
        || log "AVISO: configuración respaldada parcialmente"
fi
chmod 600 "$DEST"/* 2>/dev/null || true

# 4. Copia remota opcional
if [ -n "$REMOTE" ]; then
    case "$REMOTE" in
        s3://*)
            if command -v aws >/dev/null 2>&1; then
                log "Copiando a $REMOTE/$STAMP ..."
                aws s3 cp --recursive --only-show-errors "$DEST" "$REMOTE/$STAMP" || log "AVISO: falló la copia a S3"
            else
                log "AVISO: BACKUP_REMOTE es S3 pero aws cli no está instalado"
            fi ;;
        *)
            if command -v rsync >/dev/null 2>&1; then
                log "Copiando a $REMOTE ..."
                rsync -a "$DEST" "$REMOTE/" || log "AVISO: falló la copia rsync"
            else
                log "AVISO: rsync no está instalado"
            fi ;;
    esac
fi

# 5. Retención local
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION" -exec rm -rf {} + 2>/dev/null || true

log "Respaldo completo en $DEST (retención local: $RETENTION días)"
du -sh "$DEST" 2>/dev/null || true
