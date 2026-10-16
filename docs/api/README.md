# API REST de VozipCX

VozipCX expone una API REST construida con Django REST Framework (DRF). La usa el frontend Nuxt y se puede usar desde integraciones propias. Este documento resume las convenciones comunes (autenticación, formato, paginación, filtros, errores, límites de peticiones y roles) y enlaza la referencia de cada grupo de endpoints.

Todo lo aquí descrito sale del código de `backend/config/urls.py`, `backend/apps/api/urls.py`, `backend/apps/telephony/urls.py` y `backend/config/settings.py`. Solo se documentan rutas que existen.

## URL base

```
https://<IP_DEL_SERVIDOR>/api/
```

nginx publica `location /api/` hacia el backend (Daphne). Todas las rutas de esta documentación son relativas a esa base; por ejemplo `auth/login/` equivale a `https://<IP_DEL_SERVIDOR>/api/auth/login/`.

Las rutas terminan siempre en `/` (convención de DRF con `DefaultRouter`). Una petición sin la barra final puede terminar en redirección o en 404.

## Documentación interactiva (OpenAPI)

drf-spectacular está instalado y expuesto en `backend/config/urls.py`:

| Ruta | Contenido |
|---|---|
| `GET /api/schema/` | Esquema OpenAPI 3 (YAML por defecto; `?format=json` para JSON). |
| `GET /api/docs/` | Swagger UI sobre el esquema anterior. |

`SPECTACULAR_SETTINGS` define título `VozipCX Contact Center API`, versión `1.0.0` y `COMPONENT_SPLIT_REQUEST: True`. No sobrescribe `SERVE_PERMISSIONS`, así que con el valor por defecto de drf-spectacular el esquema y Swagger se sirven sin autenticación. Para probar endpoints protegidos desde Swagger use el botón "Authorize" con `Bearer <TOKEN>`.

El esquema se genera automáticamente y en varios endpoints personalizados (acciones `@action` y `APIView`) no describe el cuerpo ni la respuesta real. Esta documentación es la referencia para esos casos.

## Autenticación

Configuración en `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']`:

1. `JWTAuthentication` (djangorestframework-simplejwt): cabecera `Authorization: Bearer <TOKEN>`.
2. `SessionAuthentication`: sesión de Django (la usa el admin de Django; exige CSRF en métodos de escritura).

Permiso por defecto: `IsAuthenticated`. Cada ViewSet puede endurecerlo con las clases de `backend/core/permissions.py` (ver [Roles y permisos](#roles-y-permisos)).

Resumen de tokens (`SIMPLE_JWT`):

| Parámetro | Valor |
|---|---|
| Vida del access token | 8 horas |
| Vida del refresh token | 7 días |
| Rotación de refresh | Sí (`ROTATE_REFRESH_TOKENS`) y el anterior va a la lista negra (`BLACKLIST_AFTER_ROTATION`) |
| Tipo de cabecera | `Bearer` |

Flujo completo, ejemplos y renovación en el frontend: [autenticacion.md](./autenticacion.md).

```bash
curl -s https://<IP_DEL_SERVIDOR>/api/auth/me/ \
  -H "Authorization: Bearer <TOKEN>"
```

Endpoints públicos (sin token): `auth/login/`, `auth/refresh/`, `auth/password-reset/`, `auth/password-reset/confirm/`, `health/`, `schema/`, `docs/`, `telephony/sip-ws-auth/` (uso interno de nginx), el webhook de Meta y la API pública del chat web (ver [mensajeria.md](./mensajeria.md)).

## Formato

- Peticiones y respuestas en JSON (`Content-Type: application/json`). Las cargas de archivos usan `multipart/form-data` (se indica en cada endpoint).
- Fechas y horas en respuestas: `DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'` y `DATE_FORMAT = '%Y-%m-%d'`. Ejemplo: `"2025-03-10 14:25:00"`. La zona del servidor es `America/Bogota` (`USE_TZ = True`); el formato configurado no incluye el desfase horario.
- En la entrada se aceptan fechas ISO 8601 (`2025-03-10T14:25:00-05:00`).
- Las relaciones se envían y reciben como ID numérico (clave primaria), salvo que el endpoint indique un objeto anidado.
- Algunas respuestas personalizadas devuelven fechas con `isoformat()` (por ejemplo `server_time` o `timestamp`); se indica en cada caso.

## Paginación

`DEFAULT_PAGINATION_CLASS = PageNumberPagination` con `PAGE_SIZE = 50`. Aplica a los `list` de los ViewSets:

```json
{
  "count": 134,
  "next": "https://<IP_DEL_SERVIDOR>/api/contacts/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

- Parámetro: `?page=N` (desde 1). Una página fuera de rango responde `404 {"detail": "Página inválida."}`.
- El tamaño de página es fijo en 50. No hay `page_size_query_param` configurado, así que `?page_size=` se ignora aunque el frontend lo envíe en algunas pantallas.
- Las acciones personalizadas (`@action`) y las `APIView` no paginan: devuelven listas u objetos completos.

## Filtros, búsqueda y orden

Backends por defecto (`DEFAULT_FILTER_BACKENDS`): `DjangoFilterBackend`, `SearchFilter` y `OrderingFilter`. Algunos ViewSets redefinen `filter_backends` y quitan alguno; cada documento lo indica.

| Tipo | Parámetro | Ejemplo | Notas |
|---|---|---|---|
| Filtro exacto (django-filter) | nombre del campo en `filterset_fields` | `?status=active&campaign_type=outbound` | Solo los campos listados por el ViewSet. Booleanos como `true`/`false`. Relaciones por ID. |
| Búsqueda (`SearchFilter`) | `search` | `?search=perez` | `icontains` sobre los `search_fields` del ViewSet, combinados con OR. |
| Orden (`OrderingFilter`) | `ordering` | `?ordering=-created_at` | Prefijo `-` para descendente; varios campos separados por coma. Si el ViewSet no define `ordering_fields`, DRF permite los campos legibles del serializer. |

Parámetros no reconocidos se ignoran sin error.

## Códigos de respuesta y errores

No hay `EXCEPTION_HANDLER` personalizado, así que los errores de DRF tienen su forma estándar. Los mensajes de DRF y simplejwt salen en el idioma activo (`LANGUAGE_CODE = 'es-co'`), por eso el texto exacto puede variar.

| Código | Cuándo | Cuerpo típico |
|---|---|---|
| `200 OK` | Lectura o acción correcta. | Objeto o lista. |
| `201 Created` | Creación (`POST` a colección, `clone`, carga de audio). | Objeto creado. |
| `204 No Content` | Borrado (`DELETE`). | Vacío. |
| `400 Bad Request` | Validación fallida o parámetros faltantes. | `{"campo": ["mensaje"]}` o `{"error": "mensaje"}` en vistas personalizadas. |
| `401 Unauthorized` | Falta el token, expiró o es inválido. | `{"detail": "...", "code": "token_not_valid", "messages": [...]}` o `{"detail": "Las credenciales de autenticación no se proveyeron."}` |
| `403 Forbidden` | Token válido pero el rol no alcanza. | `{"detail": "Se requiere rol de administrador para esta acción."}` (mensaje de la clase de permiso) o `{"error": "..."}`. |
| `404 Not Found` | El recurso no existe o no es visible para el usuario (por ejemplo, llamadas de otro agente). | `{"detail": "No encontrado."}` |
| `405 Method Not Allowed` | Método no soportado en esa ruta. | `{"detail": "Método \"PUT\" no permitido."}` |
| `429 Too Many Requests` | Límite de peticiones superado. | `{"detail": "... Se espera que esté disponible en N segundos."}` y cabecera `Retry-After`. |
| `500` / `503` | Error interno o Asterisk AMI no disponible. | `{"error": "..."}` o `{"success": false, "message": "..."}` |

Convención de las vistas personalizadas: devuelven `{"error": "..."}` en fallos y, en telefonía, `{"success": true|false, "message": "..."}`.

## Límites de peticiones (throttling)

`DEFAULT_THROTTLE_CLASSES`: `AnonRateThrottle` y `UserRateThrottle`. Tasas en `DEFAULT_THROTTLE_RATES`:

| Alcance | Tasa | Se aplica a |
|---|---|---|
| `anon` | 20/minuto por IP | Peticiones sin autenticar (por ejemplo `auth/refresh/`). |
| `user` | 200/minuto por usuario | Peticiones autenticadas en general. |
| `login` | 5/minuto por IP | Solo `POST auth/login/` (reemplaza a los anteriores en esa vista). |
| `password_reset` | 5/hora por IP | `auth/password-reset/` y `auth/password-reset/confirm/`. |
| `webchat` | 60/minuto por IP | API pública del widget de chat web. |
| `agent_action` | 10/minuto por usuario | `agents/{id}/change_status/`, `start_break/`, `end_break/`, `save_disposition/` (reemplaza a `user` en esas acciones). |

`telephony/sip-ws-auth/` no tiene límite (lo llama nginx en cada handshake).

Los contadores se guardan en la caché de Django (Redis). Al superarse el límite la respuesta es `429` con `Retry-After`.

## Roles y permisos

Roles de usuario (`backend/apps/users/models.py`): `admin`, `supervisor`, `agent`, `analyst`. Un superusuario de Django pasa todas las comprobaciones de rol.

Clases de permiso usadas (`backend/core/permissions.py`):

| Clase | Lectura (GET, HEAD, OPTIONS) | Escritura (POST, PUT, PATCH, DELETE) |
|---|---|---|
| `IsAuthenticated` | Cualquier usuario autenticado | Cualquier usuario autenticado |
| `IsAdminUser` | `admin` | `admin` |
| `IsAdminOrSupervisor` | `admin`, `supervisor` | `admin`, `supervisor` |
| `IsAdminOrSupervisorOrReadOnly` | Cualquier usuario autenticado | `admin`, `supervisor` |
| `IsAdminSupervisorOrAnalyst` | `admin`, `supervisor`, `analyst` | `admin`, `supervisor` |

La clase de permiso del ViewSet también aplica a sus acciones `@action`, salvo que el ViewSet la redefina en `get_permissions()` (por ejemplo, las acciones de sesión del agente). Cada documento indica el permiso efectivo de cada endpoint.

## Salud del servicio

`GET /api/health/` (vista Django simple, sin autenticación ni throttling) comprueba base de datos y Redis.

```bash
curl -s https://<IP_DEL_SERVIDOR>/api/health/
```

```json
{
  "status": "healthy",
  "timestamp": "2025-03-10T14:25:00.123456-05:00",
  "service": "VozipCX Backend",
  "checks": {"database": "ok", "redis": "ok"}
}
```

Responde `503` con `"status": "unhealthy"` si alguna comprobación falla.

## Índice de la documentación de la API

| Documento | Qué cubre |
|---|---|
| [README.md](./README.md) | Este documento: convenciones comunes, errores, throttling, roles y OpenAPI. |
| [autenticacion.md](./autenticacion.md) | Login JWT, refresh, logout con lista negra, usuario actual, recuperación y cambio de contraseña, renovación en el frontend. |
| [usuarios-y-agentes.md](./usuarios-y-agentes.md) | `users/`, `agents/` y sus acciones (login, logout, estados, pausas, calificación, siguiente ID), `agent-groups/`, `break-reasons/`. |
| [telefonia.md](./telefonia.md) | Llamadas, troncales SIP, rutas entrantes y salientes, extensiones, IVR, buzones, música en espera, condiciones de horario, destinos personalizados, credenciales WebRTC, `sip-ws-auth`, seguridad y antifraude, screen pop, transferencia y conferencia. |
| [colas.md](./colas.md) | `queues/`: CRUD, recarga en Asterisk, estadísticas y miembros. |
| [campanas-y-contactos.md](./campanas-y-contactos.md) | Campañas y sus acciones, calificaciones, formularios, listas de contactos, contactos, importación masiva, lista negra (DNC) y callbacks. |
| [grabaciones-y-calidad.md](./grabaciones-y-calidad.md) | Grabaciones, plantillas de evaluación, evaluaciones y estadísticas de calidad. |
| [reportes.md](./reportes.md) | Reportes, KPIs y analítica. |
| [mensajeria.md](./mensajeria.md) | Mensajería omnicanal (WhatsApp, correo, chat web, Messenger, Instagram) y webhook de Meta. |
| [supervisor.md](./supervisor.md) | Acciones de supervisión en vivo (escucha, susurro, irrupción, dashboard) y auditoría de gestiones. |
| [websockets.md](./websockets.md) | Canales de tiempo real (Django Channels). |
| [webhooks.md](./webhooks.md) | Webhooks salientes: configuración, eventos, pruebas y entregas. |

Documentación relacionada: [Glosario](../general/glosario.md) y [Desarrollo del backend](../desarrollo/backend.md).
