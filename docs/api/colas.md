# Colas

Colas ACD de Asterisk (`Queue()`): configuración, recarga, estadísticas y miembros. Código: `QueueViewSet` en `backend/apps/api/viewsets.py`, modelos en `backend/apps/queues/models.py`, sincronización con Asterisk en `backend/apps/telephony/signals.py`.

Convenciones comunes: [README.md](./README.md). Telefonía (IVR, rutas entrantes que envían a colas): [telefonia.md](./telefonia.md). KPIs de colas: [reportes.md](./reportes.md).

## Permisos

`IsAdminOrSupervisorOrReadOnly`: cualquier usuario autenticado puede leer (`list`, `retrieve`, `stats`, `members`); crear, editar, borrar y `reload_config` requieren `admin` o `supervisor`.

## CRUD: `/api/queues/`

| Acción | Método y ruta | Notas |
|---|---|---|
| list | `GET /api/queues/` | Paginado (50). |
| create | `POST /api/queues/` | |
| retrieve | `GET /api/queues/{id}/` | |
| update | `PUT /api/queues/{id}/` | |
| partial_update | `PATCH /api/queues/{id}/` | |
| destroy | `DELETE /api/queues/{id}/` | `204`. Borra también sus miembros y estadísticas (cascada). |

Cada `create`, `update` y `destroy` dispara las señales `post_save`/`post_delete` de `Queue`, que regeneran la configuración de colas de Asterisk y la recargan (`sync_asterisk_now()`).

Filtros: `is_active` (`true`/`false`) y `strategy`. Búsqueda: `search` sobre `name` y `extension`. Este ViewSet no incluye `OrderingFilter`, así que `?ordering=` no tiene efecto.

### Campos (`QueueSerializer`, `fields = '__all__'`)

| Campo | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `id` | integer | | Solo lectura. |
| `name` | string | | Obligatorio, único. Es el nombre de la cola en Asterisk y la referencia desde IVR y rutas entrantes (`destination`). |
| `extension` | string | | Obligatorio, único. Número para marcar a la cola. |
| `description` | string | `""` | |
| `strategy` | string | `ringall` | `ringall`, `leastrecent`, `fewestcalls`, `random`, `rrmemory`, `linear`. |
| `timeout` | integer | 30 | Segundos que timbra cada agente. |
| `retry` | integer | 5 | Segundos antes de reintentar con otro agente. |
| `max_wait_time` | integer | 300 | Tiempo máximo en cola (s). |
| `announce_frequency` | integer | 30 | Frecuencia del anuncio de posición (s). |
| `announce_holdtime` | boolean | `true` | Anunciar tiempo estimado de espera. |
| `periodic_announce_frequency` | integer | 60 | Anuncio periódico (s). |
| `music_on_hold` | string | `default` | Clase de música en espera (ver `/api/telephony/music-on-hold/`). |
| `max_callers` | integer | 0 | Máximo de llamadas en espera; 0 es ilimitado. |
| `service_level` | integer | 60 | Umbral del nivel de servicio en segundos. |
| `wrap_up_time` | integer | 0 | Tiempo post-llamada del agente (s). |
| `is_active` | boolean | `true` | |
| `created_at`, `updated_at` | datetime | | Solo lectura. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/queues/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "ventas", "extension": "800", "description": "Cola de ventas", "strategy": "rrmemory", "timeout": 20, "max_wait_time": 240, "service_level": 20, "wrap_up_time": 10}'
```

Respuesta `201`:

```json
{
  "id": 2,
  "name": "ventas",
  "extension": "800",
  "description": "Cola de ventas",
  "strategy": "rrmemory",
  "timeout": 20,
  "retry": 5,
  "max_wait_time": 240,
  "announce_frequency": 30,
  "announce_holdtime": true,
  "periodic_announce_frequency": 60,
  "music_on_hold": "default",
  "max_callers": 0,
  "service_level": 20,
  "wrap_up_time": 10,
  "is_active": true,
  "created_at": "2025-03-10 11:20:03",
  "updated_at": "2025-03-10 11:20:03"
}
```

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/queues/?is_active=true&search=ven" \
  -H "Authorization: Bearer <TOKEN>"
```

Errores comunes:

| Código | Causa | Cuerpo |
|---|---|---|
| `400` | `name` o `extension` repetidos. | `{"name": ["Ya existe Cola con este Nombre."]}` |
| `400` | Estrategia inválida. | `{"strategy": ["\"xyz\" no es una elección válida."]}` |
| `403` | Escritura con rol `agent` o `analyst`. | `{"detail": "Se requiere rol de administrador o supervisor para modificar."}` |

## POST /api/queues/{id}/reload_config/

Fuerza la regeneración de toda la configuración de Asterisk y recarga `app_queue.so` y el dialplan por AMI. Útil si la recarga automática falló. Rol `admin` o `supervisor`. Sin cuerpo.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/queues/2/reload_config/ \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{"success": true, "message": "Configuración de cola ventas recargada en Asterisk"}
```

Error: `500 {"success": false, "message": "Error: ..."}`. Si AMI no conecta, los archivos se escriben igual y la respuesta sigue siendo `200` (la recarga no se ejecuta).

## GET /api/queues/{id}/stats/

Estadísticas en tiempo real guardadas en `QueueStats` (relación uno a uno con la cola), que actualiza el backend a partir de los eventos de Asterisk. Cualquier usuario autenticado.

```bash
curl -s https://<IP_DEL_SERVIDOR>/api/queues/2/stats/ \
  -H "Authorization: Bearer <TOKEN>"
```

Con estadísticas:

```json
{
  "queue": "ventas",
  "calls_waiting": 3,
  "calls_completed": 412,
  "calls_abandoned": 27,
  "avg_wait_time": 18,
  "avg_talk_time": 204,
  "agents_available": 4,
  "agents_busy": 6,
  "service_level_percentage": 86.5
}
```

Tiempos en segundos. Si la cola todavía no tiene registro de estadísticas:

```json
{"queue": "ventas", "message": "Sin estadísticas disponibles"}
```

Las definiciones de nivel de servicio, abandono y tiempos promedio están en el [Glosario](../general/glosario.md). Para históricos por rango de fechas use los reportes ([reportes.md](./reportes.md)).

## GET /api/queues/{id}/members/

Miembros (agentes) de la cola. Cualquier usuario autenticado. No paginado.

```bash
curl -s https://<IP_DEL_SERVIDOR>/api/queues/2/members/ \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{
  "queue": "ventas",
  "members": [
    {
      "id": 14,
      "agent_id": 9,
      "agent_name": "Juan Pérez - 1005",
      "penalty": 0,
      "paused": false,
      "calls_taken": 37,
      "last_call": "2025-03-10T11:05:40-05:00"
    }
  ],
  "count": 1
}
```

- `agent_id` es la clave primaria del agente (no el código `AGT...`).
- `agent_name` es la representación del agente: nombre completo y extensión SIP.
- `paused`, `calls_taken` y `last_call` los actualiza el listener de eventos AMI (`QueueMemberPause`, fin de llamada).
- `last_call` sale en ISO 8601 porque la respuesta se arma a mano y no pasa por un serializer.

## Administración de miembros

La API REST no expone creación, edición ni borrado de miembros de cola (`QueueMember`). No existe `/api/queue-members/` ni acciones para agregar o quitar agentes de una cola. Los miembros se gestionan en el admin de Django (`https://<IP_DEL_SERVIDOR>/admin/`, sección Colas, con edición en línea dentro de cada cola o en "Miembros de Colas").

Relación con la sesión del agente:

- `POST /api/agents/{id}/login/` emite `agent_logged_in`, y `core/event_handlers.py` agrega al agente (`PJSIP/<extensión>`) por AMI `QueueAdd` a cada cola donde tiene membresía.
- `POST /api/agents/{id}/logout/` emite `agent_logged_out` para retirarlo.
- Guardar o borrar un `QueueMember` también regenera la configuración de Asterisk (señales de `backend/apps/telephony/signals.py`).

Ver [usuarios-y-agentes.md](./usuarios-y-agentes.md) para las acciones de sesión del agente.

Véase también: [Glosario](../general/glosario.md), [Desarrollo del backend](../desarrollo/backend.md).
