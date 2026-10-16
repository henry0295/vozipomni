# Estructura del código

Este documento recorre el repositorio de VozipCX carpeta por carpeta y explica para qué sirve cada directorio y archivo importante, de modo que un desarrollador nuevo sepa dónde buscar antes de cambiar algo. También clasifica los scripts de la raíz: cuál es el vigente para instalar y actualizar, cuáles son utilidades de operación y cuáles parecen legados, indicando en cada caso la evidencia encontrada. La relación entre los servicios en ejecución está en [Arquitectura](../general/arquitectura.md).

## Vista general

```text
vozipomni/
├── backend/            Django 4.2 + DRF + Channels + Celery
├── frontend/           Nuxt 3 (SPA, ssr:false) + Nuxt UI v2 + Pinia + JsSIP
├── dialer_engine/      Marcador asyncio (Redis + AMI con panoramisk)
├── websocket_server/   Servidor WebSocket auxiliar (aiohttp + Redis)
├── docker/             Imágenes y configuración de Asterisk, Kamailio, RTPEngine, nginx, etc.
├── docs/               Documentación (este árbol)
├── tests/load/         Prueba de carga con k6
├── .github/workflows/  CI (ci.yml)
├── logs/               Carpeta montada para logs del backend (solo .gitkeep en el repo)
├── docker-compose.yml             Desarrollo (red bridge, puertos publicados)
├── docker-compose.prod.yml        Producción (la que usa deploy.sh)
├── env.template, .env.example     Plantillas de variables
└── scripts .sh / .ps1             Instalación, operación y utilidades
```

## backend/

```text
backend/
├── manage.py
├── Dockerfile            python:3.11-slim, instala requirements/prod.txt, usuario no root, CMD gunicorn
├── pytest.ini            Configuración de pytest (ver Pruebas y CI)
├── requirements.txt      Solo "-r requirements/base.txt"
├── requirements/         base.txt, dev.txt, prod.txt (versiones fijas)
├── config/
│   ├── settings.py       Único módulo de settings (python-decouple), sin separación dev/prod
│   ├── celery.py         App Celery, beat_schedule propio y arranque del listener AMI (worker_ready)
│   ├── urls.py           admin/, /metrics (django_prometheus), api/, api/health/, api/schema/, api/docs/
│   ├── asgi.py           ProtocolTypeRouter: HTTP + WebSocket con JwtAuthMiddlewareStack
│   ├── wsgi.py           Entrada de Gunicorn
│   ├── dialer_config.py, recording_config.py   Parámetros del marcador (lado Django) y retención de grabaciones
├── core/                 Código transversal (no está en INSTALLED_APPS)
│   ├── permissions.py    Permisos DRF por rol
│   ├── websocket_auth.py Middleware JWT por query string para Channels
│   ├── fields.py         EncryptedCharField (usa FIELD_ENCRYPTION_KEY)
│   ├── events.py, event_handlers.py   Señales de dominio (campaña iniciada, agente conectado...)
│   ├── circuit_breaker.py, metrics.py, validators.py, exceptions.py, logging_config.py
│   └── tests/            base.py, conftest.py, factories.py, helpers.py
└── apps/
    ├── users/            Modelo User (roles) y su manager
    ├── agents/           Agent, historial de estados, pausas, grupos; signals y tasks
    ├── campaigns/        Campaign, formularios y disposiciones; services y tasks del marcador
    ├── contacts/         ContactList, Contact, notas y lista negra (DNC)
    ├── queues/           Queue, QueueMember, QueueStats
    ├── telephony/        Call, troncales, rutas, IVR, extensiones; generación de config Asterisk y AMI
    ├── recordings/       Recording, evaluaciones de calidad; tasks de vinculación y retención
    ├── reports/          Report y tareas de reportes programados
    ├── audit/            Auditoría de gestiones
    ├── messaging/        Omnicanal: WhatsApp, email, chat web, Messenger/Instagram
    └── api/              Router DRF, viewsets transversales, serializers y consumers de Channels
```

Archivos clave dentro de `apps/telephony/`:

| Archivo | Propósito |
|---|---|
| `asterisk_config.py` | `AsteriskConfigGenerator`: escribe `extensions_dynamic.conf`, colas, buzones, música en espera y `pjsip_extensions.conf` |
| `pjsip_config_generator.py` | `PJSIPConfigGenerator`: troncales en `pjsip_wizard.conf` y recarga PJSIP |
| `asterisk_ami.py` | Cliente AMI por socket (`AsteriskAMI`): login, recargas, comandos |
| `ami_cdr_listener.py` | Hilo que escucha eventos AMI y crea los registros `Call` |
| `signals.py` | Regenera la configuración de Asterisk al guardar o borrar modelos de telefonía |
| `security.py`, `security_views.py` | Política antifraude, contexto `vozip-outbound-policy` y su API |
| `webrtc_views.py` | Credenciales TURN temporales y ticket del WebSocket SIP |
| `tasks.py` | Salud de Asterisk, callbacks, webhooks, alertas antifraude, llamadas huérfanas |
| `management/commands/` | `generate_asterisk_config` y `encrypt_sip_passwords` |

`apps/api/` concentra la API pública: `urls.py` (router), `viewsets.py`, `admin_viewsets.py`, `cc_viewsets.py`, `extra_viewsets.py`, `supervisor_viewsets.py`, `routing.py`, `consumers.py`, `consumers_enhanced.py` y `health_urls.py`. El detalle está en [Backend](./backend.md).

## frontend/

```text
frontend/
├── nuxt.config.ts        Módulos, ssr:false, runtimeConfig (apiBase, wsBase), iconos
├── app.vue               NuxtLayout + NuxtPage + un único <UNotifications />
├── package.json          Scripts dev/build/lint; nuxt 3, @nuxt/ui 2, pinia, jssip
├── Dockerfile, Dockerfile.dev
├── assets/css/main.css   Directivas Tailwind y variables de color
├── layouts/              default.vue (menú lateral), agent.vue (consola), auth.vue (login)
├── middleware/           access.global.ts, auth.ts, agent-only.ts, guest.ts
├── plugins/              api.ts ($api), auth.client.ts, fetch-auth.client.ts ($fetch global)
├── stores/               auth.ts, agent.ts (Pinia)
├── composables/          useHttp, useApi, useAuth, useWebRTC, useWebSocket y CRUD por recurso
├── components/           AgentSoftphone, ScreenPop, AgentDialerPanel, forms/, messaging/...
├── pages/                Rutas por archivo (admin, supervisor, analista, agent/console)
├── utils/                navigation.ts (menú y permisos por ruta), format, validation...
├── types/index.ts        Tipos compartidos
└── public/               Estáticos
```

Restos de una versión React/Vite que Nuxt no usa: `src/*.jsx`, `index.html`, `vite.config.js`, `MIGRATION_GUIDE.md` y `COMPARACION_REACT_VS_NUXT.md`. Nuxt 3 no toma `src/` ni `vite.config.js` como parte de la aplicación; se pueden ignorar al buscar código. Ver [Frontend](./frontend.md).

## dialer_engine/ y websocket_server/

| Ruta | Propósito |
|---|---|
| `dialer_engine/dialer.py` | Todo el marcador: canal de control Redis, bucles por modo, `Originate`, AMD, antifraude |
| `dialer_engine/Dockerfile` | `python:3.11-slim`, copia solo `dialer.py`, `CMD ["python", "dialer.py"]` |
| `dialer_engine/requirements.txt` | `redis`, `panoramisk`, `aiohttp` y otras, con versión fija |
| `websocket_server/server.py` | Servidor aiohttp en el puerto 8765 que se suscribe a `calls:events` en Redis |

nginx no publica `websocket_server` y no se encontró uso desde el frontend (ver [Arquitectura](../general/arquitectura.md)). Detalle del marcador en [Marcador](./marcador.md).

## docker/

| Ruta | Propósito |
|---|---|
| `asterisk/configs/` | Configuración estática montada en `/etc/asterisk` (`pjsip.conf`, `extensions.conf`, `manager.conf`, `queues.conf`, `rtp.conf`...) |
| `asterisk/entrypoint.sh` | Detecta IP, inyecta `external_*_address`, genera `kamailio_identify.conf`, fija la clave AMI y los `permit` |
| `asterisk/Dockerfile.prebuilt` | Imagen que usa `docker-compose.prod.yml`; también hay `Dockerfile` y `Dockerfile.source` |
| `kamailio/kamailio.cfg` | Enrutamiento SIP de agentes WebRTC; `entrypoint.sh` reemplaza los marcadores `*_PLACEHOLDER` |
| `kamailio/kamailio-local.cfg`, `kamailio/tls.cfg` | Copiados por el `Dockerfile`; TLS está deshabilitado en `kamailio.cfg` |
| `rtpengine/` | `Dockerfile`, `entrypoint.sh`, `rtpengine.conf` |
| `nginx/default.conf` | Configuración del compose de desarrollo |
| `nginx/default.prod.conf`, `nginx/default.https.conf` | Producción HTTP y HTTPS (con `auth_request` para `/sip/ws`) |
| `nginx/Dockerfile.prod`, `nginx/nginx-ssl-switch.sh` | Imagen de producción: activa HTTPS si encuentra los certificados |
| `nginx/entrypoint.sh` | Desarrollo: quita el bloque HTTPS si no hay certificados |
| `postgresql/init.sql` | Script inicial de la base |
| `prometheus/prometheus.yml`, `grafana/provisioning/` | Monitoreo |

## docs/

`general/` (introducción, arquitectura, glosario), `instalacion/`, `operacion/`, `administracion/`, `manuales/` (por rol), `api/`, `desarrollo/` (este conjunto) y `traza/` (una captura `.pcap` de ejemplo). `CHANGELOG.md` en la raíz de `docs/`.

## Scripts de la raíz

### Vigente

| Script | Uso |
|---|---|
| `deploy.sh` | Instalación y actualización en servidor. Usa `docker-compose.prod.yml`, genera secretos aleatorios, crea el usuario `admin` y soporta `--update`, `--clean` y `--nat`. Es el camino que documentan el `README.md` y [Actualización](../instalacion/actualizacion.md) |

### Utilidades de operación

| Script | Uso |
|---|---|
| `backup-production.sh` | Respaldo sobre `/opt/vozipomni/docker-compose.prod.yml` (ver [Respaldos](../operacion/respaldos.md)) |
| `voip-debug.sh`, `install-debug-tools.sh` | Diagnóstico SIP/RTP (ver [Depuración VoIP](../operacion/depuracion-voip.md)) |
| `diagnostico-extension.sh` | Revisión de una extensión; fija la `100` e imprime el secreto SIP, úselo con cuidado |
| `fix-db-password.sh` | Sincroniza la clave de PostgreSQL; `deploy.sh` lo sugiere cuando falla |
| `generate-dev-ssl.ps1`, `generate-dev-ssl.sh` | Certificados autofirmados para desarrollo |

Los instaladores y scripts de despliegue antiguos (`install.sh`, `init.sh`, `quickstart.sh`, `quick-deploy.sh`, `deploy-simple.sh`, `deploy-server.sh`, `deploy-frontend*.sh`, `prepare-system.sh`, `harden-security.sh`, `security-hardening.sh`, `apply-improvements.sh`, `verify-production.sh`) y `docker-compose.prod.secure.yml` se eliminaron: `deploy.sh` cubre instalación, preparación del sistema, endurecimiento (firewall, fail2ban) y actualización.

### Scripts que no están versionados

`.gitignore` ignora `/*.sh` salvo una lista de excepciones, y también `*.ps1`. Estos archivos existen en algunas copias de trabajo pero no en el repositorio, así que no llegan a un servidor con `git clone` ni con `deploy.sh --update`:

- `install-debug-tools.sh`, `diagnostico-extension.sh`
- `generate-dev-ssl.ps1` (sí está versionado `generate-dev-ssl.sh`)

Si un script debe distribuirse, agréguelo a las excepciones `!<script>.sh` de `.gitignore`.

## Configuración y secretos

- `env.template` y `.env.example` son plantillas; los valores `CHANGE_ME_IN_PRODUCTION` deben reemplazarse.
- `.env`, `.env.production`, `backend/.env`, `credentials.txt` y `docker/nginx/ssl/` contienen secretos o certificados locales. No se versionan ni se copian en tickets o documentación.
- La referencia de variables está en [Variables de entorno](../instalacion/variables-entorno.md).

## Dónde buscar

| Necesito... | Mire en |
|---|---|
| Un endpoint REST | `backend/apps/api/urls.py` y el `urls.py` de la app |
| Un permiso por rol | `backend/core/permissions.py` y `frontend/utils/navigation.ts` |
| Qué se escribe en Asterisk | `backend/apps/telephony/asterisk_config.py`, `signals.py`, `security.py` |
| Cómo llega un evento en vivo | `ami_cdr_listener.py` → grupos de Channels → `consumers_enhanced.py` |
| El softphone | `frontend/composables/useWebRTC.ts`, `components/AgentSoftphone.vue` |
| El enrutamiento SIP | `docker/kamailio/kamailio.cfg` |
| Tareas periódicas | `backend/config/settings.py` y `backend/config/celery.py` |

## Ver también

- [Arquitectura](../general/arquitectura.md)
- [Glosario](../general/glosario.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [API](../api/README.md)
- [Entorno local](./entorno-local.md)
- [Backend](./backend.md)
- [Frontend](./frontend.md)
- [Telefonía interna](./telefonia-interna.md)
- [Marcador](./marcador.md)
- [Pruebas y CI](./pruebas-y-ci.md)
- [Contribuir](./contribuir.md)
