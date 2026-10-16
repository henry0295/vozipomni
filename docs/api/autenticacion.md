# Autenticación

La API usa JWT con djangorestframework-simplejwt. El cliente obtiene un par de tokens (access y refresh) con usuario y contraseña, envía el access token en cada petición y lo renueva con el refresh token cuando expira. Las rutas están en `backend/apps/api/urls.py`; las vistas en `backend/apps/api/views.py` y `backend/apps/api/admin_viewsets.py`.

Convenciones generales (formato, errores, throttling): [README.md](./README.md).

## Resumen de endpoints

| Método | Ruta | Autenticación | Descripción |
|---|---|---|---|
| POST | `/api/auth/login/` | Pública (5/min por IP) | Obtiene access, refresh y datos del usuario. |
| POST | `/api/auth/refresh/` | Pública (20/min por IP) | Renueva el access token (y rota el refresh). |
| POST | `/api/auth/logout/` | Bearer | Invalida el refresh token. |
| GET | `/api/auth/me/` | Bearer | Datos del usuario autenticado. |
| POST | `/api/auth/password-reset/` | Pública (5/hora por IP) | Envía correo de recuperación. |
| POST | `/api/auth/password-reset/confirm/` | Pública (5/hora por IP) | Define la nueva contraseña con el enlace recibido. |
| POST | `/api/auth/change-password/` | Bearer | Cambia la contraseña del usuario autenticado. |

## Vida de los tokens

Valores de `SIMPLE_JWT` en `backend/config/settings.py`:

| Parámetro | Valor | Efecto |
|---|---|---|
| `ACCESS_TOKEN_LIFETIME` | 8 horas | Tiempo durante el que el access token es aceptado. |
| `REFRESH_TOKEN_LIFETIME` | 7 días | Tiempo máximo para renovar sin volver a iniciar sesión. |
| `ROTATE_REFRESH_TOKENS` | `True` | Cada refresh devuelve también un refresh token nuevo. |
| `BLACKLIST_AFTER_ROTATION` | `True` | El refresh usado queda en lista negra y no se puede reutilizar. |
| `UPDATE_LAST_LOGIN` | `True` | El login actualiza `last_login` del usuario. |
| `AUTH_HEADER_TYPES` | `('Bearer',)` | Cabecera `Authorization: Bearer <TOKEN>`. |
| `AUTH_TOKEN_CLASSES` | `AccessToken` | Solo el access token sirve para autenticar peticiones. |

El access token no se puede revocar antes de su vencimiento: el logout solo invalida el refresh token.

## POST /api/auth/login/

Vista `CustomTokenObtainPairView` con el serializer `CustomTokenObtainPairSerializer`, que agrega el objeto `user` a la respuesta estándar de simplejwt. Throttle propio `login` (5 intentos por minuto por IP); no aplica el límite general.

Cuerpo:

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `username` | string | Sí | Nombre de usuario (no el correo). |
| `password` | string | Sí | Contraseña. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "agente01", "password": "<CONTRASEÑA>"}'
```

Respuesta `200`:

```json
{
  "refresh": "<REFRESH_TOKEN>",
  "access": "<TOKEN>",
  "user": {
    "id": 12,
    "username": "agente01",
    "email": "agente01@example.com",
    "first_name": "Laura",
    "last_name": "Gómez",
    "name": "Laura Gómez",
    "role": "agent",
    "phone": "",
    "department": "Ventas",
    "is_active_agent": true,
    "last_activity": null
  }
}
```

`user` usa `UserSerializer`; `name` es el nombre completo o, si está vacío, el `username`.

Errores:

| Código | Causa | Cuerpo |
|---|---|---|
| `400` | Falta `username` o `password`. | `{"password": ["Este campo es requerido."]}` |
| `401` | Credenciales incorrectas o usuario inactivo. | `{"detail": "No se encontró una cuenta de usuario activa para las credenciales dadas"}` (texto de simplejwt según idioma) |
| `429` | Más de 5 intentos por minuto desde la misma IP. | `{"detail": "... Se espera que esté disponible en N segundos."}` |

## POST /api/auth/refresh/

Vista estándar `TokenRefreshView`. No requiere cabecera `Authorization`, por lo que cuenta en el límite `anon` (20/min por IP).

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `refresh` | string | Sí | Refresh token vigente. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<REFRESH_TOKEN>"}'
```

Respuesta `200` (con la rotación activa llegan ambos tokens):

```json
{
  "access": "<TOKEN>",
  "refresh": "<REFRESH_TOKEN_NUEVO>"
}
```

El cliente debe guardar el refresh nuevo: el anterior pasa a la lista negra y un segundo uso responde `401`.

Errores:

| Código | Causa | Cuerpo |
|---|---|---|
| `400` | Falta `refresh`. | `{"refresh": ["Este campo es requerido."]}` |
| `401` | Refresh expirado, inválido o en lista negra (ya usado, logout o restablecimiento de contraseña). | `{"detail": "...", "code": "token_not_valid"}` |

## POST /api/auth/logout/

Función `LogoutView` (`@api_view(['POST'])`, permiso `IsAuthenticated`). Pone en lista negra el refresh token recibido. Necesita un access token válido en la cabecera.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `refresh` | string | No | Refresh token a invalidar. Si falta, no se invalida nada. |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/auth/logout/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<REFRESH_TOKEN>"}'
```

Respuesta `200` (siempre, incluso si el refresh ya estaba vencido o en lista negra):

```json
{"message": "Logout exitoso"}
```

Errores: `401` si el access token falta o expiró. En ese caso el cliente puede descartar los tokens locales; el refresh vence solo a los 7 días.

## GET /api/auth/me/

`CurrentUserView` (`RetrieveAPIView`, permiso `IsAuthenticated`). Solo admite `GET`.

```bash
curl -s https://<IP_DEL_SERVIDOR>/api/auth/me/ \
  -H "Authorization: Bearer <TOKEN>"
```

Respuesta `200`: el mismo objeto `user` del login.

```json
{
  "id": 3,
  "username": "supervisor1",
  "email": "supervisor1@example.com",
  "first_name": "Andrés",
  "last_name": "Ruiz",
  "name": "Andrés Ruiz",
  "role": "supervisor",
  "phone": "3001234567",
  "department": "Operaciones",
  "is_active_agent": false,
  "last_activity": "2025-03-10 08:02:11"
}
```

El perfil de agente (extensión SIP, estado) no viene aquí; se consulta en `/api/agents/?user=<id>` (ver [usuarios-y-agentes.md](./usuarios-y-agentes.md)).

## POST /api/auth/password-reset/

`PasswordResetRequestView`. Sin autenticación (`authentication_classes = []`), throttle `password_reset` (5 por hora por IP).

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `email` | string | Sí | Correo del usuario. También acepta el nombre de usuario. |

Busca un usuario activo por correo (sin distinguir mayúsculas) o por `username`. Si existe y tiene correo, envía un mensaje con el enlace:

```
<FRONTEND_URL>/reset-password?uid=<UID>&token=<TOKEN_RECUPERACION>
```

`FRONTEND_URL` sale de la variable de entorno del mismo nombre (por defecto `https://<IP_DEL_SERVIDOR>`). Sin `EMAIL_HOST` configurado, Django usa el backend de consola y el correo solo queda en el log del contenedor.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/auth/password-reset/ \
  -H "Content-Type: application/json" \
  -d '{"email": "agente01@example.com"}'
```

Respuesta `200` (genérica, exista o no la cuenta, para no revelar qué correos están registrados):

```json
{"message": "Si la cuenta existe, recibirás un correo con instrucciones."}
```

Errores: `400 {"email": ["Ingresa tu correo o usuario."]}` si el campo está vacío; `429` al superar 5 solicitudes por hora.

## POST /api/auth/password-reset/confirm/

`PasswordResetConfirmView`. Sin autenticación, throttle `password_reset`.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `uid` | string | Sí | Valor `uid` del enlace (ID en base64). |
| `token` | string | Sí | Valor `token` del enlace (`default_token_generator` de Django). |
| `password` | string | Sí | Nueva contraseña. |

El token de Django vence según `PASSWORD_RESET_TIMEOUT` (no se redefine en settings; el valor por defecto de Django es 3 días) y deja de servir en cuanto la contraseña cambia. La contraseña pasa por `AUTH_PASSWORD_VALIDATORS`: similitud con datos del usuario, longitud mínima (8 por defecto), contraseñas comunes y solo numéricas.

Al confirmar, todos los refresh tokens emitidos al usuario pasan a la lista negra: se cierran sus sesiones en otros navegadores cuando intenten renovar.

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/auth/password-reset/confirm/ \
  -H "Content-Type: application/json" \
  -d '{"uid": "<UID>", "token": "<TOKEN_RECUPERACION>", "password": "<NUEVA_CONTRASEÑA>"}'
```

Respuesta `200`:

```json
{"message": "Contraseña actualizada. Ya puedes iniciar sesión."}
```

Errores:

| Código | Causa | Cuerpo |
|---|---|---|
| `400` | `uid` o `token` inválidos o vencidos, o usuario inactivo. | `{"error": "El enlace es inválido o ha expirado."}` |
| `400` | La contraseña no cumple los validadores. | `{"password": ["Esta contraseña es demasiado corta. Debe contener al menos 8 caracteres.", "..."]}` |
| `429` | Más de 5 intentos por hora. | Mensaje estándar de throttling. |

## POST /api/auth/change-password/

`ChangePasswordView`, permiso `IsAuthenticated`. Cambia la contraseña del usuario del token.

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `current_password` | string | Sí | Contraseña actual. |
| `new_password` | string | Sí | Nueva contraseña (validadores de Django). |

```bash
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/auth/change-password/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"current_password": "<CONTRASEÑA_ACTUAL>", "new_password": "<NUEVA_CONTRASEÑA>"}'
```

Respuesta `200`:

```json
{"message": "Contraseña actualizada."}
```

Errores: `400 {"current_password": ["La contraseña actual no es correcta."]}`, `400 {"new_password": [...]}` si no cumple los validadores, `401` sin token.

A diferencia del restablecimiento por correo, este cambio no invalida los refresh tokens existentes.

Para que un administrador asigne la contraseña de otro usuario existe `POST /api/users/{id}/set-password/` (ver [usuarios-y-agentes.md](./usuarios-y-agentes.md)).

## Uso del token en otras peticiones

```bash
curl -s "https://<IP_DEL_SERVIDOR>/api/campaigns/?status=active" \
  -H "Authorization: Bearer <TOKEN>"
```

Respuestas cuando el token no sirve:

```json
{"detail": "Las credenciales de autenticación no se proveyeron."}
```

```json
{
  "detail": "El token dado no es valido para ningún tipo de token",
  "code": "token_not_valid",
  "messages": [
    {"token_class": "AccessToken", "token_type": "access", "message": "El token ha expirado"}
  ]
}
```

(Los textos dependen de las traducciones de simplejwt para el idioma activo.)

El WebSocket de tiempo real y el WebSocket SIP no usan esta cabecera: ver [websockets.md](./websockets.md) y la sección de credenciales WebRTC en [telefonia.md](./telefonia.md).

## Cómo renueva el token el frontend

El frontend Nuxt guarda la sesión en `frontend/stores/auth.ts` (`setAuth`): el access en `localStorage['auth_token']` y la cookie `access_token` (8 h); el refresh en `localStorage['auth_refresh_token']` y la cookie `refresh_token` (7 días); el usuario en `localStorage['auth_user']`. Las cookies las crea el cliente con `sameSite: 'strict'`; el backend no emite cookies de sesión JWT.

Hay dos mecanismos de renovación ante un `401`:

1. `frontend/plugins/fetch-auth.client.ts` envuelve el `$fetch` global para toda URL que empiece por `/api/` (excepto `auth/login`, `auth/refresh` y `auth/password-reset`):
   - Inyecta siempre el access token actual de `localStorage`.
   - Ante un `401` llama una sola vez a `POST /api/auth/refresh/` (las peticiones concurrentes esperan la misma promesa), guarda el `access` y el `refresh` nuevos en `localStorage` y en el store, y reintenta la petición original una vez.
   - Si la renovación falla, limpia la sesión y navega a `/login`.
2. `frontend/plugins/api.ts` (instancia `$api`): ante un `401` renueva en segundo plano con el refresh leído primero de la cookie `refresh_token` y luego de `localStorage`, guarda solo el `access` nuevo y no reintenta la petición; la siguiente llamada ya sale con el token nuevo. Si falla, muestra "Sesión expirada" y redirige a `/login`.

`frontend/composables/useAuth.ts` ofrece además `refreshToken()` manual y `logout()`, que envía el refresh a `/api/auth/logout/` y limpia el store.

Con la rotación activa, el refresh anterior queda en lista negra en cada renovación. El plugin `api.ts` no guarda el refresh nuevo y lee primero la cookie `refresh_token`, que solo se escribe en el login. Después de una rotación esa cookie puede contener un refresh ya invalidado, y una renovación por ese camino termina en `/login`. Cualquier cliente propio debe reemplazar siempre el refresh guardado por el que devuelve `auth/refresh/`.

Flujo recomendado para integraciones:

```bash
# 1. Login
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "integracion", "password": "<CONTRASEÑA>"}'

# 2. Usar el access token hasta recibir 401
curl -s https://<IP_DEL_SERVIDOR>/api/calls/ -H "Authorization: Bearer <TOKEN>"

# 3. Renovar y guardar AMBOS tokens devueltos
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<REFRESH_TOKEN>"}'

# 4. Al terminar, invalidar el refresh
curl -s -X POST https://<IP_DEL_SERVIDOR>/api/auth/logout/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<REFRESH_TOKEN>"}'
```

Véase también: [Glosario](../general/glosario.md), [Desarrollo del backend](../desarrollo/backend.md).
