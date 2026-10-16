# Solución de problemas

Esta guía recoge los fallos conocidos de VozipCX en producción, organizados por área. Cada caso sigue el esquema síntoma, causa, verificación y solución. Para capturas SIP detalladas vea [depuración VoIP](depuracion-voip.md).

Los comandos asumen la instalación en `/opt/vozipomni`:

```bash
cd /opt/vozipomni
```

## Instalación y actualización

### `deploy.sh --update` falla con "required variable TURN_SECRET is missing"

- Causa: la versión anterior de `deploy.sh` no generaba `TURN_SECRET`, que ahora exige el servicio `coturn`. Bash ejecuta la copia que tenía en memoria antes del `git pull`.
- Solución: vuelva a ejecutar la actualización. La versión actual detecta que `deploy.sh` cambió con el `git pull` y se relanza sola; en ese arranque `ensure_env_secret` genera `TURN_SECRET` si falta.

```bash
sudo bash /opt/vozipomni/deploy.sh --update <IP_PRIVADA> --nat <IP_PUBLICA>
```

- Alternativa manual (solo si la variable no existe o está vacía):

```bash
grep -q '^TURN_SECRET=.\+' .env || printf '\nTURN_SECRET=%s\n' "$(openssl rand -hex 32)" >> .env
chmod 600 .env
docker compose -f docker-compose.prod.yml up -d coturn backend
```

### La actualización se detiene con "Falta <VARIABLE> en .env"

- Causa: en modo `--update`, `deploy.sh` no genera `SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `ASTERISK_AMI_PASSWORD` ni `FIELD_ENCRYPTION_KEY`, porque cambiarlos rompería datos existentes.
- Solución: recupere el valor desde un respaldo del `.env` (ver [respaldos](respaldos.md)) o desde `.env.backup_*`. No invente un `FIELD_ENCRYPTION_KEY` nuevo si ya hay contraseñas SIP cifradas.

### "Contraseña del .env no coincide con PostgreSQL"

- Causa: el volumen `postgres_data` se creó con otra contraseña. PostgreSQL solo lee `POSTGRES_PASSWORD` al inicializar el volumen.
- Verificar:

```bash
docker exec vozipomni_postgres psql -U vozipomni_user -d vozipomni -c 'SELECT 1'
```

- Solución: `deploy.sh` intenta sincronizarla con `ALTER USER` por el socket local. Si no puede, sugiere `bash fix-db-password.sh`. No acepte el reseteo del volumen salvo que quiera perder la base de datos.

### El backend no llega a healthy

```bash
docker logs --tail=100 vozipomni_backend
docker inspect --format '{{json .State.Health}}' vozipomni_backend
```

Causas habituales: migración fallida, variable requerida vacía (el compose aborta con `... requerido en .env`), o PostgreSQL/Redis caídos (`"checks"` en `/api/health/`).

### Nginx no arranca: "[SSL-switch] ERROR: faltan certificados confiables"

- Causa: no existen `docker/nginx/ssl/vozipomni.crt` y `vozipomni.key`. En producción el script de Nginx no genera autofirmados salvo que `ALLOW_SELF_SIGNED_SSL=true`.
- Solución: instale el certificado (ver [SSL y HTTPS](../instalacion/ssl-https.md)) y recree Nginx con `docker compose -f docker-compose.prod.yml up -d nginx`.

### Archivos extraños en /opt/vozipomni (`[asterisk`, `=`, `CACHED`)

- Causa: se pegó en la terminal la salida de `docker compose build`.
- Solución: bórrelos uno por uno con `rm -i --`. Nunca use `git clean -f`: `credentials.txt` y `.env.backup_*` no están versionados ni ignorados y se borrarían. Procedimiento en [mantenimiento](mantenimiento.md#limpieza-de-archivos-extranos).

## Softphone y registro

### El softphone se queda en "Conectando…"

Revise en este orden:

1. HTTPS: el navegador solo permite micrófono y WebRTC en contexto seguro. La URL debe empezar por `https://`.
2. Caché del frontend: tras una actualización el navegador puede tener JavaScript viejo. Recargue con Ctrl+F5.
3. Ticket del WebSocket: Nginx valida cada conexión a `/sip/ws` con `auth_request` contra `/api/telephony/sip-ws-auth/`. Sin ticket válido responde 401.

```bash
docker logs --since 30m vozipomni_backend 2>&1 | grep 'SIP-WS'
grep '/sip/ws' /opt/vozipomni/logs/nginx/vozipomni_access.log | tail -20
```

`[SIP-WS] Handshake rechazado` indica ticket ausente, vencido (`SIP_WS_TICKET_TTL`, 24 h por defecto), firmado con otra `SECRET_KEY` o de un usuario inactivo. Solución: cerrar sesión y volver a entrar.

4. Kamailio escuchando en el WebSocket:

```bash
ss -tlnp | grep ':8080'
docker logs --tail=50 vozipomni_kamailio
```

Debe verse `127.0.0.1:8080`. El puerto 8080 no se publica: todo pasa por Nginx.

### La extensión no registra o Asterisk no la conoce

```bash
docker exec vozipomni_asterisk asterisk -rx 'pjsip show endpoints'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show endpoint <EXTENSION>'
docker exec vozipomni_asterisk ls -l /var/lib/asterisk/dynamic/
```

Si la extensión existe en la web pero no en Asterisk, regenere la configuración:

```bash
docker exec vozipomni_backend python manage.py generate_asterisk_config
```

`diagnostico-extension.sh` hace una revisión completa, pero está fijo para la extensión `100` e imprime el secreto SIP en pantalla. Úselo con cuidado y no comparta su salida.

### El agente no recibe llamadas (480 Temporarily Unavailable)

- Causa: Kamailio no tiene al agente en `location`. El log muestra `Agente <ext> no encontrado en location`.

```bash
docker exec vozipomni_kamailio kamcmd ul.dump | grep -i 'AoR'
```

- Solución: el agente debe tener el softphone conectado. Si se registró y desaparece, revise la red del agente y los logs de Kamailio.

### IP bloqueada por Kamailio (403 o sin respuesta)

```bash
docker logs --since 24h vozipomni_kamailio 2>&1 | grep SECURITY
docker exec vozipomni_kamailio kamcmd htable.dump ipban
```

Kamailio banea una hora las IPs que hacen flood, usan escáneres SIP conocidos o envían peticiones SIP sin ser orígenes confiables. Para liberar una IP legítima:

```bash
docker exec vozipomni_kamailio kamcmd htable.delete ipban <IP>
```

Si necesita teléfonos IP de la red local, defina `KAMAILIO_TRUST_LAN=1` en `.env` y recree Kamailio.

## Audio

### Audio en un solo sentido o sin audio

1. Puertos de medios en el firewall:
   - RTPEngine: el entrypoint lo arranca con `--port-min=23000 --port-max=23300`. `deploy.sh` abre `10000:23100/udp`, así que 23101-23300 puede quedar cerrado. Compruébelo y ábralo si su firewall es restrictivo.
   - Asterisk: `rtp.conf` usa 10000-10300.
   - TURN: 3478 tcp/udp y relay 49152-49200/udp.

```bash
ufw status | grep -E '23[0-9]{3}|3478|49152'
ss -ulnp | grep -c rtpengine
```

2. NAT: si el servidor está detrás de NAT, `NAT_IPV4` debe tener la IP pública.

```bash
grep -E '^(VOZIPOMNI_IPV4|NAT_IPV4)=' .env
docker logs vozipomni_rtpengine 2>&1 | grep -E 'NAT detectado|IP directa|Interface'
docker logs vozipomni_asterisk 2>&1 | grep 'IP externa'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show transport trunk-nat-transport'
```

`external_media_address` de `trunk-nat-transport` debe ser la IP pública. Si cambió `NAT_IPV4`, recree `asterisk` y `rtpengine`.

3. TURN: el backend firma credenciales temporales con `TURN_SECRET` y coturn las valida con el mismo valor.

```bash
grep -c '^TURN_SECRET=.\+' .env
docker logs --since 30m vozipomni_coturn
```

Si cambió `TURN_SECRET`, recree `coturn` y `backend`, y los agentes deben recargar la página.

4. Navegador: en `chrome://webrtc-internals` revise si `inbound-rtp` recibe bytes. Si recibe pero no suena, el problema está en el navegador: dispositivo de salida, permisos o una versión vieja del frontend (Ctrl+F5).

### 488 Not Acceptable Here o "RTPEngine OFFER failed"

- Causa: RTPEngine no está corriendo o no escucha el puerto de control.

```bash
docker logs --tail=50 vozipomni_rtpengine
ss -ulnp | grep 22222
```

- Solución: `docker compose -f docker-compose.prod.yml up -d rtpengine`. Si sale con `ERROR: No se pudo determinar la IP de la interfaz`, revise `VOZIPOMNI_IPV4`.

## Llamadas salientes

### La consola de Asterisk muestra "Sin ruta para <número>"

- Causa: el número cayó en el catch-all de `[from-internal]` porque ninguna ruta saliente coincide. El usuario oye `ss-noservice` y la llamada se rechaza.

```bash
docker exec vozipomni_asterisk asterisk -rx 'dialplan show from-internal'
```

- Solución: cree una ruta saliente con el patrón adecuado y una troncal asociada (ver [rutas y dialplan](../administracion/rutas-y-dialplan.md)).

### "File ss-noservice does not exist"

- Causa: faltaban las locuciones del sistema. Ahora la imagen incluye las locuciones es/en 1.6.1 y el entrypoint las copia a `/var/lib/asterisk/sounds` si falta el marcador.

```bash
docker exec vozipomni_asterisk sh -c 'ls -la /var/lib/asterisk/sounds/.vozipomni-core-sounds-1.6.1; ls /var/lib/asterisk/sounds/es | head'
```

- Solución: reconstruya y recree Asterisk (`deploy.sh --update` lo hace). Si existe el marcador pero faltan archivos, bórrelo y reinicie para forzar la copia (`cp -n` no pisa audios propios):

```bash
docker exec vozipomni_asterisk rm /var/lib/asterisk/sounds/.vozipomni-core-sounds-1.6.1
docker compose -f docker-compose.prod.yml restart asterisk
```

### La llamada se corta a los 32 segundos con 408

- Causa: el ACK del 200 OK no llegaba a Asterisk, que retransmitía el 200 OK y cortaba al vencer el temporizador. Se corrigió en `kamailio.cfg` con `record_route()` en las peticiones iniciales y `alias` con puerto (`alias=<IP>:5060`).
- Verificar que la imagen tiene la corrección:

```bash
docker exec vozipomni_kamailio grep -nE '^alias=|record_route\(\)' /etc/kamailio/kamailio.cfg
```

- Verificar en la captura que aparece el ACK en ambos tramos:

```bash
docker exec -it vozipomni_kamailio sngrep -d any -r
```

- Solución: reconstruya Kamailio (`docker compose -f docker-compose.prod.yml build kamailio && docker compose -f docker-compose.prod.yml up -d kamailio`).

### La troncal no registra

```bash
docker exec vozipomni_asterisk asterisk -rx 'pjsip show registrations'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show endpoints' | grep -iA3 '<NOMBRE_TRONCAL>'
```

Revise credenciales, IP autorizada en el proveedor y el transporte: `trunk-nat-transport` (5162) si hay NAT, `trunk-transport` (5161) si no. `dtmf_mode=rfc2833` impide crear el endpoint en PJSIP; `deploy.sh --update` lo corrige a `rfc4733`.

## Llamadas entrantes

### Las llamadas entran al IVR por defecto

- Causa: no hay ruta entrante para el DID. `[from-pstn]` envía lo no configurado a `from-internal,9000`.
- Solución: cree la ruta entrante para el DID en la web.

### El proveedor envía llamadas pero Asterisk no responde

- Causa probable: `deploy.sh` solo publica 5060; las troncales usan 5161/5162. Si la troncal no registra (autenticación por IP), el INVITE del proveedor llega a un puerto cerrado.
- Solución: permita solo la IP del proveedor:

```bash
ufw allow from <IP_PROVEEDOR> to any port 5161:5162 proto udp
```

### La llamada entra pero no suena en ningún agente

```bash
docker exec vozipomni_asterisk asterisk -rx 'queue show'
docker exec vozipomni_kamailio kamcmd ul.dump | grep -i 'AoR'
```

Revise agentes pausados, cola sin miembros y agentes no registrados en Kamailio.

## Grabaciones

### Las grabaciones no aparecen en la web

- Causa: el archivo no existe, no es visible para el backend o no se vinculó a la llamada. Los nombres incluyen `UNIQUEID`, que se usa para vincularlos.

```bash
docker exec vozipomni_asterisk sh -c 'ls -lt /var/spool/asterisk/monitor | head'
docker exec vozipomni_backend sh -c 'ls -lt /var/spool/asterisk/monitor | head'
docker logs --since 2h vozipomni_celery_worker 2>&1 | grep 'Recording'
```

Use comillas en `sh -c '...'` para que el comodín se expanda dentro del contenedor y no en el host.

- Solución:
  - Si el backend no ve el directorio, recree `backend` y `celery_worker`; ambos montan `asterisk_spool`.
  - `Sin archivo de grabación para call ...` indica que MixMonitor no grabó (llamada sin puente) o que el nombre no contiene el `UNIQUEID`.
  - `scan-unlinked-recordings` vuelve a intentarlo cada 15 minutos.

## AMI y CDR

### "No se pudo conectar a Asterisk AMI"

```bash
grep -c '^ASTERISK_AMI_PASSWORD=.\+' .env
docker logs --since 30m vozipomni_backend 2>&1 | grep -i 'AMI'
docker exec vozipomni_asterisk asterisk -rx 'manager show connected'
docker exec vozipomni_backend python manage.py shell -c "from apps.telephony.asterisk_ami import AsteriskAMI; a=AsteriskAMI(); print(a.connect()); a.disconnect()"
```

- `ASTERISK_AMI_PASSWORD no está configurado`: falta en `.env`. Es obligatoria.
- `Error de autenticación AMI`: Asterisk tiene otra clave. El entrypoint la escribe en `manager.conf` al arrancar; tras cambiarla en `.env`, recree `asterisk` y los servicios Django.
- Cierre inmediato de la conexión: el cliente lee el banner de una línea antes del login porque `manager.conf` tiene `authtimeout = 10`. Si ve `Banner AMI inesperado`, confirme que el backend llega a `VOZIPOMNI_IPV4:5038`.
- Rechazo por ACL: `manager.conf` permite `127.0.0.1`, `ASTERISK_AMI_PERMIT_NETWORK` (por defecto `172.20.0.0/24`) y `ASTERISK_AMI_PERMIT_IP`. Si el log de Asterisk muestra el rechazo de otra IP interna, ajuste esas variables.

### No se registran CDR

El listener de CDR arranca con el worker de Celery.

```bash
docker logs vozipomni_celery_worker 2>&1 | grep 'CDR Listener'
```

Si aparece `Error arrancando CDR Listener`, corrija la conexión AMI y reinicie `celery_worker`.

## Reportes

- Los reportes programados no llegan: `run-scheduled-reports` corre a las 01:30. Sin `EMAIL_HOST`, Django usa el backend de consola y los correos quedan en el log del worker.

```bash
docker logs --since 24h vozipomni_celery_worker 2>&1 | grep -iE 'report|mail'
docker logs --since 10m vozipomni_celery_beat
```

- Métricas diarias en cero al iniciar el día: `reset-daily-agent-metrics` las reinicia a las 00:01, hora de `TZ`.

## Omnicanal y webhook de WhatsApp

- La verificación en Meta falla: la URL es `<PUBLIC_BASE_URL>/api/webhooks/whatsapp/<app_id>/` y debe ser HTTPS con certificado válido; Meta rechaza autofirmados.

```bash
grep '^PUBLIC_BASE_URL=' .env
docker logs --since 1h vozipomni_backend 2>&1 | grep 'WhatsApp'
curl -s "https://<DOMINIO>/api/webhooks/whatsapp/<APP_ID>/?hub.mode=subscribe&hub.verify_token=<TOKEN>&hub.challenge=prueba"
```

La respuesta correcta es `prueba`. `Verificación de webhook rechazada` indica `app_id` o `verify_token` incorrectos o proveedor inactivo.

- `Firma inválida en webhook`: el `app_secret` configurado no coincide con el de la app en Meta.
- Plantillas desactualizadas: se sincronizan cada 2 horas.
- Correos que no entran: `poll-email-accounts` corre cada 60 s; revise el log del worker.

## Notificaciones en el frontend

- Sin actualizaciones en tiempo real: los WebSocket `/ws/` van a Daphne (8001).

```bash
docker inspect --format='{{.State.Health.Status}}' vozipomni_daphne
grep ' /ws/' /opt/vozipomni/logs/nginx/vozipomni_access.log | tail
```

Un 502 en `/ws/` indica Daphne caído. Revise también Redis, que es el channel layer.

- Sin notificaciones del navegador: requieren HTTPS y permiso concedido. En mensajería solo se muestran si la pestaña no está visible o no tiene el foco.

## Rendimiento

```bash
docker stats --no-stream
docker inspect -f '{{.Name}} OOMKilled={{.State.OOMKilled}} Restarts={{.RestartCount}}' $(docker ps -aq)
df -h
```

- Contenedor reiniciado por memoria: los límites están en `deploy.resources` (por ejemplo, `daphne` 256M, `celery_worker` 1G). La transcripción con Whisper consume mucha memoria en el worker.
- API lenta: ajuste `GUNICORN_WORKERS` y `GUNICORN_TIMEOUT` en `.env` y recree `backend`.
- Colas de Celery atrasadas: ajuste `CELERY_CONCURRENCY` y recree `celery_worker`.
- Disco lleno: vea [mantenimiento](mantenimiento.md#espacio-en-disco).

## Ver también

- [Depuración VoIP](depuracion-voip.md)
- [Monitoreo](monitoreo.md)
- [Servicios Docker](servicios-docker.md)
- [Mantenimiento](mantenimiento.md)
- [Actualización](../instalacion/actualizacion.md)
- [Red y puertos](../instalacion/red-y-puertos.md)
- [Troncales SIP](../administracion/troncales-sip.md)
- [Omnicanal](../administracion/omnicanal.md)
