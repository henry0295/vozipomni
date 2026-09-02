#!/bin/bash
set -Eeuo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/vozipomni}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/vozipomni}"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.prod.yml"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

if [ -f "$INSTALL_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$INSTALL_DIR/.env"
  set +a
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
cd "$INSTALL_DIR"

docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dump \
  -U "${POSTGRES_USER:?POSTGRES_USER must be set}" \
  -d "${POSTGRES_DB:-vozipomni}" --format=custom \
  > "$BACKUP_DIR/postgres-$STAMP.dump"

tar --create --gzip --file "$BACKUP_DIR/recordings-$STAMP.tar.gz" \
  -C "$(docker volume inspect -f '{{.Mountpoint}}' vozipomni_recordings_volume 2>/dev/null || docker volume inspect -f '{{.Mountpoint}}' vozipomni_recordings)" .

find "$BACKUP_DIR" -type f -mtime +30 -delete
echo "Backup creado en $BACKUP_DIR con retención local de 30 días."