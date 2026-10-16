# Campañas y contactos

Endpoints de campañas (y sus acciones de marcación), calificaciones, formularios de gestión, listas de contactos, contactos, importación masiva, lista negra (DNC) y devoluciones de llamada (callbacks).

Código fuente:

- `backend/apps/api/viewsets.py`: `CampaignViewSet`, `CampaignFormViewSet`, `ContactViewSet`, `ContactListViewSet`.
- `backend/apps/api/admin_viewsets.py`: `BlacklistViewSet`.
- `backend/apps/api/cc_viewsets.py`: `CallbackViewSet`, `DNCCheckView`, `BulkContactImportView`.
- Lógica de inicio, pausa y estadísticas: `backend/apps/campaigns/services.py`.

Convenciones comunes: [README.md](./README.md). Calificación desde la consola del agente (`save_disposition`): [usuarios-y-agentes.md](./usuarios-y-agentes.md). Reportes de campañas: [reportes.md](./reportes.md).

## Resumen

| Recurso | Ruta | Lectura | Escritura |
|---|---|---|---|
| Campañas | `/api/campaigns/` | Autenticado | admin, supervisor |
| Formularios de campaña | `/api/campaign-forms/` | Autenticado | admin, supervisor |
| Listas de contactos | `/api/contact-lists/` | Autenticado | admin, supervisor |
| Contactos | `/api/contacts/` | Autenticado | admin, supervisor |
| Importación masiva | `/api/cc/bulk-import/` | | admin, supervisor |
| Lista negra | `/api/blacklist/` | admin, supervisor | admin, supervisor |
| Verificación DNC | `/api/cc/dnc-check/` | | Autenticado |
| Callbacks | `/api/callbacks/` | Autenticado | Autenticado |

## Campañas: `/api/campaigns/`

`CampaignViewSet` (`ModelViewSet`), permiso `IsAdminOrSupervisorOrReadOnly`. Ese permiso también rige las acciones: las de tipo `GET` las usa cualquier autenticado y las de tipo `POST`, `PATCH` o `DELETE` solo `admin` y `supervisor`.

### CRUD

| Acción | Método y ruta |
|---|---|
| list | `GET /api/campaigns/` |
| create | `POST /api/campaigns/` |
| retrieve | `GET /api/campaigns/{id}/` |
| update | `PUT /api/campaigns/{id}/` |
| partial_update | `PATCH /api/campaigns/{id}/` |
| destroy | `DELETE /api/campaigns/{id}/` |

Filtros: `campaign_type`, `status`, `dialer_type`, `agents` (ID de agente; el panel del agente usa `?agents=<id>&status=active`). `search` sobre `name` y `description`. `ordering` por campos del serializer.

### Campos (`CampaignSerializer`, `fields = '__all__'`)

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Solo lectura. |
| `name` | string | Obligatorio, único. |
| `description` | string | |
| `campaign_type` | string | `inbound`, `outbound`, `manual`, `preview`. |
| `dialer_type` | string o null | `predictive`, `progressive`, `preview`, `manual` (ver compatibilidad abajo). |
| `status` | string | `draft` (por defecto), `active`, `paused`, `finished`. Se recomienda cambiarlo con `start` y `pause`. |
| `max_calls_per_agent` | integer | 1 a 5 (1). |
| `max_retries` | integer | 0 a 10 (3). |
| `retry_delay` | integer | Segundos entre reintentos (300). |
| `call_timeout` | integer | 10 a 300 s (30). |
| `start_date` | datetime | Obligatorio. |
| `end_date` | datetime o null | Posterior a `start_date`. |
| `schedule_start_time`, `schedule_end_time` | time (`HH:MM:SS`) | Franja diaria; fin posterior al inicio. |
| `queue` | integer o null | ID de cola. |
| `contact_list` | integer o null | ID de lista. Obligatoria al crear campañas `outbound` y `preview`. |
| `script_template` | string | Guion para el agente. |
| `form_fields` | objeto | Campos de formulario heredados (JSON libre). |
| `form` | objeto o null | Solo lectura: formulario anidado. |
| `form_id` | integer o null | Solo escritura: ID de `/api/campaign-forms/`. |
| `dispositions` | lista | Solo lectura: calificaciones de la campaña. |
| `success_rate` | number | Solo lectura. |
| `is_template`, `template_name` | boolean, string | Marca la campaña como plantilla clonable. |
| `dnc_enabled` | boolean | Verificar lista negra antes de marcar (`true`). |
| `preview_timeout` | integer | Segundos para revisar el contacto en preview (30). |
| `timezone` | string | Zona de la campaña (`America/Bogota`). |
| `vip_priority_boost` | integer | Aumento de prioridad para contactos VIP (10). |
| `amd_enabled` | boolean | Detección de contestador (solo predictivo). |
| `amd_action` | string | `hangup` o `message`. |
| `amd_message` | string | Audio de Asterisk para `message`, por ejemplo `custom/mensaje-campana`. |
| `required_skills` | lista de IDs | Grupos de agentes requeridos (`/api/agent-groups/`). |
| `total_contacts`, `contacted`, `successful` | integer | Solo lectura. Los recalcula una tarea de Celery. |
| `created_at`, `updated_at` | datetime | Solo lectura. |
| `created_by` | integer o null | La vista no lo completa al crear; queda vacío si no se envía. |

Los agentes asignados no forman parte de este serializer: la relación está en el agente (`campaigns` en `/api/agents/{id}/`).

Compatibilidad `campaign_type` / `dialer_type` (validada en el serializer):

| `campaign_type` | `dialer_type` permitido |
|---|---|
| `inbound` | Ninguno (debe omitirse o ser `null`). |
| `outbound` | `progressive`, `predictive` |
| `manual` | `manual` |
| `preview` | `preview` |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/campaigns/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Renovaciones marzo", "campaign_type": "outbound", "dialer_type": "progressive", "start_date": "2025-03-10T08:00:00-05:00", "schedule_start_time": "08:00:00", "schedule_end_time": "18:00:00", "queue": 2, "contact_list": 5, "form_id": 1, "max_retries": 3, "call_timeout": 30}'
```

Respuesta `201` (extracto):

```json
{
  "id": 3,
  "dispositions": [],
  "success_rate": 0,
  "form": {"id": 1, "name": "Renovación", "description": "", "fields_schema": [], "is_active": true, "created_at": "2025-03-01 10:00:00", "updated_at": "2025-03-01 10:00:00"},
  "name": "Renovaciones marzo",
  "campaign_type": "outbound",
  "dialer_type": "progressive",
  "status": "draft",
  "max_calls_per_agent": 1,
  "max_retries": 3,
  "retry_delay": 300,
  "call_timeout": 30,
  "start_date": "2025-03-10 08:00:00",
  "end_date": null,
  "schedule_start_time": "08:00:00",
  "schedule_end_time": "18:00:00",
  "dnc_enabled": true,
  "amd_enabled": false,
  "amd_action": "hangup",
  "total_contacts": 0,
  "contacted": 0,
  "successful": 0,
  "queue": 2,
  "contact_list": 5,
  "required_skills": []
}
```

Errores `400` frecuentes: `{"dialer_type": "Debes seleccionar un tipo de marcación para este tipo de campaña."}`, `{"dialer_type": "Combinación inválida: campaign_type=outbound no permite dialer_type=manual."}`, `{"contact_list": "Las campañas salientes requieren una lista de contactos"}`, `{"end_date": "La fecha de fin debe ser posterior a la fecha de inicio"}`, `{"call_timeout": "El timeout debe estar entre 10 y 300 segundos"}`, `{"max_calls_per_agent": "Debe estar entre 1 y 5 llamadas por agente"}`.

### POST /api/campaigns/{id}/start/

Activa la campaña (`status = active`), actualiza métricas y emite `campaign_started` para que el marcador la tome. Rol `admin` o `supervisor`. Sin cuerpo.

Validaciones: no debe estar ya activa; las campañas `outbound` y `preview` necesitan `contact_list` con `total_contacts > 0`.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/campaigns/3/start/ \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{"success": true, "campaign_id": 3, "campaign_name": "Renovaciones marzo", "status": "active"}
```

Errores: `400 {"error": "Campaign 'Renovaciones marzo' is already active"}`, `400 {"error": "Campaign 'Renovaciones marzo' has no contacts to process"}`, `404 {"error": "Campaign 3 not found"}`.

`total_contacts` de la lista solo lo incrementan la importación masiva (`/api/cc/bulk-import/`) y el servicio de contactos; los contactos creados uno a uno con `POST /api/contacts/` no lo actualizan. Una lista cargada solo por esa vía puede quedar en 0 y bloquear el inicio.

### POST /api/campaigns/{id}/pause/

Pausa una campaña activa (`status = paused`) y emite `campaign_paused`. Rol `admin` o `supervisor`. Sin cuerpo.

```json
{"success": true, "campaign_id": 3, "campaign_name": "Renovaciones marzo", "status": "paused"}
```

Errores: `400 {"error": "Campaign 'Renovaciones marzo' is not active"}`, `404`.

No existe una acción `stop` o `finish` en la API. Para finalizar se cambia `status` a `finished` con `PATCH /api/campaigns/{id}/` (sin los efectos de métricas y eventos del servicio).

### GET /api/campaigns/{id}/stats/

Estadísticas calculadas en el momento a partir de las llamadas de la campaña. Cualquier autenticado.

```json
{
  "campaign_id": 3,
  "campaign_name": "Renovaciones marzo",
  "status": "active",
  "total_contacts": 1200,
  "contacted": 430,
  "successful": 96,
  "success_rate": 22.33,
  "calls": {"total": 610, "completed": 402, "answered": 5, "no_answer": 150, "busy": 38, "failed": 15},
  "dispositions": [
    {"code": "VENTA", "name": "Venta", "count": 96, "is_success": true},
    {"code": "VOLVER_LLAMAR", "name": "Volver a llamar", "count": 71, "is_success": false}
  ]
}
```

Error `404 {"error": "Campaign 3 not found"}`.

### GET /api/campaigns/{id}/next_contact/

Siguiente contacto a marcar para un agente: contactos de la lista de la campaña en estado `pending` o `callback`, sin llamadas en las últimas 24 horas, ordenados por `priority` e `id`. Cualquier autenticado; un usuario con rol `agent` debe estar asignado a la campaña.

| Query | Tipo | Requerido |
|---|---|---|
| `agent_id` | integer | Sí (solo se valida que venga). |

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/campaigns/3/next_contact/?agent_id=9" \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{
  "contact": {
    "id": 812,
    "name": "Carlos Ramírez",
    "phone": "+573001234567",
    "email": "carlos@example.com",
    "company": "Ejemplo SAS",
    "notes": "(ver observación)",
    "custom_fields": {"plan": "Básico"},
    "priority": 0,
    "call_history": [
      {"id": 5790, "date": "2025-03-08 15:05", "disposition": "Volver a llamar", "notes": "Pidió llamar en la tarde"}
    ]
  }
}
```

Sin contactos pendientes: `200 {"contact": null, "message": "No pending contacts"}`. Errores: `400 {"error": "agent_id is required"}`, `403 {"error": "El agente no está asignado a esta campaña"}`, `500 {"error": "..."}`.

Observación sobre el código: `notes` se llena con `contact.notes`, que es el gestor de la relación `ContactNote` (el modelo `Contact` no tiene un campo de texto `notes`). El codificador JSON de DRF no sabe convertir un gestor, así que, leyendo el código, la respuesta debería fallar con `500` cada vez que se encuentra un contacto. No se verificó en ejecución. El ejemplo muestra la forma que la vista intenta devolver.

### POST /api/campaigns/{id}/clone/

Crea una campaña nueva copiando la configuración (y los agentes y skills requeridos). La copia queda en `draft`, sin marca de plantilla, con métricas en cero y `created_by` = usuario actual. Las calificaciones no se copian. Rol `admin` o `supervisor`.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `name` | string | No | Por defecto `"<nombre> (copia)"`. Debe ser único. |

Respuesta `201`: la campaña nueva completa (mismo formato que `retrieve`).

### POST /api/campaigns/{id}/preview-decide/

Registra la decisión del agente en modo preview: guarda en Redis `campaign:{id}:preview:agent:{agent_id}:accepted` o `:rejected` con TTL de 120 s, que el marcador lee para continuar o saltar el contacto.

| Campo | Tipo | Requerido | Valores |
|---|---|---|---|
| `agent_id` | integer | Sí | ID del agente. |
| `decision` | string | Sí | `accept` o `reject`. |

Respuesta `200`: `{"status": "ok", "decision": "accept"}`. Errores: `400 {"error": "Se requiere agent_id y decision (accept/reject)"}`, `500` si Redis falla.

Permiso efectivo: al ser `POST`, el permiso del ViewSet solo deja pasar a `admin` y `supervisor` (y superusuarios). La comprobación interna que permitiría a un agente decidir por sí mismo nunca se alcanza: un usuario con rol `agent` recibe `403`.

### GET /api/campaigns/templates/

Campañas con `is_template = true`, ordenadas por nombre. No paginado. Cualquier autenticado.

### GET y POST /api/campaigns/{id}/dispositions/

Calificaciones (disposiciones) de la campaña.

- `GET`: cualquier autenticado. Lista no paginada.
- `POST`: `admin` o `supervisor`.

Campos (`CampaignDispositionSerializer`):

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Solo lectura. |
| `code` | string | Obligatorio, único dentro de la campaña. Es el valor que envía `save_disposition`. |
| `name` | string | Obligatorio. |
| `description` | string | |
| `is_success` | boolean | Cuenta como gestión exitosa. |
| `requires_callback` | boolean | Pide fecha de rellamada en la consola. |
| `order` | integer | Orden de presentación. |
| `form` | objeto o null | Solo lectura: formulario propio de la calificación. |
| `form_id` | integer o null | Solo escritura. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/campaigns/3/dispositions/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"code": "VENTA", "name": "Venta", "is_success": true, "requires_callback": false, "order": 1}'
```

Respuesta `201`:

```json
{"id": 21, "code": "VENTA", "name": "Venta", "description": "", "is_success": true, "requires_callback": false, "order": 1, "form": null}
```

Errores: `400 {"code": ["Ya existe una calificación con ese código en la campaña."]}`, `403 {"error": "Solo admin/supervisor pueden crear calificaciones"}` (o el `403` del ViewSet).

### PATCH y DELETE /api/campaigns/{id}/dispositions/{disposition_id}/

Edita parcialmente o borra una calificación de la campaña. Rol `admin` o `supervisor`.

- `PATCH`: mismos campos que la creación. Respuesta `200` con la calificación.
- `DELETE`: `204`.

Errores: `403 {"error": "Sin permisos"}`, `404 {"error": "Calificación no encontrada"}`.

## Formularios de campaña: `/api/campaign-forms/`

`CampaignFormViewSet` (`ModelViewSet`), permiso `IsAdminOrSupervisorOrReadOnly`. CRUD estándar (`list`, `create`, `retrieve`, `update`, `partial_update`, `destroy`). Este ViewSet solo tiene `SearchFilter` (sobre `name`) y `OrderingFilter`; no admite filtros por campo. El usuario que crea queda en `created_by` (no se expone).

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Solo lectura. |
| `name` | string | Obligatorio. |
| `description` | string | |
| `fields_schema` | lista | Definición de campos (ver abajo). |
| `is_active` | boolean | |
| `created_at`, `updated_at` | datetime | Solo lectura. |

Cada elemento de `fields_schema` debe ser un objeto con `name`, `label` y `type`; opcionales `required`, `options`, `placeholder`, `order`. Tipos previstos en el modelo: `text`, `textarea`, `number`, `select`, `multiselect`, `checkbox`, `date`, `phone`, `email` (el serializer no restringe el valor de `type`).

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/campaign-forms/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Renovación", "fields_schema": [{"name": "plan", "label": "Plan elegido", "type": "select", "required": true, "options": ["Básico", "Plus"], "order": 1}, {"name": "observacion", "label": "Observación", "type": "textarea", "order": 2}]}'
```

Errores `400`: `{"fields_schema": ["El esquema debe ser una lista de campos."]}`, `{"fields_schema": ["Campo 0: se requieren \"name\", \"label\" y \"type\"."]}`.

## Listas de contactos: `/api/contact-lists/`

`ContactListViewSet` (`ModelViewSet`), permiso `IsAdminOrSupervisorOrReadOnly`. CRUD estándar. Solo `search` sobre `name` y `description` (no hay filtros por campo ni orden). Borrar una lista borra sus contactos (cascada).

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Solo lectura. |
| `name` | string | Obligatorio, único. |
| `description` | string | |
| `total_contacts` | integer | Solo lectura (ver nota en `start`). |
| `is_active` | boolean | |
| `created_by` | integer o null | La vista no lo completa automáticamente. |
| `created_at`, `updated_at` | datetime | Solo lectura. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/contact-lists/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Base renovaciones marzo", "description": "Clientes con vencimiento en marzo"}'
```

## Contactos: `/api/contacts/`

`ContactViewSet` (`ModelViewSet`), permiso `IsAdminOrSupervisorOrReadOnly`. CRUD estándar.

Filtros:

| Parámetro | Descripción |
|---|---|
| `contact_list` | ID de lista. |
| `status` | `new`, `pending`, `callback`, `contacted`, `success`, `failed`, `blacklisted`. |
| `status__in` | Varios estados separados por coma: `?status__in=pending,callback`. |
| `campaign` | ID de campaña: devuelve los contactos de su `contact_list` (vacío si la campaña no tiene lista o no existe). |
| `search` | `first_name`, `last_name`, `phone`, `email`, `company`. |
| `ordering` | Campos del serializer, por ejemplo `-priority` o `created_at`. |

Campos (`ContactSerializer`, `fields = '__all__'`):

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Solo lectura. |
| `contact_list` | integer | Obligatorio. |
| `first_name` | string | Obligatorio. |
| `last_name`, `email`, `company`, `position`, `address`, `city` | string | |
| `country` | string | Código ISO de 2 letras. También se usa para interpretar el teléfono (por defecto `CO`). |
| `full_name` | string | Solo lectura. |
| `phone` | string | Obligatorio. Se valida con `phonenumbers` y se guarda en E.164 (`+57...`). |
| `phone2`, `phone3` | string | |
| `status` | string | Por defecto `new`. |
| `priority` | integer | 0 a 10. |
| `attempts`, `last_attempt` | | Solo lectura. |
| `next_attempt` | datetime o null | |
| `custom_fields` | objeto | Datos propios de la campaña. `save_disposition` fusiona aquí el `form_data`. |
| `timezone` | string | Zona del contacto (el marcador no llama fuera de su horario local). |
| `is_vip` | boolean | |
| `dnc_opt_out` | boolean | El contacto pidió no ser llamado. |
| `whatsapp_opt_in` | boolean | Consentimiento para WhatsApp. Al cambiarlo se fijan `whatsapp_opt_in_at` y, si no se envía, `whatsapp_opt_in_source = "agente"`. |
| `whatsapp_opt_in_at`, `whatsapp_opt_in_source` | datetime, string | |
| `created_at`, `updated_at` | datetime | Solo lectura. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/contacts/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"contact_list": 5, "first_name": "Carlos", "last_name": "Ramírez", "phone": "300 123 4567", "email": "carlos@example.com", "country": "CO", "custom_fields": {"plan": "Básico"}}'
```

Respuesta `201` (extracto):

```json
{
  "id": 812,
  "full_name": "Carlos Ramírez",
  "contact_list": 5,
  "first_name": "Carlos",
  "last_name": "Ramírez",
  "email": "carlos@example.com",
  "phone": "+573001234567",
  "country": "CO",
  "status": "new",
  "priority": 0,
  "attempts": 0,
  "last_attempt": null,
  "custom_fields": {"plan": "Básico"},
  "is_vip": false,
  "dnc_opt_out": false,
  "whatsapp_opt_in": false,
  "created_at": "2025-03-10 12:00:41",
  "updated_at": "2025-03-10 12:00:41"
}
```

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/contacts/?campaign=3&status__in=pending,callback&ordering=-priority" \
  -H "Authorization: Bearer <TOKEN>"
```

Errores `400`: `{"phone": ["Número de teléfono inválido"]}`, `{"phone": ["Número de teléfono demasiado corto"]}`, `{"email": ["Formato de email inválido"]}`, `{"priority": "La prioridad debe estar entre 0 y 10"}`, `{"phone": "Debe proporcionar al menos un número de teléfono"}`.

## Importación masiva: POST /api/cc/bulk-import/

`BulkContactImportView`, rol `admin` o `supervisor`. `multipart/form-data`. Inserta en lotes de 1000 y suma los importados a `total_contacts` de la lista.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `contact_list_id` | integer | Sí | Lista destino. |
| `file` | archivo | Sí | `.csv` (UTF-8 sin BOM: con BOM la primera columna no se reconoce) o `.xlsx`. |
| `skip_duplicates` | string | No (`true`) | `true` omite teléfonos ya existentes en la lista. Siempre omite repetidos dentro del mismo archivo. |

Columnas (primera fila como cabecera): `phone` (obligatoria), `first_name`, `last_name`, `email`, `company`, `address`, `city`, `country` (por defecto `CO`) y `whatsapp_opt_in` (`si`, `sí`, `yes`, `true`, `1`, `x` cuentan como aceptado). En CSV los nombres de columna deben ir en minúsculas tal cual; en Excel la cabecera se pasa a minúsculas antes de procesar. Los teléfonos se validan como números de Colombia y se guardan en E.164; los inválidos se omiten y se reportan.

La vista acepta la extensión `.xls`, pero la lectura usa openpyxl, que solo abre `.xlsx`; un `.xls` real termina en `400` con el error de lectura.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/cc/bulk-import/ \
  -H "Authorization: Bearer <TOKEN>" \
  -F "contact_list_id=5" \
  -F "skip_duplicates=true" \
  -F "file=@contactos.csv"
```

```json
{
  "success": true,
  "imported": 1180,
  "skipped": 20,
  "errors": ["Row 14: Invalid phone '12345'", "Row 88: Missing phone number"],
  "total_errors": 2
}
```

`errors` trae como máximo 10 mensajes; `total_errors` es el total. `skipped` incluye duplicados e inválidos.

Errores `400`: `{"error": "contact_list_id y file son requeridos"}`, `{"error": "Formato no soportado. Use CSV o XLSX."}`, `{"error": "Contact list 5 not found"}` y cualquier otro error de lectura del archivo.

## Lista negra (DNC): `/api/blacklist/`

`BlacklistViewSet` (`ModelViewSet`), permiso `IsAdminOrSupervisor` (también para leer). Acepta JSON y `multipart/form-data`. Cada alta, edición o baja invalida la caché DNC del marcador en Redis para ese número.

### CRUD

| Acción | Método y ruta |
|---|---|
| list | `GET /api/blacklist/` |
| create | `POST /api/blacklist/` |
| retrieve | `GET /api/blacklist/{id}/` |
| update | `PUT /api/blacklist/{id}/` |
| partial_update | `PATCH /api/blacklist/{id}/` |
| destroy | `DELETE /api/blacklist/{id}/` |

Filtros: `is_active`; `search` sobre `phone` y `reason`; orden por defecto `-added_at`.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Solo lectura. |
| `phone` | string | Obligatorio, único. Se normaliza a dígitos con `+` inicial opcional; mínimo 7 dígitos. |
| `reason` | string | |
| `is_active` | boolean | |
| `added_by`, `added_by_name`, `added_at` | | Solo lectura (usuario que lo agregó). |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/blacklist/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+57 300 765 4321", "reason": "Solicitud del titular"}'
```

```json
{"id": 77, "phone": "+573007654321", "reason": "Solicitud del titular", "is_active": true, "added_by": 1, "added_by_name": "Administrador", "added_at": "2025-03-10 12:10:00"}
```

Errores `400`: `{"phone": ["Número demasiado corto."]}` y el error de unicidad de `phone` si el valor enviado coincide exactamente con uno guardado. La unicidad se valida antes de normalizar: un duplicado escrito con otro formato (espacios, guiones) llega a la base de datos y termina en error del servidor. Para cargas con formatos mixtos use `bulk-import`, que normaliza y omite duplicados.

### POST /api/blacklist/bulk-import/

Alta masiva. Acepta un archivo o texto.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `file` | archivo | Uno de los dos | CSV o XLSX con columnas `phone[, reason]`. La primera fila se trata como cabecera si no tiene dígitos. |
| `numbers` | string | Uno de los dos | Un número por línea. |
| `reason` | string | No | Motivo por defecto (`Importación masiva`). |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/blacklist/bulk-import/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"numbers": "3001112233\n3004445566", "reason": "Lista del cliente"}'
```

```json
{"imported": 2, "skipped": 0, "invalid": 0}
```

`skipped` son números ya existentes o repetidos; `invalid`, los de menos de 7 dígitos. Error `400 {"error": "No se encontraron números para importar."}`.

### GET /api/blacklist/check/

Indica si un número está bloqueado, por lista negra activa o por un contacto con `dnc_opt_out`. Compara los últimos 10 dígitos. Rol `admin` o `supervisor`.

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/blacklist/check/?phone=3007654321" \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{"phone": "3007654321", "blocked": true, "in_blacklist": true, "dnc_opt_out": false}
```

Error `400 {"error": "phone requerido"}`.

## Verificación DNC para cualquier usuario: POST /api/cc/dnc-check/

`DNCCheckView`, permiso `IsAuthenticated` (la usan agentes antes de marcar manualmente). Misma lógica que `blacklist/check/`, pero por `POST`.

| Campo | Tipo | Requerido |
|---|---|---|
| `phone` | string | Sí |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/cc/dnc-check/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+573007654321"}'
```

```json
{"phone": "+573007654321", "blocked": true, "in_blacklist": true, "dnc_opt_out": false}
```

Error `400 {"error": "phone requerido"}`.

## Devoluciones de llamada: `/api/callbacks/`

`CallbackViewSet` (`ModelViewSet`), permiso `IsAuthenticated` para todo (incluido borrar) y sin filtro por usuario: cualquier autenticado ve y modifica todos los callbacks.

### CRUD

| Acción | Método y ruta |
|---|---|
| list | `GET /api/callbacks/` |
| create | `POST /api/callbacks/` |
| retrieve | `GET /api/callbacks/{id}/` |
| update | `PUT /api/callbacks/{id}/` |
| partial_update | `PATCH /api/callbacks/{id}/` |
| destroy | `DELETE /api/callbacks/{id}/` |

Filtros: `status`, `campaign`, `agent`. `search` sobre `phone`, `contact_name`, `notes`. `ordering` por `scheduled_at`, `priority`, `created_at` (orden por defecto del modelo: `-priority`, `scheduled_at`).

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Solo lectura. |
| `phone` | string | Obligatorio. |
| `contact_name` | string | |
| `notes` | string | |
| `status` | string | `pending` (por defecto), `scheduled`, `dialing`, `completed`, `failed`, `cancelled`. |
| `priority` | integer | Mayor valor primero. |
| `scheduled_at` | datetime o null | |
| `attempts` | integer | Solo lectura. |
| `max_attempts` | integer | 3. |
| `call`, `campaign`, `agent` | integer o null | Llamada origen, campaña y agente asignado. |
| `campaign_name`, `agent_name` | string | Solo lectura. |
| `created_by` | integer | Solo lectura (usuario del token). |
| `created_at`, `updated_at` | datetime | Solo lectura. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/callbacks/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+573001234567", "contact_name": "Carlos Ramírez", "notes": "Pidió llamar en la tarde", "status": "scheduled", "scheduled_at": "2025-03-10T16:00:00-05:00", "campaign": 3, "agent": 9}'
```

```json
{
  "id": 140,
  "phone": "+573001234567",
  "contact_name": "Carlos Ramírez",
  "notes": "Pidió llamar en la tarde",
  "status": "scheduled",
  "priority": 0,
  "scheduled_at": "2025-03-10 16:00:00",
  "attempts": 0,
  "max_attempts": 3,
  "call": null,
  "campaign": 3,
  "campaign_name": "Renovaciones marzo",
  "agent": 9,
  "agent_name": "Juan Pérez",
  "created_by": 3,
  "created_at": "2025-03-10 12:20:00",
  "updated_at": "2025-03-10 12:20:00"
}
```

### POST /api/callbacks/{id}/cancel/

Cancela un callback en estado `pending` o `scheduled`. Sin cuerpo. Respuesta `{"status": "cancelled"}`. Error `400 {"error": "Solo se pueden cancelar callbacks pendientes/programados"}`.

### POST /api/callbacks/{id}/reschedule/

Reprograma y deja el estado en `scheduled`.

| Campo | Tipo | Requerido |
|---|---|---|
| `scheduled_at` | datetime ISO 8601 | Sí |

Respuesta `{"status": "rescheduled", "scheduled_at": "2025-03-11T09:00:00-05:00"}` (devuelve el valor recibido). Error `400 {"error": "scheduled_at requerido"}`. El valor no pasa por el serializer; un formato inválido termina en error del servidor.

### GET /api/callbacks/pending_count/

Contadores globales para el dashboard.

```json
{"pending": 34, "overdue": 6}
```

`pending` cuenta los estados `pending` y `scheduled`; `overdue`, los de esos estados con `scheduled_at` ya vencido.

Véase también: [Glosario](../general/glosario.md), [Desarrollo del backend](../desarrollo/backend.md).
