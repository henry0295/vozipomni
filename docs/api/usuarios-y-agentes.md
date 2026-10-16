# Usuarios y agentes

Endpoints para administrar usuarios y roles, perfiles de agente (extensión SIP, estado, sesión), grupos de agentes y razones de pausa. Código fuente:

- `backend/apps/api/admin_viewsets.py`: `UserAdminViewSet` (`/api/users/`).
- `backend/apps/api/viewsets.py`: `AgentViewSet` (`/api/agents/`).
- `backend/apps/api/extra_viewsets.py`: `AgentGroupViewSet` (`/api/agent-groups/`) y `AgentBreakReasonViewSet` (`/api/break-reasons/`).

Convenciones de paginación, filtros, errores y roles: [README.md](./README.md). Autenticación: [autenticacion.md](./autenticacion.md).

## Usuarios: `/api/users/`

`UserAdminViewSet` (`ModelViewSet`), permiso `IsAdminUser`: todas las operaciones requieren rol `admin` (o superusuario).

### CRUD

| Acción | Método y ruta | Notas |
|---|---|---|
| list | `GET /api/users/` | Paginado. Orden por defecto `username`. |
| create | `POST /api/users/` | `password` obligatorio. |
| retrieve | `GET /api/users/{id}/` | |
| update | `PUT /api/users/{id}/` | Requiere los campos obligatorios (`username`). `password` opcional. |
| partial_update | `PATCH /api/users/{id}/` | Solo los campos enviados. |
| destroy | `DELETE /api/users/{id}/` | No borra: desactiva (`is_active = false`) y responde `200 {"status": "deactivated"}`. |

Filtros y orden:

| Parámetro | Valores |
|---|---|
| `role` | `admin`, `supervisor`, `agent`, `analyst` |
| `is_active` | `true` / `false` |
| `is_active_agent` | `true` / `false` |
| `search` | `username`, `email`, `first_name`, `last_name` |
| `ordering` | `username`, `date_joined`, `last_login` |

Campos (`UserAdminSerializer`):

| Campo | Tipo | Lectura/escritura | Descripción |
|---|---|---|---|
| `id` | integer | Solo lectura | |
| `username` | string | Obligatorio | Único. |
| `email` | string | Opcional | Único (se valida sin distinguir mayúsculas). |
| `first_name`, `last_name` | string | Opcional | |
| `name` | string | Solo lectura | Nombre completo o `username`. |
| `role` | string | Opcional | `admin`, `supervisor`, `agent` (por defecto), `analyst`. |
| `role_display` | string | Solo lectura | Etiqueta: Administrador, Supervisor, Agente, Analista. |
| `phone`, `department` | string | Opcional | |
| `is_active` | boolean | Opcional | |
| `is_active_agent` | boolean | Opcional | |
| `has_agent_profile` | boolean | Solo lectura | `true` si el usuario tiene perfil en `/api/agents/`. |
| `last_login`, `last_activity`, `date_joined` | datetime | Solo lectura | |
| `password` | string | Solo escritura | Pasa por los validadores de contraseña de Django. |

Crear un usuario con rol `agent` no crea su perfil de agente. El perfil (extensión SIP) se crea con `POST /api/agents/`, que además puede crear el usuario.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/users/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"username": "analista1", "email": "analista1@example.com", "first_name": "Sofía", "last_name": "Mejía", "role": "analyst", "password": "<CONTRASEÑA>"}'
```

Respuesta `201`:

```json
{
  "id": 25,
  "username": "analista1",
  "email": "analista1@example.com",
  "first_name": "Sofía",
  "last_name": "Mejía",
  "name": "Sofía Mejía",
  "role": "analyst",
  "role_display": "Analista",
  "phone": "",
  "department": "",
  "is_active": true,
  "is_active_agent": false,
  "has_agent_profile": false,
  "last_login": null,
  "last_activity": null,
  "date_joined": "2025-03-10 09:15:42"
}
```

Errores comunes:

| Código | Causa | Cuerpo |
|---|---|---|
| `400` | Crear sin contraseña. | `{"password": ["La contraseña es obligatoria al crear un usuario."]}` |
| `400` | Contraseña débil. | `{"password": ["Esta contraseña es demasiado común.", "..."]}` |
| `400` | Correo repetido. | `{"email": ["Este correo ya está en uso."]}` |
| `400` | Un admin intenta cambiar su propio rol o desactivarse con `PUT`/`PATCH`. | `{"role": "No puedes cambiar tu propio rol."}` / `{"is_active": "No puedes desactivar tu propia cuenta."}` |
| `400` | `DELETE` sobre la propia cuenta. | `{"error": "No puedes eliminar tu propia cuenta."}` |
| `403` | El usuario no es admin. | `{"detail": "Se requiere rol de administrador para esta acción."}` |

### POST /api/users/{id}/set-password/

Asigna una contraseña a otro usuario. Rol `admin`.

| Campo | Tipo | Requerido |
|---|---|---|
| `password` | string | Sí |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/users/25/set-password/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"password": "<NUEVA_CONTRASEÑA>"}'
```

Respuesta `200`: `{"status": "password updated"}`. Error `400 {"password": [...]}` si no cumple los validadores. No invalida los refresh tokens ya emitidos a ese usuario.

### POST /api/users/{id}/toggle-active/

Alterna `is_active`. Rol `admin`. Sin cuerpo.

Respuesta `200`: `{"is_active": false}`. Error `400 {"error": "No puedes desactivar tu propia cuenta."}` si `id` es el propio usuario.

## Agentes: `/api/agents/`

`AgentViewSet` (`ModelViewSet`). Permiso base `IsAdminOrSupervisorOrReadOnly`: cualquier usuario autenticado puede leer; crear, editar y borrar requiere `admin` o `supervisor`. Las acciones `login`, `logout`, `change_status`, `start_break`, `end_break` y `save_disposition` se abren a cualquier usuario autenticado (`get_permissions`).

### CRUD

| Acción | Método y ruta | Permiso | Notas |
|---|---|---|---|
| list | `GET /api/agents/` | Autenticado | Paginado. Orden por defecto `-created_at`. |
| create | `POST /api/agents/` | admin, supervisor | Crea también el usuario (rol `agent`). |
| retrieve | `GET /api/agents/{id}/` | Autenticado | |
| update | `PUT /api/agents/{id}/` | admin, supervisor | |
| partial_update | `PATCH /api/agents/{id}/` | admin, supervisor | |
| destroy | `DELETE /api/agents/{id}/` | admin, supervisor | Borra el endpoint PJSIP, desactiva el usuario (`is_active` y `is_active_agent` en `false`) y elimina el agente. `204`. |

`{id}` es la clave primaria numérica del agente, no el código `agent_id` (por ejemplo `AGT001`).

Filtros y orden:

| Parámetro | Valores |
|---|---|
| `status` | `available`, `busy`, `oncall`, `break`, `offline`, `wrapup` |
| `webrtc_enabled` | `true` / `false` |
| `user` | ID del usuario (útil para encontrar el perfil del usuario actual) |
| `search` | `agent_id`, `sip_extension`, `user__username`, `user__first_name`, `user__last_name`, `user__email` |
| `ordering` | `created_at`, `agent_id`, `status`, `calls_today` |

Campos (`AgentSerializer`, `fields = '__all__'` más campos auxiliares):

| Campo | Tipo | Lectura/escritura | Descripción |
|---|---|---|---|
| `id` | integer | Solo lectura | |
| `user` | integer | Solo lectura | ID del usuario vinculado. |
| `user_details` | objeto | Solo lectura | `UserSerializer` del usuario (id, username, email, name, role...). |
| `agent_id` | string | Obligatorio al crear | Código único del agente. |
| `sip_extension` | string | Obligatorio al crear | Extensión SIP única. |
| `sip_password` | string | Opcional | Clave SIP. Si no se envía se genera. |
| `status` | string | Solo lectura | Se cambia con las acciones de este recurso. |
| `is_available` | boolean | Solo lectura | `status == "available"` y `current_calls < max_concurrent_calls`. |
| `webrtc_enabled` | boolean | Opcional (por defecto `true`) | |
| `max_concurrent_calls` | integer | Opcional (por defecto 1) | |
| `auto_answer` | boolean | Opcional | |
| `recording_enabled` | boolean | Opcional (por defecto `true`) | |
| `campaigns` | lista de IDs | Opcional | Campañas asignadas. |
| `current_campaign` | integer o null | Opcional | |
| `current_calls`, `last_call_time`, `logged_in_at`, `last_status_change` | | Solo lectura | Estado en tiempo real. |
| `calls_today`, `talk_time_today`, `available_time_today`, `break_time_today`, `oncall_time_today`, `wrapup_time_today` | integer | Solo lectura | Métricas del día (segundos, salvo `calls_today`). |
| `created_at`, `updated_at` | datetime | Solo lectura | |
| `username`, `password`, `first_name`, `last_name`, `email` | string | Solo escritura | Datos del usuario vinculado. `username` es obligatorio al crear. |

Nota de seguridad: `sip_password` no está marcado como solo escritura en el serializer, así que `GET /api/agents/` y `GET /api/agents/{id}/` devuelven la clave SIP en texto plano a cualquier usuario autenticado, incluidos los agentes.

Comportamiento al crear:

- `username` es obligatorio; se valida que el usuario y el correo no existan.
- El usuario se crea con rol `agent` e `is_active_agent = true`. Sin `password`, la cuenta queda sin contraseña utilizable hasta que un admin la defina (`/api/users/{id}/set-password/`).
- Se validan duplicados de `agent_id` y `sip_extension`.
- Si no se envía `sip_password` se genera una clave aleatoria.
- Con `webrtc_enabled = true` se crea el endpoint PJSIP en Asterisk. Además, una señal `post_save` crea o corrige el registro en `/api/telephony/extensions/` (tipo `WEBRTC` o `PJSIP`) y recarga PJSIP.

Comportamiento al actualizar: los campos de usuario enviados (`username`, `password`, `first_name`, `last_name`, `email`) se aplican al usuario vinculado. Si cambia `sip_extension`, se borra el endpoint PJSIP anterior y se crea el nuevo solo si también se envía `sip_password`.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/agents/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"username": "agente05", "password": "<CONTRASEÑA>", "first_name": "Juan", "last_name": "Pérez", "email": "agente05@example.com", "agent_id": "AGT005", "sip_extension": "1005", "webrtc_enabled": true, "campaigns": [3]}'
```

Respuesta `201` (extracto):

```json
{
  "id": 9,
  "user_details": {
    "id": 31,
    "username": "agente05",
    "email": "agente05@example.com",
    "first_name": "Juan",
    "last_name": "Pérez",
    "name": "Juan Pérez",
    "role": "agent",
    "phone": "",
    "department": "",
    "is_active_agent": true,
    "last_activity": null
  },
  "is_available": false,
  "sip_password": "<CLAVE_SIP>",
  "agent_id": "AGT005",
  "sip_extension": "1005",
  "status": "offline",
  "webrtc_enabled": true,
  "max_concurrent_calls": 1,
  "auto_answer": false,
  "recording_enabled": true,
  "current_calls": 0,
  "last_call_time": null,
  "logged_in_at": null,
  "last_status_change": "2025-03-10 09:30:12",
  "calls_today": 0,
  "talk_time_today": 0,
  "available_time_today": 0,
  "break_time_today": 0,
  "oncall_time_today": 0,
  "wrapup_time_today": 0,
  "created_at": "2025-03-10 09:30:12",
  "updated_at": "2025-03-10 09:30:12",
  "user": 31,
  "current_campaign": null,
  "campaigns": [3]
}
```

Errores comunes de creación (`400`): `{"username": "Se requiere un nombre de usuario para crear un nuevo agente"}`, `{"username": "El nombre de usuario \"agente05\" ya está en uso"}`, `{"email": "..."}`, `{"agent_id": "El ID de agente \"AGT005\" ya está en uso"}`, `{"sip_extension": "La extensión SIP \"1005\" ya está en uso"}`.

### POST /api/agents/{id}/login/

Inicia la sesión del agente: `status = available` y `logged_in_at = ahora`. Después, `AgentService.login_agent` emite el evento `agent_logged_in` (métricas, alta en colas ACD de Asterisk, eventos en vivo). Si esa parte falla, el login queda hecho igual y el error solo se registra en el log.

Permiso: cualquier usuario autenticado, pero un usuario que no sea admin o supervisor solo puede iniciar su propio perfil (`agent.user == usuario del token`). Sin cuerpo.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/agents/9/login/ \
  -H "Authorization: Bearer <TOKEN>"
```

Respuesta `200`:

```json
{"status": "logged in", "agent_id": "AGT005", "sip_extension": "1005"}
```

Errores: `403 {"error": "No tiene permisos para iniciar sesión de este agente"}`, `404` si el agente no existe, `500 {"error": "..."}` ante error inesperado.

### POST /api/agents/{id}/logout/

Cierra la sesión: `status = offline`, `logged_in_at = null`, `current_calls = 0`, y `AgentService.logout_agent` emite `agent_logged_out` (baja de colas). Mismas reglas de permiso que `login`. Sin cuerpo.

Respuesta `200`: `{"status": "logged out"}`. Errores: `403 {"error": "No tiene permisos para cerrar sesión de este agente"}`, `404`, `500`.

### POST /api/agents/{id}/change_status/

Cambia el estado del agente. Permiso: cualquier usuario autenticado; el código no comprueba que el agente sea del propio usuario. Throttle `agent_action` (10/min por usuario).

| Campo | Tipo | Requerido | Valores |
|---|---|---|---|
| `status` | string | Sí | `available`, `busy`, `oncall`, `break`, `offline`, `wrapup` |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/agents/9/change_status/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"status": "wrapup"}'
```

Respuesta `200`: `{"status": "updated", "new_status": "wrapup"}`.

Errores `400`:

```json
{"error": "Invalid status", "valid_statuses": ["available", "busy", "oncall", "break", "offline", "wrapup"]}
```

`{"error": "El campo status debe ser una cadena de texto.", "valid_statuses": [...]}` si `status` no es texto. `429` al superar 10 cambios por minuto.

Esta acción solo guarda el estado en el modelo; no llama a `AgentService`, por lo que no pausa ni reanuda al agente en las colas de Asterisk.

### POST /api/agents/{id}/start_break/

Pone al agente en `break`. Permiso: autenticado (sin comprobación de propietario). Throttle `agent_action`.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `reason` | string | No (por defecto `personal`) | Solo se devuelve en la respuesta; no se guarda. Los códigos válidos se consultan en `/api/break-reasons/`. |

Respuesta `200`: `{"status": "break started", "reason": "almuerzo"}`.

### POST /api/agents/{id}/end_break/

Devuelve al agente a `available`. Permiso: autenticado. Throttle `agent_action`. Sin cuerpo.

Respuesta `200`: `{"status": "break ended", "new_status": "available"}`.

### GET /api/agents/{id}/stats/

Métricas del día del agente. Permiso: autenticado.

```json
{
  "agent_id": "AGT005",
  "status": "available",
  "is_available": true,
  "calls_today": 14,
  "talk_time_today": 2310,
  "available_time_today": 5400,
  "break_time_today": 900,
  "oncall_time_today": 2450,
  "wrapup_time_today": 420,
  "session_duration": 9800,
  "occupancy": 52.3,
  "logged_in_at": "2025-03-10 07:58:03"
}
```

Tiempos en segundos. `session_duration` se calcula desde `logged_in_at`; `occupancy` es `(oncall + talk + wrapup) / session_duration * 100` (ver [Glosario](../general/glosario.md)).

### POST /api/agents/{id}/save_disposition/

Guarda la calificación (disposición) de una llamada desde la consola del agente. Permiso: autenticado; el agente se toma del `{id}` de la URL. Throttle `agent_action`.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `call_id` | string | No | `call_id` de la llamada (no el ID numérico). Si existe, debe pertenecer al agente. |
| `campaign_id` | integer | Con `disposition_code` | El agente debe estar asignado a la campaña. |
| `disposition_code` | string | Con `campaign_id` | `code` de una calificación de esa campaña. |
| `notes` | string | No | Se limpian etiquetas HTML (bleach). |
| `form_data` | objeto | No | Respuestas del formulario de gestión (`{"campo": "valor"}`); cada valor se limpia de HTML. |
| `callback_date` | string ISO 8601 | No | Si la calificación tiene `requires_callback`, intenta crear una devolución de llamada (ver limitación más abajo). |
| `contact_id` | integer | No | Si llega con `form_data`, se fusiona en `custom_fields` del contacto. |

Efectos, en este orden: actualiza `disposition`, `notes` y `metadata.form_data` de la llamada; intenta crear un `CallbackRequest` si corresponde; actualiza `custom_fields` del contacto.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/agents/9/save_disposition/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"call_id": "WEB-20250310101500-1a2b3c4d", "campaign_id": 3, "disposition_code": "VENTA", "notes": "Aceptó la renovación", "contact_id": 812, "form_data": {"interes": "alto"}}'
```

Respuesta `200`:

```json
{"status": "disposition saved", "disposition": "Venta", "callback_created": false}
```

`callback_created` refleja `requires_callback` de la calificación (puede ser `true` aunque no se haya enviado `callback_date`).

Errores:

| Código | Cuerpo |
|---|---|
| `403` | `{"error": "Agent is not assigned to this campaign"}` |
| `403` | `{"error": "Call does not belong to this agent"}` |
| `404` | `{"error": "Campaign 3 not found"}` |
| `400` | `{"error": "Disposition VENTA not found for campaign 3"}` |
| `429` | Más de 10 peticiones por minuto. |

Un `call_id` inexistente se ignora sin error. Un `callback_date` con formato inválido produce un `500`.

Limitación actual del código: al crear la devolución de llamada, la vista pasa `contact_id` a `CallbackRequest.objects.create()`, pero el modelo `CallbackRequest` no tiene campo `contact`. Por eso, con una calificación que tiene `requires_callback = true` y un `callback_date`, la petición termina en `500` después de haber guardado la calificación en la llamada, y el callback no se crea. Hasta que se corrija, cree el callback con `POST /api/callbacks/` (ver [campanas-y-contactos.md](./campanas-y-contactos.md)).

### GET /api/agents/next_available/

Propone el siguiente `agent_id` (mismo prefijo del último, numeración con 3 dígitos) y la siguiente `sip_extension` libre (por defecto `AGT001` y `100`). Permiso: autenticado.

```json
{"agent_id": "AGT006", "sip_extension": "1006"}
```

### POST /api/agents/check_availability/

Verifica si un código o una extensión están libres. Permiso: `admin` o `supervisor` (es `POST` y hereda el permiso del ViewSet).

| Campo | Tipo | Requerido |
|---|---|---|
| `agent_id` | string | No |
| `sip_extension` | string | No |

Respuesta `200` (solo incluye las claves consultadas):

```json
{"agent_id_available": false, "sip_extension_available": true}
```

### POST /api/agents/hangup/

Cuelga una llamada activa por `call_id` vía AMI. Tiene la misma lógica que `POST /api/calls/hangup/` (ver [telefonia.md](./telefonia.md)), pero aquí hereda el permiso del ViewSet: solo `admin` y `supervisor` (un agente recibe `403`). Los agentes deben usar `/api/calls/hangup/`.

| Campo | Tipo | Requerido |
|---|---|---|
| `call_id` | string | Sí |

## Grupos de agentes: `/api/agent-groups/`

`AgentGroupViewSet` (`ModelViewSet`), permiso `IsAdminOrSupervisorOrReadOnly`: lectura para cualquier autenticado, escritura y acciones para `admin` y `supervisor`. Los grupos también se usan como "skills requeridos" de campañas (`required_skills`).

| Acción | Método y ruta |
|---|---|
| list | `GET /api/agent-groups/` |
| create | `POST /api/agent-groups/` |
| retrieve | `GET /api/agent-groups/{id}/` |
| update | `PUT /api/agent-groups/{id}/` |
| partial_update | `PATCH /api/agent-groups/{id}/` |
| destroy | `DELETE /api/agent-groups/{id}/` |

Filtros: `is_active`; `search` sobre `name` y `description`. El usuario que crea queda en `created_by` (no se expone en la respuesta).

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Solo lectura. |
| `name` | string | Obligatorio, único. |
| `description` | string | Opcional. |
| `agents` | lista de IDs | IDs de agentes (clave primaria). |
| `agent_count` | integer | Solo lectura. |
| `is_active` | boolean | Por defecto `true`. |
| `created_at`, `updated_at` | datetime | Solo lectura. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/agent-groups/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Cobranza nivel 2", "description": "Agentes con experiencia en cobranza", "agents": [9, 11]}'
```

```json
{
  "id": 4,
  "name": "Cobranza nivel 2",
  "description": "Agentes con experiencia en cobranza",
  "agents": [9, 11],
  "agent_count": 2,
  "is_active": true,
  "created_at": "2025-03-10 10:02:00",
  "updated_at": "2025-03-10 10:02:00"
}
```

### POST /api/agent-groups/{id}/add_agent/ y /remove_agent/

Agrega o retira un agente del grupo. Rol `admin` o `supervisor`.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `agent_id` | integer | Sí | Clave primaria del agente (no el código `AGT...`). |

Respuesta `200`:

```json
{"success": true, "message": "Agente AGT005 agregado al grupo Cobranza nivel 2"}
```

Error `404 {"error": "Agente no encontrado"}`.

## Razones de pausa: `/api/break-reasons/`

`AgentBreakReasonViewSet` (`ModelViewSet`), permiso `IsAdminOrSupervisorOrReadOnly`. Las usan la consola del agente y el reporte de pausas.

| Acción | Método y ruta |
|---|---|
| list | `GET /api/break-reasons/` |
| create | `POST /api/break-reasons/` |
| retrieve | `GET /api/break-reasons/{id}/` |
| update | `PUT /api/break-reasons/{id}/` |
| partial_update | `PATCH /api/break-reasons/{id}/` |
| destroy | `DELETE /api/break-reasons/{id}/` |

Filtros: `is_active`, `is_paid`; `search` sobre `name` y `code`; `ordering` por `order` o `name` (por defecto `order`).

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Solo lectura. |
| `name` | string | Obligatorio, único. |
| `code` | string | Obligatorio, único (máx. 20). |
| `is_paid` | boolean | Por defecto `true`. |
| `max_duration` | integer o null | Minutos máximos; `null` es sin límite. |
| `order` | integer | Orden de presentación. |
| `is_active` | boolean | |
| `created_at` | datetime | Solo lectura. |

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/break-reasons/?is_active=true" \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {"id": 1, "name": "Almuerzo", "code": "almuerzo", "is_paid": false, "max_duration": 60, "order": 1, "is_active": true, "created_at": "2025-01-05 08:00:00"},
    {"id": 2, "name": "Baño", "code": "bano", "is_paid": true, "max_duration": 10, "order": 2, "is_active": true, "created_at": "2025-01-05 08:00:00"}
  ]
}
```

## Historial de estados

El modelo `AgentStatusHistory` (estados con inicio, fin, duración y motivo) no tiene un endpoint REST propio. Sus datos se consultan a través de los reportes de agentes y pausas ([reportes.md](./reportes.md)) y del monitor de supervisión ([supervisor.md](./supervisor.md)). Lo alimentan el listener de eventos AMI y `AgentService`; la acción `change_status` de esta API no crea registros de historial.

Véase también: [Glosario](../general/glosario.md), [Desarrollo del backend](../desarrollo/backend.md).
