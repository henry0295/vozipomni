# Telefonía

Endpoints de llamadas, troncales SIP, enrutamiento, extensiones, IVR y recursos de Asterisk, credenciales del softphone WebRTC, política antifraude y funciones de contact center sobre la llamada en curso (screen pop, transferencia, conferencia).

Código fuente:

- `backend/apps/api/viewsets.py`: `CallViewSet` en `/api/calls/`.
- `backend/apps/telephony/urls.py` (montado en `/api/telephony/`): `views.py`, `webrtc_views.py`, `security_views.py`.
- `backend/apps/api/urls.py`: `/api/trunks/` (mismo `SIPTrunkViewSet`) y rutas `/api/cc/...` de `backend/apps/api/cc_viewsets.py`.

Convenciones comunes: [README.md](./README.md). Colas: [colas.md](./colas.md). Supervisión (escucha, susurro, irrupción): [supervisor.md](./supervisor.md). Grabaciones: [grabaciones-y-calidad.md](./grabaciones-y-calidad.md).

Los cambios en troncales, rutas, extensiones, IVR, buzones, música en espera, condiciones de horario y destinos personalizados regeneran la configuración de Asterisk y la recargan por AMI (en `perform_*` o en señales `post_save`/`post_delete`). Si Asterisk no está disponible, el registro se guarda igual y el error queda en el log.

No existe un endpoint REST de "click-to-call" u originate de llamadas para agentes: el softphone WebRTC marca por SIP (JsSIP) y registra la llamada con `POST /api/calls/`.

## Resumen

| Recurso | Ruta | Permiso |
|---|---|---|
| Llamadas (con control por rol) | `/api/calls/` | Ver detalle |
| Llamadas (CRUD simple) | `/api/telephony/calls/` | Autenticado |
| Troncales SIP | `/api/trunks/` y `/api/telephony/trunks/` | admin |
| IVR | `/api/telephony/ivr/` | admin |
| Extensiones | `/api/telephony/extensions/` | Lectura: autenticado. Escritura: admin |
| Rutas entrantes | `/api/telephony/inbound-routes/` | admin |
| Rutas salientes | `/api/telephony/outbound-routes/` | admin |
| Buzones de voz | `/api/telephony/voicemail/` | admin |
| Música en espera | `/api/telephony/music-on-hold/` | admin |
| Condiciones de horario | `/api/telephony/time-conditions/` | admin |
| Destinos personalizados | `/api/telephony/custom-destinations/` | admin |
| Credenciales WebRTC | `/api/telephony/webrtc-credentials/` | Autenticado |
| Validación de ticket SIP WS | `/api/telephony/sip-ws-auth/` | Pública (uso de nginx) |
| Seguridad y antifraude | `/api/telephony/security/...` | admin |
| Screen pop, transferencia, conferencia | `/api/cc/...` | Autenticado |

## Llamadas: `/api/calls/`

`CallViewSet` de `backend/apps/api/viewsets.py`. Es el recurso que usan la consola del agente, el historial y los reportes.

Permisos:

| Rol | Alcance |
|---|---|
| `admin`, `supervisor` | Todas las llamadas, lectura y escritura. |
| `analyst` | Todas las llamadas, solo lectura. Por código también puede usar `create`; `hangup` pasa el permiso pero exige perfil de agente dueño de la llamada. |
| `agent` | Solo sus llamadas (`agent.user = usuario del token`) en todas las operaciones, incluidas `update` y `destroy`. Las de otros agentes responden `404`. |

### CRUD

| Acción | Método y ruta | Notas |
|---|---|---|
| list | `GET /api/calls/` | Paginado. Orden por defecto `-start_time`. |
| create | `POST /api/calls/` | Cualquier autenticado. Registra una llamada iniciada desde WebRTC. |
| retrieve | `GET /api/calls/{id}/` | |
| update | `PUT /api/calls/{id}/` | |
| partial_update | `PATCH /api/calls/{id}/` | |
| destroy | `DELETE /api/calls/{id}/` | `204`. |

Filtros: `direction` (`inbound`, `outbound`), `status`, `agent` (ID), `campaign` (ID). `search` sobre `call_id`, `caller_id`, `called_number`. `ordering` por `start_time` o `talk_time`.

Estados (`status`): `initiated`, `ringing`, `answered`, `completed`, `busy`, `no_answer`, `failed`, `cancelled`, `voicemail`, `machine`, `abandoned`, `transferred`.

Campos (`CallSerializer`, todos los del modelo `Call` más calculados):

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer | Solo lectura. |
| `call_id` | string | Único. Si se omite al crear se genera `WEB-<AAAAMMDDhhmmss>-<8 hex>`. |
| `channel`, `unique_id` | string | Canal y Unique ID de Asterisk. `unique_id` es de solo lectura. |
| `direction` | string | Obligatorio: `inbound` u `outbound`. |
| `status` | string | Por defecto `initiated`. |
| `caller_id`, `called_number` | string | Obligatorios. Solo dígitos con `+` opcional; se quitan espacios y guiones. |
| `agent`, `campaign`, `contact`, `queue`, `disposition` | integer o null | El agente debe estar activo; la campaña debe estar `active` o `paused`. |
| `agent_name`, `campaign_name` | string | Solo lectura. |
| `start_time`, `answer_time`, `end_time` | datetime | Solo lectura (`start_time` se fija al crear). |
| `queue_enter_time` | datetime | |
| `wait_time`, `talk_time`, `hold_time` | integer (s) | Solo lectura. |
| `duration` | integer (s) | Solo lectura: `end_time - start_time`. |
| `duration_formatted` | string | Solo lectura: `HH:MM:SS`. |
| `recording_file` | string | |
| `is_recorded` | boolean | Solo lectura. |
| `transferred`, `transfer_to` | boolean, string | |
| `notes` | string | |
| `metadata` | objeto | Incluye `last_heartbeat`, `quality_metrics`, `client_duration`, `form_data` según el flujo. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/calls/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"direction": "outbound", "caller_id": "1005", "called_number": "3001234567", "agent": 9, "campaign": 3, "contact": 812}'
```

Respuesta `201` (extracto):

```json
{
  "id": 5821,
  "duration": 0,
  "agent_name": "Juan Pérez",
  "campaign_name": "Renovaciones marzo",
  "duration_formatted": "00:00:00",
  "call_id": "WEB-20250310101500-1a2b3c4d",
  "channel": "",
  "unique_id": "",
  "direction": "outbound",
  "status": "initiated",
  "caller_id": "1005",
  "called_number": "3001234567",
  "start_time": "2025-03-10 10:15:00",
  "answer_time": null,
  "end_time": null,
  "wait_time": 0,
  "talk_time": 0,
  "hold_time": 0,
  "is_recorded": false,
  "notes": "",
  "metadata": {},
  "agent": 9,
  "campaign": 3,
  "contact": 812,
  "queue": null,
  "disposition": null
}
```

Errores `400`: `{"caller_id": ["Formato de número inválido"]}`, `{"agent": "El agente no está activo"}`, `{"campaign": "La campaña no está activa"}`, `{"call_id": ["..."]}` si el `call_id` ya existe.

### POST /api/calls/{id}/heartbeat/

El frontend lo envía cada 30 s durante una llamada para detectar llamadas huérfanas. Guarda `metadata.last_heartbeat` y, si llegan, `metadata.quality_metrics` y `metadata.client_duration`.

Permiso: `admin`, `supervisor` o el agente dueño de la llamada. Un `analyst` recibe `403` (es `POST`).

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `quality_metrics` | objeto | No | Métricas del cliente WebRTC (formato libre). |
| `duration` | integer | No | Duración vista por el cliente, en segundos. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/calls/5821/heartbeat/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"duration": 95, "quality_metrics": {"rtt": 42, "jitter": 3, "packets_lost": 0}}'
```

```json
{"status": "ok", "call_id": "WEB-20250310101500-1a2b3c4d", "server_time": "2025-03-10T10:16:35.120000-05:00"}
```

### POST /api/calls/hangup/

Cuelga una llamada por `call_id` con AMI `Hangup`. Permiso: cualquier autenticado; si no es `admin` ni `supervisor` debe tener perfil de agente y ser el dueño de la llamada.

| Campo | Tipo | Requerido |
|---|---|---|
| `call_id` | string | Sí |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/calls/hangup/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"call_id": "WEB-20250310101500-1a2b3c4d"}'
```

Respuestas `200`:

| Situación | Cuerpo |
|---|---|
| Colgada por AMI | `{"status": "success", "message": "Llamada terminada correctamente", "call_id": "..."}` |
| Sin canal registrado | `{"status": "success", "message": "Llamada marcada como completada (sin canal activo)", "call_id": "..."}` |
| AMI falló con excepción | `{"status": "success", "message": "Llamada marcada como completada (error en AMI)", "call_id": "...", "warning": "..."}` |
| Ya terminada (`completed`, `cancelled`, `failed`) | `{"status": "already_ended", "message": "La llamada ya finalizó", "call_id": "..."}` |

En los tres primeros casos la llamada queda `completed` con `end_time`.

Errores: `400 {"error": "Se requiere call_id en el body"}`, `400` si el estado no es colgable (por ejemplo `busy`), `403 {"error": "Usuario no tiene perfil de agente"}`, `403 {"error": "No tiene permisos para colgar esta llamada"}`, `404 {"error": "No se encontró llamada con ID: ..."}`, `500` si AMI responde con error.

## Llamadas (CRUD simple): `/api/telephony/calls/`

`CallViewSet` de `backend/apps/telephony/views.py`. `ModelViewSet` con permiso `IsAuthenticated`, `fields = '__all__'` sin campos calculados y sin restricción por rol: cualquier usuario autenticado, incluidos los agentes, puede listar y modificar todas las llamadas por esta ruta. Filtros: `direction`, `status`, `agent`, `campaign`; `search` por `caller_id`, `called_number`, `call_id`. Para integraciones use `/api/calls/`, que aplica los permisos por rol.

`ordering_fields` incluye `duration`, que es una propiedad y no una columna; `?ordering=duration` produce un error del servidor.

## Troncales SIP: `/api/trunks/` y `/api/telephony/trunks/`

El mismo `SIPTrunkViewSet` está registrado en las dos rutas. Permiso `IsAdminUser` (solo `admin`) para todo, incluidas las acciones. Crear, editar o borrar regenera `pjsip_wizard.conf` y recarga PJSIP.

### CRUD

| Acción | Método y ruta |
|---|---|
| list | `GET /api/telephony/trunks/` |
| create | `POST /api/telephony/trunks/` |
| retrieve | `GET /api/telephony/trunks/{id}/` |
| update | `PUT /api/telephony/trunks/{id}/` |
| partial_update | `PATCH /api/telephony/trunks/{id}/` |
| destroy | `DELETE /api/telephony/trunks/{id}/` |

Campos principales (modelo `SIPTrunk`, `fields = '__all__'`):

| Grupo | Campos |
|---|---|
| Básicos | `name` (único, obligatorio), `description`, `trunk_type` (`nat_provider`, `no_nat_provider`, `pbx_lan`, `corporate`, `custom`) |
| Conexión | `host` (obligatorio), `port` (5060), `protocol` (`udp`, `tcp`, `tls`) |
| Autenticación saliente | `outbound_auth_username`, `outbound_auth_password` (solo escritura), `from_user`, `from_domain` |
| Autenticación entrante | `inbound_auth_username`, `inbound_auth_password` (solo escritura) |
| Registro | `sends_registration` (`true`), `registration_server_uri`, `registration_client_uri`, `registration_retry_interval` (60), `registration_expiration` (3600) |
| Comportamiento SIP | `sends_auth`, `accepts_auth`, `accepts_registrations` |
| Media | `rtp_symmetric`, `force_rport`, `rewrite_contact`, `direct_media`, `codec` (`ulaw,alaw,g729`), `dtmf_mode` (`rfc4733`, `rfc2833`, `inband`, `info`, `auto`) |
| Dialplan y timers | `context` (`from-pstn`, `from-pbx`, `from-trunk`, `custom`), `custom_context`, `timers`, `timers_min_se`, `timers_sess_expires` |
| Qualify | `qualify_enabled`, `qualify_frequency`, `qualify_timeout` |
| Canales y Caller ID | `max_channels` (10), `caller_id`, `caller_id_name` |
| NAT | `local_net`, `external_media_address`, `external_signaling_address` |
| Avanzado | `language` (`es`), `trust_id_inbound`, `trust_id_outbound`, `send_pai`, `send_rpid`, `pjsip_config_custom` |
| Estado (solo lectura) | `is_active` (editable), `is_registered`, `last_registration_time`, `calls_total`, `calls_active`, `calls_successful`, `calls_failed`, `created_at`, `updated_at` |
| Calculados (solo lectura) | `registration_status` (solo en `retrieve`, consulta AMI; `null` en `list`), `registration_detail` (`{text, class, icon}`), `username` (= `outbound_auth_username`), `password` (`"********"` o `""`) |

Las contraseñas de autenticación nunca se devuelven.

Validaciones (`400`): `pjsip_config_custom` obligatorio con `trunk_type = custom`; `registration_server_uri` obligatorio con `sends_registration = true`; `outbound_auth_username` con `sends_auth = true`; `inbound_auth_username` con `accepts_auth = true`.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/telephony/trunks/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "proveedor-principal", "trunk_type": "nat_provider", "host": "sip.proveedor.example", "port": 5060, "protocol": "udp", "sends_registration": true, "registration_server_uri": "sip:sip.proveedor.example", "registration_client_uri": "sip:<USUARIO_SIP>@sip.proveedor.example", "sends_auth": true, "outbound_auth_username": "<USUARIO_SIP>", "outbound_auth_password": "<CLAVE_SIP>", "max_channels": 30}'
```

### GET /api/telephony/trunks/statuses/

Estado de registro de todas las troncales activas en una sola consulta AMI (`PJSIPShowEndpoints` y `PJSIPShowRegistrations`). Respuesta: objeto con el ID de la troncal como clave.

```json
{
  "1": {"status": "Registrado", "class": "success"},
  "2": {"status": "Disponible", "class": "success"},
  "4": {"status": "No Encontrado", "class": "gray", "detail": "Endpoint no encontrado en Asterisk. Regenere la configuración."}
}
```

Valores de `status`: `Registrado`, `No Registrado`, `Rechazado`, `Conectando...`, `Disponible`, `Sin Registro`, `EP sin Registro`, `Inalcanzable`, `Sin Contacto`, `No Encontrado`, `No Configurado`, `Desconectado` (sin AMI), `Error`. `class`: `success`, `warning`, `error`, `gray`.

Si hay troncales sin endpoint, regenera la configuración PJSIP una vez cada 120 s como máximo. Solo se procesa una consulta a la vez: una segunda petición simultánea recibe `429 {"error": "La consulta de estados AMI ya está en progreso"}` (bloqueo de 20 s en caché).

### POST /api/telephony/trunks/regenerate_config/

Regenera `pjsip_wizard.conf` y recarga PJSIP. Sin cuerpo.

Respuesta: `200 {"success": true, "message": "..."}` o `500 {"success": false, "message": "..."}`.

### POST /api/telephony/trunks/force_register_all/

Escribe la configuración, recarga PJSIP, espera 3 s y devuelve el estado de registro de cada troncal activa con `sends_registration = true`.

```json
{
  "success": true,
  "message": "Configuración regenerada y registro forzado",
  "trunk_statuses": {"proveedor-principal": "Registered"}
}
```

### GET /api/telephony/trunks/{id}/preview_config/

Texto PJSIP que se generará para la troncal. Puede incluir las credenciales de la troncal en texto plano.

```json
{"success": true, "trunk_name": "proveedor-principal", "config": "[proveedor-principal]\ntype = wizard\n..."}
```

### POST /api/telephony/trunks/{id}/test_connection/

Consulta el estado en Asterisk. Con `sends_registration = true` revisa el registro; si no, la disponibilidad del endpoint (contactos).

```json
{
  "success": true,
  "trunk": "proveedor-principal",
  "registered": true,
  "available": true,
  "status": "Registered",
  "message": "Estado de registro: Registered",
  "requires_registration": true
}
```

Sin AMI: `503 {"success": false, "message": "No se pudo conectar a Asterisk AMI", "registered": false, "available": false}`.

### POST /api/telephony/trunks/{id}/force_register/

Regenera y recarga, espera 2 s y devuelve el estado de registro de esa troncal: `{"success": true, "message": "Configuración recargada", "status": "Registered", "registered": true}`. Error `400 {"success": false, "message": "Esta troncal no está configurada para registrarse"}` si la troncal no se registra.

## Rutas entrantes: `/api/telephony/inbound-routes/`

`InboundRouteViewSet` (`ModelViewSet`), permiso `admin`. CRUD estándar (`list`, `create`, `retrieve`, `update`, `partial_update`, `destroy`). Filtros: `destination_type`, `is_active`; `search` por `did`, `description`. Orden por defecto `priority`, `did`.

| Campo | Tipo | Descripción |
|---|---|---|
| `did` | string | Número entrante (único). |
| `description` | string | Obligatorio. |
| `destination_type` | string | `ivr`, `queue`, `extension`, `voicemail`, `announcement`, `custom_destination`. |
| `destination` | string | IVR: extensión del IVR. Cola: `name` de la cola. Extensión: número. Buzón: `mailbox`. Destino personalizado: `name`. Anuncio: nombre del audio. |
| `priority` | integer | Por defecto 1. |
| `time_condition` | string | Nombre de la condición de horario (opcional). |
| `is_active` | boolean | |
| `status` | string | Solo lectura: `Activo` / `Inactivo`. |

Se valida que el destino exista y esté activo: `400 {"destination": "La cola seleccionada no existe o está inactiva."}`.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/telephony/inbound-routes/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"did": "6015551234", "description": "Línea principal", "destination_type": "ivr", "destination": "700", "time_condition": "horario-oficina"}'
```

## Rutas salientes: `/api/telephony/outbound-routes/`

`OutboundRouteViewSet` (`ModelViewSet`), permiso `admin`. CRUD estándar. Filtros: `trunk`, `is_active`; `search` por `name`, `pattern`.

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | string | Obligatorio. |
| `pattern` | string | Patrón de Asterisk, por ejemplo `_3XXXXXXXXX`. |
| `trunk` | integer | ID de la troncal. |
| `trunk_name` | string | Solo lectura. |
| `prepend` | string | Dígitos a anteponer. |
| `prefix` | string | Dígitos a eliminar. |
| `callerid_prefix` | string | |
| `priority` | integer | Menor valor se evalúa primero. |
| `ring_time` | integer | Segundos (60). |
| `dial_options` | string | Opciones de `Dial()` (`trg`). |
| `is_active` | boolean | |
| `status` | string | Solo lectura. |

Todas las llamadas por rutas salientes pasan por la política antifraude del dialplan (ver [Seguridad y antifraude](#seguridad-y-antifraude)).

## Extensiones: `/api/telephony/extensions/`

`ExtensionViewSet`. `list` y `retrieve` para cualquier autenticado; el resto solo `admin`. Filtros: `extension_type` (`PJSIP`, `WEBRTC`), `is_active`; `search` por `extension`, `name`. Orden por defecto `extension`.

| Campo | Tipo | Descripción |
|---|---|---|
| `extension` | string | Único. |
| `name` | string | Obligatorio. |
| `extension_type` | string | `PJSIP` (softphone) o `WEBRTC` (navegador). |
| `secret` | string | Solo escritura; se devuelve `"********"`. Si se omite se genera una de 12 caracteres. Enviar `"********"` en una edición conserva la actual. |
| `context` | string | `from-internal` (por defecto), `from-external`, `custom`. |
| `transport` | string | `transport-udp`, `transport-tcp`, `transport-wss`. Por defecto según el tipo. |
| `callerid` | string | Por defecto `"<nombre>" <extensión>`. |
| `email` | string | |
| `voicemail_enabled` | boolean | |
| `max_contacts` | integer | 1. |
| `codecs` | string | Por defecto `opus,ulaw,alaw` (WEBRTC) o `ulaw,alaw,g729` (PJSIP). |
| `is_active` | boolean | |
| `status` | string | Solo lectura. |

Las extensiones de los agentes se crean y sincronizan solas al crear o editar el agente (ver [usuarios-y-agentes.md](./usuarios-y-agentes.md)).

### POST /api/telephony/extensions/{id}/reload_config/

Regenera la configuración de Asterisk y recarga `res_pjsip.so`, `chan_pjsip.so` y el dialplan. Rol `admin`.

```json
{"success": true, "message": "Configuración de extensión 1005 recargada"}
```

## IVR: `/api/telephony/ivr/`

`IVRViewSet` (`ModelViewSet`), permiso `admin`. CRUD estándar.

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | string | Único. |
| `description` | string | |
| `extension` | string | Único; es la referencia usada por rutas entrantes y otros IVR. |
| `welcome_message` | string | Obligatorio. Audio de Asterisk sin extensión (por ejemplo `custom/bienvenida`). |
| `spoken` | string | Audio adicional antes del menú. |
| `invalid_message`, `timeout_message` | string | |
| `timeout` | integer | 1 a 60 s. |
| `timeout_retries`, `invalid_retries` | integer | 1 a 10. `max_attempts` se calcula como el mayor. |
| `timeout_destination_type`, `timeout_destination` | string | Obligatorios. |
| `invalid_destination_type`, `invalid_destination` | string | Obligatorios. |
| `menu_options` | objeto | Obligatorio, al menos una tecla. |
| `is_active` | boolean | |

Tipos de destino: `queue`, `extension`, `ivr`, `voicemail`, `announcement`, `custom_destination`. Cada destino debe existir y estar activo; un IVR no puede apuntar a sí mismo.

`menu_options` usa teclas `0`-`9`, `*`, `#`:

```json
{
  "1": {"type": "queue", "destination": "ventas", "spoken": ""},
  "2": {"type": "extension", "destination": "1005", "spoken": ""},
  "0": {"type": "ivr", "destination": "701", "spoken": ""}
}
```

Se acepta el formato antiguo `{"1": "100"}`, que se normaliza a `{"type": "extension", "destination": "100", "spoken": ""}`.

### GET /api/telephony/ivr/audio_catalog/

Lista los audios disponibles para `Playback()` en los directorios de sonidos de Asterisk (`.wav`, `.gsm`, `.ulaw`, `.alaw`, `.sln`, `.mp3`) más los ya usados en IVR. Query opcional `source` (solo se devuelve en la respuesta).

```json
{
  "source": "internal",
  "allow_manual": true,
  "count": 2,
  "items": [
    {"label": "custom/bienvenida", "value": "custom/bienvenida"},
    {"label": "es/vm-goodbye", "value": "es/vm-goodbye"}
  ]
}
```

### POST /api/telephony/ivr/upload_audio/

Sube un audio a `sounds/custom/`. `multipart/form-data`.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `file` | archivo | Sí | `.wav`, `.gsm`, `.ulaw`, `.alaw`, `.sln` o `.mp3`. |
| `name` | string | No | Nombre sin extensión; se normaliza a minúsculas, dígitos, `_` y `-`. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/telephony/ivr/upload_audio/ \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@bienvenida.wav" -F "name=bienvenida"
```

Respuesta `201`:

```json
{
  "success": true,
  "filename": "bienvenida.wav",
  "saved_path": "/var/lib/asterisk/sounds/custom/bienvenida.wav",
  "playback_name": "custom/bienvenida",
  "message": "Audio cargado correctamente como custom/bienvenida"
}
```

Errores: `400 {"detail": "..."}` (sin archivo, formato no soportado, vacío), `500` si no se puede escribir.

## Buzones de voz: `/api/telephony/voicemail/`

`VoicemailViewSet` (`ModelViewSet`), permiso `admin`. CRUD estándar. Filtros: `is_active`; `search` por `mailbox`, `name`, `email`.

Campos: `mailbox` (único), `name`, `email` (obligatorio), `password` (solo escritura; se devuelve `"****"`), `email_attach`, `email_delete`, `max_messages`, `is_active`; solo lectura `status` y `messages` (cantidad de archivos en `INBOX`).

`GET /api/telephony/voicemail/{id}/messages/` devuelve `{"mailbox": "1005", "messages": [], "count": 0}`. La lectura real de mensajes no está implementada (la lista siempre llega vacía).

## Música en espera: `/api/telephony/music-on-hold/`

`MusicOnHoldViewSet` (`ModelViewSet`), permiso `admin`. CRUD estándar. Filtros: `mode`, `is_active`; `search` por `name`, `description`.

Campos: `name` (único), `description` (obligatorio), `mode` (`files`, `quietmp3`, `custom`), `directory`, `application`, `is_active`; solo lectura `status` y `files` (cantidad de archivos).

`GET /api/telephony/music-on-hold/{id}/files/`:

```json
{"name": "default", "directory": "/var/lib/asterisk/moh", "files": [{"name": "macroform-cold_day.wav", "size": 1323052}], "count": 1}
```

## Condiciones de horario: `/api/telephony/time-conditions/`

`TimeConditionViewSet` (`ModelViewSet`), permiso `admin`. CRUD estándar. Filtros: `is_active`; `search` por `name`.

Campos: `name` (único), `time_groups` (lista JSON), `true_destination_type`, `true_destination`, `false_destination_type`, `false_destination`, `is_active`; solo lectura `status` y `times` (resumen del primer grupo). Tipos de destino: los mismos de las rutas entrantes.

### GET /api/telephony/time-conditions/{id}/evaluate/

Indica si la condición se cumple ahora y a qué destino iría la llamada. Cada elemento de `time_groups` se interpreta como `{"days": "mon-fri", "start_time": "08:00", "end_time": "18:00", "name": "..."}`; `days` acepta `mon-fri`, `mon-sat`, `sat-sun`, listas `mon,wed,fri` o un día.

```json
{
  "name": "horario-oficina",
  "matches": true,
  "matched_group": "mon-fri",
  "current_day": "mon",
  "current_time": "10:20",
  "current_destination_type": "ivr",
  "current_destination": "700"
}
```

Usa `datetime.now()`, es decir, la hora local del contenedor del backend, que puede no coincidir con `America/Bogota`.

## Destinos personalizados: `/api/telephony/custom-destinations/`

`CustomDestinationViewSet` (`ModelViewSet`), permiso `admin`. CRUD estándar. Filtros: `is_active`; `search` por `name`, `context`, `extension`.

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | string | Único; es la referencia desde rutas, IVR y condiciones. |
| `description` | string | |
| `context`, `extension` (`s`), `priority` (1) | string, string, integer | Nodo del dialplan. |
| `failover_context`, `failover_extension`, `failover_priority` | | Destino si falla (opcional). |
| `is_active` | boolean | |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/telephony/custom-destinations/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "encuesta-post-llamada", "context": "encuesta", "extension": "s", "priority": 1}'
```

## Credenciales WebRTC

### GET /api/telephony/webrtc-credentials/

`WebRTCCredentialsView`, permiso `IsAuthenticated`. Entrega al softphone los servidores ICE y un ticket firmado para abrir el WebSocket SIP.

```bash
curl -s https://<IP_DEL_SERVIDOR>/api/telephony/webrtc-credentials/ \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{
  "ice_servers": [
    {"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]},
    {
      "urls": ["turn:<IP_DEL_SERVIDOR>:3478?transport=udp", "turn:<IP_DEL_SERVIDOR>:3478?transport=tcp"],
      "username": "1741650000:12",
      "credential": "<CREDENCIAL_TURN>"
    }
  ],
  "turn_enabled": true,
  "turn_ttl": 43200,
  "ws_ticket": "<TICKET_WS>",
  "ws_ticket_ttl": 86400
}
```

- TURN: solo si `TURN_SECRET` está definido. Usuario `<expiración unix>:<id de usuario>` y credencial HMAC-SHA1 con el secreto compartido de coturn (TURN REST). Vida `TURN_CREDENTIAL_TTL` (12 h por defecto). Host: `TURN_HOST`, o el de `PUBLIC_BASE_URL`, o el host de la petición. Puerto `TURN_PORT` (3478).
- `ws_ticket`: `django.core.signing` con el ID del usuario; vida `SIP_WS_TICKET_TTL` (24 h por defecto). El cliente abre `wss://<IP_DEL_SERVIDOR>/sip/ws?ticket=<TICKET_WS>`.

### GET /api/telephony/sip-ws-auth/

`SipWsAuthView`, uso interno. nginx la invoca con `auth_request` (ubicación interna `/_sip_ws_auth`) en cada handshake de `/sip/ws` y `/asterisk/ws`, pasando la URI original en `X-Original-URI`. Sin autenticación ni throttling.

- Toma `ticket` del query string de `X-Original-URI` o, si falta, de `?ticket=` de la propia petición.
- `204` con cabecera `X-Vozip-User: <id>` si el ticket es válido, no venció y el usuario está activo.
- `401` sin cuerpo en caso contrario (se registra la IP de `X-Real-IP`).

La ruta también es alcanzable desde fuera por `location /api/`; solo confirma si un ticket es válido.

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://<IP_DEL_SERVIDOR>/api/telephony/sip-ws-auth/?ticket=<TICKET_WS>"
```

## Seguridad y antifraude

`backend/apps/telephony/security_views.py`. Todo requiere rol `admin`. La política es un registro único (`TelephonySecurityPolicy`) que se aplica en el dialplan (`[vozip-outbound-policy]`) y en el marcador.

### GET, PUT, PATCH /api/telephony/security/policy/

`GET` devuelve la política. `PUT` y `PATCH` hacen actualización parcial (ambos con `partial=True`), guardan quién la modificó y ejecutan `apply_policy()`.

| Campo | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `block_international` | boolean | `true` | Bloquea números con `00` o `+` distinto al indicativo propio. |
| `home_country_code` | string | `57` | Solo dígitos. |
| `blocked_prefixes` | string | `01900` y `1900` | Uno por línea (o separados por coma). |
| `allowed_prefixes` | string | vacío | Lista blanca: si tiene valores, solo se permiten esos prefijos. |
| `max_number_length` | integer | 15 | 7 a 20; 0 sin límite. |
| `max_concurrent_outbound` | integer | 0 | Salientes simultáneas totales; 0 sin límite. |
| `enforce_trunk_channels` | boolean | `true` | Respeta `max_channels` de cada troncal. |
| `max_calls_per_extension_hour` | integer | 0 | 0 sin límite. |
| `alert_emails` | string | vacío | Correos de alerta, uno por línea; vacío envía a los administradores activos. |
| `alert_calls_per_10min` | integer | 150 | 0 desactiva. |
| `alert_international_per_hour` | integer | 5 | 0 desactiva. |
| `alert_blocked_per_10min` | integer | 10 | 0 desactiva. |
| `blocked_list`, `allowed_list` | lista | | Solo lectura: prefijos normalizados. |
| `updated_at`, `updated_by_name` | | | Solo lectura. |

```bash
curl -s -X PATCH https://<IP_DEL_SERVIDOR>/api/telephony/security/policy/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"block_international": true, "blocked_prefixes": "01900\n1900\n0088", "max_concurrent_outbound": 60}'
```

Respuesta `200`: la política más `apply_result`:

```json
{
  "block_international": true,
  "home_country_code": "57",
  "blocked_prefixes": "01900\n1900\n0088",
  "allowed_prefixes": "",
  "max_number_length": 15,
  "max_concurrent_outbound": 60,
  "enforce_trunk_channels": true,
  "max_calls_per_extension_hour": 0,
  "alert_emails": "",
  "alert_calls_per_10min": 150,
  "alert_international_per_hour": 5,
  "alert_blocked_per_10min": 10,
  "updated_at": "2025-03-10 11:02:45",
  "updated_by_name": "Administrador",
  "blocked_list": ["01900", "1900", "0088"],
  "allowed_list": [],
  "apply_result": {"dialplan": true, "reloaded": true, "published": true}
}
```

Errores `400`: `{"home_country_code": ["Indicativo numérico, ej: 57"]}`, `{"alert_emails": ["Correo inválido: ..."]}`, `{"max_number_length": ["Entre 7 y 20 dígitos (0 = sin límite)."]}`.

### POST /api/telephony/security/policy/test/

Evalúa un número con la misma lógica del dialplan, sin marcar.

| Campo | Tipo | Requerido |
|---|---|---|
| `number` | string | Sí |

```json
{"number": "+14155550100", "allowed": false, "reason": "international", "reason_label": "Internacional bloqueada"}
```

Motivos posibles de `reason`: `invalid` (sin dígitos, sin etiqueta), `too_long`, `international`, `blocked_prefix`, `not_allowed`; vacío si se permite.

### POST /api/telephony/security/policy/apply/

Regenera el dialplan, recarga Asterisk y publica la política para el marcador. Sin cuerpo. Respuesta `{"dialplan": true, "reloaded": true, "published": true}` con `200`, o `500` si no se pudo escribir el dialplan (con `error`).

### GET /api/telephony/security/summary/

Contadores de las últimas 24 horas:

```json
{
  "events_24h": 18,
  "critical_24h": 1,
  "by_type": {"international": 12, "blocked_prefix": 5, "alert_international": 1},
  "outbound_24h": 1432,
  "international_24h": 3
}
```

### GET /api/telephony/security/events/

`SecurityEventViewSet` (`ReadOnlyModelViewSet`): `list` (paginado) y `retrieve` (`/security/events/{id}/`). Orden `-created_at`.

| Query | Tipo | Descripción |
|---|---|---|
| `event_type` | string | `international`, `blocked_prefix`, `not_allowed`, `too_long`, `trunk_full`, `global_limit`, `extension_rate`, `dialer_blocked`, `alert_spike`, `alert_international`, `alert_blocked`. |
| `severity` | string | `info`, `warning`, `critical`. |
| `days` | integer | Ventana hacia atrás, 1 a 90 (por defecto 7). |

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 311,
      "event_type": "international",
      "event_type_display": "Internacional bloqueada",
      "severity": "warning",
      "number": "+14155550100",
      "trunk": "proveedor-principal",
      "source": "1005",
      "detail": "",
      "notified": false,
      "created_at": "2025-03-10 09:41:07"
    }
  ]
}
```

## Funciones sobre la llamada en curso: `/api/cc/`

`backend/apps/api/cc_viewsets.py`. Permiso `IsAuthenticated` en todas.

Nota de seguridad: `consultive-transfer` y `conference` insertan `channel`, `extension` y `third_party` directamente en comandos AMI, sin validar formato ni comprobar que el canal pertenezca al usuario. Cualquier usuario autenticado puede redirigir u originar canales.

### GET /api/cc/screen-pop/

Datos del contacto y últimas llamadas de un número, para mostrar al recibir una llamada. Compara por los últimos 10 dígitos contra `phone`, `phone2` y `phone3`.

| Query | Tipo | Requerido |
|---|---|---|
| `phone` | string | Sí |

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/cc/screen-pop/?phone=573001234567" \
  -H "Authorization: Bearer <TOKEN>"
```

```json
{
  "phone": "573001234567",
  "contact": {
    "id": 812,
    "full_name": "Carlos Ramírez",
    "phone": "+573001234567",
    "phone2": "",
    "phone3": "",
    "email": "carlos@example.com",
    "company": "Ejemplo SAS",
    "city": "Bogotá",
    "country": "CO",
    "is_vip": false,
    "dnc_opt_out": false,
    "status": "callback",
    "attempts": 2,
    "custom_fields": {"interes": "alto"},
    "notes": [{"note": "Cliente prefiere la tarde", "created_at": "2025-03-08T15:10:00-05:00", "is_important": true}]
  },
  "call_history": [
    {"call_id": "WEB-20250308150500-9f8e7d6c", "direction": "outbound", "start_time": "2025-03-08T15:05:00-05:00", "duration": 185, "disposition": "Volver a llamar", "agent": "Juan Pérez", "campaign": "Renovaciones marzo"}
  ],
  "is_known": true
}
```

`contact` es `null` e `is_known` es `false` si el número no existe. Error `400 {"error": "phone requerido"}`.

### GET /api/cc/available-agents/

Agentes con `status = available` y WebRTC habilitado, para elegir destino de transferencia.

```json
{
  "available_agents": [
    {"id": 11, "name": "María Torres", "sip_extension": "1007", "status": "available", "calls_today": 9}
  ],
  "count": 1
}
```

### POST /api/cc/consultive-transfer/

Transfiere la llamada.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `channel` | string | Sí | Canal a transferir, por ejemplo `PJSIP/1005-0000002a`. |
| `extension` | string | Sí | Extensión destino. |
| `blind` | boolean | No (por defecto `true`) | `true`: AMI `Redirect` inmediato al contexto `from-internal`. `false`: origina una llamada a `PJSIP/<extension>` con la variable `TRANSFER_SOURCE_CHANNEL`; luego hay que completar con `blind=true`. |
| `caller_id` | string | No | Solo en modo consultivo (por defecto `Transferencia`). |

Respuesta ciega:

```json
{"success": true, "response": "Response: Success\r\n...", "transfer_type": "blind"}
```

Respuesta consultiva:

```json
{
  "status": "consultive_leg_initiated",
  "transfer_type": "consultive",
  "channel": "PJSIP/1005-0000002a",
  "extension": "1007",
  "message": "Llamada originada al agente receptor. Llame a POST /api/cc/consultive-transfer/ con blind=true para completar la transferencia cuando esté listo."
}
```

Errores: `400 {"error": "channel y extension requeridos"}`, `503` sin AMI, `500`. En modo ciego un fallo de AMI llega con `200` y `"success": false`.

### POST /api/cc/conference/

Conferencia a tres: redirige el canal actual a `ConfBridge` y origina una llamada al tercero hacia la misma sala.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `channel` | string | Sí | Canal actual. |
| `third_party` | string | Sí | Número o extensión del tercero (se marca como `Local/<third_party>@from-internal`). |
| `caller_id` | string | No | Por defecto `ConferenceBridge`. |
| `conference_id` | string | No | Por defecto `conf-<timestamp>`. |

```json
{"status": "conference_initiated", "conference_id": "conf-1741623600", "third_party": "3009876543"}
```

Errores: `400 {"error": "channel y third_party requeridos"}`, `503` sin AMI, `500`.

## Acciones AMI expuestas

Resumen de las operaciones de la API que ejecutan acciones en Asterisk por AMI:

| Endpoint | Acción AMI |
|---|---|
| `POST /api/calls/hangup/`, `POST /api/agents/hangup/` | `Hangup` |
| `POST /api/cc/consultive-transfer/` | `Redirect` (ciega) u `Originate` (consultiva) |
| `POST /api/cc/conference/` | `Redirect` + `Originate` a `ConfBridge` |
| `GET /api/telephony/trunks/statuses/`, `test_connection`, `force_register*`, `retrieve` de troncal | `PJSIPShowEndpoints`, `PJSIPShowRegistrations` |
| Recargas (`regenerate_config`, `reload_config`, `security/policy/apply/`, CRUD de configuración) | `Reload` de módulos y dialplan |
| `POST /api/agents/{id}/login/` y `logout/` | Alta y baja en colas mediante eventos de `AgentService` |

La escucha silenciosa, el susurro y la irrupción (ChanSpy) están en [supervisor.md](./supervisor.md).

Véase también: [Glosario](../general/glosario.md), [Desarrollo del backend](../desarrollo/backend.md).
