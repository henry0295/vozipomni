# Grabaciones y calidad

Endpoints para consultar, reproducir, descargar y borrar grabaciones de llamadas, y para la gestión de calidad: plantillas de evaluación, evaluaciones de grabaciones y estadísticas.

Código fuente:

- `backend/apps/api/viewsets.py`: `RecordingViewSet` en `/api/recordings/`.
- `backend/apps/api/admin_viewsets.py`: `EvaluationTemplateViewSet` en `/api/evaluation-templates/` y `RecordingEvaluationViewSet` en `/api/evaluations/`.
- `backend/apps/api/cc_viewsets.py`: `QualityStatsView` en `/api/cc/quality-stats/`.
- `backend/apps/recordings/models.py`: modelos `Recording`, `RecordingNote`, `EvaluationTemplate`, `RecordingEvaluation`.
- `backend/apps/recordings/tasks.py`: tareas Celery que vinculan los archivos a las llamadas.

Convenciones comunes (paginación, errores, roles): [README.md](./README.md). Llamadas: [telefonia.md](./telefonia.md). Términos: [Glosario](../general/glosario.md).

No hay endpoints REST para las notas de grabación (`RecordingNote`); solo se gestionan desde el admin de Django. La transcripción (`transcribe_recording`, Whisper local) es una tarea Celery y tampoco tiene endpoint para lanzarla.

## Resumen

| Recurso | Ruta | Lectura | Escritura |
|---|---|---|---|
| Grabaciones | `/api/recordings/` | `admin`, `supervisor`, `analyst` | Solo `DELETE`: `admin`, `supervisor` |
| Plantillas de evaluación | `/api/evaluation-templates/` | `admin`, `supervisor`, `analyst` | `admin`, `supervisor` |
| Evaluaciones | `/api/evaluations/` | `admin`, `supervisor`, `analyst` | `admin`, `supervisor` |
| Estadísticas de calidad | `/api/cc/quality-stats/` | `admin`, `supervisor` | No aplica |

Los agentes (`role = agent`) no tienen acceso a ninguno de estos endpoints (`403`).

## Grabaciones: `/api/recordings/`

`RecordingViewSet` con permiso `IsAdminSupervisorOrAnalyst`. Solo admite `GET`, `HEAD`, `OPTIONS` y `DELETE` (`http_method_names`); `POST`, `PUT` y `PATCH` responden `405`. Las grabaciones las crean las tareas Celery (`recordings.link_recording_to_call` y `recordings.scan_unlinked_recordings`) a partir de los archivos de MixMonitor, no la API.

### Endpoints

| Acción | Método y ruta | Permiso |
|---|---|---|
| list | `GET /api/recordings/` | `admin`, `supervisor`, `analyst` |
| retrieve | `GET /api/recordings/{id}/` | `admin`, `supervisor`, `analyst` |
| download | `GET /api/recordings/{id}/download/` | `admin`, `supervisor`, `analyst` |
| destroy | `DELETE /api/recordings/{id}/` | `admin`, `supervisor` |

### Filtros del listado

El ViewSet redefine `filter_backends` con `DjangoFilterBackend` y `SearchFilter`; no hay `OrderingFilter`, así que `?ordering=` se ignora. El orden es el del modelo: `-created_at`. Paginación estándar de 50.

| Parámetro | Tipo | Efecto |
|---|---|---|
| `status` | string | `recording`, `completed`, `failed`, `archived`. |
| `agent` | integer | ID del agente. |
| `campaign` | integer | ID de la campaña. |
| `date_from` | fecha `AAAA-MM-DD` | `created_at` (fecha) mayor o igual. |
| `date_to` | fecha `AAAA-MM-DD` | `created_at` (fecha) menor o igual. |
| `search` | string | `icontains` sobre `filename` y `call__call_id`. |

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/recordings/?status=completed&date_from=2025-03-01&date_to=2025-03-10&search=ast-" \
  -H "Authorization: Bearer <TOKEN>"
```

### Campos (`RecordingSerializer`)

Serializa todos los campos del modelo (`fields = '__all__'`) más dos calculados.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer | |
| `call` | integer | ID de la llamada (relación uno a uno). |
| `call_details` | objeto | Llamada completa con `CallSerializer` (ver [telefonia.md](./telefonia.md)). Solo lectura. |
| `filename` | string | Nombre del archivo. |
| `file_path` | string | Ruta en el servidor. |
| `file_size` | integer | Bytes. Solo lectura. |
| `file_size_mb` | number | MB con dos decimales. Solo lectura. |
| `format` | string | Por defecto `wav`. |
| `duration` | integer | Segundos. Solo lectura. |
| `codec` | string | |
| `status` | string | `recording`, `completed`, `failed`, `archived`. |
| `agent`, `campaign` | integer o null | |
| `transcription`, `transcription_status` | string | Se llenan con la tarea de transcripción. |
| `is_public` | boolean | |
| `access_count` | integer | Reproducciones o descargas. Solo lectura. |
| `created_at`, `updated_at` | datetime | Solo lectura. |
| `archived_at` | datetime o null | |

Ejemplo de elemento del listado:

```json
{
  "id": 812,
  "file_size_mb": 1.42,
  "call_details": {
    "id": 5530,
    "call_id": "ast-1741617900.45",
    "direction": "inbound",
    "status": "completed",
    "caller_id": "3001234567",
    "called_number": "6015550000",
    "agent_name": "Laura Gómez",
    "campaign_name": "Servicio al cliente",
    "duration": 186,
    "duration_formatted": "00:03:06"
  },
  "filename": "20250310-142500_1741617900.45_3001234567_6015550000.wav",
  "file_path": "/var/spool/asterisk/monitor/20250310-142500_1741617900.45_3001234567_6015550000.wav",
  "file_size": 1489920,
  "format": "wav",
  "duration": 186,
  "codec": "",
  "status": "completed",
  "transcription": "",
  "transcription_status": "",
  "is_public": false,
  "access_count": 3,
  "created_at": "2025-03-10 14:28:10",
  "updated_at": "2025-03-10 14:28:10",
  "archived_at": null,
  "call": 5530,
  "agent": 12,
  "campaign": 4
}
```

`call_details` se muestra recortado; en la respuesta real incluye todos los campos de la llamada.

### Descargar o reproducir: `GET /api/recordings/{id}/download/`

Devuelve el archivo de audio (`FileResponse`), no JSON. Exige el mismo token que el resto de la API, así que un `<audio src>` directo no funciona: el frontend debe pedir el archivo con la cabecera `Authorization` y reproducirlo como blob.

| Parámetro | Efecto |
|---|---|
| `inline=1` | `Content-Disposition: inline` para reproducir en el navegador. Sin el parámetro (o con otro valor) se envía como adjunto. |

Comportamiento:

- Solo sirve archivos cuya ruta real (`realpath` de `file_path`) esté dentro de `/var/spool/asterisk/monitor` o `/app/recordings` (`RECORDING_DIRS`). Evita que una ruta manipulada en la base de datos exponga otros archivos.
- `Content-Type` se deduce de la extensión (`mimetypes`); si no se reconoce, `audio/wav`.
- Nombre del archivo: `filename` de la grabación o, si está vacío, el nombre en disco.
- Incrementa `access_count` en 1.

```bash
# Descargar
curl -s -o grabacion.wav "https://<IP_DEL_SERVIDOR>/api/recordings/812/download/" \
  -H "Authorization: Bearer <TOKEN>"

# Reproducir en línea
curl -s -o - "https://<IP_DEL_SERVIDOR>/api/recordings/812/download/?inline=1" \
  -H "Authorization: Bearer <TOKEN>" | ffplay -nodisp -autoexit -
```

```javascript
const res = await fetch(`/api/recordings/${id}/download/?inline=1`, {
  headers: { Authorization: `Bearer ${token}` },
})
if (!res.ok) throw new Error((await res.json()).error)
audio.src = URL.createObjectURL(await res.blob())
```

Errores:

| Código | Cuerpo | Causa |
|---|---|---|
| `404` | `{"error": "El archivo de la grabación no está disponible"}` | `file_path` vacío, fuera de los directorios permitidos o el archivo no existe en disco. |
| `404` | `{"detail": "No encontrado."}` | La grabación no existe. |
| `403` | `{"detail": "Se requiere rol de administrador, supervisor o analista."}` | Rol `agent`. |

### Borrar: `DELETE /api/recordings/{id}/`

Borra el archivo de audio del disco (si existe; los errores del sistema de archivos se ignoran) y luego el registro. Responde `204` sin cuerpo. No es reversible. Un `analyst` recibe `403`.

```bash
curl -s -X DELETE "https://<IP_DEL_SERVIDOR>/api/recordings/812/" \
  -H "Authorization: Bearer <TOKEN>"
```

## Plantillas de evaluación: `/api/evaluation-templates/`

`EvaluationTemplateViewSet`, permiso `IsAdminSupervisorOrAnalyst` (el `analyst` solo lee). CRUD completo del router (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`).

| Acción | Método y ruta |
|---|---|
| list | `GET /api/evaluation-templates/` |
| create | `POST /api/evaluation-templates/` |
| retrieve | `GET /api/evaluation-templates/{id}/` |
| update | `PUT /api/evaluation-templates/{id}/` |
| partial_update | `PATCH /api/evaluation-templates/{id}/` |
| destroy | `DELETE /api/evaluation-templates/{id}/` |

Filtros: `is_active`, `is_default` (booleanos). `search` sobre `name`. Orden del modelo: primero la plantilla por defecto y luego por nombre.

### Campos

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer | |
| `name` | string | Obligatorio, único (máx. 200). |
| `description` | string | |
| `criteria` | lista | Obligatoria, al menos un criterio. Ver validación. |
| `is_active` | boolean | Por defecto `true`. |
| `is_default` | boolean | Solo puede haber una: al guardar una con `true`, las demás pasan a `false`. |
| `max_total_score` | integer | Suma de `max_score` de los criterios. Solo lectura. |
| `evaluations_count` | integer | Evaluaciones que usan la plantilla. Solo lectura. |
| `created_by` | integer | Usuario que la creó. Solo lectura (se toma del token). |
| `created_at`, `updated_at` | datetime | Solo lectura. |

Validación de cada elemento de `criteria`:

| Clave | Regla |
|---|---|
| `label` | Obligatoria. |
| `name` | Opcional. Si falta se genera desde `label` (minúsculas, caracteres no alfanuméricos por `_`). No puede repetirse. |
| `max_score` | Entero entre 1 y 100. Por defecto 5. |
| `description` | Opcional; se guarda recortada. |
| `weight` | Se conserva tal cual. El docstring del modelo dice que los pesos deben sumar 100, pero el código no lo valida ni lo usa en el cálculo. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/evaluation-templates/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Servicio al cliente 2025",
    "description": "Plantilla para llamadas entrantes",
    "is_default": true,
    "criteria": [
      {"label": "Saludo", "max_score": 5},
      {"label": "Validación de identidad", "max_score": 10},
      {"name": "resolution", "label": "Resolución", "max_score": 10}
    ]
  }'
```

Respuesta `201`:

```json
{
  "id": 3,
  "name": "Servicio al cliente 2025",
  "description": "Plantilla para llamadas entrantes",
  "criteria": [
    {"label": "Saludo", "max_score": 5, "name": "saludo", "description": ""},
    {"label": "Validación de identidad", "max_score": 10, "name": "validaci_n_de_identidad", "description": ""},
    {"name": "resolution", "label": "Resolución", "max_score": 10, "description": ""}
  ],
  "is_active": true,
  "is_default": true,
  "max_total_score": 25,
  "evaluations_count": 0,
  "created_by": 1,
  "created_at": "2025-03-10 15:02:11",
  "updated_at": "2025-03-10 15:02:11"
}
```

La generación automática de `name` usa `[^a-z0-9]+`, por eso las letras con tilde se convierten en `_` (por ejemplo `validaci_n_de_identidad`). Para nombres legibles, envíe `name` explícito.

Errores de validación (`400`), por ejemplo:

```json
{"criteria": ["Criterio 2: la etiqueta es obligatoria."]}
```

Otros mensajes: `Debe definir al menos un criterio.`, `Criterio N: formato inválido.`, `Criterio duplicado: <name>`, `Criterio <label>: max_score debe ser numérico.`, `Criterio <label>: max_score entre 1 y 100.`

### Borrar una plantilla

- Sin evaluaciones asociadas: se borra y responde `204`.
- Con evaluaciones: no se borra; se desactiva (`is_active = false`, `is_default = false`) para conservar el histórico y responde `200`:

```json
{"status": "deactivated", "reason": "La plantilla tiene evaluaciones asociadas"}
```

## Evaluaciones: `/api/evaluations/`

`RecordingEvaluationViewSet`, permiso `IsAdminSupervisorOrAnalyst`. CRUD completo y una acción extra. Cada grabación admite una sola evaluación (relación uno a uno).

| Acción | Método y ruta |
|---|---|
| list | `GET /api/evaluations/` |
| create | `POST /api/evaluations/` |
| retrieve | `GET /api/evaluations/{id}/` |
| update | `PUT /api/evaluations/{id}/` |
| partial_update | `PATCH /api/evaluations/{id}/` |
| destroy | `DELETE /api/evaluations/{id}/` |
| pending-recordings | `GET /api/evaluations/pending-recordings/` |

Filtros: `template` (ID), `recording__agent` (ID del agente), `feedback_sent` (booleano). `search` sobre `recording__filename`, `recording__call__call_id` y `comments`. `ordering` admitido; por defecto `-created_at`.

### Campos

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer | |
| `recording` | integer | Obligatorio. ID de la grabación; único. |
| `recording_filename`, `call_id` | string | Solo lectura. |
| `agent_id`, `agent_name` | integer, string | Agente de la grabación. Solo lectura. |
| `evaluator`, `evaluator_name` | integer, string | Usuario del token al crear. Solo lectura. |
| `template`, `template_name` | integer o null, string | Plantilla usada. |
| `scores_data` | objeto | `{"<name del criterio>": puntaje}` cuando hay plantilla. |
| `greeting`, `clarity`, `professionalism`, `resolution`, `closing` | integer | Criterios fijos (modo legacy), 0 a 5. |
| `total_score` | number | Calculado al guardar, normalizado de 0 a 100. Solo lectura. |
| `comments` | string | |
| `feedback_sent` | boolean | |
| `created_at`, `updated_at` | datetime | Solo lectura. |

### Modos de evaluación

Con plantilla (`template` informado):

- `scores_data` debe traer todos los criterios de la plantilla, cada uno numérico entre 0 y su `max_score`.
- Las claves que no son criterios de la plantilla se descartan.
- `total_score = suma de puntajes / max_total_score * 100` (dos decimales).
- Si la plantilla tiene criterios llamados `greeting`, `clarity`, `professionalism`, `resolution` o `closing`, esos valores se copian también a los campos legacy.

Sin plantilla (legacy):

- Se usan los cinco campos fijos, cada uno entero entre 0 y 5 (por defecto 0).
- `total_score = suma de los cinco / 25 * 100`.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/evaluations/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "recording": 812,
    "template": 3,
    "scores_data": {"saludo": 5, "validaci_n_de_identidad": 8, "resolution": 9},
    "comments": "Buen manejo, faltó confirmar el correo."
  }'
```

Respuesta `201`:

```json
{
  "id": 57,
  "recording": 812,
  "recording_filename": "20250310-142500_1741617900.45_3001234567_6015550000.wav",
  "call_id": "ast-1741617900.45",
  "agent_id": 12,
  "agent_name": "Laura Gómez",
  "evaluator": 1,
  "evaluator_name": "Carlos Ruiz",
  "template": 3,
  "template_name": "Servicio al cliente 2025",
  "scores_data": {"saludo": 5.0, "validaci_n_de_identidad": 8.0, "resolution": 9.0},
  "greeting": 0,
  "clarity": 0,
  "professionalism": 0,
  "resolution": 9,
  "closing": 0,
  "total_score": 88.0,
  "comments": "Buen manejo, faltó confirmar el correo.",
  "feedback_sent": false,
  "created_at": "2025-03-10 15:10:44",
  "updated_at": "2025-03-10 15:10:44"
}
```

Errores (`400`):

| Cuerpo | Causa |
|---|---|
| `{"scores_data": "Falta el criterio \"Resolución\"."}` | Falta un criterio de la plantilla. |
| `{"scores_data": "Valor inválido en \"resolution\"."}` | Valor no numérico. |
| `{"scores_data": "\"Resolución\" debe estar entre 0 y 10."}` | Fuera de rango. |
| `{"greeting": "Debe estar entre 0 y 5."}` | Modo legacy fuera de rango. |
| `{"recording": ["..."]}` | La grabación ya tiene evaluación (restricción de unicidad) o no existe. |

### Grabaciones pendientes de evaluar: `GET /api/evaluations/pending-recordings/`

Grabaciones con `status = completed` y sin evaluación, de la más reciente a la más antigua. Máximo 200 resultados, sin paginación.

| Parámetro | Efecto |
|---|---|
| `agent` | Filtra por ID de agente. |

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/evaluations/pending-recordings/?agent=12" \
  -H "Authorization: Bearer <TOKEN>"
```

```json
[
  {
    "id": 815,
    "filename": "20250310-150102_1741620062.51_3109876543_6015550000.wav",
    "duration": 243,
    "created_at": "2025-03-10 15:05:20",
    "call_id": "ast-1741620062.51",
    "agent_id": 12,
    "agent_name": "Laura Gómez",
    "campaign": "Servicio al cliente"
  }
]
```

## Estadísticas de calidad: `GET /api/cc/quality-stats/`

`QualityStatsView`, permiso `IsAdminOrSupervisor` (el `analyst` recibe `403`). Agrega las evaluaciones filtradas.

| Parámetro | Efecto |
|---|---|
| `days` | Últimos N días. Se ignora si viene `date_from` o si no es entero. |
| `date_from`, `date_to` | Rango por fecha de creación (`AAAA-MM-DD`). |
| `agent_id` | ID del agente de la grabación. |
| `template` | ID de la plantilla. |

Una evaluación aprueba con `total_score >= 80` (`PASS_THRESHOLD`).

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/cc/quality-stats/?days=30" \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{
  "total_evaluations": 42,
  "average_score": 83.6,
  "min_score": 52.0,
  "max_score": 100.0,
  "agents_evaluated": 9,
  "pass_rate": 71.4,
  "pass_threshold": 80,
  "top_agents": [
    {"agent_id": 12, "name": "Laura Gómez", "avg_score": 92.3, "count": 6}
  ],
  "daily_trend": [
    {"date": "2025-03-09", "avg_score": 81.2, "count": 4},
    {"date": "2025-03-10", "avg_score": 88.0, "count": 3}
  ],
  "category_breakdown": [
    {"category": "greeting", "label": "Saludo", "avg_score": 86.0},
    {"category": "clarity", "label": "Claridad", "avg_score": 80.5},
    {"category": "professionalism", "label": "Profesionalismo", "avg_score": 90.0},
    {"category": "resolution", "label": "Resolución", "avg_score": 78.1},
    {"category": "closing", "label": "Cierre", "avg_score": 84.3}
  ],
  "totals": {
    "count": 42,
    "avg_total": 83.57,
    "min_score": 52.0,
    "max_score": 100.0,
    "avg_greeting": 4.3,
    "avg_clarity": 4.02,
    "avg_professionalism": 4.5,
    "avg_resolution": 3.9,
    "avg_closing": 4.21
  },
  "daily_trending": [
    {"date": "2025-03-09", "avg_score": 81.2, "count": 4},
    {"date": "2025-03-10", "avg_score": 88.0, "count": 3}
  ]
}
```

Notas:

- Sin evaluaciones: `average_score` y `pass_rate` son `null` y `category_breakdown` es `[]`.
- `top_agents`: 10 agentes con mejor promedio.
- `category_breakdown` usa solo los cinco criterios legacy (0 a 5 escalado a 0 a 100). Las evaluaciones con plantillas cuyos criterios tienen otros nombres aportan 0 a este desglose.
- `totals` y `daily_trending` se mantienen por compatibilidad con clientes anteriores; `daily_trending` es igual a `daily_trend`.
