# Mantenimiento

Esta guía reúne las tareas de mantenimiento de un servidor VozipCX en producción: rutina diaria, semanal y mensual, control del espacio en disco (sobre todo por las grabaciones), rotación de logs, actualizaciones del sistema operativo, cambio seguro de contraseñas y secretos, limpieza de archivos sueltos en `/opt/vozipomni` y revisión del certificado HTTPS. Se basa en `docker-compose.prod.yml`, `deploy.sh`, `backend/config/recording_config.py`, `backend/apps/recordings/tasks.py`, `backend/config/celery.py`, `backend/config/settings.py`, `docker/asterisk/entrypoint.sh`, `docker/nginx/entrypoint.sh` y `.gitignore`.

Todos los comandos se ejecutan en el servidor, como root o con `sudo`, desde el directorio de instalación (por defecto `/opt/vozipomni`). Para abreviar se usa:

```bash
cd /opt/vozipomni
alias dc='docker compose -f docker-compose.prod.yml'
```

Antes de cualquier tarea que reinicie servicios, haz un respaldo (ver [Respaldos](./respaldos.md)) y elige una ventana sin llamadas: reiniciar Asterisk, Kamailio, RTPEngine o coturn corta las llamadas en curso.

## Rutina de mantenimiento

### Diaria

| Tarea | Cómo |
|---|---|
| Estado de los contenedores | `dc ps`. Todos deben estar `running` y los que tienen healthcheck, `healthy`. |
| Salud del backend | `curl -fsS -H 'X-Forwarded-Proto: https' http://localhost:8000/api/health/` debe responder `"status": "healthy"`. |
| Espacio en disco | `df -h /` y `df -h /var/lib/docker`. Actúa antes del 80%. |
| Errores recientes | `dc logs --since 24h backend celery_worker | grep -iE 'error|critical' | tail -50` |
| Respaldo | Verifica que el respaldo de la noche se generó y tiene un tamaño razonable. |

### Semanal

| Tarea | Cómo |
|---|---|
| Crecimiento de grabaciones | Ver [Grabaciones](#grabaciones) más abajo. |
| Retención de grabaciones | `dc logs --since 7d celery_worker | grep '\[Retention\]'` para confirmar que la limpieza corre. |
| Uso de Docker | `docker system df` (imágenes, caché de build y volúmenes). |
| Logs fuera de Docker | `du -sh logs/ logs/nginx/` en `/opt/vozipomni`. |
| Eventos de seguridad | Revisar **Telefonía → Seguridad y antifraude → Eventos de seguridad** en la web. |
| Agentes SIP registrados | `docker exec vozipomni_asterisk asterisk -rx 'pjsip show contacts'` en horario laboral. |

### Mensual

| Tarea | Cómo |
|---|---|
| Actualizaciones del sistema operativo | Ver [Actualizaciones del sistema operativo](#actualizaciones-del-sistema-operativo). |
| Limpieza de imágenes Docker | Ver [Limpieza segura de Docker](#limpieza-segura-de-docker). |
| Vencimiento del certificado | Ver [Certificado HTTPS](#certificado-https). |
| Prueba de restauración | Restaurar un respaldo en un servidor de pruebas. |
| Revisión de accesos | Usuarios inactivos en **Usuarios y roles** y agentes retirados en **Agentes**. |
| Actualización de VozipCX | Si hay versión nueva, seguir [Actualización](../instalacion/actualizacion.md). |

## Espacio en disco

### Grabaciones

Asterisk graba con `MixMonitor` en WAV (`.wav`, opciones `ab`: agrega al archivo y solo graba cuando la llamada está conectada). Los archivos quedan en `/var/spool/asterisk/monitor`, dentro del volumen `asterisk_spool`, que comparten `asterisk`, `backend` y `celery_worker`.

Para medirlas:

```bash
docker exec vozipomni_asterisk du -sh /var/spool/asterisk/monitor
docker exec vozipomni_asterisk sh -c 'ls /var/spool/asterisk/monitor | wc -l'
```

Estimación de crecimiento: un WAV de telefonía a 8 kHz y 16 bits ocupa cerca de 1 MB por minuto de conversación. Por ejemplo, 30 agentes con 4 horas de conversación al día generan unos 7 GB diarios. Calcula tu caso con los minutos hablados del reporte y deja margen.

### Retención automática

La tarea `recordings.cleanup_old_recordings` (en `backend/apps/recordings/tasks.py`) aplica la política de `backend/config/recording_config.py`:

| Variable de `.env` | Valor por defecto | Efecto |
|---|---|---|
| `RECORDING_ARCHIVE_DAYS` | 90 | Marca como archivadas las grabaciones más antiguas que N días. |
| `RECORDING_DELETE_DAYS` | 180 | Borra el archivo físico de las archivadas más antiguas que N días. El registro en la base de datos se conserva. |
| `RECORDING_DELETE_LOW_PRIORITY` | 30 | Definida en la configuración; en la tarea revisada no se usa. |

La tarea está programada a las 02:00. Hay dos definiciones del calendario: `backend/config/settings.py` usa el nombre registrado `recordings.cleanup_old_recordings`, y `backend/config/celery.py` usa `apps.recordings.tasks.cleanup_old_recordings`, que no coincide con ese nombre. Confirma que la limpieza corre buscando `[Retention]` en los logs de `celery_worker`. Si no aparece nada tras varios días con grabaciones antiguas, revisa la tarea periódica en el administrador de Django (`/admin/`, Periodic tasks).

Para cambiar los plazos, edita las variables en `.env` y recrea los servicios de Django con `dc up -d`. Antes de reducirlos, confirma con el área legal o de calidad el tiempo que deben conservarse las grabaciones y respáldalas si hace falta (ver [Grabaciones y calidad](../administracion/grabaciones-y-calidad.md)).

No borres archivos a mano dentro de `monitor/`: la base de datos quedaría apuntando a archivos inexistentes y la web mostraría errores al reproducir.

### Limpieza segura de Docker

Seguro:

```bash
docker image prune -f        # solo imágenes huérfanas (<none>), p. ej. tras un rebuild
docker builder prune -f      # caché de construcción
```

Nunca en producción:

- `docker volume prune` ni `docker system prune --volumes`: borran los volúmenes que no estén en uso por un contenedor. Si los servicios están detenidos en ese momento, se pierden la base de datos (`postgres_data`), las grabaciones (`asterisk_spool`) y la configuración de Asterisk.
- `docker system prune -a`: borra todas las imágenes sin contenedor; el siguiente arranque tendrá que reconstruir y descargar todo.
- `sudo bash deploy.sh --clean`: borra volúmenes, `.env`, `credentials.txt` y logs. Es solo para reinstalar desde cero.

## Rotación de logs

Todos los servicios de `docker-compose.prod.yml` usan la plantilla `x-logging`:

```yaml
driver: "json-file"
options:
  max-size: "20m"
  max-file: "5"
```

Cada contenedor guarda como máximo 5 archivos de 20 MB (unos 100 MB). Con 16 servicios, el tope ronda 1,6 GB en `/var/lib/docker/containers`. Consúltalos con `dc logs <servicio>`.

Estos logs no los rota Docker, porque están montados desde el host:

| Ruta | Origen | Qué hacer |
|---|---|---|
| `/opt/vozipomni/logs/nginx/` | Accesos y errores de nginx. | Crear una regla de `logrotate` (abajo). |
| `/opt/vozipomni/logs/` | Logs de la aplicación Django. Si se escriben a archivo, `backend/core/logging_config.py` usa `RotatingFileHandler` de 10 MB con 5 copias. | Revisar el tamaño cada semana. |
| Volumen `asterisk_logs` (`/var/log/asterisk`) | Logs de Asterisk. | Revisar con `docker exec vozipomni_asterisk du -sh /var/log/asterisk`. Para rotar: `docker exec vozipomni_asterisk asterisk -rx 'logger rotate'`. |

Regla sugerida en `/etc/logrotate.d/vozipomni-nginx`:

```text
/opt/vozipomni/logs/nginx/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

`copytruncate` evita tener que reiniciar nginx. Prueba la regla con `logrotate -d /etc/logrotate.d/vozipomni-nginx`. Si tienes fail2ban leyendo logs de `/opt/vozipomni/logs`, la rotación no le afecta.

## Actualizaciones del sistema operativo

1. Programa una ventana sin llamadas y avisa a supervisión.
2. Haz un respaldo.
3. Actualiza (Debian/Ubuntu):

   ```bash
   apt update && apt upgrade -y
   ```

   En RHEL, Rocky o Alma: `dnf upgrade -y`.
4. Si se actualizó `docker-ce` o `containerd`, Docker reinicia todos los contenedores; es normal que haya un corte corto.
5. Si hay kernel nuevo (existe `/var/run/reboot-required` en Debian/Ubuntu), reinicia con `reboot`. Los servicios tienen `restart: unless-stopped` y vuelven solos.
6. Verifica con `dc ps` que todo esté `healthy`, entra a la web y haz una llamada de prueba desde la consola de agente.

No actualices VozipCX y el sistema operativo en la misma ventana: si algo falla, no sabrás cuál de los dos lo causó.

## Cambio de contraseñas y secretos

Las contraseñas viven en `/opt/vozipomni/.env` (permisos 600). `deploy.sh` también las copia a `backend/.env` y a `credentials.txt`. Reglas generales:

- Genera valores solo alfanuméricos, como hace `deploy.sh`: `openssl rand -base64 32 | tr -d '=+/' | cut -c1-25`. Las contraseñas de Redis y PostgreSQL van dentro de URLs (`redis://:<clave>@...`, `postgresql://...`) y la de AMI se inserta con `sed`; caracteres como `/`, `@`, `&` o `:` las rompen.
- Cambiar una variable de `.env` no afecta a los contenedores que ya corren. Hay que recrearlos con `dc up -d`, que recrea solo los servicios cuya configuración cambió. `docker restart` no sirve: conserva el entorno anterior.
- Actualiza el mismo valor en `backend/.env` y en `credentials.txt` (o retira la línea) para no dejar datos desactualizados.
- Nunca pegues el `.env`, `credentials.txt` ni la salida de `git diff` del servidor en tickets o chats.

| Secreto | Servicios que lo usan | Qué se rompe mientras no coincide |
|---|---|---|
| `ASTERISK_AMI_PASSWORD` | `asterisk`, `backend`, `daphne`, `celery_worker`, `celery_beat`, `dialer_engine` | El backend no conecta a AMI: "No se pudo conectar a Asterisk AMI" en supervisión, no se recarga PJSIP al guardar agentes, no se agregan ni pausan agentes en colas y el marcador no origina llamadas. |
| `TURN_SECRET` | `coturn` y los servicios de Django (firman las credenciales TURN) | Los agentes detrás de NAT estricto no consiguen relay: llamadas sin audio. |
| `POSTGRES_PASSWORD` | `postgres` (solo al crear el volumen) y los servicios de Django | Django no conecta a la base: errores 500 y no se puede iniciar sesión. |
| `REDIS_PASSWORD` | `redis`, servicios de Django, `kamailio`, `rtpengine`, `websocket_server`, `dialer_engine` | Celery, WebSockets, tiempo real, Kamailio y RTPEngine fallan; los softphones no registran. |

### AMI

1. En `.env`, cambia `ASTERISK_AMI_PASSWORD`. Haz lo mismo en `backend/.env`.
2. En una ventana sin llamadas: `dc up -d`. Al arrancar, `docker/asterisk/entrypoint.sh` escribe la nueva clave en `docker/asterisk/configs/manager.conf` (línea `secret = ...`).
3. Verifica: `dc logs --tail=50 backend | grep -i ami` y prueba **Escuchar** desde el Monitor en vivo.

Nota: como `docker/asterisk/configs` está montado desde el repositorio, `git status` mostrará `manager.conf` modificado con la clave real. Es esperado: no lo agregues a un commit.

### TURN

1. Cambia `TURN_SECRET` en `.env`.
2. `dc up -d` recrea `coturn` y los servicios de Django.
3. Pide a los agentes recargar la consola con Ctrl+F5. La consola pide credenciales TURN nuevas en cada registro y las renueva cada 30 minutos; hasta entonces las anteriores dejan de servir.

### PostgreSQL

`POSTGRES_PASSWORD` solo se aplica cuando se crea el volumen por primera vez. En una instalación existente hay que cambiar la clave dentro de la base primero:

1. Entra a psql y cambia la clave de forma interactiva (no queda en el historial de la shell):

   ```bash
   dc exec postgres psql -U vozipomni_user -d vozipomni
   \password vozipomni_user
   \q
   ```

2. Pon la misma clave en `POSTGRES_PASSWORD` de `.env` y en `DB_PASSWORD` de `backend/.env`.
3. `dc up -d` para recrear los servicios de Django (y `postgres`, con un corte breve).
4. Verifica el health del backend y el inicio de sesión en la web.

Entre los pasos 1 y 3 los servicios de Django no pueden abrir conexiones nuevas; hazlo seguido. Alternativa: `sudo bash deploy.sh --update <IP>` compara la clave del `.env` con la base y ejecuta `ALTER USER` por el socket local si no coinciden (función `sync_postgres_password`). Si esa sincronización falla, en modo interactivo ofrece resetear PostgreSQL borrando los datos: responde **N**.

### Redis

1. Cambia `REDIS_PASSWORD` en `.env` y en `backend/.env`.
2. En una ventana sin llamadas: `dc up -d`. Se recrean Redis y todos sus clientes, incluidos Kamailio y RTPEngine, así que se cortan las llamadas en curso.
3. Los softphones reintentan el registro solos (hasta 5 veces); si alguno queda en **Conectando...**, el agente debe recargar con Ctrl+F5.
4. Los datos de Redis se conservan (`--appendonly yes` en el volumen `redis_data`).

### Secretos que no se deben rotar a la ligera

- `FIELD_ENCRYPTION_KEY`: cifra los campos `EncryptedCharField` de la base de datos. Si la cambias sin migrar los datos, esos valores quedan ilegibles. No la cambies y respáldala aparte.
- `SECRET_KEY`: al cambiarla se invalidan todas las sesiones y tickets firmados; todos los usuarios deben volver a entrar.

## Limpieza de archivos sueltos en /opt/vozipomni

`/opt/vozipomni` es un clon de Git con archivos que no están en el repositorio pero son necesarios:

| Archivo | Estado en Git | Contenido |
|---|---|---|
| `.env`, `backend/.env` | Ignorado | Todas las contraseñas. |
| `credentials.txt` | Sin seguimiento y **no** ignorado | Usuario admin y contraseñas de PostgreSQL, Redis y AMI. |
| `.env.backup_<fecha>` | Sin seguimiento | Copias del `.env` que crea `deploy.sh`. |
| `docker/nginx/ssl/*.crt`, `*.key` | Ignorado | Certificado y clave privada HTTPS. |
| `logs/` | Ignorado | Logs de la aplicación y nginx. |
| `docker/asterisk/configs/manager.conf` | Modificado | Clave AMI real (ver arriba). |

Por eso:

- **Nunca** ejecutes `git clean -f`, `git clean -fd` ni `git clean -fdx`. El primero borra `credentials.txt` y las copias del `.env`; con `-x` también borra `.env`, `backend/.env`, los certificados y los logs.
- **Nunca** ejecutes `git add .` ni `git add -A` en el servidor: `credentials.txt` no está ignorado y se subiría al repositorio.
- `deploy.sh --update` ejecuta `git stash` antes de `git pull`. Cada stash guarda los cambios locales, incluido `manager.conf` con la clave AMI. Revisa `git stash list` de vez en cuando y elimina solo los que sepas que no necesitas.

Procedimiento seguro:

1. Lista lo que sobra sin borrar nada: `git status --short` (los `??` son archivos sin seguimiento) o `git clean -n` (simulación).
2. Revisa cada archivo. Si es un respaldo o script viejo, cópialo fuera del servidor o a un directorio con permisos 700 antes de borrarlo.
3. Borra uno por uno con `rm <archivo>`, nunca con comodines amplios.
4. `credentials.txt`: consérvalo con `chmod 600` y dueño root, o pásalo a un gestor de contraseñas. Si lo eliminas, en cada actualización `deploy.sh` no encuentra la clave de admin y muestra al final una clave aleatoria que no corresponde a la cuenta real (no la cambia, porque el usuario admin ya existe).
5. Verifica permisos: `ls -l .env backend/.env credentials.txt docker/nginx/ssl/` (600 para `.env`, `credentials.txt` y la `.key`).

## Certificado HTTPS

nginx usa `docker/nginx/ssl/vozipomni.crt` y `vozipomni.key`. Si no existen al arrancar, el entrypoint genera un certificado autofirmado. Revisa el vencimiento:

```bash
openssl x509 -in /opt/vozipomni/docker/nginx/ssl/vozipomni.crt -noout -subject -enddate
openssl x509 -in /opt/vozipomni/docker/nginx/ssl/vozipomni.crt -noout -checkend 2592000 && echo "Vigente más de 30 días"
```

Lo que ve el cliente (útil si hay un balanceador delante):

```bash
echo | openssl s_client -connect <DOMINIO_O_IP>:443 -servername <DOMINIO> 2>/dev/null | openssl x509 -noout -enddate
```

Renueva al menos 30 días antes. Tras reemplazar los archivos, recarga nginx con `dc restart nginx` y verifica que la consola de agente conecte: el softphone usa WSS por el mismo certificado. Si el certificado vence o no es de confianza, los agentes verán **Conectando...** o **Desconectado**. Ver [SSL y HTTPS](../instalacion/ssl-https.md).

## Ver también

- [Respaldos](./respaldos.md)
- [Monitoreo](./monitoreo.md)
- [Servicios Docker](./servicios-docker.md)
- [Solución de problemas](./solucion-de-problemas.md)
- [Actualización](../instalacion/actualizacion.md)
- [SSL y HTTPS](../instalacion/ssl-https.md)
- [Grabaciones y calidad](../administracion/grabaciones-y-calidad.md)
- [Glosario](../general/glosario.md)
