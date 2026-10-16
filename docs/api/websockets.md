# WebSockets (tiempo real)

VozipCX tiene dos servicios WebSocket:

1. Django Channels, servido por Daphne detrás de nginx en `wss://<IP_DEL_SERVIDOR>/ws/...`. Es el que usa el frontend (consola del agente, dashboard, supervisión y bandeja omnicanal).
2. Un servidor aiohttp independiente (`websocket_server/server.py`) en el puerto `WS_PORT` (8765 por defecto) con ruta `/ws`. El frontend no lo usa; reenvía mensajes de canales pub/sub de Redis.

Código fuente:

- `backend/config/asgi.py`: `ProtocolTypeRouter` con `JwtAuthMiddlewareStack` para `websocket`.
- `backend/core/websocket_auth.py`: autenticación por `?token=`.
- `backend/apps/api/routing.py`: rutas.
- `backend/apps/api/consumers.py` y `backend/apps/api/consumers_enhanced.py`: consumers.
- Productores de eventos: `backend/apps/telephony/ami_cdr_listener.py`, `backend/apps/telephony/asterisk_ami.py`, `backend/apps/telephony/security.py`, `backend/core/event_handlers.py`, `backend/apps/messaging/realtime.py`.
- `docker/nginx/*.conf`: `location /ws/` hacia Daphne.
- `websocket_server/server.py`: servidor aiohttp.

Convenciones de la API REST: [README.md](./README.md). Token JWT: [autenticacion.md](./autenticacion.md). Términos: [Glosario](../general/glosario.md).

## Django Channels

### Conexión y autenticación

- URL: `wss://<IP_DEL_SERVIDOR>/ws/<ruta>/?token=<TOKEN>` (o `ws://` sin TLS). nginx hace el upgrade en `location /ws/` con `proxy_read_timeout 86400`.
- `JwtAuthMiddleware` lee el parámetro `token` de la query string, lo valida como access token de simplejwt y carga el usuario (debe estar activo). Sin token, con token vencido o inválido, el usuario es anónimo y el consumer rechaza la conexión.
- No se acepta la cabecera `Authorization` ni cookies de sesión: el token va siempre en la URL.
- El token se valida solo al conectar. Si expira (8 horas) con la conexión abierta, la conexión sigue viva; al reconectar hay que usar un token vigente.
- `asgi.py` no usa `AllowedHostsOriginValidator`: no se valida el origen del handshake.
- Capa de canales: `channels_redis` (`RedisChannelLayer`) sobre `REDIS_URL`.

El token viaja en la URL, así que puede quedar en logs de acceso de proxies. Use siempre `wss://` en producción.

### Rutas

| Ruta | Consumer | Quién puede conectar | Grupos |
|---|---|---|---|
| `/ws/agent/<agent_id>/` | `AgentConsumer` | El usuario dueño del agente, `admin`, `supervisor` o superusuario. | `agent_<agent_id>` |
| `/ws/campaign/<campaign_id>/` | `CampaignConsumer` | `admin`, `supervisor`, `analyst`, superusuario o agentes asignados a la campaña. | `campaign_<campaign_id>` |
| `/ws/dashboard/` | `RealtimeDashboardConsumer` | `is_staff`, superusuario o rol `admin`, `supervisor`, `analyst`. | `dashboard`, `asterisk_events` |
| `/ws/asterisk/` | `AsteriskEventConsumer` | Cualquier usuario autenticado. | `asterisk_events` y, si tiene perfil de agente, `agent_<agent.id>` |
| `/ws/messaging/` | `MessagingConsumer` | `admin`, `supervisor`, superusuario o usuario con perfil de agente. | `messaging_all` (supervisores) o `messaging_agent_<agent.id>` + `messaging_unassigned` (agentes) |
| Cualquier otra | `NotFoundConsumer` | Nadie. | |

`<agent_id>` y `<campaign_id>` son claves primarias numéricas (`Agent.id`, `Campaign.id`).

`consumers.py` también define `DashboardConsumer`, pero no está enrutado; `/ws/dashboard/` usa `RealtimeDashboardConsumer`.

### Códigos de cierre

| Código | Consumer | Causa |
|---|---|---|
| `4401` | `AgentConsumer`, `CampaignConsumer`, `MessagingConsumer` | Sin usuario autenticado (token ausente o inválido). |
| `4403` | `AgentConsumer`, `CampaignConsumer`, `MessagingConsumer` | Autenticado sin acceso (otro agente, campaña ajena, usuario sin perfil de agente en mensajería). |
| `4404` | `NotFoundConsumer` | Ruta inexistente. |
| Sin código propio | `RealtimeDashboardConsumer`, `AsteriskEventConsumer` | Rechazan el handshake con `close()` sin código; el navegador suele reportar `1006`. |

### Ejemplo de conexión (JavaScript)

```javascript
const token = localStorage.getItem('auth_token') // access token JWT
const proto = location.protocol === 'https:' ? 'wss' : 'ws'
let socket
let retry = 1000

function connect () {
  socket = new WebSocket(`${proto}://${location.host}/ws/dashboard/?token=${encodeURIComponent(token)}`)

  socket.onopen = () => {
    retry = 1000
    socket.send(JSON.stringify({ action: 'refresh_agents' }))
  }

  socket.onmessage = (evt) => {
    const msg = JSON.parse(evt.data)
    switch (msg.type) {
      case 'initial_data': /* stats, agents, queues, active_calls */ break
      case 'stats_update': /* msg.data */ break
      case 'dashboard_update':
        if (msg.event === 'security.event') { /* alerta antifraude: msg.data */ }
        else if (msg.event_type) { /* evento AMI: msg.event_type, msg.data */ }
        break
    }
  }

  socket.onclose = (evt) => {
    if (evt.code === 4401) return // renovar el token antes de reintentar
    setTimeout(connect, retry)
    retry = Math.min(retry * 2, 30000)
  }
}

connect()
```

El frontend usa `frontend/composables/useWebSocket.ts` (`buildWsUrl()` agrega el token) y mantiene polling de respaldo cada 10 a 30 s por si el socket cae.

### `/ws/dashboard/`

Al conectar envía `initial_data`:

```json
{
  "type": "initial_data",
  "stats": {
    "calls_today": 320,
    "calls_answered": 268,
    "calls_abandoned": 14,
    "calls_active": 7,
    "agents_available": 6,
    "agents_oncall": 9,
    "agents_wrapup": 1,
    "agents_break": 2,
    "avg_talk_time": 184.25,
    "service_level": 91.04,
    "timestamp": "2025-03-10T21:05:12.345678+00:00"
  },
  "agents": [
    {"id": 12, "name": "Laura Gómez", "extension": "1012", "status": "oncall", "calls_today": 38,
     "talk_time_today": 5788, "last_call": "2025-03-10T20:58:00+00:00", "logged_in_at": "2025-03-10T13:00:03+00:00"}
  ],
  "queues": [
    {"id": 2, "name": "Soporte", "strategy": "rrmemory", "members_count": 5, "calls_waiting": 1,
     "calls_completed": 131, "calls_abandoned": 7, "service_level_percentage": 80.0}
  ],
  "active_calls": [
    {"id": 5531, "channel": "PJSIP/1012-0000a1b2", "caller_id": "3001234567", "agent": "Laura Gómez",
     "duration": 0, "start_time": "2025-03-10T21:03:40+00:00"}
  ]
}
```

- `stats.service_level`: % de contestadas con espera de 20 s o menos sobre las contestadas del día (100 si no hay contestadas). Es distinto del nivel de servicio de [reportes.md](./reportes.md).
- "Hoy" es `start_time__date = timezone.now().date()`.
- Las fechas van en `isoformat()` UTC.

Mensajes del cliente al servidor (JSON con `action`):

| `action` | Respuesta |
|---|---|
| `refresh_stats` | `{"type": "stats_update", "data": {...}}` (mismo formato que `stats`). |
| `refresh_agents` | `{"type": "agents_update", "data": [...]}`. |
| `refresh_queues` | `{"type": "queues_update", "data": [...]}`. |
| `refresh_campaigns` | `{"type": "campaigns_update", "data": [{"id", "name", "type", "contacts_total", "contacts_called", "success_rate"}]}` (campañas activas ya iniciadas). |

Mensajes que envía el servidor por el grupo `dashboard` (se reenvían tal cual, con `type: "dashboard_update"`):

| Origen | Forma | Contenido |
|---|---|---|
| Listener AMI (`ami_cdr_listener`) | `{"type": "dashboard_update", "event_type": "...", "data": {...}}` | Ver tabla de eventos AMI. |
| Antifraude (`telephony/security.py`) | `{"type": "dashboard_update", "event": "security.event", "data": {"id", "type", "severity", "number", "trunk", "source"}}` | Cada `TelephonySecurityEvent` registrado. |
| Campañas (`core/event_handlers.py`) | `{"type": "dashboard_update", "event": "started"` o `"stopped", "campaign_id": 4}` | Inicio o parada de campaña. |

Ejemplo de evento de seguridad:

```json
{
  "type": "dashboard_update",
  "event": "security.event",
  "data": {"id": 91, "type": "international", "severity": "warning", "number": "00923001234567", "trunk": "troncal-principal", "source": "1012"}
}
```

Valores de `data.type` (`TelephonySecurityEvent.TYPE_CHOICES`): `international`, `blocked_prefix`, `not_allowed`, `too_long`, `trunk_full`, `global_limit`, `extension_rate`, `dialer_blocked`, `alert_spike`, `alert_international`, `alert_blocked`. `data.severity`: `info`, `warning`, `critical`. Configuración antifraude: [telefonia.md](./telefonia.md).

Además, el consumer está en `asterisk_events`: cuando llega un evento `call.hangup`, `agent.call_completed` o `queue.caller_abandon`, envía un `stats_update` recalculado (no reenvía el evento en sí).

### Eventos AMI

Los emite el listener AMI que arranca con el worker de Celery (`ami_cdr_listener.start_listener`) a los grupos `asterisk_events` (como `{"type": "asterisk_event", "event_type", "data"}`) y `dashboard` (como `dashboard_update`):

| `event_type` | `data` |
|---|---|
| `agent.status_changed` | `agent_id`, `agent_code`, `sip_extension`, `old_status`, `new_status` |
| `call.completed` / `call.ended` | `call_id`, `direction`, `status`, `duration` (billsec), `agent_id`, `queue_name` |
| `queue.caller_join` | `queue_name`, `caller`, `position`, `count` |
| `queue.caller_abandon` | `queue_name`, `uniqueid`, `hold_time` |

El cliente AMI asíncrono de `backend/apps/telephony/asterisk_ami.py` también publica en `asterisk_events` (`type: "asterisk.event"`) los eventos `call.new_channel`, `call.state_change`, `call.hangup`, `call.bridge`, `agent.call_connected`, `agent.call_completed`, `queue.member_added`, `queue.member_removed`, `queue.member_status`, `queue.caller_join`, `queue.caller_leave`, `queue.caller_abandon`, con datos como `channel`, `queue`, `member`, `caller_id`. No se verificó qué proceso instancia ese cliente en producción.

### `/ws/asterisk/`

Reenvía los mensajes del grupo `asterisk_events` como JSON con la forma `{"type", "event_type", "data"}`:

- `is_staff` o superusuario: todos los eventos. Ojo: se basa en `is_staff`, no en el rol `admin`.
- Usuario con perfil de agente: solo eventos `call.*` cuyo `data.channel` contenga `PJSIP/<extensión>` o cuyo `data.member` termine en la extensión; `agent.*` cuyo `data.member` contenga la extensión; `queue.*` cuyo `data.interface` o `data.member` contenga la extensión.
- Otros usuarios: se conectan pero no reciben eventos.

Los eventos del listener AMI de Celery no traen `channel`, `member` ni `interface`, así que con el filtro anterior solo llegan a usuarios `is_staff`; a los agentes solo les llegan los del cliente AMI asíncrono.

```json
{"type": "asterisk.event", "event_type": "call.hangup", "data": {"channel": "PJSIP/1012-0000a1b2", "cause": "16"}}
```

### `/ws/agent/<agent_id>/`

Canal de la consola del agente.

Del cliente al servidor:

| `type` | Efecto |
|---|---|
| `status_change` | Con `status`, reenvía `{"type": "status_update", "status": "..."}` a todas las conexiones del grupo `agent_<id>`. No guarda nada en la base de datos; el cambio real de estado se hace por REST (`agents/{id}/change_status/`). |
| `call_action` | Se acepta pero no tiene implementación. |

Del servidor al cliente:

| `type` | Contenido |
|---|---|
| `status_update` | `{"type": "status_update", "status": "available"}` |
| `incoming_call` | `{"type": "incoming_call", "call_data": {...}}`. El handler existe, pero no se encontró en el backend ningún productor que envíe `incoming_call` al grupo. |

Si el mismo agente tiene abierto `/ws/asterisk/` (que también se une a `agent_<id>`), un `status_change` llega a ese consumer, que no tiene handler para `agent_status_update`; Channels lo trata como error en esa conexión.

```javascript
const ws = new WebSocket(`wss://${location.host}/ws/agent/${agentId}/?token=${encodeURIComponent(token)}`)
ws.onopen = () => ws.send(JSON.stringify({ type: 'status_change', status: 'available' }))
ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

### `/ws/campaign/<campaign_id>/`

Solo tiene el handler `campaign_stats_update`, que enviaría `{"type": "stats_update", "stats": {...}}`. No se encontró en el backend ningún productor que publique en `campaign_<id>`; las notificaciones de campaña van al grupo `dashboard`.

### `/ws/messaging/`

Eventos de la bandeja omnicanal (`backend/apps/messaging/realtime.py`). Cada evento se envía a `messaging_all`, al grupo del agente asignado (o a `messaging_unassigned` si no hay agente) y, en reasignaciones, al agente anterior y a `messaging_unassigned`.

Forma del mensaje:

```json
{
  "type": "messaging",
  "event": "message.new",
  "conversation_id": 318,
  "agent_id": 12,
  "status": "open",
  "message_id": 5121,
  "direction": "inbound",
  "preview": "Hola, quiero información",
  "created": false,
  "channel_type": "whatsapp"
}
```

| `event` | Cuándo | Campos extra |
|---|---|---|
| `message.new` | Mensaje entrante registrado o saliente creado. | `message_id`, `direction`, `preview` (120 caracteres); en entrantes también `created` (conversación nueva) y `channel_type`. |
| `message.status` | Cambio de estado de entrega (Meta, envío propio). | `message_id`, `message_status`, `error` (en WhatsApp). |
| `message.media` | Terminó la descarga de un adjunto entrante. | `message_id` |
| `conversation.assigned` | `assign` o `take`. | |
| `conversation.closed` | `close`. | |
| `conversation.reopened` | `reopen`. | |

`status` y `agent_id` son el estado actual de la conversación. El frontend recarga la lista o la conversación al recibir cada evento.

## Servidor WebSocket independiente (puerto 8765)

`websocket_server/server.py` (aiohttp), contenedor `vozipomni_websocket`. En `docker-compose.prod.yml` corre con `network_mode: host` y `WS_PORT` (por defecto 8765). nginx no lo publica: se accede directo a `ws://<IP_DEL_SERVIDOR>:8765/ws`.

| Ruta | Descripción |
|---|---|
| `GET /ws` | WebSocket. |
| `GET /health` | `{"status": "healthy", "clients": N, "asterisk_clients": N, "timestamp": "..."}`. |

Autenticación:

- Con `?token=<TOKEN>`: valida la firma HS256 con `SECRET_KEY` y la expiración (mismo token de simplejwt). Si falla, acepta el handshake, envía `{"action": "error", "message": "Token inválido o expirado"}` y cierra.
- Sin token: solo se aceptan conexiones desde `127.0.0.1` o `::1`; las demás reciben `{"action": "error", "message": "Token requerido"}` y se cierran.
- Lee `role` del token con valor por defecto `agent`. El token de VozipCX no incluye `role`, así que todos quedan como `agent`; el rol no se usa para filtrar.

Parámetros opcionales: `type` (`browser` por defecto o `asterisk`) e `id` (identificador del cliente).

Mensajes del cliente (`action`):

| `action` | Respuesta |
|---|---|
| `ping` | `{"action": "pong", "timestamp": "..."}` |
| `asterisk_config_request` con `config_key` | `{"action": "asterisk_config_response", "config_key", "data"}` (valor de Redis `asterisk:config:<key>`). |
| `generate_report` con `report_data` | Encola en la lista Redis `reports:queue`, publica en `reports:new` y responde `{"action": "report_queued", "status": "processing"}`. No se encontró en el backend un consumidor de esa cola. |
| `subscribe_campaign` con `campaign_id` | Registra el cliente en el set Redis `campaign:<id>:subscribers` y responde `{"action": "subscribed", "campaign_id"}`. El reenvío no filtra por esta suscripción. |
| Otra | `{"action": "error", "message": "Unknown action: ..."}` |

Difusión: el servidor se suscribe a los canales Redis `asterisk:config`, `campaigns:updates`, `reports:generated` y `calls:events`, y reenvía cada mensaje tal cual a todos los clientes conectados, sin filtrar por usuario. En el código solo se encontraron publicaciones en `calls:events`, desde `dialer_engine/dialer.py`, con `type` `manual_contact_assigned`, `preview_contact_assigned` y `contact_skipped_dnc` (incluyen `campaign_id`).

```javascript
const ws = new WebSocket(`ws://<IP_DEL_SERVIDOR>:8765/ws?token=${encodeURIComponent(token)}&type=browser`)
ws.onopen = () => ws.send(JSON.stringify({ action: 'ping' }))
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data)
  if (msg.action === 'error') console.warn(msg.message)
  else console.log(msg)
}
```

Como el puerto 8765 no pasa por nginx, no tiene TLS y cualquier cliente con un token válido recibe todos los eventos difundidos. Si no lo usa, conviene no exponerlo fuera de la red interna.
