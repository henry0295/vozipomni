# Webhooks

VozipCX maneja dos tipos de webhook:

1. Entrantes: Meta (WhatsApp Cloud API, Facebook Messenger e Instagram) llama a VozipCX para entregar mensajes y estados.
2. Salientes: VozipCX llama a URLs externas configuradas en `/api/webhooks/` cuando ocurren eventos del contact center.

No hay webhooks entrantes de correo: el correo se lee por IMAP (ver cuentas de correo en [mensajeria.md](./mensajeria.md)). Tampoco hay otros webhooks entrantes (proveedores SMS, CRM u otros) en las rutas del backend.

Código fuente:

- `backend/apps/api/urls.py`: ruta `webhooks/whatsapp/<str:app_id>/` (declarada antes del router) y registro de `WebhookViewSet` en `webhooks`.
- `backend/apps/messaging/urls.py`: alias `webhooks/meta/<str:app_id>/`.
- `backend/apps/messaging/views.py`: `MetaWebhookView`.
- `backend/apps/messaging/whatsapp.py` y `backend/apps/messaging/meta_pages.py`: procesamiento de eventos.
- `backend/apps/api/cc_viewsets.py`: `WebhookViewSet`.
- `backend/apps/telephony/models.py`: `WEBHOOK_EVENTS`, `WebhookEndpoint`, `WebhookDelivery`.
- `backend/apps/telephony/webhook_service.py` y `backend/apps/telephony/tasks.py` (`deliver_webhook`): entrega.

Convenciones comunes: [README.md](./README.md). Configuración de proveedores de Meta y diagnóstico de la URL: [mensajeria.md](./mensajeria.md). Guía funcional: [Administración omnicanal](../administracion/omnicanal.md). Términos: [Glosario](../general/glosario.md).

## Webhook entrante de Meta

### Rutas

| Ruta | Uso |
|---|---|
| `GET`/`POST /api/webhooks/whatsapp/<APP_ID>/` | Oficial. Es la que muestra la interfaz y la que devuelve `webhook_url` en los proveedores. |
| `GET`/`POST /api/messaging/webhooks/meta/<APP_ID>/` | Alias anterior, misma vista. Se conserva para Apps que ya la tienen registrada en Meta. |

`<APP_ID>` es el ID numérico de la App de Meta registrada como proveedor en `/api/messaging/whatsapp/providers/`. Una misma URL recibe los eventos de WhatsApp, Messenger e Instagram de esa App.

La vista es pública: `authentication_classes = []`, `permission_classes = [AllowAny]` y sin throttling (Meta envía ráfagas). La seguridad depende del `verify_token` (verificación) y de la firma `X-Hub-Signature-256` (eventos).

Meta exige HTTPS con certificado válido y un dominio accesible desde Internet. La URL pública se construye con `PUBLIC_BASE_URL` (variable de entorno) o, si no existe, con el host de la petición. Para diagnosticarla use `GET /api/messaging/whatsapp/providers/webhook-info/` y `POST /api/messaging/whatsapp/providers/{id}/check-webhook/` ([mensajeria.md](./mensajeria.md)).

### Verificación: `GET`

Meta llama con los parámetros de suscripción:

| Parámetro | Valor esperado |
|---|---|
| `hub.mode` | `subscribe` |
| `hub.verify_token` | El `verify_token` del proveedor (comparación en tiempo constante con `hmac.compare_digest`). |
| `hub.challenge` | Cadena que se devuelve tal cual. |

Si el proveedor existe, está activo y el token coincide: responde `200` con `Content-Type: text/plain` y el cuerpo igual a `hub.challenge`, y marca `webhook_verified = true` y `webhook_verified_at`. En cualquier otro caso responde `403` con el texto `Forbidden`.

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/webhooks/whatsapp/<APP_ID>/?hub.mode=subscribe&hub.verify_token=<VERIFY_TOKEN>&hub.challenge=1234567890"
```

Respuesta: `1234567890`.

El `verify_token` lo genera el sistema al crear el proveedor; se consulta en `webhook-info` y se regenera con `POST /api/messaging/whatsapp/providers/{id}/regenerate-verify-token/` (eso pone `webhook_verified = false` y obliga a verificar de nuevo en Meta).

### Eventos: `POST`

Orden de validación:

| Paso | Resultado si falla |
|---|---|
| 1. Existe un proveedor activo con ese `app_id`. | `404` sin cuerpo. |
| 2. Si el proveedor tiene `app_secret`, la cabecera `X-Hub-Signature-256` debe ser `sha256=` + HMAC-SHA256 hexadecimal del cuerpo crudo con el `app_secret`. | `403` `Invalid signature`. |
| 3. El cuerpo es JSON válido. | `400` `Bad request`. |

Si el proveedor no tiene `app_secret`, la firma no se verifica y cualquiera que conozca la URL puede inyectar eventos. Configure siempre el App Secret en el proveedor.

Tras validar, actualiza `last_webhook_at` y procesa el cuerpo según `object`:

| `object` | Procesador | Qué hace |
|---|---|---|
| `whatsapp_business_account` | `process_webhook_payload` | Para cada `entry[].changes[]` con `field = messages`: busca la línea activa por `value.metadata.phone_number_id` (del mismo proveedor), registra `value.messages[]` como entrantes y aplica `value.statuses[]`. Otros `field` se ignoran. |
| `page` | `process_page_webhook` (Messenger) | Para cada `entry[]` busca la página configurada por `entry.id` y procesa `entry.messaging[]`. |
| `instagram` | `process_page_webhook` (Instagram) | Igual, buscando por `page_id` o `instagram_account_id`. |

Siempre responde `200` con el texto `EVENT_RECEIVED`, incluso si falla el procesamiento interno (el error queda en el log). Así se evita que Meta reintente en bucle.

```bash
BODY='{"object":"whatsapp_business_account","entry":[{"id":"<WABA_ID>","changes":[{"field":"messages","value":{"messaging_product":"whatsapp","metadata":{"display_phone_number":"573000000000","phone_number_id":"<PHONE_NUMBER_ID>"},"contacts":[{"wa_id":"573001234567","profile":{"name":"Andrés"}}],"messages":[{"from":"573001234567","id":"wamid.<ID_EXTERNO>","timestamp":"1741617900","type":"text","text":{"body":"Hola"}}]}}]}]}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "<APP_SECRET>" | sed 's/^.* //')

curl -s -X POST "https://<IP_DEL_SERVIDOR>/api/webhooks/whatsapp/<APP_ID>/" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIG" \
  -d "$BODY"
```

Respuesta: `EVENT_RECEIVED`.

#### Mensajes de WhatsApp

Tipos reconocidos en `messages[].type` y cómo se guardan:

| Tipo de Meta | `message_type` | `body` | `metadata` |
|---|---|---|---|
| `text` | `text` | `text.body` | |
| `image`, `video`, `audio`, `document`, `sticker` | Mismo nombre | `caption` | `media_id`, `mime_type`, `filename`, `voice` |
| `location` | `location` | Nombre, dirección o `Ubicación compartida` | `latitude`, `longitude`, `name`, `address`, `url` |
| `contacts` | `contacts` | `Contacto compartido: ...` | `contacts` |
| `interactive` | `interactive` | Título del botón o elemento de lista | `reply_id`, `interactive_type` |
| `button` | `button` | `button.text` | `payload` |
| `reaction` | `reaction` | Emoji | `reacted_message_id` |
| Otro | `unknown` | Título del error o `Mensaje no soportado` | |

Si el mensaje responde a otro (`context`), se guarda `metadata.reply_to`.

Comportamiento:

- Duplicados: si ya existe un mensaje con el mismo `external_id` (`messages[].id`) en el canal, se ignora (Meta reintenta webhooks).
- El nombre de perfil sale de `value.contacts[]`; el contacto se asocia por los últimos 10 dígitos del número.
- Los adjuntos se descargan en segundo plano (`download_whatsapp_media`); al terminar se emite `message.media` por WebSocket.
- Palabras clave de baja o alta (`opt_out_keywords`, `opt_in_keywords` de la línea, sin distinguir mayúsculas): actualizan `whatsapp_opt_in` de los contactos con ese número, envían la respuesta configurada y omiten las demás respuestas automáticas.
- Luego se aplican asignación automática, mensaje fuera de horario y bienvenida (ver [mensajeria.md](./mensajeria.md)).

#### Estados de WhatsApp

`statuses[].status` con valores `sent`, `delivered`, `read` o `failed` actualiza el mensaje saliente cuyo `external_id` coincide con `statuses[].id`. El estado no retrocede (`read` no vuelve a `delivered`); `failed` siempre se aplica y guarda el primer error (`code`, `title`, `error_data.details`) en `error_message`. También actualiza el destinatario del envío masivo, si aplica, y emite `message.status` por WebSocket.

#### Eventos de Messenger e Instagram

| Evento en `entry.messaging[]` | Acción |
|---|---|
| `message` (sin `is_echo`) | Mensaje entrante del `sender.id`. Texto como `text`; adjuntos según su tipo, descargados en segundo plano. Guarda `mid`, `reply_to` y `quick_reply_payload`. |
| `message` con `is_echo` | Se ignora (mensajes enviados por la propia página). |
| `postback` | Entrante `button` con `postback.title` y `metadata.payload`. |
| `delivery` | Marca como `delivered` los salientes `sent` (por `mids` o por `watermark`). |
| `read` | Marca como `read` los salientes hasta el `watermark`. |

Para recibirlos, la página debe estar suscrita (`POST /api/messaging/meta/pages/{id}/subscribe/`) a `messages`, `messaging_postbacks`, `message_deliveries` y `message_reads`.

## Webhooks salientes: `/api/webhooks/`

`WebhookViewSet`, permiso `IsAdminOrSupervisor` (`admin`, `supervisor` o superusuario). CRUD completo y acciones. Paginado.

| Método y ruta | Descripción |
|---|---|
| `GET /api/webhooks/` | Listado. |
| `POST /api/webhooks/` | Crear. |
| `GET /api/webhooks/{id}/` | Detalle. |
| `PUT`/`PATCH /api/webhooks/{id}/` | Editar. |
| `DELETE /api/webhooks/{id}/` | Borrar (también borra su historial de entregas). |
| `POST /api/webhooks/{id}/test/` | Envía un evento de prueba. |
| `GET /api/webhooks/{id}/deliveries/` | Últimas 50 entregas. |
| `GET /api/webhooks/available_events/` | Eventos suscribibles. |

La ruta del webhook de Meta (`/api/webhooks/whatsapp/<APP_ID>/`) se declara antes del router para que no la capture este ViewSet.

### Campos (`WebhookEndpointSerializer`)

| Campo | Tipo | Notas |
|---|---|---|
| `id` | integer | |
| `name` | string | Obligatorio (máx. 200). |
| `url` | string | Obligatorio. URL válida (máx. 500). |
| `secret` | string | Solo escritura. Si se define, se firma cada envío. |
| `events` | lista | Eventos a notificar. Vacía = todos. |
| `headers` | objeto | Cabeceras adicionales en cada envío. |
| `is_active` | boolean | Por defecto `true`. |
| `retry_on_failure` | boolean | Por defecto `true`. |
| `timeout_seconds` | integer | Por defecto 10. |
| `last_triggered_at`, `last_status_code` | | Solo lectura. |
| `delivery_count` | integer | Entregas totales (`total_deliveries`). Solo lectura. |
| `failed_deliveries` | integer | |
| `success_rate` | number | `(1 - fallidas / totales) * 100`; 100 si no hay entregas. Solo lectura. |
| `created_at`, `updated_at` | datetime | Solo lectura. |

El serializer no valida que los valores de `events` existan en `WEBHOOK_EVENTS`.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/webhooks/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CRM",
    "url": "https://crm.example.com/hooks/vozipomni",
    "secret": "<SECRETO_WEBHOOK>",
    "events": ["callback.completed"],
    "headers": {"X-Api-Key": "<API_KEY_CRM>"},
    "timeout_seconds": 10
  }'
```

Respuesta `201`:

```json
{
  "id": 3,
  "name": "CRM",
  "url": "https://crm.example.com/hooks/vozipomni",
  "events": ["callback.completed"],
  "headers": {"X-Api-Key": "<API_KEY_CRM>"},
  "is_active": true,
  "retry_on_failure": true,
  "timeout_seconds": 10,
  "last_triggered_at": null,
  "last_status_code": null,
  "delivery_count": 0,
  "failed_deliveries": 0,
  "success_rate": 100.0,
  "created_at": "2025-03-10 16:40:00",
  "updated_at": "2025-03-10 16:40:00"
}
```

`headers` sí se devuelve en las respuestas; no guarde ahí credenciales que no deban ver otros supervisores.

### Eventos: `GET /api/webhooks/available_events/`

```json
[
  {"value": "call.initiated", "label": "Llamada iniciada"},
  {"value": "call.answered", "label": "Llamada contestada"},
  {"value": "call.completed", "label": "Llamada completada"},
  {"value": "call.abandoned", "label": "Llamada abandonada"},
  {"value": "agent.login", "label": "Agente conectado"},
  {"value": "agent.logout", "label": "Agente desconectado"},
  {"value": "agent.status", "label": "Cambio de estado agente"},
  {"value": "campaign.started", "label": "Campaña iniciada"},
  {"value": "campaign.paused", "label": "Campaña pausada"},
  {"value": "campaign.finished", "label": "Campaña finalizada"},
  {"value": "callback.created", "label": "Callback creado"},
  {"value": "callback.completed", "label": "Callback completado"}
]
```

Estado actual del código: aunque se listan 12 eventos, el único que se despacha es `callback.completed`, desde la tarea `process_pending_callbacks` cuando la devolución de llamada se origina con éxito. El resto se pueden suscribir pero hoy no se envían. Además está el evento `test` de la acción de prueba.

| Evento | Cuerpo |
|---|---|
| `callback.completed` | `{"callback_id": 17, "phone": "3001234567", "campaign_id": 4}` |
| `test` | `{"event": "test", "message": "Prueba de webhook desde VoZIPOMNI", "timestamp": "2025-03-10T21:40:00.123456+00:00"}` |

### Formato de la entrega

`POST` a `url` con el payload del evento como cuerpo (sin sobre adicional), serializado con `json.dumps(payload, default=str)`.

| Cabecera | Valor |
|---|---|
| `Content-Type` | `application/json` |
| `X-Webhook-Event` | Tipo de evento, por ejemplo `callback.completed`. |
| `X-Webhook-Delivery` | `<endpoint_id>-<evento>-<timestamp unix>`. |
| `X-Webhook-Signature` | `sha256=<hex>` (solo si hay `secret`): HMAC-SHA256 del cuerpo exacto con el `secret`. |
| Cabeceras de `headers` | Se agregan después de las anteriores y pueden sobrescribirlas. |

Éxito = respuesta HTTP 2xx. Timeout: `timeout_seconds`.

Reintentos: si falla y `retry_on_failure` es `true`, se reprograma hasta completar 3 intentos: el segundo a los 30 s y el tercero a los 120 s. Cada intento queda en `WebhookDelivery` y actualiza `last_triggered_at`, `last_status_code`, `total_deliveries` y `failed_deliveries`. Las entregas no se ordenan ni se deduplican; el receptor debe tolerar repeticiones.

Verificación de la firma en el receptor (calcule el HMAC sobre el cuerpo crudo, antes de parsear el JSON):

```python
import hashlib
import hmac

def firma_valida(cuerpo_crudo: bytes, cabecera: str, secreto: str) -> bool:
    esperado = 'sha256=' + hmac.new(secreto.encode(), cuerpo_crudo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, cabecera or '')
```

```javascript
// Node.js (Express con express.raw({ type: 'application/json' }))
const crypto = require('crypto')
function firmaValida (rawBody, cabecera, secreto) {
  const esperado = 'sha256=' + crypto.createHmac('sha256', secreto).update(rawBody).digest('hex')
  const a = Buffer.from(esperado)
  const b = Buffer.from(cabecera || '')
  return a.length === b.length && crypto.timingSafeEqual(a, b)
}
```

### Probar: `POST /api/webhooks/{id}/test/`

Encola la entrega del evento `test` a ese endpoint (aunque no esté suscrito a él ni esté activo). Responde de inmediato:

```json
{"status": "test dispatched"}
```

El resultado se ve en `deliveries`.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/webhooks/3/test/ \
  -H "Authorization: Bearer <TOKEN>"
```

### Historial: `GET /api/webhooks/{id}/deliveries/`

Últimas 50 entregas, de la más reciente a la más antigua (sin paginación).

```json
[
  {
    "id": 120,
    "event_type": "test",
    "status_code": 200,
    "success": true,
    "duration_ms": 184,
    "attempt": 1,
    "error_message": "",
    "created_at": "2025-03-10 16:41:02"
  },
  {
    "id": 119,
    "event_type": "callback.completed",
    "status_code": null,
    "success": false,
    "duration_ms": 10004,
    "attempt": 2,
    "error_message": "Timeout",
    "created_at": "2025-03-10 16:20:31"
  }
]
```

El payload enviado y el cuerpo de la respuesta se guardan en `WebhookDelivery` (`payload`, `response_body` hasta 1000 caracteres) pero ningún endpoint los expone y los modelos no están registrados en el admin de Django; solo se consultan en la base de datos (tabla `webhook_deliveries`).

### Errores

| Código | Cuándo |
|---|---|
| `400` | Validación al crear o editar (`url` inválida, campos obligatorios). |
| `403` | Rol distinto de `admin` o `supervisor`. |
| `404` | Endpoint inexistente. |
