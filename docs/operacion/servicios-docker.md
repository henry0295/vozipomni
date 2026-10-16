# Servicios Docker

Este documento describe cada servicio definido en `docker-compose.prod.yml`, cómo se conectan entre sí y qué datos guarda cada volumen. Está pensado como referencia rápida para operadores que necesitan revisar el estado del sistema, reiniciar un componente o entrar a un contenedor sin afectar al resto de la plataforma.

Todos los comandos asumen una instalación hecha con `deploy.sh` en `/opt/vozipomni` (valor por defecto de `INSTALL_DIR`) y el plugin `docker compose` v2.

```bash
cd /opt/vozipomni
```

## Modelo de red

La producción mezcla dos modelos de red:

- Red bridge `backend` (172.20.0.0/24): PostgreSQL, Redis, Django (backend, daphne), Celery (worker y beat).
- Red bridge `voip` (172.21.0.0/24): compartida por `backend` y `celery_worker` para el acceso a AMI.
- `network_mode: host`: Asterisk, Kamailio, RTPEngine, coturn, Nginx, frontend, websocket_server, dialer_engine, Prometheus y Grafana. Estos servicios no usan `ports:`; se enlazan directamente a las interfaces del servidor, así que su exposición depende del firewall del host.

Los servicios en bridge publican sus puertos solo en `127.0.0.1`, por eso no son accesibles desde fuera del servidor.

## Inventario de servicios

| Servicio (compose) | Contenedor | Imagen / build | Red | Puertos | Volúmenes y montajes | depends_on | Función |
|---|---|---|---|---|---|---|---|
| `postgres` | `vozipomni_postgres` | `postgres:14-alpine` | backend | `127.0.0.1:5432` | `postgres_data`, `./docker/postgresql/init.sql` | - | Base de datos principal |
| `redis` | `vozipomni_redis` | `redis:7-alpine` | backend | `127.0.0.1:6379` | `redis_data` | - | Caché, broker de Celery, channel layer de Channels. `appendonly yes`, `maxmemory 512mb`, `allkeys-lru` |
| `backend` | `vozipomni_backend` | build `./backend` | backend, voip | `127.0.0.1:8000` | `static_volume`, `media_volume`, `recordings_volume`, `asterisk_spool`, `asterisk_lib`, `asterisk_configs`, `./logs`, `./docker/asterisk/configs:/etc/asterisk` | postgres, redis (healthy) | API Django con Gunicorn. Al arrancar ejecuta `migrate` y `collectstatic` |
| `daphne` | `vozipomni_daphne` | build `./backend` | backend | `127.0.0.1:8001` | `static_volume`, `media_volume`, `recordings_volume`, `./logs` | postgres, redis, backend (healthy) | Servidor ASGI para WebSocket `/ws/` |
| `celery_worker` | `vozipomni_celery_worker` | build `./backend` | backend, voip | - | `media_volume`, `recordings_volume`, `asterisk_spool`, `./logs`, `./docker/asterisk/configs`, `asterisk_configs`, `whisper_cache` | postgres, redis, backend (healthy) | Tareas asíncronas, vinculación de grabaciones, listener de CDR por AMI |
| `celery_beat` | `vozipomni_celery_beat` | build `./backend` | backend | - | `./logs` | postgres, redis, backend (healthy) | Planificador de tareas periódicas (`DatabaseScheduler`) |
| `asterisk` | `vozipomni_asterisk` | build `./docker/asterisk` (`Dockerfile.prebuilt`, Asterisk 21.12.3) | host | 5080 udp/tcp, 5161/udp, 5162/udp, 5038/tcp (AMI), 8088/8089, RTP 10000-10300/udp | `asterisk_logs`, `asterisk_spool`, `asterisk_lib`, `./docker/asterisk/configs:/etc/asterisk`, `asterisk_configs` | - | PBX: dialplan, colas, troncales, grabación (MixMonitor). `privileged: true` |
| `kamailio` | `vozipomni_kamailio` | build `./docker/kamailio` (repositorio Kamailio 5.7) | host | 5060 udp/tcp, `127.0.0.1:8080` (WebSocket) | - | redis (healthy), asterisk, rtpengine (started) | Proxy SIP de agentes WebRTC, registro, antiflood |
| `rtpengine` | `vozipomni_rtpengine` | build `./docker/rtpengine` (Sipwise mr12.0) | host | `127.0.0.1:22222` (control NG), 23000-23300/udp | - | redis (healthy) | Puente de medios WebRTC (DTLS/SRTP) a RTP plano |
| `coturn` | `vozipomni_coturn` | `coturn/coturn:4.6.3` | host | 3478 udp/tcp, relay 49152-49200/udp | - | - | TURN para agentes detrás de NAT estricto |
| `nginx` | `vozipomni_nginx` | build `./docker/nginx` (`Dockerfile.prod`) | host | 80, 443 | `static_volume`, `media_volume`, `./docker/nginx/ssl`, `./logs/nginx` | backend (healthy), frontend (started) | Proxy inverso, TLS, validación del ticket del WebSocket SIP |
| `frontend` | `vozipomni_frontend` | build `./frontend` (Nuxt 3) | host | 3000 | - | backend (healthy) | Interfaz web |
| `websocket_server` | `vozipomni_websocket` | build `./websocket_server` | host | 8765 (`WS_PORT`) | - | redis (healthy) | Servidor WebSocket auxiliar |
| `dialer_engine` | `vozipomni_dialer` | build `./dialer_engine` | host | - (cliente AMI) | - | redis (healthy), asterisk (started) | Marcador predictivo/progresivo |
| `prometheus` | sin `container_name` | `prom/prometheus:v2.50.1` | host | `127.0.0.1:9090` | `prometheus_data`, `./docker/prometheus/prometheus.yml` | - | Métricas, retención 30 días |
| `grafana` | sin `container_name` | `grafana/grafana:10.3.3` | host | `127.0.0.1:3001` | `grafana_data`, `./docker/grafana/provisioning` | prometheus | Tableros de métricas |

Notas:

- `prometheus` y `grafana` no tienen `container_name`. Docker Compose v2 les asigna un nombre del tipo `vozipomni-prometheus-1`. Para no depender del nombre, use `docker compose ... logs prometheus` o `docker compose ... exec prometheus`.
- `backend`, `daphne`, `celery_worker` y `celery_beat` se construyen desde el mismo contexto `./backend`. Si cambia el código del backend, reconstruya los cuatro.
- Todos los servicios usan `restart: unless-stopped` y el driver de logs `json-file` con `max-size: 20m` y `max-file: 5`.
- En modo host, `frontend` (3000), `websocket_server` (8765) y AMI (5038) escuchan en `0.0.0.0`. El firewall que configura `deploy.sh` no publica esos puertos y deniega 5038, 5432 y 6379. Revise [red-y-puertos](../instalacion/red-y-puertos.md) antes de tocar el firewall.

## Healthchecks

| Servicio | Comprobación | Intervalo |
|---|---|---|
| postgres | `pg_isready -U <usuario> -d <bd>` | 5 s |
| redis | `redis-cli -a <clave> ping` | 15 s |
| backend | `curl` a `http://localhost:8000/api/health/` con `X-Forwarded-Proto: https`, espera `"status": "healthy"` | 15 s, `start_period` 120 s |
| daphne | igual que backend, en el puerto 8001 | 20 s |
| celery_worker | `celery -A config inspect ping -d celery@$HOSTNAME` | 30 s |
| celery_beat | proceso 1 contiene `celery` | 30 s |
| asterisk | `asterisk -rx 'core show uptime seconds'` | 15 s |
| nginx | `curl http://localhost/health` | 30 s |
| dialer_engine | ping a Redis desde Python | 30 s |
| prometheus / grafana | `/-/healthy` y `/api/health` | 30 s |

Kamailio, RTPEngine, coturn, frontend y websocket_server no tienen healthcheck; `docker compose ps` solo mostrará si están en ejecución.

## Comandos habituales

Estado de todos los servicios:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml ps --format 'table {{.Name}}\t{{.Status}}'
```

Estado de salud de un contenedor concreto (el mismo método que usa `deploy.sh`):

```bash
docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' vozipomni_backend
```

Logs:

```bash
docker compose -f docker-compose.prod.yml logs --tail=100 backend
docker compose -f docker-compose.prod.yml logs -f celery_worker
docker logs --tail=200 vozipomni_kamailio
docker logs -f --since 10m vozipomni_asterisk
```

Reiniciar un solo servicio:

```bash
docker compose -f docker-compose.prod.yml restart backend
```

Recrear un servicio para que tome cambios del `.env` (`restart` no relee variables de entorno):

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate backend
```

Reiniciar `asterisk`, `kamailio` o `rtpengine` corta las llamadas en curso. Hágalo en una ventana de mantenimiento.

Abrir una shell:

```bash
docker exec -it vozipomni_backend bash
docker exec -it vozipomni_postgres psql -U vozipomni_user -d vozipomni
docker exec -it vozipomni_asterisk asterisk -rvvv
docker exec -it vozipomni_kamailio bash
docker exec -it vozipomni_redis sh
```

El contenedor `backend` se ejecuta como el usuario `vozipomni` (uid 1000). Para Redis, la clave está en `REDIS_PASSWORD` del `.env`; pásela con `redis-cli -a` dentro del contenedor sin pegarla en tickets ni chats.

Comandos de gestión de Django:

```bash
docker exec vozipomni_backend python manage.py showmigrations
docker exec vozipomni_backend python manage.py generate_asterisk_config
docker exec vozipomni_backend python manage.py generate_asterisk_config --only-trunks
```

`generate_asterisk_config` admite `--no-reload`, `--only-extensions` y `--only-trunks`.

Reconstruir un servicio:

```bash
# Backend y sus servicios hermanos (mismo código)
docker compose -f docker-compose.prod.yml build backend daphne celery_worker celery_beat
docker compose -f docker-compose.prod.yml up -d backend daphne celery_worker celery_beat

# Solo Kamailio
docker compose -f docker-compose.prod.yml build kamailio
docker compose -f docker-compose.prod.yml up -d kamailio
```

Para actualizaciones completas use `deploy.sh --update` (ver [actualizacion](../instalacion/actualizacion.md)); reconstruye todas las imágenes, aplica migraciones y recarga Asterisk.

No pegue en la terminal la salida de `docker compose build`. Las líneas como `[asterisk 3/12]` o `=> CACHED` se interpretan como comandos y crean archivos basura en `/opt/vozipomni`. Ver [mantenimiento](mantenimiento.md#limpieza-de-archivos-extranos).

Uso de recursos en vivo:

```bash
docker stats --no-stream
```

Los límites de memoria y CPU están en la sección `deploy.resources` de cada servicio (por ejemplo, `asterisk` 4G, `backend` 2G, `celery_worker` 1G, `daphne` 256M).

## Volúmenes

El nombre real de cada volumen lleva el prefijo del proyecto, que es el nombre del directorio de instalación: con `/opt/vozipomni` queda `vozipomni_<volumen>` (por ejemplo `vozipomni_postgres_data`).

```bash
docker volume ls --filter name=vozipomni_
docker volume inspect -f '{{.Mountpoint}}' vozipomni_asterisk_spool
```

| Volumen | Montado en | Contenido | ¿Respaldar? |
|---|---|---|---|
| `postgres_data` | postgres `/var/lib/postgresql/data` | Base de datos completa | Sí, con `pg_dump` |
| `redis_data` | redis `/data` | AOF de Redis: caché, colas de Celery, estado temporal | No es crítico |
| `static_volume` | backend, daphne, nginx `/app/static` | Estáticos de Django (`collectstatic`) | No, se regenera |
| `media_volume` | backend, daphne, celery_worker, nginx `/app/media` | Archivos subidos desde la web | Sí |
| `recordings_volume` | backend, daphne, celery_worker `/app/recordings` | Grabaciones gestionadas por la aplicación | Sí |
| `asterisk_spool` | asterisk, backend, celery_worker `/var/spool/asterisk` | Grabaciones de MixMonitor en `monitor/`, correo de voz | Sí |
| `asterisk_lib` | asterisk, backend `/var/lib/asterisk` | `astdb.sqlite3`, locuciones del sistema y propias (`sounds/custom`), documentación XML | Sí (al menos `sounds/custom`) |
| `asterisk_configs` | asterisk, backend, celery_worker `/var/lib/asterisk/dynamic` | Configuración generada por el backend: `pjsip_agents.conf`, `pjsip_wizard.conf`, `extensions_dynamic.conf`, `queues_dynamic.conf`, `kamailio_identify.conf` | Recomendado (se puede regenerar) |
| `asterisk_logs` | asterisk `/var/log/asterisk` | Logs de Asterisk, `cdr-csv`, `cdr-custom` | Opcional |
| `prometheus_data` | prometheus `/prometheus` | Series de métricas (30 días) | No |
| `grafana_data` | grafana `/var/lib/grafana` | Usuarios y tableros de Grafana | Opcional |
| `whisper_cache` | celery_worker `/root/.cache/whisper` | Modelos de transcripción descargados | No |

Montajes de directorios del host relevantes:

- `./docker/asterisk/configs` a `/etc/asterisk` (Asterisk, backend y celery_worker). El entrypoint de Asterisk edita estos archivos al arrancar (secreto AMI en `manager.conf`, IP externa en `pjsip.conf`), así que la copia del host contiene datos sensibles.
- `./docker/nginx/ssl` a `/etc/nginx/ssl`: certificado y clave TLS (`vozipomni.crt`, `vozipomni.key`).
- `./logs` a `/app/logs` y `./logs/nginx` a `/var/log/nginx`.

Para ver un volumen sin conocer su ruta en el host, móntelo en un contenedor temporal, igual que hace `deploy.sh`:

```bash
docker run --rm -v vozipomni_asterisk_spool:/data alpine ls -lh /data/monitor
```

No ejecute `docker volume prune`, `docker system prune --volumes` ni `docker compose down -v` en producción. Con el stack detenido, esos comandos borran la base de datos y las grabaciones.

## Ver también

- [Arquitectura](../general/arquitectura.md)
- [Red y puertos](../instalacion/red-y-puertos.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [Monitoreo](monitoreo.md)
- [Respaldos](respaldos.md)
- [Mantenimiento](mantenimiento.md)
- [Solución de problemas](solucion-de-problemas.md)
