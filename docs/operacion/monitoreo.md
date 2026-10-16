# Monitoreo

Este documento reúne lo que un operador necesita para saber si VozipCX está sano: el endpoint de salud del backend, los healthchecks de Docker, Prometheus y Grafana, los logs que conviene vigilar, las tareas periódicas de Celery y los comandos de Asterisk y Kamailio para revisar el estado de la telefonía.

Los comandos asumen la instalación en `/opt/vozipomni`:

```bash
cd /opt/vozipomni
```

## Revisión rápida

```bash
# 1. Contenedores y su salud
docker compose -f docker-compose.prod.yml ps

# 2. Backend: base de datos y Redis
curl -s -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/api/health/

# 3. Telefonía: endpoints, troncales y llamadas
docker exec vozipomni_asterisk asterisk -rx 'pjsip show registrations'
docker exec vozipomni_asterisk asterisk -rx 'core show channels count'

# 4. Disco
df -h /var/lib/docker /opt/vozipomni
```

## Endpoint de salud del backend

`/api/health/` está definido en `backend/apps/api/health_urls.py`. Comprueba la base de datos (`SELECT 1`) y Redis (escritura y lectura en la caché) y responde:

- HTTP 200 con `"status": "healthy"` si ambas comprobaciones pasan.
- HTTP 503 con `"status": "unhealthy"` si alguna falla. El campo `checks` indica cuál (`database` o `redis`).

```json
{"status": "healthy", "timestamp": "...", "service": "VozipCX Backend", "checks": {"database": "ok", "redis": "ok"}}
```

Desde el servidor, directo a Gunicorn y a Daphne:

```bash
curl -s -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/api/health/
curl -s -H 'X-Forwarded-Proto: https' http://127.0.0.1:8001/api/health/
```

La cabecera `X-Forwarded-Proto: https` es necesaria porque en producción `SECURE_SSL_REDIRECT` está activo: sin ella Django responde con una redirección 301 en lugar del JSON.

Desde fuera, a través de Nginx:

```bash
curl -sk https://<IP_O_DOMINIO>/api/health/
```

Nginx expone además `/health`, que devuelve un texto fijo. Solo indica que Nginx está vivo, no que el backend funcione.

```bash
curl -sk https://<IP_O_DOMINIO>/health
```

## Healthchecks de Docker

Los healthchecks definidos en `docker-compose.prod.yml` están resumidos en [servicios-docker](servicios-docker.md#healthchecks). Para listar solo los contenedores con problemas:

```bash
docker ps --filter health=unhealthy --format 'table {{.Names}}\t{{.Status}}'
docker ps -a --filter status=exited --format 'table {{.Names}}\t{{.Status}}'
```

Para ver la salida de las últimas comprobaciones de un contenedor:

```bash
docker inspect --format '{{json .State.Health}}' vozipomni_backend
```

Kamailio, RTPEngine, coturn, frontend y websocket_server no tienen healthcheck. Revíselos por logs y con los comandos de la sección de telefonía.

## Prometheus y Grafana

Ambos corren en `network_mode: host` y escuchan solo en `127.0.0.1`:

- Prometheus: `127.0.0.1:9090`, retención `30d`.
- Grafana: `127.0.0.1:3001`, usuario `GRAFANA_USER` (por defecto `admin`), contraseña `GRAFANA_PASSWORD` del `.env`. El registro de usuarios está deshabilitado.

Para abrirlos desde su equipo, cree un túnel SSH:

```bash
ssh -L 9090:127.0.0.1:9090 -L 3001:127.0.0.1:3001 <usuario>@<IP_SERVIDOR>
```

Luego abra `http://localhost:9090` y `http://localhost:3001`. No publique estos puertos en el firewall.

Grafana solo trae aprovisionada la fuente de datos `Prometheus` (`docker/grafana/provisioning/datasources/prometheus.yml`). El repositorio no incluye tableros; hay que crearlos o importarlos.

### Qué se recolecta

Trabajos definidos en `docker/prometheus/prometheus.yml` (intervalo de 15 s):

| Job | Destino | Observaciones |
|---|---|---|
| `django` | `127.0.0.1:8000/metrics` | Métricas de `django-prometheus` del backend (Gunicorn) |
| `celery` | `127.0.0.1:8001/metrics` | El puerto 8001 es Daphne. En la práctica recoge las métricas Django del proceso ASGI; no hay un exportador de Celery en el compose |
| `node` | `127.0.0.1:9100` | Requiere `node_exporter`, que no está en el compose |
| `redis` | `127.0.0.1:9121` | Requiere `redis_exporter`, que no está en el compose |
| `prometheus` | `127.0.0.1:9090` | El propio Prometheus |

Además, la tarea `update-prometheus-metrics` de Celery actualiza cada minuto métricas de agentes.

Estado de los targets:

```bash
curl -s http://127.0.0.1:9090/api/v1/targets | grep -o '"scrapeUrl":"[^"]*"\|"health":"[^"]*"\|"lastError":"[^"]*"'
```

Es normal que `node` y `redis` aparezcan como `down` si no ha instalado esos exportadores. Si `django` aparece caído con un error de redirección, la causa probable es `SECURE_SSL_REDIRECT`: Prometheus consulta por HTTP sin `X-Forwarded-Proto`. Compruebe la respuesta manualmente:

```bash
curl -si http://127.0.0.1:8000/metrics | head -5
curl -s -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/metrics | head -20
```

`/metrics` no está publicado en Nginx; solo se consulta desde el propio servidor.

## Logs clave

| Qué vigilar | Comando | Buscar |
|---|---|---|
| Errores del API | `docker logs --since 1h vozipomni_backend 2>&1 \| grep -E 'ERROR\|Traceback'` | Excepciones, errores de BD |
| Handshake del softphone | `docker logs --since 1h vozipomni_backend 2>&1 \| grep 'SIP-WS'` | `[SIP-WS] Handshake rechazado` |
| Conexión AMI | `docker logs --since 1h vozipomni_backend 2>&1 \| grep -i 'AMI'` | `Error conectando a Asterisk AMI`, `Error de autenticación AMI` |
| Grabaciones | `docker logs --since 1h vozipomni_celery_worker 2>&1 \| grep 'Recording'` | `Grabación vinculada`, `Sin archivo de grabación` |
| Retención | `docker logs --since 24h vozipomni_celery_worker 2>&1 \| grep 'Retention'` | Archivos archivados y eliminados |
| CDR | `docker logs vozipomni_celery_worker 2>&1 \| grep 'CDR Listener'` | `AMI CDR Listener arrancado` o `Error arrancando CDR Listener` |
| Tareas programadas | `docker logs --since 10m vozipomni_celery_beat` | `Sending due task` |
| Seguridad SIP | `docker logs --since 24h vozipomni_kamailio 2>&1 \| grep SECURITY` | `SECURITY FLOOD`, `SECURITY SCANNER`, `SECURITY UNTRUSTED` |
| RTPEngine | `docker logs --since 1h vozipomni_rtpengine 2>&1 \| grep -iE 'error\|warn'` | Fallos de puertos o de interfaz |
| Kamailio a RTPEngine | `docker logs --since 1h vozipomni_kamailio 2>&1 \| grep 'RTPEngine'` | `RTPEngine OFFER failed` |
| TURN | `docker logs --since 1h vozipomni_coturn` | Errores de autenticación o de relay |
| WhatsApp | `docker logs --since 1h vozipomni_backend 2>&1 \| grep 'WhatsApp'` | `Verificación de webhook rechazada`, `Firma inválida` |
| Nginx | `tail -f /opt/vozipomni/logs/nginx/vozipomni_error.log` | 502/504 hacia los upstream |

El backend escribe además un log JSON rotativo en `/app/logs/vozipomni.log` (montado en `/opt/vozipomni/logs/`), con rotación a 10 MB y 5 copias.

Conteo diario de IPs baneadas por Kamailio:

```bash
docker logs --since 24h vozipomni_kamailio 2>&1 | grep SECURITY | grep -oE 'from [0-9.]+|SCANNER [0-9.]+|desde [0-9.]+' | awk '{print $2}' | sort | uniq -c | sort -rn | head
```

## Tareas periódicas de Celery

`celery_beat` usa `django_celery_beat.schedulers:DatabaseScheduler`. Las tareas por defecto están en `CELERY_BEAT_SCHEDULE` de `backend/config/settings.py`:

| Nombre | Frecuencia | Propósito |
|---|---|---|
| `process-pending-callbacks` | cada 60 s | Ejecuta callbacks programados |
| `process-pending-calls` | cada 60 s | Revisa campañas activas del marcador |
| `update-prometheus-metrics` | cada 60 s | Actualiza métricas de agentes para Prometheus |
| `update-agent-statistics` | cada 60 s | Recalcula estadísticas de agentes |
| `reset-daily-agent-metrics` | diario 00:01 | Reinicia métricas diarias de agentes |
| `close-agent-status-history` | cada 6 h (minuto 0) | Cierra historial de estados huérfano |
| `detect-orphan-calls` | cada 300 s | Detecta llamadas colgadas sin heartbeat |
| `check-asterisk-health` | cada 120 s | Comprueba la salud de Asterisk |
| `sync-telephony-config` | cada 5 min | Sincroniza configuración de telefonía a Redis |
| `check-fraud-alerts` | cada 120 s | Evalúa alertas antifraude |
| `reset-extension-rate-counters` | diario 03:15 | Reinicia contadores de tasa por extensión |
| `scan-unlinked-recordings` | cada 15 min | Vincula grabaciones que quedaron sin asociar a una llamada |
| `run-scheduled-reports` | diario 01:30 | Genera y envía reportes programados |
| `poll-email-accounts` | cada 60 s | Lee buzones IMAP del canal email |
| `dispatch-scheduled-broadcasts` | cada 60 s | Envía difusiones programadas |
| `sync-whatsapp-templates` | cada 2 h (minuto 0) | Sincroniza el estado de plantillas de WhatsApp en Meta |
| `cleanup-old-recordings` | diario 02:00 | Aplica la retención de grabaciones |

Las horas siguen `TZ` (por defecto `America/Bogota`).

`backend/config/celery.py` también define `app.conf.beat_schedule`, con otros intervalos y algunos nombres de tarea distintos (por ejemplo, `process-pending-calls` cada 10 s y `generate-daily-reports`). No confirmé cuál de las dos definiciones prevalece en ejecución. Para ver las tareas que beat tiene registradas en la base de datos:

```bash
docker exec vozipomni_backend python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
for t in PeriodicTask.objects.all().order_by('name'):
    print(t.enabled, t.name, t.task, t.interval or t.crontab, t.last_run_at)
"
```

Las mismas tareas se ven en el admin de Django (`/admin/`, sección Periodic tasks). Para confirmar que el worker está vivo y ver qué ejecuta:

```bash
docker exec vozipomni_celery_worker celery -A config inspect ping
docker exec vozipomni_celery_worker celery -A config inspect active
```

## Estado de la telefonía

Asterisk, con comandos de una línea:

```bash
docker exec vozipomni_asterisk asterisk -rx 'core show uptime'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show endpoints'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show registrations'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show contacts'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show transports'
docker exec vozipomni_asterisk asterisk -rx 'core show channels'
docker exec vozipomni_asterisk asterisk -rx 'core show calls'
docker exec vozipomni_asterisk asterisk -rx 'queue show'
docker exec vozipomni_asterisk asterisk -rx 'manager show connected'
```

- `pjsip show registrations`: las troncales con registro deben estar en `Registered`.
- `pjsip show endpoints`: los agentes y `kamailio-endpoint`. Los agentes WebRTC llegan a Asterisk a través de Kamailio.
- `queue show`: miembros de cada cola, si están pausados y llamadas en espera.
- `manager show connected`: sesiones AMI activas (backend, celery_worker, dialer).

Kamailio (el módulo `ctl` está cargado, así que `kamcmd` funciona):

```bash
docker exec vozipomni_kamailio kamcmd core.uptime
docker exec vozipomni_kamailio kamcmd ul.dump
docker exec vozipomni_kamailio kamcmd htable.dump ipban
```

`ul.dump` lista los agentes registrados en Kamailio; `htable.dump ipban` lista las IPs baneadas en memoria (expiran a la hora).

El script `voip-debug.sh` agrupa varios de estos comandos:

```bash
bash /opt/vozipomni/voip-debug.sh pjsip-endpoints
bash /opt/vozipomni/voip-debug.sh calls-active
bash /opt/vozipomni/voip-debug.sh kamailio-stats
bash /opt/vozipomni/voip-debug.sh port-test
```

## Ver también

- [Servicios Docker](servicios-docker.md)
- [Solución de problemas](solucion-de-problemas.md)
- [Depuración VoIP](depuracion-voip.md)
- [Mantenimiento](mantenimiento.md)
- [Reportes](../administracion/reportes.md)
- [Seguridad y antifraude](../administracion/seguridad-antifraude.md)
