# Respaldos

Este documento explica qué datos de VozipCX hay que respaldar, cómo usar `backup-production.sh`, cómo hacer respaldos y restauraciones manuales de PostgreSQL y de los volúmenes, y cómo recuperar la plataforma en un servidor nuevo. Incluye recomendaciones de retención.

Los comandos asumen la instalación en `/opt/vozipomni` y el directorio de respaldos por defecto `/var/backups/vozipomni`. Ejecútelos como root.

```bash
cd /opt/vozipomni
export BACKUP_DIR=/var/backups/vozipomni
export STAMP=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$BACKUP_DIR" && chmod 700 "$BACKUP_DIR"
```

## Qué respaldar

| Elemento | Ubicación | Importancia | Cómo |
|---|---|---|---|
| Base de datos | volumen `vozipomni_postgres_data` | Crítica | `pg_dump` |
| Grabaciones de llamadas (MixMonitor) | volumen `vozipomni_asterisk_spool`, carpeta `monitor/` | Crítica | `tar` del volumen |
| Grabaciones de la aplicación | volumen `vozipomni_recordings_volume` (`/app/recordings`) | Alta | `backup-production.sh` o `tar` |
| Archivos subidos | volumen `vozipomni_media_volume` | Alta | `tar` del volumen |
| Locuciones propias | volumen `vozipomni_asterisk_lib`, carpeta `sounds/custom/` | Alta | `tar` |
| Configuración dinámica de Asterisk | volumen `vozipomni_asterisk_configs` | Media (se regenera desde la BD) | `tar` |
| Variables y secretos | `/opt/vozipomni/.env`, `/opt/vozipomni/backend/.env` | Crítica | copia cifrada |
| Credenciales iniciales | `/opt/vozipomni/credentials.txt` | Alta | copia cifrada |
| Certificados TLS | `/opt/vozipomni/docker/nginx/ssl/` | Alta si usa certificados comprados | copia cifrada |
| Grafana | volumen `vozipomni_grafana_data` | Baja | `tar` opcional |

No hace falta respaldar `redis_data`, `static_volume`, `prometheus_data` ni `whisper_cache`.

El `.env` contiene `FIELD_ENCRYPTION_KEY`, la clave con la que se cifran las contraseñas SIP en la base de datos. Un volcado de PostgreSQL sin su `.env` correspondiente no permite recuperar esas contraseñas. Guarde siempre el `.env` junto con el volcado y con la misma retención.

Las grabaciones de las llamadas las escribe Asterisk en `/var/spool/asterisk/monitor` (volumen `asterisk_spool`), con nombres del tipo `AAAAMMDD-HHMMSS_<UNIQUEID>_<origen>_<destino>.wav`. `backup-production.sh` no incluye este volumen; respáldelo aparte como se indica más abajo.

## Script backup-production.sh

`backup-production.sh`, en la raíz del repositorio, hace lo siguiente:

1. Carga `/opt/vozipomni/.env` (necesita `POSTGRES_USER`; usa `POSTGRES_DB` o `vozipomni` por defecto).
2. Crea `BACKUP_DIR` (por defecto `/var/backups/vozipomni`) con permisos 700.
3. Genera `postgres-<fecha>.dump` con `pg_dump --format=custom` dentro del servicio `postgres`.
4. Genera `recordings-<fecha>.tar.gz` a partir del punto de montaje del volumen `vozipomni_recordings_volume` (o `vozipomni_recordings` como alternativa).
5. Borra todos los archivos de `BACKUP_DIR` con más de 30 días (`find -mtime +30 -delete`).

Variables que acepta: `INSTALL_DIR` y `BACKUP_DIR`.

```bash
sudo bash /opt/vozipomni/backup-production.sh
sudo BACKUP_DIR=/mnt/respaldos/vozipomni bash /opt/vozipomni/backup-production.sh
ls -lh /var/backups/vozipomni
```

Tenga en cuenta:

- La limpieza de 30 días afecta a cualquier archivo dentro de `BACKUP_DIR`, incluidos los respaldos manuales que ponga ahí. Use un directorio distinto para lo que deba conservar más tiempo.
- No respalda `asterisk_spool`, `media_volume`, `asterisk_lib`, el `.env` ni los certificados.
- La fecha del nombre está en UTC.

### Programación con cron

Ejemplo diario a las 03:30, fuera de la tarea de retención de grabaciones (02:00) y de los reportes programados (01:30):

```bash
cat > /etc/cron.d/vozipomni-backup <<'EOF'
30 3 * * * root /bin/bash /opt/vozipomni/backup-production.sh >> /var/log/vozipomni-backup.log 2>&1
EOF
chmod 644 /etc/cron.d/vozipomni-backup
```

## Respaldos manuales

### PostgreSQL

Volcado en formato custom (el mismo que usa el script):

```bash
docker exec vozipomni_postgres pg_dump -U vozipomni_user -d vozipomni --format=custom \
  > "$BACKUP_DIR/postgres-$STAMP.dump"
```

Comprobar que el volcado se puede leer:

```bash
docker exec -i vozipomni_postgres pg_restore --list < "$BACKUP_DIR/postgres-$STAMP.dump" | head
```

Si cambió `POSTGRES_USER` o `POSTGRES_DB` en el `.env`, use esos valores.

### Grabaciones y volúmenes

Con un contenedor temporal, sin depender de la ruta del volumen en el host:

```bash
# Grabaciones de MixMonitor
docker run --rm -v vozipomni_asterisk_spool:/data:ro -v "$BACKUP_DIR":/backup alpine \
  tar -czf "/backup/spool-$STAMP.tar.gz" -C /data monitor

# Archivos subidos
docker run --rm -v vozipomni_media_volume:/data:ro -v "$BACKUP_DIR":/backup alpine \
  tar -czf "/backup/media-$STAMP.tar.gz" -C /data .

# Locuciones propias
docker run --rm -v vozipomni_asterisk_lib:/data:ro -v "$BACKUP_DIR":/backup alpine \
  sh -c "[ -d /data/sounds/custom ] && tar -czf /backup/sounds-custom-$STAMP.tar.gz -C /data sounds/custom || echo 'Sin locuciones propias'"

# Configuración dinámica de Asterisk
docker run --rm -v vozipomni_asterisk_configs:/data:ro -v "$BACKUP_DIR":/backup alpine \
  tar -czf "/backup/asterisk-dynamic-$STAMP.tar.gz" -C /data .
```

El volumen de grabaciones puede ser grande. Revise el tamaño antes de respaldar:

```bash
docker run --rm -v vozipomni_asterisk_spool:/data:ro alpine du -sh /data/monitor
df -h "$BACKUP_DIR"
```

### Configuración y secretos

```bash
tar -czf "$BACKUP_DIR/config-$STAMP.tar.gz" -C /opt/vozipomni \
  .env backend/.env credentials.txt docker/nginx/ssl
chmod 600 "$BACKUP_DIR/config-$STAMP.tar.gz"
```

Si alguno de los archivos no existe, `tar` avisa y sigue con el resto. Este archivo contiene todas las contraseñas del sistema. Cífrelo antes de sacarlo del servidor, por ejemplo:

```bash
gpg --symmetric --cipher-algo AES256 "$BACKUP_DIR/config-$STAMP.tar.gz"
```

### Copia fuera del servidor

Un respaldo que solo vive en el mismo disco no protege contra la pérdida del servidor. Copie los archivos a otro equipo o almacenamiento que usted controle:

```bash
rsync -av --progress /var/backups/vozipomni/ <usuario>@<SERVIDOR_RESPALDO>:/respaldos/vozipomni/
```

## Restaurar en el mismo servidor

1. Detenga los servicios que escriben en la base de datos:

```bash
cd /opt/vozipomni
docker compose -f docker-compose.prod.yml stop backend daphne celery_worker celery_beat dialer_engine websocket_server
```

2. Restaure el volcado. `--clean --if-exists` elimina los objetos antes de recrearlos:

```bash
docker exec -i vozipomni_postgres pg_restore -U vozipomni_user -d vozipomni \
  --clean --if-exists --no-owner < /var/backups/vozipomni/postgres-<FECHA>.dump
```

Es normal ver algunos avisos sobre extensiones u objetos inexistentes. Revise que no haya errores sobre tablas de la aplicación.

3. Restaure las grabaciones si hace falta (se agregan a las existentes):

```bash
docker run --rm -v vozipomni_asterisk_spool:/data -v /var/backups/vozipomni:/backup alpine \
  tar -xzf /backup/spool-<FECHA>.tar.gz -C /data
```

4. Arranque todo, regenere la configuración de Asterisk desde la base de datos y reinicie Asterisk para que el entrypoint corrija los permisos de `monitor/`:

```bash
docker compose -f docker-compose.prod.yml up -d
docker exec vozipomni_backend python manage.py generate_asterisk_config
docker compose -f docker-compose.prod.yml restart asterisk
```

5. Verifique:

```bash
curl -s -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/api/health/
docker exec vozipomni_asterisk asterisk -rx 'pjsip show endpoints'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show registrations'
```

## Restaurar en un servidor nuevo

El objetivo es que el servidor nuevo use el mismo `.env` (sobre todo `FIELD_ENCRYPTION_KEY`, `SECRET_KEY` y las contraseñas) antes de cargar los datos.

1. Copie los respaldos al servidor nuevo, en `/var/backups/vozipomni`.

2. Clone el repositorio y ponga la configuración antes de ejecutar `deploy.sh`:

```bash
git clone https://github.com/henry0295/vozipomni.git /opt/vozipomni
cd /opt/vozipomni
# si cifró el archivo: gpg -d config-<FECHA>.tar.gz.gpg > /tmp/config.tar.gz
tar -xzf /var/backups/vozipomni/config-<FECHA>.tar.gz -C /opt/vozipomni
chmod 600 .env credentials.txt
```

3. Ejecute la instalación con la IP del servidor nuevo (y `--nat` si está detrás de NAT). Como `.env` ya existe, `deploy.sh` reutiliza las credenciales y solo actualiza `VOZIPOMNI_IPV4`, `ALLOWED_HOSTS` y `CORS_ORIGINS`:

```bash
sudo bash deploy.sh <IP_PRIVADA> --nat <IP_PUBLICA>
```

No use `--clean`: borra el `.env` y `credentials.txt` y genera credenciales nuevas.

4. Con la instalación funcionando, siga los pasos 1 a 5 de "Restaurar en el mismo servidor" para cargar la base de datos, las grabaciones, `media`, `sounds-custom` y la configuración dinámica. Para `media` y locuciones:

```bash
docker run --rm -v vozipomni_media_volume:/data -v /var/backups/vozipomni:/backup alpine \
  tar -xzf /backup/media-<FECHA>.tar.gz -C /data
docker run --rm -v vozipomni_asterisk_lib:/data -v /var/backups/vozipomni:/backup alpine \
  tar -xzf /backup/sounds-custom-<FECHA>.tar.gz -C /data
```

5. Si la IP pública cambió:

- Pida a los proveedores de troncales que autoricen la nueva IP.
- Revise en `.env` los valores que contengan la IP o el dominio anterior (`FRONTEND_URL`, `PUBLIC_BASE_URL`, `TURN_HOST`) y recree los servicios afectados.
- Actualice el webhook de WhatsApp en Meta si cambió el dominio.
- Si usaba un certificado emitido para el dominio, instálelo de nuevo (ver [SSL y HTTPS](../instalacion/ssl-https.md)).

## Retención recomendada

| Respaldo | Frecuencia | Retención local | Retención fuera del servidor |
|---|---|---|---|
| PostgreSQL + `.env` | Diaria | 30 días (la que aplica el script) | 12 semanas, más una copia mensual durante 12 meses |
| Grabaciones (`spool`, `recordings`) | Diaria o incremental | Según espacio disponible | Según la política de la empresa y la normatividad aplicable |
| `media`, `sounds-custom`, configuración dinámica | Semanal y después de cambios | 30 días | 12 semanas |
| Certificados y `credentials.txt` | Tras cada cambio | Última versión | Última versión, cifrada |

La aplicación también borra grabaciones por su cuenta: `cleanup-old-recordings` archiva las grabaciones con más de `RECORDING_ARCHIVE_DAYS` días (90 por defecto) y elimina el archivo físico después de `RECORDING_DELETE_DAYS` (180 por defecto). Si debe conservar grabaciones más tiempo, sus respaldos tienen que cubrir esa diferencia. Para ver los valores que usa el worker:

```bash
docker exec vozipomni_celery_worker python -c "from config.recording_config import RECORDING_RETENTION as r; print(r)"
```

Pruebe la restauración al menos una vez por trimestre en un servidor aparte. Un respaldo que nunca se ha restaurado no está comprobado.

## Ver también

- [Servicios Docker](servicios-docker.md)
- [Mantenimiento](mantenimiento.md)
- [Instalación](../instalacion/instalacion.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [Grabaciones y calidad](../administracion/grabaciones-y-calidad.md)
