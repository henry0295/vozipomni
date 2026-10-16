# Supervisión en vivo y auditoría de gestiones

Endpoints del panel de supervisión (métricas del momento, estado de agentes, escucha, susurro, irrupción, pausa y desconexión forzadas) y de la auditoría de las calificaciones que registran los agentes.

Código fuente:

- `backend/apps/api/supervisor_viewsets.py`: `SupervisorViewSet` en `/api/supervisor/`.
- `backend/apps/api/extra_viewsets.py`: `AuditViewSet` en `/api/audits/`.
- `backend/apps/audit/models.py`: modelo `CallDispositionAudit`.
- `docker/asterisk/configs/extensions.conf`: contexto `[from-spy]` que ejecuta `ChanSpy`.

Convenciones comunes: [README.md](./README.md). Llamadas y canales: [telefonia.md](./telefonia.md). Eventos en tiempo real del tablero: [websockets.md](./websockets.md). KPIs por período: [reportes.md](./reportes.md). Términos: [Glosario](../general/glosario.md).

## Permisos

Ambos ViewSets usan `IsAdminOrSupervisor`: solo `admin`, `supervisor` o superusuario. `agent` y `analyst` reciben `403 {"detail": "Se requiere rol de administrador o supervisor para esta acción."}`.

## Resumen

| Método y ruta | Descripción |
|---|---|
| `GET /api/supervisor/dashboard/` | Resumen de agentes, llamadas del día y colas. |
| `GET /api/supervisor/agents/` | Estado detallado de cada agente y su llamada activa. |
| `POST /api/supervisor/{call_pk}/spy/` | Escuchar en silencio. |
| `POST /api/supervisor/{call_pk}/whisper/` | Hablarle solo al agente. |
| `POST /api/supervisor/{call_pk}/barge/` | Entrar a la llamada con ambas partes. |
| `POST /api/supervisor/{agent_pk}/force_break/` | Poner al agente en pausa. |
| `POST /api/supervisor/{agent_pk}/force_logout/` | Desconectar al agente. |
| `/api/audits/` | Auditoría de calificaciones (CRUD y acciones). |

El docstring del módulo muestra rutas como `/api/supervisor/spy/{call_id}/`, pero `SupervisorViewSet` es un `ViewSet` registrado en `DefaultRouter` con acciones `detail=True`, así que la ruta real lleva el ID antes de la acción: `/api/supervisor/{pk}/spy/`. Es la forma que usa el frontend (`frontend/pages/supervisor/index.vue`).

## Dashboard: `GET /api/supervisor/dashboard/`

Sin parámetros. "Hoy" se calcula con `timezone.now()` truncado a medianoche UTC, es decir desde las 19:00 del día anterior en hora de Colombia.

```bash
curl -s https://<IP_DEL_SERVIDOR>/api/supervisor/dashboard/ \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{
  "timestamp": "2025-03-10T21:05:12.345678+00:00",
  "agents": {
    "total": 25,
    "online": 18,
    "available": 6,
    "oncall": 9,
    "break": 2,
    "wrapup": 1,
    "offline": 7
  },
  "campaigns_active": 3,
  "calls": {
    "total": 320,
    "inbound": 210,
    "outbound": 110,
    "answered": 268,
    "abandoned": 14,
    "active_now": 7,
    "answer_rate": 83.8,
    "avg_talk_time": 184.0
  },
  "queues": [
    {"id": 2, "name": "Soporte", "calls_waiting": 1, "agents_available": 3}
  ]
}
```

| Campo | Cálculo |
|---|---|
| `agents.*` | Conteo de agentes por `status` en este momento. `online` excluye `offline`. |
| `campaigns_active` | Campañas con `status = active`. |
| `calls.answered` | Llamadas de hoy con `status = completed`. |
| `calls.active_now` | Llamadas de hoy en `initiated`, `ringing` o `answered`. |
| `calls.answer_rate` | `answered / total * 100` (un decimal). |
| `calls.avg_talk_time` | Conversación promedio de las contestadas, redondeada a entero. |
| `queues[].calls_waiting` | Llamadas de hoy de esa cola en `ringing`. |
| `queues[].agents_available` | Agentes `available` que son miembros no pausados de la cola. |

`timestamp` usa `isoformat()` en UTC.

## Estado de agentes: `GET /api/supervisor/agents/`

Todos los agentes con sus contadores del día y la llamada activa (si tienen una en `initiated`, `ringing` o `answered`).

```json
{
  "agents": [
    {
      "id": 12,
      "agent_id": "AG012",
      "name": "Laura Gómez",
      "sip_extension": "1012",
      "status": "oncall",
      "current_campaign": "Servicio al cliente",
      "calls_today": 38,
      "talk_time_today": 5788,
      "available_time_today": 9120,
      "break_time_today": 1800,
      "wrapup_time_today": 900,
      "session_duration": 25200,
      "occupancy": 50.0,
      "logged_in_at": "2025-03-10 08:00:03",
      "current_call_id": 5531,
      "current_call_channel": "PJSIP/1012-0000a1b2"
    }
  ],
  "total": 25
}
```

- `current_call_id` es la clave primaria de la llamada (`Call.id`), no el `call_id` de Asterisk. Es el valor que esperan `spy`, `whisper` y `barge`.
- `session_duration`: segundos desde `logged_in_at` (0 si no hay sesión).
- `occupancy`: (en llamada + conversación + post-llamada del día) / sesión * 100.

## Escucha, susurro e irrupción

`POST /api/supervisor/{call_pk}/spy/`, `.../whisper/` y `.../barge/` funcionan igual y solo cambian el modo:

| Acción | `SPY_MODE` | Efecto en `ChanSpy` |
|---|---|---|
| `spy` | `listen` | El supervisor escucha; nadie lo oye. |
| `whisper` | `whisper` | El supervisor habla solo con el agente. |
| `barge` | `barge` | El supervisor habla con agente y cliente. |

Flujo: la vista busca la llamada por clave primaria con estado `initiated`, `ringing` o `answered`, se conecta a Asterisk por AMI y origina una llamada a `PJSIP/<supervisor_extension>` en el contexto `from-spy` (extensión `s`) con las variables `SPY_MODE` y `SPY_CHANNEL` (canal de la llamada). Al contestar su softphone, el supervisor queda enganchado a la llamada. Si la llamada no tiene `channel` registrado, el dialplan cuelga (rama `nospy`).

Cuerpo:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `supervisor_extension` | string | Sí | Extensión PJSIP del supervisor que recibirá la llamada. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/supervisor/5531/whisper/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"supervisor_extension": "1900"}'
```

Respuestas `200`:

```json
{"success": true, "message": "Escuchando llamada ast-1741617900.45"}
```

```json
{"success": true, "message": "Susurrando al agente en llamada ast-1741617900.45"}
```

```json
{"success": true, "message": "Unido a la llamada ast-1741617900.45"}
```

Errores:

| Código | Cuerpo | Causa |
|---|---|---|
| `400` | `{"error": "supervisor_extension requerido"}` | Falta la extensión. |
| `404` | `{"error": "Llamada activa no encontrada"}` | No existe o ya no está activa. |
| `500` | `{"error": "..."}` | Excepción al originar por AMI. |
| `503` | `{"error": "No se pudo conectar a Asterisk AMI"}` | AMI no disponible. |

La respuesta `200` solo confirma que se envió el Originate a AMI; no confirma que el supervisor haya contestado. La vista no valida que `supervisor_extension` pertenezca al usuario que hace la petición.

## Pausa forzada: `POST /api/supervisor/{agent_pk}/force_break/`

Cambia `status` del agente a `break`. `agent_pk` es la clave primaria del agente (`id` de `GET /api/supervisor/agents/`).

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `reason` | string | No | Se devuelve en la respuesta. Por defecto `supervisor_forced`. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/supervisor/12/force_break/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Retroalimentación"}'
```

```json
{"success": true, "agent_id": "AG012", "new_status": "break", "reason": "Retroalimentación"}
```

Error `404 {"error": "Agente no encontrado"}`.

Alcance verificado en el código: solo guarda `status` y `last_status_change`. No persiste `reason`, no registra `AgentStatusHistory`, no pausa al agente en las colas de Asterisk y no emite evento por WebSocket. Para una pausa con motivo e historial use las acciones del agente (`agents/{id}/start_break/`, ver [usuarios-y-agentes.md](./usuarios-y-agentes.md)).

## Desconexión forzada: `POST /api/supervisor/{agent_pk}/force_logout/`

Llama a `Agent.logout()`: `status = offline`, `logged_in_at = null`, `current_calls = 0`. Sin cuerpo.

```json
{"success": true, "agent_id": "AG012", "new_status": "offline"}
```

Error `404 {"error": "Agente no encontrado"}`. Igual que la pausa forzada, no cuelga llamadas en curso ni saca al agente de las colas de Asterisk.

## Auditoría de gestiones: `/api/audits/`

`AuditViewSet` sobre `CallDispositionAudit`: una auditoría por llamada (relación uno a uno) para revisar la calificación que puso el agente. CRUD completo del router más acciones.

| Método y ruta | Descripción |
|---|---|
| `GET /api/audits/` | Listado paginado. |
| `POST /api/audits/` | Crear. |
| `GET /api/audits/{id}/` | Detalle. |
| `PUT`/`PATCH /api/audits/{id}/` | Editar. |
| `DELETE /api/audits/{id}/` | Borrar (`204`). |
| `POST /api/audits/{id}/approve/` | Aprobar. |
| `POST /api/audits/{id}/reject/` | Rechazar (nota obligatoria). |
| `POST /api/audits/{id}/correct/` | Corregir la calificación. |
| `GET /api/audits/summary/` | Resumen por estado. |

Filtros: `status` (`pending`, `approved`, `rejected`, `corrected`), `agent`, `campaign`. `search` sobre `call__call_id`, `agent__agent_id`, `agent__user__username`. `ordering` por `created_at`, `audited_at`, `quality_score`; por defecto `-created_at`.

### Campos

| Campo | Notas |
|---|---|
| `id` | |
| `call`, `call_id` | ID de la llamada (único) y su `call_id`. |
| `agent`, `agent_name` | |
| `campaign` | |
| `original_disposition`, `original_disposition_name` | Calificación del agente. |
| `agent_notes` | |
| `status` | `pending`, `approved`, `rejected`, `corrected`. |
| `audited_by`, `audited_by_name` | Solo lectura (se fija en las acciones). |
| `corrected_disposition`, `corrected_disposition_name` | |
| `supervisor_notes` | |
| `quality_score` | Decimal con un decimal (el modelo lo describe como 1 a 10; no hay validación de rango). |
| `created_at`, `audited_at` | Solo lectura. |

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/audits/?status=pending&agent=12" \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 88,
      "call": 5530,
      "call_id": "ast-1741617900.45",
      "agent": 12,
      "agent_name": "Laura Gómez",
      "campaign": 4,
      "original_disposition": 31,
      "original_disposition_name": "Venta",
      "agent_notes": "Cliente acepta plan básico",
      "status": "pending",
      "audited_by": null,
      "audited_by_name": null,
      "corrected_disposition": null,
      "corrected_disposition_name": null,
      "supervisor_notes": "",
      "quality_score": null,
      "created_at": "2025-03-10 14:29:00",
      "audited_at": null
    }
  ]
}
```

### Acciones

Todas fijan `audited_by` con el usuario del token y `audited_at` con la hora actual.

`POST /api/audits/{id}/approve/`, cuerpo opcional `{"notes": "..."}`:

```json
{"success": true, "status": "approved"}
```

`POST /api/audits/{id}/reject/`, `notes` obligatorio:

```json
{"success": true, "status": "rejected"}
```

Error `400 {"error": "Se requiere una nota de rechazo"}`.

`POST /api/audits/{id}/correct/`:

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/audits/88/correct/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"corrected_disposition_id": 33, "notes": "Era solo interesado", "quality_score": 7.5}'
```

```json
{"success": true, "status": "corrected"}
```

Errores: `400 {"error": "corrected_disposition_id requerido"}`, `404 {"error": "Calificación no encontrada"}`. La vista no comprueba que la nueva calificación sea de la misma campaña, y `quality_score` se guarda tal cual (si no se envía, queda `null`).

Las tres acciones sobrescriben `supervisor_notes` con `notes` (vacío si no se envía).

### Resumen: `GET /api/audits/summary/`

Sobre todas las auditorías (no aplica los filtros de la URL).

```json
{
  "total": 240,
  "by_status": {"pending": 35, "approved": 180, "rejected": 10, "corrected": 15},
  "avg_quality_score": 8.12,
  "pending": 35
}
```

`avg_quality_score` es `null` si no hay puntajes.
