# Reportes, KPIs y analítica

Endpoints de reportes guardados (generación asíncrona con Celery), exportación inmediata a CSV o Excel, KPIs en tiempo real y analítica por período.

Código fuente:

- `backend/apps/reports/views.py`: `ReportViewSet` registrado en `/api/reports/` (`backend/apps/api/urls.py`).
- `backend/apps/reports/analytics.py`: cálculos de la analítica (`analytics/...`).
- `backend/apps/reports/exporters.py`: datasets tabulares (`DATASETS`) y render CSV/XLSX.
- `backend/apps/reports/tasks.py`: tareas `generate_report`, `run_scheduled_reports`, `generate_campaign_report`, `generate_daily_reports`.
- `backend/apps/reports/models.py`: modelo `Report`.

Convenciones comunes: [README.md](./README.md). Guía funcional de reportes: [Administración de reportes](../administracion/reportes.md). Términos (AHT, ASA, SLA, FCR): [Glosario](../general/glosario.md).

## Permisos

`ReportViewSet` usa `IsAdminSupervisorOrAnalyst` y lo ajusta en `get_permissions()`:

| Operación | Roles |
|---|---|
| Cualquier `GET`/`HEAD`/`OPTIONS` (listado, detalle, KPIs, analítica, exportación, datasets, descarga) | `admin`, `supervisor`, `analyst` |
| `POST /api/reports/` (crear) y `POST /api/reports/{id}/generate/` | `admin`, `supervisor`, `analyst` |
| `PUT`, `PATCH`, `DELETE /api/reports/{id}/` | `admin`, `supervisor` |

Los agentes reciben `403` con `{"detail": "Los reportes están disponibles para admin, supervisor y analista."}`. Un superusuario de Django pasa siempre.

## Resumen de endpoints

| Método y ruta | Qué devuelve |
|---|---|
| `GET /api/reports/` | Reportes guardados (paginado). |
| `POST /api/reports/` | Crea un reporte y lo genera (o lo deja programado). |
| `GET /api/reports/{id}/` | Detalle. |
| `PUT`/`PATCH /api/reports/{id}/` | Edita. |
| `DELETE /api/reports/{id}/` | Borra el registro. |
| `POST /api/reports/{id}/generate/` | Regenera el archivo. |
| `GET /api/reports/{id}/download/` | Archivo generado. |
| `GET /api/reports/datasets/` | Datasets exportables. |
| `GET /api/reports/export/` | Exportación inmediata CSV o XLSX. |
| `GET /api/reports/kpis/` | KPIs del período. |
| `GET /api/reports/calls-by-hour/` | Llamadas por hora (24 filas). |
| `GET /api/reports/calls-by-queue/` | Llamadas por cola. |
| `GET /api/reports/agent-performance/` | KPIs por agente. |
| `GET /api/reports/call-summary/` | Resumen diario. |
| `GET /api/reports/dashboard-stats/` | Estadísticas del día para el dashboard. |
| `GET /api/reports/agent-session/` | Sesión, tiempos por estado y línea de tiempo por agente. |
| `GET /api/reports/queue-detail/` | Detalle por cola con abandono y SLA. |
| `GET /api/reports/analytics/summary/` | KPIs del período, período anterior y tendencias. |
| `GET /api/reports/analytics/agents/` | Ranking y KPIs de agentes. |
| `GET /api/reports/analytics/breaks/` | Pausas por motivo y agente. |
| `GET /api/reports/analytics/queues/` | Nivel de servicio y abandono por cola. |
| `GET /api/reports/analytics/abandoned/` | Llamadas perdidas y devoluciones. |
| `GET /api/reports/analytics/campaigns/` | KPIs de campañas y tipificaciones. |
| `GET /api/reports/analytics/omnichannel/` | Conversaciones por canal. |
| `GET /api/reports/analytics/quality/` | Evaluaciones de calidad. |

## Filtros comunes

### Período

Todos los endpoints con período usan `_parse_date_range()`. Los cálculos usan la hora local del servidor (`America/Bogota`).

| `period` | Desde | Hasta |
|---|---|---|
| `today` (por defecto) | Hoy 00:00 | Ahora |
| `yesterday` | Ayer 00:00 | Ayer 23:59:59.999999 |
| `thisweek` | Lunes de esta semana 00:00 | Ahora |
| `lastweek` | Lunes de la semana pasada 00:00 | Domingo de la semana pasada 23:59:59.999999 |
| `last7days` | Hace 6 días 00:00 (7 días incluyendo hoy) | Ahora |
| `last30days` | Hace 29 días 00:00 | Ahora |
| `thismonth` | Día 1 del mes 00:00 | Ahora |
| `lastmonth` | Día 1 del mes anterior 00:00 | Último día del mes anterior 23:59:59.999999 |
| `custom` | `start_date` (`AAAA-MM-DD`) 00:00 | `end_date` 23:59:59; si falta `end_date`, ahora |

- Un `period` desconocido se trata como `today`.
- Con `custom`, si `start_date` falta o no tiene formato `AAAA-MM-DD`, se usa hoy (sin error).
- Las respuestas de analítica y `kpis` incluyen `period: {"start", "end"}` en ISO 8601 con desfase horario.

### Filtros de la analítica

Solo en `analytics/...` (función `_analytics_filters()`):

| Parámetro | Valor | Notas |
|---|---|---|
| `campaign` | ID numérico | Se ignora si no son solo dígitos. |
| `agent` | ID numérico de agente | Igual. |
| `queue` | ID numérico de cola | Igual. |
| `direction` | `inbound` o `outbound` | Otro valor se ignora. |
| `sla` | Segundos (1 a 600, por defecto 20) | Solo lo usa `analytics/summary`. Un valor no numérico vuelve a 20. |

No todos los reportes aplican todos los filtros; se indica en cada uno. Los endpoints `kpis`, `calls-by-hour`, `calls-by-queue`, `agent-performance`, `call-summary`, `agent-session` y `queue-detail` solo aceptan el período: ignoran `campaign`, `agent`, `queue`, `direction` y `sla`.

## Reportes guardados

### Campos (`ReportSerializer`)

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer | |
| `name` | string | Obligatorio (máx. 200). |
| `report_type` | string | Obligatorio: `campaign`, `agent`, `queue`, `calls`, `custom`. |
| `format` | string | Obligatorio: `pdf`, `excel`, `csv`, `json`. |
| `filters` | objeto | Opcional. Admite `dataset` y los filtros de exportación (`campaign`, `agent`, `queue`, `direction`, `status`, `channel_type`). Las claves que empiezan por `_` las escribe el sistema. |
| `date_from`, `date_to` | datetime | Obligatorios. Rango del reporte. |
| `is_scheduled` | boolean | Si es `true`, el reporte actúa como plantilla programada. |
| `schedule_frequency` | string | `daily`, `weekly` o `monthly` (vacío equivale a `daily`). |
| `status` | string | `pending`, `processing`, `completed`, `failed`. Solo lectura. |
| `file_path`, `file_size` | string, integer | Solo lectura. |
| `error_message` | string | Solo lectura. |
| `created_by`, `created_by_name` | integer, string | Solo lectura. |
| `created_at`, `completed_at` | datetime | Solo lectura. |

Cómo se genera (`generate_report`):

- Dataset: `filters.dataset` si viene; si no, según `report_type`: `calls` y `campaign` usan `calls`, `agent` usa `agents`, `queue` usa `queues`, `custom` usa `daily`. Valores posibles en [Datasets de exportación](#datasets-de-exportación).
- `pdf` no está soportado y se entrega como Excel.
- `json` no genera archivo: guarda un resumen en `filters._summary` y queda `completed` (la descarga responde `404`).
- Al terminar, `filters` incluye `_summary` (`total_calls`, `answered`, `missed`, `abandoned`, `answer_rate`, `avg_talk_time`, `total_talk_time`) y `_rows` (filas del archivo).
- Archivo en `MEDIA_ROOT/reports/<id>_<nombre>.<ext>`.

Programados (`run_scheduled_reports`, Celery Beat): cada reporte con `is_scheduled = true` se copia con el período anterior (día anterior, semana anterior los lunes o mes anterior el día 1), se genera y se envía por correo al creador si tiene email.

### Listar: `GET /api/reports/`

Paginado, orden `-created_at`. Filtro propio: `is_scheduled=true|false`. No define `search_fields` ni `filterset_fields`, así que `search` y los filtros por campo no tienen efecto; `ordering` sí.

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/reports/?is_scheduled=false" \
  -H "Authorization: Bearer <TOKEN>"
```

### Crear: `POST /api/reports/`

Se guarda con `status = pending` y el usuario del token como `created_by`. Si `is_scheduled` es `false`, encola `generate_report` de inmediato.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/reports/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Llamadas campaña cobranza marzo",
    "report_type": "campaign",
    "format": "excel",
    "filters": {"campaign": 4, "dataset": "calls", "direction": "outbound"},
    "date_from": "2025-03-01T00:00:00-05:00",
    "date_to": "2025-03-31T23:59:59-05:00"
  }'
```

Respuesta `201`:

```json
{
  "id": 21,
  "created_by_name": "Carlos Ruiz",
  "name": "Llamadas campaña cobranza marzo",
  "report_type": "campaign",
  "format": "excel",
  "filters": {"campaign": 4, "dataset": "calls", "direction": "outbound"},
  "date_from": "2025-03-01 00:00:00",
  "date_to": "2025-03-31 23:59:59",
  "file_path": "",
  "file_size": 0,
  "status": "pending",
  "error_message": "",
  "is_scheduled": false,
  "schedule_frequency": "",
  "created_by": 1,
  "created_at": "2025-03-10 16:00:02",
  "completed_at": null
}
```

Consulte `GET /api/reports/{id}/` hasta que `status` sea `completed` o `failed`.

### Regenerar: `POST /api/reports/{id}/generate/`

Encola `generate_report` con el mismo rango y filtros.

```json
{"status": "generating report"}
```

### Descargar: `GET /api/reports/{id}/download/`

Devuelve el archivo como adjunto (nombre en disco). Si `status` no es `completed` o el archivo no existe:

```json
{"error": "El reporte no tiene archivo disponible"}
```

con código `404`.

```bash
curl -s -OJ "https://<IP_DEL_SERVIDOR>/api/reports/21/download/" \
  -H "Authorization: Bearer <TOKEN>"
```

### Editar y borrar

`PUT`/`PATCH /api/reports/{id}/` y `DELETE /api/reports/{id}/` (solo `admin` y `supervisor`). Editar no regenera el archivo. Borrar elimina el registro pero no el archivo en disco.

## Exportación inmediata

### Datasets: `GET /api/reports/datasets/`

```json
[
  {"value": "calls", "label": "Detalle de llamadas"},
  {"value": "agents", "label": "Rendimiento de agentes"},
  {"value": "daily", "label": "Resumen diario"},
  {"value": "queues", "label": "Resumen por cola"},
  {"value": "chats", "label": "Conversaciones (WhatsApp, email, chat web, redes)"},
  {"value": "hourly", "label": "Llamadas por hora (nivel de servicio / ASA)"},
  {"value": "agent_kpis", "label": "KPIs y ranking de agentes (AHT, ocupación, calidad)"},
  {"value": "breaks", "label": "Pausas por agente y motivo"},
  {"value": "queue_sla", "label": "Nivel de servicio y abandono por cola"},
  {"value": "abandoned", "label": "Llamadas perdidas y devoluciones"},
  {"value": "campaign_kpis", "label": "KPIs de campañas (contactabilidad, conversión)"},
  {"value": "dispositions", "label": "Tipificaciones"},
  {"value": "omnichannel", "label": "Omnicanal por canal (primera respuesta, resolución)"},
  {"value": "quality", "label": "Calidad por agente"}
]
```

### Datasets de exportación

| `dataset` | Contenido | Columnas principales |
|---|---|---|
| `calls` | Una fila por llamada, orden por inicio. | ID llamada, Inicio, Contestada, Fin, Dirección, Estado, Origen, Destino, Agente, Extensión, Campaña, Cola, Espera (s), Conversación (s), Retención (s), Calificación, Transferida, Grabada, Notas. |
| `agents` | Una fila por agente con llamadas. | Agente, ID agente, Extensión, Total llamadas, Contestadas, Perdidas, Abandonadas, Transferidas, % respuesta, Conversación total (s), TMO (s), Espera prom. (s), Retención prom. (s). |
| `daily` | Una fila por día. | Fecha, Total, Entrantes, Salientes, Contestadas, Perdidas, Abandonadas, Buzón, % respuesta, Conversación total (s), TMO (s). |
| `queues` | Una fila por cola (excluye llamadas sin cola). | Cola, Total, Contestadas, Abandonadas, Perdidas, % respuesta, % abandono, Espera prom. (s), Espera máx. (s), TMO (s). |
| `chats` | Una fila por conversación (excluye difusiones sin respuesta del cliente). | ID, Canal, Contacto, Identificador, Agente, Campaña, Estado, Inicio, Asignada, Primera respuesta (s), Cierre, Duración (s), Tipificación, Etiquetas, Mensajes entrantes, Mensajes salientes, Notas de cierre. |
| `hourly` | 24 filas (de `analytics/summary`, SLA 20 s). | Hora, Total, Contestadas, Abandonadas, Perdidas, Nivel de servicio (%), ASA (s). |
| `agent_kpis` | Ranking de `analytics/agents`. | Ranking, Agente, Extensión, Puntaje, Llamadas, Atendidas, Entrantes, Salientes, Chats, AHT (s), Conversación/Retención/Post-llamada prom. (s), Conectado, Disponible, En llamada, Pausa (s), Ocupación (%), Utilización (%), Llamadas/hora, Transferencias (%), Tipificación (%), Conversión (%), Calidad, Evaluaciones. |
| `breaks` | Pausas por agente y motivo, más una fila `TOTAL` por agente. | Agente, Motivo, Pausas, Tiempo (s), Excedidas. |
| `queue_sla` | Colas de `analytics/queues`. | Cola, Ofrecidas, Atendidas, Abandonadas, Abandono corto (<5 s), % atención, % abandono, Nivel de servicio (%), Umbral SL (s), ASA (s), Espera máx. (s), Espera prom. abandono (s), AHT (s). |
| `abandoned` | Perdidas de `analytics/abandoned` (hasta 2000 revisadas). | Fecha, Número, Cola, Estado, Espera (s), Intentos del número, Devuelta, Devuelta en (s), Devuelta por. |
| `campaign_kpis` | Campañas de `analytics/campaigns`. | Campaña, Tipo, Estado, Llamadas, Contactadas, Contactabilidad (%), Contestador, No contesta/ocupado, Tipificadas (%), Éxitos, Conversión (%), Rellamadas, Conversación prom. (s), Agentes, Chats, Contactos base, Contactos trabajados, Penetración (%), Pendientes, Intentos prom. |
| `dispositions` | Tipificaciones de llamadas y chats. | Campaña, Tipificación, Exitosa, Llamadas, Chats, Total, % del total. |
| `omnichannel` | Una fila por canal. | Canal, Conversaciones, Cerradas, Abiertas, Sin asignar, % respondidas, % 1ª respuesta ≤ 5 min, 1ª respuesta prom. (s), Resolución prom. (s), Mensajes entrantes, Mensajes salientes. |
| `quality` | Una fila por agente evaluado. | Agente, Evaluaciones, Promedio, Mínimo, Máximo, Bajo 60. |

Los datasets `calls` y `chats` tienen un máximo de 100 000 filas (`MAX_ROWS`).

### Exportar: `GET /api/reports/export/`

Genera el archivo en la misma petición (no se guarda en `Report`).

| Parámetro | Valor | Por defecto |
|---|---|---|
| `dataset` | Uno de la tabla anterior. | `calls` |
| `format` | `csv` o `xlsx`. | `xlsx` |
| `period`, `start_date`, `end_date` | Ver [Período](#período). | `today` |
| `campaign`, `agent`, `queue` | ID. | |
| `direction` | `inbound`, `outbound`. | |
| `status` | Estado de llamada. Solo lo aplican `calls`, `agents`, `daily` y `queues`. | |
| `channel_type` | Tipo de canal. Solo lo aplica `chats`. | |

En esta acción `?format=` es el formato del archivo, no el renderer de DRF (la vista desactiva `URL_FORMAT_OVERRIDE` con una clase de negociación propia).

Formato de salida:

- `xlsx`: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, cabecera en negrita con panel congelado.
- `csv`: `text/csv; charset=utf-8`, con BOM UTF-8 y separador `;` (pensado para Excel con configuración regional es-CO).
- `Content-Disposition: attachment; filename="vozipomni_<dataset>_<AAAAMMDD>_<AAAAMMDD>.<ext>"`, expuesta al navegador con `Access-Control-Expose-Headers: Content-Disposition`.

```bash
curl -s -OJ "https://<IP_DEL_SERVIDOR>/api/reports/export/?dataset=queue_sla&format=csv&period=custom&start_date=2025-03-01&end_date=2025-03-10" \
  -H "Authorization: Bearer <TOKEN>"
```

Errores `400`:

```json
{"error": "Dataset inválido. Opciones: calls, agents, daily, queues, chats, hourly, agent_kpis, breaks, queue_sla, abandoned, campaign_kpis, dispositions, omnichannel, quality"}
```

```json
{"error": "Formato inválido (csv|xlsx)"}
```

## KPIs y tableros

### `GET /api/reports/kpis/`

KPIs de las llamadas con `start_time` en el período. SLA fijo de 20 s sobre el total de llamadas (no solo entrantes). Los datos de agentes son del momento actual, no del período.

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/reports/kpis/?period=today" \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{
  "totalCalls": 320,
  "answeredCalls": 268,
  "missedCalls": 30,
  "abandonedCalls": 14,
  "failedCalls": 5,
  "voicemailCalls": 3,
  "transferredCalls": 11,
  "answerRate": 83.8,
  "abandonRate": 4.4,
  "missedRate": 9.4,
  "avgTalkTime": 184.2,
  "avgWaitTime": 12.7,
  "avgHoldTime": 8.1,
  "maxWaitTime": 95,
  "avgHandleTime": 192.3,
  "totalHoldTime": 2171,
  "serviceLevel": 72.5,
  "slaThreshold": 20,
  "inboundCalls": 210,
  "outboundCalls": 110,
  "totalTalkTime": 49366,
  "activeAgents": 18,
  "availableAgents": 6,
  "oncallAgents": 9,
  "breakAgents": 2,
  "avgOccupancy": 64.3,
  "period": {"start": "2025-03-10T00:00:00-05:00", "end": "2025-03-10T16:05:12.123456-05:00"}
}
```

Reglas: contestada = `status completed`; perdidas = `no_answer` + `busy` + `cancelled`; `avgHandleTime` = conversación promedio + retención promedio.

### `GET /api/reports/calls-by-hour/`

Lista de 24 elementos (0 a 23), rellenando horas sin llamadas.

```json
[
  {"hour": 8, "total": 41, "answered": 35, "missed": 4, "inbound": 30, "outbound": 11, "label": "08:00"}
]
```

### `GET /api/reports/calls-by-queue/`

Orden por total descendente. Si hay llamadas sin cola, se agrega una fila con `queueId: null` y `queueName: "Directas (sin cola)"` (con `avgTalk: 0`).

```json
[
  {"queueId": 2, "queueName": "Soporte", "total": 150, "answered": 131, "missed": 9, "avgWait": 14.2, "avgTalk": 201.5},
  {"queueId": null, "queueName": "Directas (sin cola)", "total": 60, "answered": 48, "missed": 8, "avgWait": 0.0, "avgTalk": 0}
]
```

### `GET /api/reports/agent-performance/`

Una fila por agente (todos los agentes, también sin llamadas), orden por `totalCalls` descendente. Los campos `*Today`, `sessionTime` y `occupancy` vienen de los contadores del día del agente, no del período.

```json
[
  {
    "agentId": 12,
    "agentName": "Laura Gómez",
    "extension": "1012",
    "status": "available",
    "totalCalls": 38,
    "answeredCalls": 33,
    "missedCalls": 3,
    "transferredCalls": 2,
    "abandonedCalls": 0,
    "answerRate": 86.8,
    "avgTalkTime": 175.4,
    "avgWaitTime": 9.8,
    "avgHoldTime": 6.0,
    "totalTalkTime": 5788,
    "totalHoldTime": 198,
    "callsToday": 38,
    "talkTimeToday": 5788,
    "availableTimeToday": 9120,
    "breakTimeToday": 1800,
    "oncallTimeToday": 6100,
    "wrapupTimeToday": 900,
    "sessionTime": 25200,
    "occupancy": 47.2,
    "loggedInAt": "2025-03-10T08:00:03-05:00"
  }
]
```

### `GET /api/reports/call-summary/`

Una fila por día del período.

```json
[
  {
    "date": "2025-03-10",
    "total": 320, "answered": 268, "missed": 30, "abandoned": 14,
    "voicemail": 3, "transferred": 11, "inbound": 210, "outbound": 110,
    "avgTalkTime": 184.2, "avgHoldTime": 8.1, "totalTalkTime": 49366
  }
]
```

### `GET /api/reports/dashboard-stats/`

No recibe parámetros. "Hoy" se calcula con `timezone.now()` (UTC) truncado a medianoche, es decir desde las 19:00 del día anterior en hora de Colombia; a diferencia de `period=today` en los demás endpoints. `activeCalls` cuenta llamadas `initiated`, `ringing` o `answered`; `queuedCalls` cuenta las `ringing`.

```json
{
  "callsToday": 320,
  "answeredToday": 268,
  "missedToday": 30,
  "abandonedToday": 14,
  "voicemailToday": 3,
  "transferredToday": 11,
  "activeCalls": 7,
  "queuedCalls": 2,
  "inboundToday": 210,
  "outboundToday": 110,
  "answerRate": 83.8,
  "abandonRate": 4.4,
  "avgTalkTime": 184.2,
  "avgWaitTime": 12.7,
  "avgHoldTime": 8.1,
  "totalTalkTime": 49366,
  "activeAgents": 18,
  "availableAgents": 6,
  "busyAgents": 9,
  "breakAgents": 2,
  "wrapupAgents": 1
}
```

### `GET /api/reports/agent-session/`

Una fila por agente, orden por `sessionTime` descendente. Combina los contadores del día del agente con `AgentStatusHistory` del período. `timeline` trae hasta 20 cambios de estado.

```json
[
  {
    "agentId": 12,
    "agentName": "Laura Gómez",
    "extension": "1012",
    "currentStatus": "oncall",
    "sessionTime": 25200,
    "availableTime": 18240,
    "oncallTime": 12200,
    "breakTime": 3600,
    "wrapupTime": 1800,
    "occupancy": 55.6,
    "loggedInAt": "2025-03-10T08:00:03-05:00",
    "timeline": [
      {"status": "available", "start": "2025-03-10T08:00:03-05:00", "end": "2025-03-10T08:04:40-05:00", "duration": 277}
    ]
  }
]
```

### `GET /api/reports/queue-detail/`

Una fila por cola activa, orden por `totalCalls`. El SLA usa `service_level` de la cola (60 s si no está definido). `callsWaiting`, `agentsAvailable` y `agentsBusy` vienen de `QueueStats` (0 si no existe).

```json
[
  {
    "queueId": 2,
    "queueName": "Soporte",
    "extension": "8002",
    "strategy": "rrmemory",
    "totalCalls": 150,
    "answeredCalls": 131,
    "abandonedCalls": 7,
    "voicemailCalls": 1,
    "noAnswerCalls": 5,
    "abandonRate": 4.7,
    "slaPercentage": 80.0,
    "slaThreshold": 20,
    "avgWaitTime": 14.2,
    "maxWaitTime": 95,
    "avgTalkTime": 201.5,
    "avgHoldTime": 7.3,
    "totalTalkTime": 26396,
    "callsWaiting": 1,
    "agentsAvailable": 3,
    "agentsBusy": 4
  }
]
```

## Analítica por período

Todas las respuestas agregan `period: {"start", "end"}`. Cuando la función devuelve una lista, la respuesta es `{"rows": [...], "period": {...}}`.

Convenciones de cálculo (`analytics.py`):

| Concepto | Fórmula |
|---|---|
| Ofrecidas | Llamadas entrantes. |
| Contestada | `status = completed`. |
| Perdidas | `no_answer`, `busy`, `cancelled`. |
| Abandono corto | Abandonada con espera menor a 5 s; no penaliza el nivel de servicio. |
| Nivel de servicio | Entrantes contestadas con espera menor o igual al umbral / (entrantes - abandonos cortos). |
| ASA | Espera promedio de las entrantes contestadas. |
| AHT | (conversación + retención + post-llamada) / contestadas. |
| Abandono (%) | Abandonadas / entrantes. |
| Ocupación | (en llamada + post-llamada) / (conectado - pausas). |
| Utilización | (en llamada + post-llamada) / conectado. |
| FCR estimado | 100 - % de números que llamaron más de una vez en el período. |
| Contactabilidad | Salientes contestadas / salientes. |
| Conversión | Llamadas con tipificación exitosa / contestadas. |
| Llamada corta | Contestada con conversación menor a 10 s. |

Los tiempos de agente (conectado, pausa, post-llamada) salen de `AgentStatusHistory`; los estados abiertos se cuentan hasta ahora o hasta el fin del período.

### `GET /api/reports/analytics/summary/`

Filtros: período, `campaign`, `agent`, `queue`, `direction`, `sla`.

Estructura:

| Clave | Contenido |
|---|---|
| `current` | Bloque de KPIs del período. |
| `previous` | Mismo bloque para el período anterior de igual duración (termina 1 s antes de `start`). |
| `previousPeriod` | `{"start", "end"}` del período anterior. |
| `daily` | Por día: `date`, `total`, `inbound`, `outbound`, `answered`, `abandoned`, `missed`, `answerRate`, `abandonRate`, `serviceLevel`, `aht` (sin post-llamada), `asa`. |
| `hourly` | 24 filas: `hour`, `label`, `total`, `answered`, `abandoned`, `missed`, `serviceLevel` (sin descontar abandonos cortos), `asa`. |
| `heatmap` | `days` (`Lun` a `Dom`), `matrix` (7 x 24 con llamadas por día de la semana y hora), `max`. |
| `byStatus` | `status`, `label`, `count` por estado de llamada. |
| `talkDistribution` | `label`, `count` en tramos de conversación: `< 30 s`, `30 s – 1 min`, `1 – 3 min`, `3 – 5 min`, `5 – 10 min`, `> 10 min`. |
| `period` | Período consultado. |

Campos de `current` y `previous` (función `kpi_block`):

| Campo | Significado |
|---|---|
| `totalCalls` | Llamadas del período. |
| `inboundCalls`, `outboundCalls` | Por dirección. |
| `answeredCalls` | Contestadas. |
| `inboundAnswered`, `outboundAnswered` | Contestadas por dirección. |
| `abandonedCalls` | Abandonadas. |
| `shortAbandoned` | Abandonadas con espera menor a 5 s. |
| `missedCalls` | `no_answer` + `busy` + `cancelled`. |
| `failedCalls` | Fallidas. |
| `voicemailCalls` | Buzón. |
| `machineCalls` | Contestador automático. |
| `transferredCalls` | Transferidas. |
| `shortCalls` | Contestadas con menos de 10 s de conversación. |
| `answerRate` | % contestadas sobre el total. |
| `inboundAnswerRate` | % entrantes contestadas. |
| `abandonRate` | % abandonadas sobre entrantes. |
| `serviceLevel` | Nivel de servicio (%). |
| `slaThreshold` | Umbral usado (s). |
| `contactRate` | Contactabilidad saliente (%). |
| `transferRate` | % transferidas sobre contestadas. |
| `shortCallRate` | % llamadas cortas sobre contestadas. |
| `asa` | Velocidad promedio de respuesta (s). |
| `maxWaitTime` | Espera máxima de entrantes (s). |
| `avgAbandonWait` | Espera promedio antes de abandonar (s). |
| `avgTalkTime`, `avgHoldTime` | Promedios de conversación y retención (s). |
| `avgWrapupTime` | Post-llamada / contestadas (s). |
| `aht` | Tiempo medio de operación (s). |
| `totalTalkTime` | Conversación total (s). |
| `totalHandleTime` | Conversación + retención + post-llamada (s). |
| `uniqueCallers` | Números entrantes distintos. |
| `repeatCallers` | Números que llamaron más de una vez. |
| `repeatRate` | % de números repetidos. |
| `fcr` | Resolución en primer contacto estimada (%). |
| `typedCalls`, `typingRate` | Llamadas tipificadas y % sobre contestadas. |
| `successCalls`, `conversionRate` | Tipificaciones exitosas y % sobre contestadas. |
| `recordedCalls` | Llamadas grabadas. |
| `loggedTime`, `breakTime`, `wrapupTime` | Tiempos de agentes en el período (s). |
| `occupancy`, `utilization` | Ocupación y utilización (%). |
| `agentsWorked` | Agentes con tiempo conectado en el período. |
| `callsPerAgentHour` | Contestadas por hora de agente conectado (0 si hay menos de 60 s conectados). |

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/reports/analytics/summary/?period=last7days&direction=inbound&sla=30" \
  -H "Authorization: Bearer <TOKEN>"
```

Ejemplo (recortado; `previous` tiene los mismos campos que `current`):

```json
{
  "current": {
    "totalCalls": 1840, "inboundCalls": 1840, "outboundCalls": 0,
    "answeredCalls": 1630, "inboundAnswered": 1630, "outboundAnswered": 0,
    "abandonedCalls": 96, "shortAbandoned": 21, "missedCalls": 88,
    "failedCalls": 12, "voicemailCalls": 14, "machineCalls": 0,
    "transferredCalls": 57, "shortCalls": 33,
    "answerRate": 88.6, "inboundAnswerRate": 88.6, "abandonRate": 5.2,
    "serviceLevel": 81.4, "slaThreshold": 30, "contactRate": 0,
    "transferRate": 3.5, "shortCallRate": 2.0,
    "asa": 11.8, "maxWaitTime": 240, "avgAbandonWait": 38.5,
    "avgTalkTime": 190.2, "avgHoldTime": 7.9, "avgWrapupTime": 22.4, "aht": 220.5,
    "totalTalkTime": 310026, "totalHandleTime": 359415,
    "uniqueCallers": 1422, "repeatCallers": 198, "repeatRate": 13.9, "fcr": 86.1,
    "typedCalls": 1580, "typingRate": 96.9, "successCalls": 410, "conversionRate": 25.2,
    "recordedCalls": 1630,
    "loggedTime": 604800, "breakTime": 54000, "wrapupTime": 36512,
    "occupancy": 65.3, "utilization": 59.4, "agentsWorked": 21, "callsPerAgentHour": 9.7
  },
  "previous": {"totalCalls": 1712, "answerRate": 86.1, "serviceLevel": 78.0, "aht": 231.0},
  "previousPeriod": {"start": "2025-02-26T07:54:49-05:00", "end": "2025-03-03T23:59:59-05:00"},
  "daily": [
    {"date": "2025-03-10", "total": 280, "inbound": 280, "outbound": 0, "answered": 250, "abandoned": 14, "missed": 12,
     "answerRate": 89.3, "abandonRate": 5.0, "serviceLevel": 82.1, "aht": 196.0, "asa": 11.2}
  ],
  "hourly": [
    {"hour": 8, "label": "08:00", "total": 190, "answered": 172, "abandoned": 9, "missed": 7, "serviceLevel": 80.5, "asa": 12.0}
  ],
  "heatmap": {"days": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"], "matrix": [[0, 0, 0, 0, 0, 0, 0, 1, 40]], "max": 64},
  "byStatus": [{"status": "completed", "label": "Contestada", "count": 1630}],
  "talkDistribution": [{"label": "< 30 s", "count": 80}, {"label": "30 s – 1 min", "count": 140}],
  "period": {"start": "2025-03-04T00:00:00-05:00", "end": "2025-03-10T16:05:10-05:00"}
}
```

`heatmap.matrix` se muestra recortado; en la respuesta real tiene 7 filas de 24 valores.

### `GET /api/reports/analytics/agents/`

Filtros: período, `campaign`, `agent`, `queue`, `direction` (sobre llamadas; los tiempos de estado y chats no se filtran por campaña ni cola). Incluye agentes con llamadas, con tiempo conectado o con conversaciones en el período.

Cada fila de `rows`: `agentId`, `agentName`, `extension`, `status`, `totalCalls`, `inboundCalls`, `outboundCalls`, `answeredCalls`, `missedCalls`, `transferredCalls`, `shortCalls`, `chats`, `avgTalkTime`, `maxTalkTime`, `avgHoldTime`, `avgWrapupTime`, `aht`, `totalTalkTime`, `loggedTime`, `availableTime`, `oncallTime`, `wrapupTime`, `breakTime`, `occupancy`, `utilization`, `callsPerHour`, `transferRate`, `typingRate`, `successCalls`, `conversionRate`, `qualityScore`, `evaluations`, `score`, `rank`.

`score` (0 a 100) pondera llamadas por hora relativas al mejor agente (35 %), ocupación (25 %), calidad (30 %, solo si tiene evaluaciones) y 100 - % de transferencias (10 %). `rank` ordena por `score` y luego por contestadas.

```json
{
  "rows": [
    {"agentId": 12, "agentName": "Laura Gómez", "extension": "1012", "status": "available",
     "totalCalls": 210, "answeredCalls": 190, "chats": 14, "aht": 205.1, "occupancy": 71.2,
     "utilization": 64.0, "callsPerHour": 10.4, "transferRate": 2.1, "qualityScore": 92.3,
     "evaluations": 6, "score": 88.7, "rank": 1}
  ],
  "period": {"start": "2025-03-04T00:00:00-05:00", "end": "2025-03-10T16:05:10-05:00"}
}
```

La fila se muestra recortada; incluye todos los campos listados.

### `GET /api/reports/analytics/breaks/`

Filtros: período y `agent`. Los límites salen de `max_duration` (minutos) de los motivos de pausa (`AgentBreakReason`), comparando por nombre o código sin distinguir mayúsculas.

```json
{
  "totalBreaks": 64,
  "totalTime": 54000,
  "exceededCount": 5,
  "byReason": [
    {"reason": "Almuerzo", "count": 20, "total": 36000, "max": 3900, "exceeded": 3, "avg": 1800, "limit": 3600, "share": 66.7}
  ],
  "byAgent": [
    {"agentId": 12, "agentName": "Laura Gómez", "count": 6, "total": 5400, "exceeded": 1,
     "reasons": {"Almuerzo": {"count": 2, "total": 3900, "exceeded": 1}}}
  ],
  "exceeded": [
    {"agentName": "Laura Gómez", "reason": "Almuerzo", "duration": 3900, "limit": 3600, "excess": 300,
     "start": "2025-03-10T12:01:00-05:00"}
  ],
  "period": {"start": "2025-03-10T00:00:00-05:00", "end": "2025-03-10T16:05:10-05:00"}
}
```

`exceeded` trae hasta 100 elementos, del mayor exceso al menor. Una pausa sin motivo se agrupa como `Sin motivo`.

### `GET /api/reports/analytics/queues/`

Filtros: período, `campaign`, `agent`, `queue`. Solo llamadas entrantes. El umbral de nivel de servicio es `service_level` de cada cola (20 s si no está definido).

```json
{
  "queues": [
    {"queueId": 2, "queueName": "Soporte", "offered": 900, "answered": 812, "abandoned": 50, "shortAbandoned": 12,
     "voicemail": 5, "missed": 33, "transferred": 20, "answerRate": 90.2, "abandonRate": 5.6,
     "serviceLevel": 83.1, "slaThreshold": 20, "asa": 10.9, "maxWait": 240, "avgAbandonWait": 41.2, "aht": 208.4}
  ],
  "waitDistribution": [
    {"label": "0–10 s", "answered": 520, "abandoned": 10},
    {"label": "> 120 s", "answered": 8, "abandoned": 6}
  ],
  "period": {"start": "2025-03-04T00:00:00-05:00", "end": "2025-03-10T16:05:10-05:00"}
}
```

`waitDistribution` tiene seis tramos: `0–10 s`, `10–20 s`, `20–30 s`, `30–60 s`, `60–120 s`, `> 120 s`. Las entrantes sin cola aparecen con `queueId: null` y `queueName: "Directas (sin cola)"`.

### `GET /api/reports/analytics/abandoned/`

Filtros: período, `campaign`, `agent`, `queue`, `direction`. Llamadas entrantes `abandoned`, `no_answer`, `voicemail` o `cancelled` con número conocido. Se considera devuelta si hay una llamada posterior saliente al número o entrante contestada del mismo número (comparando los últimos 10 dígitos). Se revisan hasta 2000 llamadas y se devuelven hasta 300 filas.

```json
{
  "total": 180,
  "uniqueNumbers": 142,
  "returned": 120,
  "pending": 60,
  "returnRate": 66.7,
  "avgReturnDelay": 1260,
  "rows": [
    {"callId": "ast-1741620062.51", "start": "2025-03-10T15:01:02-05:00", "caller": "3109876543",
     "queue": "Soporte", "status": "abandoned", "statusLabel": "Abandonada", "waitTime": 45, "attempts": 2,
     "returned": true, "returnedAt": "2025-03-10T15:20:10-05:00", "returnDelay": 1148, "returnedBy": "Laura"}
  ],
  "period": {"start": "2025-03-10T00:00:00-05:00", "end": "2025-03-10T16:05:10-05:00"}
}
```

`returnedBy` es el nombre (first_name) del agente de la llamada de devolución.

### `GET /api/reports/analytics/campaigns/`

Filtros: período, `campaign`, `agent`, `direction` (`queue` no se aplica a campañas). Sin `campaign`, incluye campañas con actividad en el período y todas las activas.

```json
{
  "rows": [
    {"campaignId": 4, "campaignName": "Cobranza marzo", "type": "outbound", "dialer": "predictive", "status": "active",
     "calls": 5200, "answered": 1900, "machine": 700, "noAnswer": 2400, "abandoned": 60, "contactRate": 36.5,
     "typed": 1850, "typingRate": 97.4, "success": 420, "conversionRate": 21.6, "callbacks": 130,
     "avgTalkTime": 142.0, "totalTalkTime": 269800, "agents": 14, "chats": 35,
     "contactsTotal": 12000, "contactsTouched": 8100, "contactsPending": 3900, "contactsSuccess": 400,
     "penetration": 67.5, "avgAttempts": 1.8}
  ],
  "dispositions": {
    "total": 1885,
    "success": 425,
    "untypedCalls": 50,
    "typingRate": 97.4,
    "rows": [
      {"campaign": "Cobranza marzo", "name": "Promesa de pago", "isSuccess": true, "calls": 400, "chats": 20, "total": 420, "share": 22.3}
    ]
  },
  "period": {"start": "2025-03-01T00:00:00-05:00", "end": "2025-03-10T16:05:10-05:00"}
}
```

`success` de cada campaña suma llamadas y chats exitosos; `conversionRate` usa solo llamadas.

### `GET /api/reports/analytics/omnichannel/`

Filtros: período, `campaign`, `agent`. Conversaciones con `started_at` en el período, excluyendo difusiones sin respuesta del cliente. Objetivo de primera respuesta: 300 s (`frtTarget`).

```json
{
  "totals": {
    "total": 420, "closed": 380, "open": 40, "unassigned": 6, "responded": 410,
    "responseRate": 97.6, "frtWithinTarget": 88.3, "avgFirstResponse": 95.4, "avgResolution": 1820.0,
    "resolutionRate": 90.5, "typingRate": 94.2, "success": 60,
    "inboundMessages": 3100, "outboundMessages": 2950
  },
  "frtTarget": 300,
  "byChannel": [
    {"total": 300, "closed": 270, "open": 30, "unassigned": 4, "responded": 295, "responseRate": 98.3,
     "frtWithinTarget": 90.0, "avgFirstResponse": 80.2, "avgResolution": 1500.0, "resolutionRate": 90.0,
     "typingRate": 95.0, "success": 45, "inboundMessages": 2400, "outboundMessages": 2300,
     "channel": "whatsapp", "label": "WhatsApp"}
  ],
  "byAgent": [
    {"agentId": 12, "agentName": "Laura Gómez", "total": 40, "closed": 38, "avgFirstResponse": 60.0, "avgResolution": 1200.0}
  ],
  "hourly": [{"hour": 9, "label": "09:00", "total": 52}],
  "period": {"start": "2025-03-10T00:00:00-05:00", "end": "2025-03-10T16:05:10-05:00"}
}
```

`hourly` trae 24 elementos; `byAgent`, hasta 50. `typingRate` se calcula sobre conversaciones cerradas.

### `GET /api/reports/analytics/quality/`

Filtros: período (sobre `created_at` de la evaluación), `agent`, `campaign`. `coverage` = evaluaciones / llamadas grabadas del período.

```json
{
  "evaluations": 42,
  "avgScore": 83.6,
  "minScore": 52.0,
  "maxScore": 100.0,
  "recordedCalls": 1630,
  "coverage": 2.6,
  "feedbackRate": 40.5,
  "distribution": [
    {"label": "< 60", "count": 3},
    {"label": "60–79", "count": 9},
    {"label": "80–89", "count": 17},
    {"label": "≥ 90", "count": 13}
  ],
  "byAgent": [
    {"agentId": 12, "agentName": "Laura Gómez", "evaluations": 6, "avgScore": 92.3, "minScore": 85.0, "maxScore": 100.0, "belowTarget": 0}
  ],
  "byEvaluator": [
    {"evaluator": "Carlos", "evaluations": 30, "avgScore": 82.1}
  ],
  "period": {"start": "2025-03-04T00:00:00-05:00", "end": "2025-03-10T16:05:10-05:00"}
}
```

Más detalle de evaluaciones: [grabaciones-y-calidad.md](./grabaciones-y-calidad.md).

## Errores

| Código | Cuándo |
|---|---|
| `400` | `export` con `dataset` o `format` inválidos; validación al crear o editar un reporte. |
| `403` | Rol `agent`, o `analyst` intentando `PUT`, `PATCH` o `DELETE`. |
| `404` | Reporte inexistente o sin archivo disponible en `download`. |
