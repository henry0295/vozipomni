# Mensajería omnicanal

Endpoints de la bandeja omnicanal (WhatsApp, correo, chat web, Facebook Messenger e Instagram): canales, conversaciones, mensajes, plantillas y líneas de WhatsApp, envíos masivos, etiquetas, respuestas rápidas, cuentas de correo, widgets de chat web, páginas de Meta, métricas y la API pública del widget.

Código fuente:

- `backend/apps/messaging/urls.py`, montado en `/api/messaging/` desde `backend/apps/api/urls.py`.
- `backend/apps/messaging/views.py`: canales, conversaciones, mensajes, WhatsApp (proveedores, líneas, plantillas) y webhook de Meta.
- `backend/apps/messaging/views_omni.py`: etiquetas, respuestas rápidas, envíos masivos, correo, chat web, páginas de Meta, métricas y API pública del widget.
- `backend/apps/messaging/routing.py`: ingreso de mensajes entrantes, asignación automática y respuestas automáticas.
- `backend/apps/messaging/realtime.py`: notificaciones en tiempo real (ver [websockets.md](./websockets.md)).

Convenciones comunes: [README.md](./README.md). Webhook de Meta (entrante): [webhooks.md](./webhooks.md). Configuración funcional: [Administración omnicanal](../administracion/omnicanal.md). Términos: [Glosario](../general/glosario.md).

## Resumen

| Recurso | Ruta base (`/api/messaging/...`) | Lectura | Escritura |
|---|---|---|---|
| Canales | `channels/` | Autenticado | `admin`, `supervisor` |
| Conversaciones | `conversations/` | Autenticado (agente: propias y sin asignar) | Ver cada acción |
| Mensajes | `messages/{id}/media/`, `messages/{id}/retry/` | Autenticado (mismo alcance) | Autenticado |
| Proveedores de WhatsApp (Apps de Meta) | `whatsapp/providers/` | `admin` | `admin` |
| Líneas de WhatsApp | `whatsapp/lines/` | Autenticado (agente: solo activas y conectadas) | `admin` |
| Plantillas de WhatsApp | `whatsapp/templates/` | Autenticado (agente: solo aprobadas) | `admin` |
| Envíos masivos | `whatsapp/broadcasts/` | `admin`, `supervisor` | `admin`, `supervisor` |
| Etiquetas | `tags/` | Autenticado | `admin`, `supervisor` |
| Respuestas rápidas | `quick-replies/` | Autenticado | `admin`, `supervisor` |
| Cuentas de correo | `email/accounts/` | `admin`, `supervisor` | `admin` |
| Widgets de chat web | `webchat/widgets/` | `admin`, `supervisor` | `admin` |
| Páginas de Messenger e Instagram | `meta/pages/` | `admin`, `supervisor` | `admin` |
| Métricas de chat | `metrics/` | `admin`, `supervisor`, `analyst` | No aplica |
| API pública del widget | `webchat/public/<key>/...` | Pública (límite 60/min por IP) | Pública |
| Webhook de Meta (alias) | `webhooks/meta/<APP_ID>/` | Pública | Pública |

"Supervisor" en esta app significa `admin`, `supervisor` o superusuario (`_is_supervisor()`).

## Canales: `/api/messaging/channels/`

`ChannelViewSet`, CRUD completo. Permiso `IsAdminOrSupervisorOrReadOnly`. Filtros `channel_type`, `is_active`; `search` sobre `name` e `identifier`; orden por defecto `channel_type`, `name`. Paginado.

Los canales de WhatsApp, correo, chat web y páginas de Meta se crean automáticamente al crear la línea, cuenta, widget o página correspondiente; normalmente no hace falta crearlos a mano.

| Campo | Notas |
|---|---|
| `id`, `name`, `identifier`, `is_active`, `created_at` | |
| `channel_type` | `whatsapp`, `sms`, `email`, `chat` (legacy), `webchat`, `messenger`, `instagram`. |
| `channel_type_display` | Solo lectura. |
| `conversation_count` | Conversaciones `open` o `waiting`. Solo lectura. |
| `whatsapp_line_id` | ID de la línea si es WhatsApp. Solo lectura. |

## Conversaciones: `/api/messaging/conversations/`

`ConversationViewSet`, permiso `IsAuthenticated`. Métodos permitidos: `GET`, `POST`, `PATCH` (no hay `PUT` ni `DELETE`).

Alcance por rol:

- `admin`, `supervisor`: todas las conversaciones.
- Otros roles: solo las asignadas a su perfil de agente y las sin asignar. Sin perfil de agente, el listado es vacío.
- En acciones de escritura (`messages` POST, `send-template`, `close`, `reopen`, `tags`, `attachments`, `start`), un no supervisor que intenta actuar sobre una conversación de otro agente recibe `403 {"error": "Esta conversación está asignada a otro agente."}`.

### Endpoints

| Método y ruta | Descripción |
|---|---|
| `GET conversations/` | Listado paginado. |
| `GET conversations/{id}/` | Detalle con `contact_details`. |
| `POST conversations/` | Creación genérica del ModelViewSet (el frontend usa `start` o `start-email`). |
| `PATCH conversations/{id}/` | Edición parcial de campos escribibles. |
| `GET conversations/stats/` | Contadores de la bandeja. |
| `POST conversations/start/` | Inicia una conversación de WhatsApp con plantilla. |
| `POST conversations/start-email/` | Inicia un hilo de correo saliente. |
| `GET conversations/{id}/messages/` | Mensajes de la conversación (marca los entrantes como leídos). |
| `POST conversations/{id}/messages/` | Envía texto. |
| `POST conversations/{id}/send-template/` | Envía plantilla de WhatsApp. |
| `POST conversations/{id}/attachments/` | Envía archivo (multipart). |
| `POST conversations/{id}/assign/` | Asigna o libera (solo supervisores). |
| `POST conversations/{id}/take/` | El agente toma la conversación. |
| `GET conversations/{id}/close-options/` | Tipificaciones y etiquetas disponibles para cerrar. |
| `POST conversations/{id}/close/` | Cierra con tipificación, etiquetas y notas. |
| `POST conversations/{id}/reopen/` | Reabre. |
| `POST conversations/{id}/tags/` | Reemplaza las etiquetas. |

### Filtros del listado

| Parámetro | Efecto |
|---|---|
| `status` | `open`, `waiting`, `closed`. |
| `channel`, `agent`, `campaign` | ID. |
| `mine=1` | Solo las del agente del usuario. |
| `unassigned=1` | Solo sin agente. |
| `active=1` | Excluye cerradas. |
| `line` | ID de línea de WhatsApp. |
| `channel_type` | Tipo de canal. |
| `search` | Sobre `contact_identifier`, `contact_name`, nombre y apellido del contacto. |
| `ordering` | `started_at`, `closed_at`, `last_message_at`. Sin `ordering`: último mensaje más reciente primero. |

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/messaging/conversations/?active=1&channel_type=whatsapp" \
  -H "Authorization: Bearer <TOKEN>"
```

### Campos (`ConversationSerializer`)

| Campo | Notas |
|---|---|
| `id`, `channel`, `channel_name`, `channel_type`, `whatsapp_line_id` | |
| `agent`, `agent_name` | |
| `contact`, `display_name`, `contact_name`, `contact_identifier` | `display_name`: nombre del contacto, nombre de perfil, `Visitante web` o el identificador. |
| `status`, `status_display` | |
| `started_at`, `closed_at`, `last_message_at`, `last_inbound_at` | Solo lectura. |
| `window_open`, `window_hours` | Ventana de mensajería: WhatsApp 24 h, Messenger e Instagram 168 h (7 días), otros canales sin ventana (`window_hours: null`, `window_open: true`). |
| `campaign`, `campaign_name` | |
| `last_message` | `{body, direction, message_type, status, sent_at}` o `null`. |
| `unread_count` | Entrantes sin leer. |
| `disposition`, `disposition_name`, `tags`, `close_notes`, `closed_reason` | `closed_reason`: `agent`, `broadcast` o `system`. Solo lectura. |
| `assigned_at`, `first_response_at`, `subject`, `metadata` | Solo lectura (excepto `subject`). |

El detalle agrega `contact_details`: `{id, full_name, phone, email, company, city, is_vip, custom_fields}` o `null`.

```json
{
  "id": 318,
  "channel": 3,
  "channel_name": "WhatsApp · Ventas",
  "channel_type": "whatsapp",
  "whatsapp_line_id": 1,
  "agent": 12,
  "agent_name": "Laura Gómez",
  "contact": 904,
  "display_name": "Andrés Martínez",
  "contact_name": "Andrés",
  "contact_identifier": "573001234567",
  "status": "open",
  "status_display": "Abierta",
  "started_at": "2025-03-10 09:12:40",
  "closed_at": null,
  "last_message_at": "2025-03-10 09:20:02",
  "last_inbound_at": "2025-03-10 09:19:10",
  "window_open": true,
  "window_hours": 24,
  "campaign": 4,
  "campaign_name": "Ventas marzo",
  "last_message": {"body": "Perfecto, gracias", "direction": "outbound", "message_type": "text", "status": "delivered", "sent_at": "2025-03-10T09:20:02-05:00"},
  "unread_count": 0,
  "disposition": null,
  "disposition_name": null,
  "tags": [{"id": 2, "name": "Cotización", "color": "#0ea5e9"}],
  "close_notes": "",
  "closed_reason": "",
  "assigned_at": "2025-03-10 09:12:41",
  "first_response_at": "2025-03-10 09:13:30",
  "subject": "",
  "metadata": {}
}
```

### Contadores: `GET conversations/stats/`

Sobre el mismo alcance del usuario.

```json
{"open": 14, "waiting": 3, "unassigned": 2, "mine": 6, "closed_today": 21, "unread": 9}
```

### Mensajes de la conversación

`GET conversations/{id}/messages/` devuelve todos los mensajes en orden de envío (sin paginación). Marca los entrantes como leídos y, en WhatsApp, confirma la lectura del último a Meta.

Campos (`MessageSerializer`, todos de solo lectura): `id`, `conversation`, `direction` (`inbound`, `outbound`), `message_type` (`text`, `template`, `image`, `audio`, `video`, `document`, `sticker`, `location`, `contacts`, `interactive`, `button`, `reaction`, `system`, `unknown`), `body`, `media_url`, `status` (`pending`, `sent`, `delivered`, `read`, `failed`, `received`), `error_message`, `sender`, `sender_name` (`Sistema` para mensajes automáticos), `metadata` (sin `local_path`), `has_media`, `is_read`, `sent_at`, `external_id`.

`POST conversations/{id}/messages/` envía texto:

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/messaging/conversations/318/messages/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"body": "Hola Andrés, te comparto la cotización."}'
```

- `body` obligatorio, máximo 4096 caracteres.
- Si un agente escribe en una conversación sin asignar, se la asigna.
- Respuesta `201` con el mensaje; `502` si el envío al proveedor falló (el mensaje queda con `status: failed`).

```json
{
  "id": 5120,
  "conversation": 318,
  "direction": "outbound",
  "message_type": "text",
  "body": "Hola Andrés, te comparto la cotización.",
  "media_url": null,
  "status": "sent",
  "error_message": "",
  "sender": 7,
  "sender_name": "Laura Gómez",
  "metadata": {},
  "has_media": false,
  "is_read": false,
  "sent_at": "2025-03-10 09:25:13",
  "external_id": "wamid.<ID_EXTERNO>"
}
```

Errores `400`:

| Cuerpo | Causa |
|---|---|
| `{"body": ["El mensaje no puede estar vacío."]}` | Sin texto. |
| `{"body": ["Máximo 4096 caracteres."]}` | Texto largo. |
| `{"error": "Han pasado más de 24 h desde el último mensaje del cliente. Para escribirle debes usar una plantilla aprobada por Meta.", "code": "window_closed", "requires_template": true}` | Ventana de WhatsApp cerrada. En Messenger e Instagram el mensaje habla de 7 días. |
| Error de Meta (`WhatsAppAPIError.to_dict()`) | La API de Meta rechazó la petición. |

### Plantillas en una conversación

`POST conversations/{id}/send-template/` (solo conversaciones de WhatsApp):

```json
{"template_id": 9, "body_params": ["Andrés", "15 de marzo"], "header_params": []}
```

Respuesta `201` con el mensaje (`message_type: template`, `body` con la vista previa ya rellenada) o `502` si falló. Errores `400`: `{"error": "La conversación no es de WhatsApp"}`, `{"template_id": ["Plantilla no encontrada"]}`.

### Iniciar conversación de WhatsApp: `POST conversations/start/`

WhatsApp exige una plantilla aprobada para iniciar.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/messaging/conversations/start/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"line_id": 1, "to": "573001234567", "template_id": 9, "body_params": ["Andrés"], "contact_id": 904}'
```

- `to` se normaliza a dígitos y debe tener al menos 8.
- Si ya hay una conversación abierta con ese número en la línea, se reutiliza. Si no, se crea asignada al agente del usuario, con la campaña por defecto de la línea y `status: open`.
- Respuesta `201` `{"conversation": {...}, "message": {...}}`; `400` si el envío falló.

Errores: `404 {"error": "Línea de WhatsApp no encontrada"}`, `400 {"to": ["Número inválido. Usa formato internacional, ej: 573001234567"]}`, `400 {"template_id": ["Plantilla no encontrada para esta línea"]}`, `400 {"error": "La plantilla está en estado PENDING; solo se pueden usar aprobadas."}`.

### Iniciar correo: `POST conversations/start-email/`

```json
{"account_id": 2, "to": "cliente@example.com", "subject": "Seguimiento de su solicitud", "body": "Buen día..."}
```

Crea la conversación asignada al usuario (si tiene perfil de agente) y envía el correo. Asocia el contacto por email si existe. Respuesta `201` `{"conversation", "message"}` o `400` si el envío falló. Errores: `404 {"error": "Cuenta de email no encontrada"}`, `400 {"to": ["Email inválido"]}`, `400 {"error": "Asunto y mensaje son obligatorios"}`.

### Adjuntos: `POST conversations/{id}/attachments/`

`multipart/form-data` con `file` y `caption` opcional (máx. 1024).

| Tipo MIME | Se envía como | Límite |
|---|---|---|
| `image/jpeg`, `image/png` | `image` | 5 MB |
| Otras imágenes | `document` | 100 MB |
| `audio/*` | `audio` | 16 MB |
| `video/mp4`, `video/3gpp` | `video` | 16 MB |
| Otros | `document` | 100 MB |
| Cualquier tipo en canal de correo | | 20 MB |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/messaging/conversations/318/attachments/ \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@cotizacion.pdf" -F "caption=Cotización"
```

Respuesta `201` con el mensaje o `502` si falló. Errores `400`: `{"file": ["Adjunta un archivo."]}`, `{"file": ["El archivo supera el límite de 5 MB para este tipo."]}`, ventana cerrada (`code: window_closed`).

### Asignar, tomar, cerrar y reabrir

`POST conversations/{id}/assign/` (solo supervisores). Body `{"agent_id": 12}` asigna y pone `open`; `{"agent_id": null}` libera y pone `waiting`. Responde la conversación. Errores: `403 {"error": "Solo supervisores pueden reasignar"}`, `404 {"error": "Agente no encontrado"}`.

`POST conversations/{id}/take/` asigna la conversación al agente del usuario. Errores: `400 {"error": "Tu usuario no tiene perfil de agente"}`, `409 {"error": "Ya está asignada a otro agente"}` (un supervisor sí puede tomarla).

`GET conversations/{id}/close-options/`:

```json
{
  "dispositions": [{"id": 31, "code": "VENTA", "name": "Venta", "is_success": true, "requires_callback": false}],
  "disposition_required": true,
  "tags": [{"id": 2, "name": "Cotización", "color": "#0ea5e9"}],
  "current_tags": [2]
}
```

`POST conversations/{id}/close/`:

```json
{"disposition_id": 31, "tag_ids": [2], "notes": "Cliente acepta la propuesta"}
```

- Si la campaña de la conversación tiene tipificaciones, `disposition_id` es obligatorio salvo que se envíe `skip_disposition: true`.
- `notes` se guarda en `close_notes` (máx. 2000). `tag_ids` reemplaza las etiquetas (solo activas).
- Si la tipificación tiene `requires_callback` y hay contacto, el contacto pasa a `status: callback`.
- Responde la conversación cerrada (`closed_reason: agent`).

Errores `400`: `{"error": "La conversación ya está cerrada"}`, `{"disposition_id": ["La tipificación no pertenece a la campaña de la conversación."]}`, `{"error": "Selecciona una tipificación para cerrar la conversación.", "code": "disposition_required"}`.

`POST conversations/{id}/reopen/` deja `open` si tiene agente o `waiting` si no.

`POST conversations/{id}/tags/` con `{"tag_ids": [1, 2]}` reemplaza las etiquetas.

Cada cambio de asignación, cierre, reapertura, mensaje nuevo o estado de entrega emite un evento por WebSocket (`conversation.assigned`, `conversation.closed`, `conversation.reopened`, `message.new`, `message.status`); ver [websockets.md](./websockets.md).

## Mensajes: `/api/messaging/messages/`

`MessageViewSet` solo expone dos acciones de detalle (no hay listado). Mismo alcance que las conversaciones.

`GET messages/{id}/media/` devuelve el adjunto con `Content-Disposition: inline`. Errores `404`: `{"error": "El archivo aún se está descargando, intenta en unos segundos."}` (adjunto entrante de WhatsApp pendiente de descarga) o `{"error": "El mensaje no tiene adjunto"}`.

`POST messages/{id}/retry/` reintenta un saliente con `status: failed`. Responde el mensaje. Error `400 {"error": "Solo se reintentan mensajes salientes fallidos"}`.

## WhatsApp Business

### Proveedores (Apps de Meta): `/api/messaging/whatsapp/providers/`

`WhatsAppProviderViewSet`, solo `admin`. CRUD completo.

| Campo | Notas |
|---|---|
| `name`, `app_id` | `app_id` numérico (ID de la App de Meta). |
| `app_secret`, `access_token` | Solo escritura. `access_token` obligatorio al crear. Enviar vacío al editar conserva el valor. |
| `verify_token` | Generado por el sistema. Solo lectura. Se usa en la verificación del webhook. |
| `api_version`, `business_id`, `is_active` | |
| `has_app_secret`, `has_access_token`, `access_token_hint` | Indicadores; el hint muestra solo los últimos 6 caracteres. |
| `webhook_url` | `https://<dominio>/api/webhooks/whatsapp/<APP_ID>/`. |
| `webhook_verified`, `webhook_verified_at`, `last_webhook_at`, `last_error` | Solo lectura. |
| `lines_count`, `created_at`, `updated_at` | Solo lectura. |

Acciones:

| Método y ruta | Descripción |
|---|---|
| `POST whatsapp/providers/{id}/test/` | Valida el token contra Meta. `200 {"success": true, "identity": {...}, "message": "Token válido — <nombre>"}` o error de Meta. |
| `POST whatsapp/providers/{id}/regenerate-verify-token/` | Nuevo `verify_token` y `webhook_verified = false`. Responde el proveedor. Hay que actualizar el token en Meta. |
| `GET whatsapp/providers/{id}/phone-numbers/?waba_id=<WABA_ID>` | Números de la cuenta de WhatsApp Business. `400 {"error": "waba_id requerido"}`. |
| `GET whatsapp/providers/webhook-info/` | Diagnóstico de la URL pública del webhook. |
| `POST whatsapp/providers/{id}/check-webhook/` | Simula la verificación de Meta contra la URL pública. |
| `DELETE whatsapp/providers/{id}/` | `400 {"error": "Elimina primero las líneas de este proveedor."}` si tiene líneas. |

`GET whatsapp/providers/webhook-info/`:

```json
{
  "base_url": "https://omni.example.com",
  "source": "PUBLIC_BASE_URL",
  "host": "omni.example.com",
  "is_https": true,
  "is_ip": false,
  "is_private": false,
  "public_ready": true,
  "issues": [],
  "path_template": "/api/webhooks/whatsapp/{APP_ID}/",
  "url_template": "https://omni.example.com/api/webhooks/whatsapp/{APP_ID}/",
  "providers": [
    {
      "id": 1,
      "name": "App VozipOmni",
      "app_id": "<APP_ID>",
      "webhook_url": "https://omni.example.com/api/webhooks/whatsapp/<APP_ID>/",
      "verify_token": "<VERIFY_TOKEN>",
      "webhook_verified": true,
      "last_webhook_at": "2025-03-10 09:19:10"
    }
  ]
}
```

La base sale de `PUBLIC_BASE_URL` o, si no está definida, del host de la petición (forzando `https://`). `issues` explica por qué Meta no podría alcanzarla (sin HTTPS, IP en lugar de dominio, red privada, `PUBLIC_BASE_URL` sin definir).

`POST whatsapp/providers/{id}/check-webhook/` hace un `GET` desde el propio servidor a la URL pública con `hub.mode=subscribe`, el `verify_token` y un desafío aleatorio, con verificación TLS estricta. Siempre responde `200`:

```json
{"ok": true, "stage": "done", "url": "https://omni.example.com/api/webhooks/whatsapp/<APP_ID>/", "message": "La URL responde correctamente con HTTPS válido. Ya puedes verificarla en Meta."}
```

Valores de `stage` cuando `ok` es `false`: `https` (la URL no es HTTPS), `ssl` (certificado inválido), `connection` (DNS, puerto 443 o firewall), `timeout` (más de 10 s), `response` (respondió otro código o no devolvió el desafío). Incluye `detail` cuando aplica. La prueba sale del mismo servidor, así que no garantiza que el firewall acepte tráfico entrante desde Internet.

### Líneas: `/api/messaging/whatsapp/lines/`

`WhatsAppLineViewSet`. `list` y `retrieve` para cualquier autenticado (los no supervisores solo ven líneas activas con `status: connected`); el resto solo `admin`.

Campos principales: `provider`, `name`, `waba_id` y `phone_number_id` (numéricos), `default_campaign`, `auto_assign`, `max_chats_per_agent`, `welcome_message`, `time_condition`, `after_hours_message`, `opt_out_keywords`, `opt_in_keywords` (separadas por coma), `opt_out_reply`, `opt_in_reply`, `is_active`. De solo lectura: `display_phone_number`, `verified_name`, `quality_rating`, `messaging_limit`, `status` (`pending`, `connected`, `error`, `disabled`), `status_detail`, `webhook_subscribed`, `last_sync_at`, `channel_id`, `templates_count`, `open_conversations`.

Crear una línea crea su canal `whatsapp`. Borrar una línea con conversaciones la deshabilita (`200 {"status": "disabled", "reason": "..."}`); sin conversaciones, la borra con su canal (`204`).

| Método y ruta | Descripción |
|---|---|
| `POST whatsapp/lines/{id}/test/` | Consulta el número en Meta y actualiza nombre verificado, calidad y estado (`connected`). `{"success": true, "phone": {...}, "line": {...}}`. |
| `POST whatsapp/lines/{id}/subscribe/` | Suscribe la App a la WABA para recibir webhooks. `{"success": true, "message": "..."}`. |
| `POST whatsapp/lines/{id}/sync-templates/` | Sincroniza plantillas desde Meta. `{"success": true, ...}` con el resultado de la sincronización. |
| `POST whatsapp/lines/{id}/send-test/` | Envía una plantilla de prueba. Body `{"to": "573001234567", "template_name": "hello_world", "language": "en_US"}` (valores por defecto). |

### Plantillas: `/api/messaging/whatsapp/templates/`

`WhatsAppTemplateViewSet`. Métodos `GET`, `POST`, `DELETE`. `list`/`retrieve` para cualquier autenticado (los no supervisores solo ven `APPROVED` de líneas activas); crear y borrar solo `admin`. Filtros `line`, `status`, `category`, `language`; `search` por `name`.

Campos: `id`, `line`, `line_name`, `meta_id`, `name`, `language`, `category`, `status`, `rejected_reason`, `components`, `body_text`, `header_text`, `body_param_count`, `header_param_count`, `updated_at`.

`POST whatsapp/templates/` crea la plantilla en Meta (queda `PENDING` hasta aprobación):

```json
{
  "line": 1,
  "name": "confirmacion_cita",
  "language": "es",
  "category": "UTILITY",
  "header_text": "Confirmación",
  "body_text": "Hola {{1}}, tu cita es el {{2}}.",
  "footer_text": "VozipOmni",
  "body_examples": ["Andrés", "15 de marzo"]
}
```

- `name`: minúsculas, números y guion bajo.
- `category`: `MARKETING`, `UTILITY` o `AUTHENTICATION` (por defecto `UTILITY`).
- `language` por defecto `es`.
- Si faltan ejemplos para las variables `{{n}}`, se completan con `ejemplo1`, `ejemplo2`...

Respuesta `201` con la plantilla. `DELETE` la borra en Meta y en local; si Meta responde que no existe, la borra igual en local.

## Envíos masivos: `/api/messaging/whatsapp/broadcasts/`

`WhatsAppBroadcastViewSet`, permiso `IsAdminOrSupervisor`. CRUD completo más acciones. Filtros `status`, `line`; `search` por `name`. Paginado.

| Campo | Notas |
|---|---|
| `name`, `line`, `template`, `contact_list` | La plantilla debe ser de la misma línea. |
| `body_params`, `header_params` | Listas; deben cubrir las variables de la plantilla. |
| `require_opt_in` | Solo contactos con `whatsapp_opt_in`. |
| `rate_per_minute` | 1 a 1000 (por defecto 60). |
| `scheduled_at` | Si es futura, el envío queda `scheduled`. |
| `status` | `draft`, `scheduled`, `running`, `paused`, `completed`, `cancelled`. Solo lectura. |
| `started_at`, `finished_at`, `total_recipients`, `skipped_count`, `last_error` | Solo lectura. |
| `line_name`, `template_name`, `template_language`, `template_body`, `body_param_count`, `header_param_count`, `contact_list_name`, `created_by_name`, `created_at` | Solo lectura. |
| `stats` | `{pending, sent, delivered, read, failed, replied}`. Solo lectura. |

Solo se editan envíos en `draft`, `scheduled` o `paused`. No se puede borrar uno en `running` (`400 {"error": "Pausa o cancela el envío antes de eliminarlo."}`).

| Método y ruta | Descripción y respuesta |
|---|---|
| `POST whatsapp/broadcasts/preview/` | Body `{"contact_list": 5, "require_opt_in": true}`. Responde `{"total", "eligible", "opted_in", "dnc"}`. |
| `POST whatsapp/broadcasts/{id}/start/` | Genera destinatarios (excluye DNC y lista negra) y encola el envío. Responde el envío. `400` si la plantilla no está aprobada, falta lista, el estado no lo permite o ningún contacto cumple (`{"error": "Ningún contacto cumple las condiciones (opt-in, DNC, teléfono válido).", "total": 0, "skipped": N}`). |
| `POST whatsapp/broadcasts/{id}/pause/` | Solo desde `running`. |
| `POST whatsapp/broadcasts/{id}/resume/` | Solo desde `paused`. |
| `POST whatsapp/broadcasts/{id}/cancel/` | Cualquier estado salvo `completed` o `cancelled`. |
| `GET whatsapp/broadcasts/{id}/recipients/?status=` | Destinatarios paginados: `{id, phone, status, error, sent_at, contact_name, conversation_id}`. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/messaging/whatsapp/broadcasts/7/start/ \
  -H "Authorization: Bearer <TOKEN>"
```

## Etiquetas: `/api/messaging/tags/`

`ConversationTagViewSet`, CRUD. Lectura para autenticados, escritura `admin`/`supervisor`. Sin paginación. Filtro `is_active`; `search` por `name`. Campos: `id`, `name`, `color`, `is_active`, `usage` (solo lectura), `created_at`.

## Respuestas rápidas: `/api/messaging/quick-replies/`

`QuickReplyViewSet`, CRUD. Lectura para autenticados, escritura `admin`/`supervisor`. Sin paginación. `search` sobre `title`, `shortcut`, `body`.

Campos: `id`, `title`, `shortcut` (se normaliza con `/` inicial y sin espacios), `body`, `campaign`, `campaign_name`, `channel_type` (vacío = todos), `order`, `is_active`, `created_at`, `updated_at`.

| Parámetro | Efecto |
|---|---|
| `for_agent=1` | Modo chat: activas, globales más las de `campaign`, y si viene `channel_type`, las de ese canal o sin canal. |
| `campaign=global` | Solo globales. |
| `campaign=<id>` | De esa campaña. |
| `channel_type` | De ese tipo de canal. |

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/messaging/quick-replies/?for_agent=1&campaign=4&channel_type=whatsapp" \
  -H "Authorization: Bearer <TOKEN>"
```

## Configuración de canales

`email/accounts/`, `webchat/widgets/` y `meta/pages/` comparten reglas: `list` y `retrieve` para `admin` y `supervisor`; crear, editar, borrar y acciones solo `admin`. Crear el objeto crea su canal. Borrar uno con conversaciones lo deshabilita junto con su canal (`200 {"status": "disabled", "reason": "El canal tiene conversaciones; se deshabilitó para conservar el historial."}`); sin conversaciones responde `204`.

Campos de enrutamiento comunes: `default_campaign`, `default_campaign_name`, `auto_assign`, `max_chats_per_agent`, `welcome_message`, `time_condition`, `time_condition_name`, `after_hours_message`, `is_active`, además de `channel_id` y `open_conversations`.

Comportamiento al llegar un mensaje (`routing.ingest_inbound`): se reutiliza la conversación abierta del contacto (o una cerrada por envío masivo en los últimos 7 días), se asigna al agente conectado con menos chats abiertos (prioriza agentes de la campaña por defecto y respeta `max_chats_per_agent`), fuera de horario se envía `after_hours_message` (máximo cada 4 h) y, dentro de horario, `welcome_message` en conversaciones nuevas.

### Cuentas de correo: `/api/messaging/email/accounts/`

Campos: `name`, `email_address`, `from_name`, `signature`, `imap_host`, `imap_port`, `imap_ssl`, `imap_username`, `imap_password` (solo escritura), `imap_folder`, `smtp_host`, `smtp_port`, `smtp_starttls`, `smtp_ssl`, `smtp_username`, `smtp_password` (solo escritura), `has_imap_password`, `has_smtp_password`, `last_polled_at`, `last_error`. Contraseñas vacías al editar conservan el valor.

El correo entrante se lee por IMAP (no hay webhook de correo entrante).

| Método y ruta | Respuesta |
|---|---|
| `POST email/accounts/{id}/test/` | `{"imap": true, "smtp": true, "errors": []}`. `200` si ambas pasan, `400` si alguna falla (con los mensajes en `errors`). |
| `POST email/accounts/{id}/poll/` | Lee el buzón ahora. `{"success": true, "new_messages": 3}` o `400 {"error": "..."}`. |

### Widgets de chat web: `/api/messaging/webchat/widgets/`

Campos: `name`, `widget_key` (solo lectura), `allowed_origins`, `title`, `subtitle`, `primary_color` (hexadecimal, ej. `#16a34a`), `position`, `require_name`, `require_email`, `intro_text`, `embed_code` (solo lectura).

`embed_code` tiene esta forma:

```html
<script src="https://<IP_DEL_SERVIDOR>/webchat/widget.js" data-key="<WIDGET_KEY>" data-api="https://<IP_DEL_SERVIDOR>/api/messaging/webchat/public" async></script>
```

`POST webchat/widgets/{id}/regenerate-key/` genera una nueva clave (el código de inserción anterior deja de funcionar). Responde el widget.

### Páginas de Messenger e Instagram: `/api/messaging/meta/pages/`

Campos: `provider`, `provider_name`, `platform` (`messenger` o `instagram`), `name`, `page_id`, `instagram_account_id`, `page_access_token` (solo escritura), `has_token`, `subscribed`, `last_error`.

| Método y ruta | Descripción |
|---|---|
| `GET meta/pages/discover/?provider=<id>` | Páginas accesibles con el token del proveedor, con `configured_messenger` y `configured_instagram`. `404 {"error": "Proveedor no encontrado"}`. |
| `POST meta/pages/{id}/test/` | Consulta la página o cuenta en Meta. `{"success": true, "info": {...}}`. |
| `POST meta/pages/{id}/subscribe/` | Suscribe la página a `messages`, `messaging_postbacks`, `message_deliveries`, `message_reads`. `{"success": true, "message": "Página suscrita a los eventos de mensajes."}`. |

Los eventos de estas páginas llegan al mismo webhook de Meta (ver [webhooks.md](./webhooks.md)).

## Métricas de chat: `GET /api/messaging/metrics/`

`ChatMetricsView`, roles `admin`, `supervisor`, `analyst`.

| Parámetro | Efecto |
|---|---|
| `date_from`, `date_to` | `AAAA-MM-DD`. Por defecto, últimos 7 días hasta ahora. |
| `channel_type`, `channel`, `campaign`, `agent` | Filtros. |
| `sla_minutes` | Objetivo de primera respuesta (mínimo 1, por defecto 5). |

Excluye conversaciones de envíos masivos sin respuesta del cliente. Tiempos en segundos (`null` si no hay datos).

```json
{
  "period": {"start": "2025-03-04T00:00:00-05:00", "end": "2025-03-10T23:59:59-05:00"},
  "total_conversations": 420,
  "closed_conversations": 380,
  "open_conversations": 40,
  "unassigned": 6,
  "avg_first_response": 95,
  "avg_handle_time": 1820,
  "avg_time_to_assign": 12,
  "sla_minutes": 5,
  "sla_pct": 88.3,
  "messages_inbound": 3100,
  "messages_outbound": 2950,
  "by_agent": [
    {"agent_id": 12, "name": "Laura Gómez", "conversations": 40, "closed": 38, "avg_first_response": 60, "avg_handle_time": 1200, "messages_sent": 310}
  ],
  "by_channel": [{"channel_type": "whatsapp", "conversations": 300}],
  "by_disposition": [{"disposition": "Venta", "is_success": true, "count": 45}],
  "by_tag": [{"tag": "Cotización", "color": "#0ea5e9", "count": 60}],
  "daily": [{"date": "2025-03-10", "conversations": 70, "closed": 64, "avg_first_response": 88}]
}
```

Para la analítica omnicanal con el período estándar de reportes, ver `GET /api/reports/analytics/omnichannel/` en [reportes.md](./reportes.md).

## API pública del widget de chat web

Rutas bajo `/api/messaging/webchat/public/<WIDGET_KEY>/`. Sin autenticación; límite `webchat` de 60 peticiones por minuto por IP.

Reglas comunes:

- Si la clave no existe o el widget está inactivo: `404 {"error": "Widget no encontrado"}`.
- Si la petición trae cabecera `Origin` y no está en `allowed_origins`: `403 {"error": "Origen no autorizado"}`. Si está permitido, la respuesta incluye `Access-Control-Allow-Origin` con ese origen.
- Los `POST` leen el cuerpo como JSON aunque llegue como `text/plain` (el widget lo envía así para evitar el preflight CORS).
- La sesión del visitante es un token firmado por Django (`signing`) válido 30 días y ligado al widget. Token inválido o vencido: `401 {"error": "Sesión inválida"}`.

| Método y ruta | Descripción |
|---|---|
| `GET config/` | Apariencia y disponibilidad. |
| `POST session/` | Crea la sesión del visitante. |
| `GET messages/?token=&after=` | Mensajes nuevos (polling). |
| `POST messages/` | Envía un mensaje del visitante. |
| `GET media/<message_id>/?token=` | Adjunto de un mensaje de la conversación del visitante. |

`GET config/`:

```json
{
  "title": "Hablemos",
  "subtitle": "Respondemos en minutos",
  "color": "#16a34a",
  "position": "right",
  "require_name": true,
  "require_email": false,
  "intro_text": "Déjanos tu mensaje",
  "online": true,
  "offline_text": ""
}
```

`offline_text` es el mensaje de fuera de horario cuando `online` es `false`.

`POST session/` con `{"name": "Andrés", "email": "cliente@example.com", "page_url": "https://sitio.example.com/precios"}`:

```json
{"token": "<TOKEN_VISITANTE>", "visitor_id": "wc_3f9a1c2b7d4e5f60", "name": "Andrés"}
```

Errores `400`: `{"name": ["Escribe tu nombre."]}`, `{"email": ["Email inválido."]}`, `{"email": ["Escribe tu email."]}`.

`GET messages/?token=<TOKEN_VISITANTE>&after=0` devuelve hasta 200 mensajes con `id` mayor a `after` y marca como `delivered` los salientes enviados:

```json
{
  "messages": [
    {"id": 6001, "direction": "inbound", "type": "text", "body": "Hola, quiero información", "sent_at": "2025-03-10T10:00:01-05:00", "agent": null, "has_media": false, "filename": null},
    {"id": 6002, "direction": "outbound", "type": "text", "body": "Con gusto, ¿qué producto te interesa?", "sent_at": "2025-03-10T10:00:40-05:00", "agent": "Laura", "has_media": false, "filename": null}
  ],
  "status": "open",
  "agent": "Laura"
}
```

Si el visitante aún no tiene conversación: `{"messages": [], "status": null}`.

`POST messages/` con `{"token": "<TOKEN_VISITANTE>", "body": "Hola"}` (máx. 2000 caracteres) registra el mensaje entrante y aplica asignación y respuestas automáticas. Respuesta `201`:

```json
{"message": {"id": 6003, "direction": "inbound", "type": "text", "body": "Hola", "sent_at": "2025-03-10T10:01:05-05:00", "agent": null, "has_media": false, "filename": null}, "status": "waiting"}
```

Errores `400`: `{"body": ["Mensaje vacío."]}`, `{"body": ["Máximo 2000 caracteres."]}`.

Ejemplo desde un sitio web:

```javascript
const api = 'https://<IP_DEL_SERVIDOR>/api/messaging/webchat/public/<WIDGET_KEY>'
const { token } = await (await fetch(`${api}/session/`, {
  method: 'POST',
  headers: { 'Content-Type': 'text/plain' },
  body: JSON.stringify({ name: 'Andrés', page_url: location.href }),
})).json()

await fetch(`${api}/messages/`, {
  method: 'POST',
  headers: { 'Content-Type': 'text/plain' },
  body: JSON.stringify({ token, body: 'Hola' }),
})

let lastId = 0
setInterval(async () => {
  const data = await (await fetch(`${api}/messages/?token=${encodeURIComponent(token)}&after=${lastId}`)).json()
  for (const m of data.messages) lastId = Math.max(lastId, m.id)
}, 3000)
```

## Webhook de Meta

La URL oficial es `/api/webhooks/whatsapp/<APP_ID>/`; `/api/messaging/webhooks/meta/<APP_ID>/` se conserva como alias con la misma vista. Verificación, firma y eventos: [webhooks.md](./webhooks.md).
