# Frontend

Este documento explica cómo está construido el frontend Nuxt 3 de VozipCX: configuración, layouts, middleware, stores, composables (con énfasis en el cliente HTTP recomendado y en el ciclo de vida del softphone WebRTC), plugins, navegación por rol, convenciones de interfaz con Nuxt UI v2 y los pasos para agregar una página. El papel del frontend dentro de la plataforma y el flujo de señalización del softphone están en [Arquitectura](../general/arquitectura.md).

## Stack y scripts

Según `frontend/package.json`: `nuxt ^3.10.3`, `@nuxt/ui ^2.14.2`, `@pinia/nuxt ^0.5.1` + `pinia ^2.1.7`, `jssip ^3.10.1`, `@vueuse/nuxt ^10.9.0`, `zod ^3.22.4`, iconos `@iconify-json/heroicons` y `@iconify-json/lucide`. Las versiones usan rangos `^`; `npm install` puede resolver versiones más nuevas que las probadas (ver [Contribuir](./contribuir.md)).

| Script | Acción |
|---|---|
| `npm run dev` | Servidor de desarrollo en el puerto 3000 |
| `npm run build` | Build de producción (`.output/`) |
| `npm run preview` | Sirve el build |
| `npm run lint`, `npm run lint:fix` | ESLint (`@nuxtjs/eslint-config-typescript`) |

No hay script de pruebas. La imagen de producción (`frontend/Dockerfile`, `node:20-alpine`) ejecuta `node .output/server/index.mjs` en el puerto 3000; `Dockerfile.dev` ejecuta `npm run dev`.

## nuxt.config.ts

| Clave | Valor | Motivo |
|---|---|---|
| `modules` | `@nuxt/ui`, `@pinia/nuxt`, `@vueuse/nuxt` | Tailwind llega con Nuxt UI |
| `ssr` | `false` | La aplicación es una SPA; Nitro solo sirve el shell y los iconos |
| `colorMode.preference` | `light` | |
| `ui.icons` | `heroicons`, `lucide` | |
| `icon.provider` | `server` con `serverBundle: 'local'` y `fallbackToApi: false` | La CSP bloquea `api.iconify.design`; los iconos salen de `/api/_nuxt_icon` |
| `icon.clientBundle.scan.globInclude` | incluye `.ts` | Para detectar los iconos de `utils/navigation.ts` |
| `typescript.strict` | `true` | |

`runtimeConfig.public` solo tiene dos claves:

| Clave | Variable | Por defecto |
|---|---|---|
| `apiBase` | `NUXT_PUBLIC_API_BASE` | `http://localhost:8000/api` |
| `wsBase` | `NUXT_PUBLIC_WS_BASE` | `ws://localhost:8000/ws` |

En producción ambas son relativas (`/api`, `/ws`) porque nginx sirve todo desde el mismo origen. Las variables `NUXT_PUBLIC_APP_NAME`, `NUXT_PUBLIC_TURN_*` y `NUXT_PUBLIC_KAMAILIO_*` que aparecen en plantillas y en los compose no tienen efecto: no existen en `runtimeConfig`. Las credenciales TURN se piden al backend en tiempo de ejecución.

Si usa un ícono nuevo desde un archivo que el escáner no revisa, o uno interno de Nuxt UI, agréguelo a `icon.clientBundle.icons`; en producción no hay descarga de iconos por HTTP.

## app.vue y notificaciones

`app.vue` renderiza `<NuxtLayout><NuxtPage /></NuxtLayout>` y un único `<UNotifications />` global, y fija `titleTemplate` a `<título> - VozipCX`. El comentario del archivo explica el motivo: si el contenedor de notificaciones solo existiera en algunas páginas, los toasts del resto se acumularían y aparecerían juntos al volver a ellas. No agregue otro `<UNotifications />` en layouts ni páginas; use `useToast().add(...)`.

## Layouts

| Layout | Uso |
|---|---|
| `layouts/default.vue` | Admin, supervisor y analista: encabezado con migas de pan, menú de usuario (`/profile`, cerrar sesión), menú lateral agrupado y `<ScreenPop />` global |
| `layouts/agent.vue` | Contenedor a pantalla completa sin menú, para `/agent/console` |
| `layouts/auth.vue` | Tarjeta centrada para login y recuperación de contraseña |

El menú lateral sale de `navigationForRole(user.role)`; el estado de grupos abiertos se guarda con `useLocalStorage('sidebar-expanded-menus')`, y el ítem activo es la regla de prefijo más largo (`ruleForPath`).

## Navegación y roles

`frontend/utils/navigation.ts` es la fuente única del menú y de los permisos por ruta:

- `Role = 'admin' | 'supervisor' | 'analyst' | 'agent'`.
- `NAVIGATION`: grupos Supervisión, Omnicanal, Operación, Calidad, Reportes, Telefonía y Administración, cada enlace con `roles`. Un enlace sin `roles` queda abierto a cualquier autenticado.
- `canAccessRoute(path, role)`: busca la regla más específica; las rutas sin regla quedan libres para usuarios con sesión.
- `homeForRole(role)`: agente → `/agent/console`, supervisor → `/supervisor`, resto → `/dashboard`.
- `PUBLIC_ROUTES`: `/`, `/login`, `/forgot-password`, `/reset-password`.

Esto es solo experiencia de usuario. El backend aplica sus propios permisos (`backend/core/permissions.py`, ver [Backend](./backend.md)); una ruta visible en el menú no autoriza nada por sí misma.

## Middleware

| Archivo | Tipo | Lógica |
|---|---|---|
| `access.global.ts` | Global, solo cliente | Rutas públicas pasan; sin token → `/login`; un agente solo entra a `/agent/*` y `/profile`; los demás roles no entran a `/agent*`; si `canAccessRoute` falla muestra el toast "Acceso restringido" y redirige a `homeForRole` |
| `auth.ts` | Nombrado | Sin token → `/login`; agente fuera de `/agent/*` → consola; no agente en `/agent/*` → `/dashboard` |
| `agent-only.ts` | Nombrado | Un rol distinto de `agent` → `/dashboard` (lo usa `pages/agent/console.vue` junto con `auth`) |
| `guest.ts` | Nombrado | Usuario con sesión en login o recuperación → su página de inicio |

`pages/profile.vue` declara `middleware: 'auth'`, que manda a los agentes a la consola aunque el guardián global les permita `/profile`. Téngalo presente si trabaja en el perfil del agente.

## Stores (Pinia)

`stores/auth.ts` (`useAuthStore`):

- Estado `user`, `token`, `refreshToken`; getter `isAuthenticated`.
- `setAuth()` guarda en `localStorage` (`auth_token`, `auth_user`, `auth_refresh_token`) y en cookies `access_token` (8 h) y `refresh_token` (7 días) con `sameSite: 'strict'`.
- `loadFromStorage()` rehidrata al arrancar (lo llama `plugins/auth.client.ts`); `clearAuth()` limpia todo.
- El login, logout y refresco viven en `composables/useAuth.ts` (`/auth/login/`, `/auth/logout/` con el refresh para ponerlo en lista negra, `/auth/refresh/`, `/auth/me/`).

`stores/agent.ts` (`useAgentStore`): estado del agente (`status`, `currentCall`, `pauseReason`, estadísticas del día), acciones `login`, `logout`, `changeStatus` (no permite cambiar estando `oncall` salvo a `wrapup`), `startBreak`/`endBreak`, `startCall`/`endCall`, y `connectWebSocket()` a `/ws/agent/<id>/?token=...`, que reintenta a los 3 s salvo cierre 4403.

## Clientes HTTP

Hay tres patrones en el código. Para páginas nuevas use `useHttp`.

### useHttp (recomendado)

`composables/useHttp.ts` es un envoltorio mínimo de `$fetch` con base `apiBase`:

```ts
const http = useHttp()
const data = await http.get('/blacklist/', { page: 1 })
const rows = http.results(data)                 // desempaqueta "results" de DRF
await http.post('/blacklist/', { phone, reason })
await http.patch(`/blacklist/${id}/`, body)
await http.del(`/blacklist/${id}/`)
await http.download('<ruta-que-devuelve-un-archivo>', query, 'archivo.xlsx')
toast.add({ title: 'Error', description: http.errorMessage(err), color: 'red' })
```

No agrega cabeceras ni muestra toasts por su cuenta: el token, el refresco y el reintento los pone `plugins/fetch-auth.client.ts`, y cada página decide qué mensaje mostrar con `errorMessage` (lee `error`, `detail` o el primer campo con error). Para archivos use `blob()`, `download()` y `blobErrorMessage()`.

### useApi (anterior)

`composables/useApi.ts` expone `apiFetch(url, opts)`, que llama a `$api` y devuelve `{ data, error }` sin lanzar excepciones. Lo usan sobre todo los composables CRUD (`useAgents`, `useCampaigns`, `useTrunks`, `useExtensions`, etc.). `$api` sale de `plugins/api.ts` (`$fetch.create` con `baseURL: apiBase`):

- Agrega `Authorization: Bearer` (cookie `access_token` o `localStorage`) y `X-Request-ID`.
- Muestra toasts globales para 400 (por campo), 403, 404, 409, 429 y 5xx (503 silencioso).
- Ante 401 renueva el token en segundo plano, pero no reintenta la petición fallida; solo la siguiente usa el token nuevo.
- Como `$fetch.create` conserva el `create` original, las peticiones de `$api` no pasan por el envoltorio global de `fetch-auth.client.ts`.

No mezcle `useApi` y `useHttp` en la misma página: el primero ya muestra toasts y el segundo no, y terminará con mensajes duplicados o ausentes.

### $fetch directo

Algunas páginas y componentes (por ejemplo `components/ScreenPop.vue`) llaman `$fetch('/api/...')` con un `authHeaders()` local. Funciona porque el envoltorio global intercepta esas URL, pero no lo replique en código nuevo.

## plugins/fetch-auth.client.ts

Reemplaza `globalThis.$fetch` por un envoltorio que:

1. Solo intercepta URL que empiezan por `/api/` o por `apiBase + '/'`, y omite `/auth/login`, `/auth/refresh` y `/auth/password-reset`.
2. Inyecta siempre el `auth_token` vigente de `localStorage` (evita tokens viejos capturados en closures).
3. Ante 401 renueva una sola vez con el refresh token (promesa compartida para peticiones concurrentes), guarda el access y el refresh rotado, y reintenta la petición original una vez.
4. Si la renovación falla, llama `clearAuth()`, navega a `/login` y relanza el error.
5. Conserva `raw`, `native` y `create` del `$fetch` original.

## useWebRTC y el softphone

`composables/useWebRTC.ts` mantiene un solo agente de usuario JsSIP para toda la aplicación: el UA, el elemento de audio y los temporizadores son variables de módulo, y el estado visible (`webrtc_session`, `webrtc_registered`, `webrtc_status`, `webrtc_last_error`, `webrtc_last_call_error`, etc.) usa `useState`. Así `components/AgentSoftphone.vue` y `pages/agent/console.vue` comparten la misma sesión y no quedan llamadas "fantasma".

Ciclo de vida:

1. `AgentSoftphone.vue` llama `register()` con `wsUrl` = origen de la página (ws/wss) + `/sip/ws`, `sipServer` = host de la página, puerto 443 y la extensión del agente.
2. `register()` detiene un UA previo y pide credenciales con `fetchWebRTCCredentials()` → `GET <apiBase>/telephony/webrtc-credentials/`. La respuesta trae `ice_servers` (STUN + TURN temporal) y `ws_ticket`; si `ice_servers` viene vacío se conservan los STUN públicos por defecto.
3. `withTicket()` agrega `?ticket=<ws_ticket>` a la URL del WebSocket (reemplazando uno anterior). nginx valida ese ticket con `auth_request` antes de pasar a Kamailio (ver [Telefonía interna](./telefonia-interna.md)).
4. Se crea `JsSIP.UA` con `register: true`, `session_timers: false` y `use_preloaded_route: false`, envuelto en `markRaw` para que Vue no lo haga reactivo.
5. Un `setInterval` de 30 minutos vuelve a pedir credenciales (las TURN duran 12 h por defecto). Cada reconexión también pide credenciales nuevas, así no se reutilizan tickets vencidos.
6. En `disconnected` programa una reconexión con espera exponencial (máximo 30 s).
7. `newRTCSession`: si ya hay una llamada, termina la nueva; si no, `handleNewSession()` registra `confirmed` (inicia cronómetro, heartbeat cada 30 s a `/api/calls/heartbeat/` y `agentStore.startCall`), `ended` y `failed`.
8. Audio remoto: en llamadas salientes JsSIP ya creó el `RTCPeerConnection` antes de `newRTCSession`, así que se usa `session.connection` directamente; si aún no existe, se espera el evento `peerconnection`. `attachRemoteAudio()` crea un `<audio autoplay playsinline>` oculto, escucha `track` y además revisa `pc.getReceivers()` por si el track (early media) ya había llegado.
9. `call(número)` y `answer()` pasan `pcConfig.iceServers` con los servidores vigentes e `iceTransportPolicy: 'all'`.
10. Fin de llamada: `handleCallEnded()` detiene heartbeat y cronómetro, retira el audio del DOM y llama `agentStore.endCall()`. `unregister()` (en `onUnmounted` del softphone) termina la sesión, detiene el UA y limpia todos los temporizadores, incluido el de credenciales.

Detalles a tener en cuenta al modificarlo: en el manejador `disconnected` el contador `_reconnectAttempts` se pone en cero dentro del `setTimeout`, así que en la práctica el límite de 5 intentos nunca se alcanza. El heartbeat llama `$api('/api/calls/heartbeat/')` aunque `$api` ya tiene `baseURL`; con `apiBase` relativo funciona, con uno absoluto podría duplicar `/api`. Solo se verificó leyendo el código.

## Otros composables

| Composable | Uso |
|---|---|
| `useAuth` | Login, logout, refresco, usuario actual |
| `useAuthorization` | `hasRole`, `isAdmin`, `isSupervisor`, `isAgent`, `canAccess`, `requireRole` |
| `useWebSocket` | `buildWsUrl()` (resuelve `wsBase` relativo con ws/wss y agrega `?token=`) y conexión con reintento hasta 30 s |
| `useFormValidation` | Validación con esquemas zod (`campaignSchema`, `contactSchema`, `sipTrunkSchema`...) |
| `useApiError`, `useErrorBoundary` | Manejo de errores |
| `useReports`, `useMessaging` | Reportes y omnicanal |
| `useAgents`, `useCampaigns`, `useCalls`, `useRecordings`, `useTrunks`, `useExtensions`, `useInboundRoutes`, `useOutboundRoutes`, `useIVR`, `useVoicemail`, `useTimeConditions` | CRUD sobre `apiFetch` |

## Convenciones de interfaz

- Componentes de Nuxt UI v2: `UButton`, `UCard`, `UFormGroup`, `UInput`, `USelect`, `USelectMenu`, `UTable`, `UModal`, `UBadge`, `UTabs`, `UPagination`, `UDropdown`, `UToggle`, `UAlert`. Reutilice esos componentes antes de agregar una librería de interfaz nueva.
- Mensajes con `useToast().add({ title, description, color, timeout })`; rojo para errores, naranja para advertencias, verde para confirmaciones.
- Textos de interfaz en español, directamente en las plantillas; no hay i18n.
- Formularios en `UModal` con `UCard` y botones Cancelar/Guardar en el `#footer` (ver `pages/contacts/blacklist.vue`).
- Iconos `i-heroicons-*` o `i-lucide-*`.
- Tipos compartidos en `types/index.ts`; evite redeclarar `User` o `Role` (ya hay duplicados en `useAuth.ts` y `utils/navigation.ts`).
- Los archivos React de `src/` y `vite.config.js` son restos de una versión anterior y no se usan.

## Agregar una página

1. Cree `pages/<modulo>/index.vue` (o `pages/<modulo>.vue`). La ruta sale del nombre del archivo.
2. En `<script setup lang="ts">` use `const http = useHttp()` y `const toast = useToast()`; cargue datos en `onMounted` y muestre errores con `http.errorMessage(e)`.
3. Si la página no debe usar el layout por defecto, declare `definePageMeta({ layout: 'agent' })` o `'auth'`.
4. Agregue el enlace en `NAVIGATION` de `utils/navigation.ts` con sus `roles`. Sin esa entrada la ruta queda abierta a cualquier usuario con sesión (salvo agentes).
5. Verifique que el endpoint del backend tenga los mismos límites por rol en `permission_classes`.
6. Use `useHead({ title: '...' })` para el título de la pestaña.
7. Ejecute `npm run lint` y `npx vue-tsc --noEmit` antes de abrir el PR (ver [Pruebas y CI](./pruebas-y-ci.md)).

## Ver también

- [Arquitectura](../general/arquitectura.md)
- [Glosario](../general/glosario.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [API](../api/README.md)
- [Entorno local](./entorno-local.md)
- [Estructura del código](./estructura-del-codigo.md)
- [Backend](./backend.md)
- [Telefonía interna](./telefonia-interna.md)
- [Marcador](./marcador.md)
- [Pruebas y CI](./pruebas-y-ci.md)
- [Contribuir](./contribuir.md)
