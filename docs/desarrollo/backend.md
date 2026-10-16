# Backend

Este documento describe cómo está organizado el backend Django de VozipCX para quien va a modificarlo: puntos clave de `settings.py`, apps y modelos, capa de API y permisos, tareas de Celery y su programación, WebSockets con Channels, el ciclo de vida del listener AMI, las señales que regeneran la configuración de Asterisk y los pasos para agregar un endpoint o una migración. Los servicios en ejecución (Gunicorn, Daphne, worker, beat) se describen en [Arquitectura](../general/arquitectura.md); la referencia de endpoints para consumidores está en [API](../api/README.md).

## Stack

Versiones fijadas en `backend/requirements/base.txt`: Django 4.2.9, djangorestframework 3.14.0, djangorestframework-simplejwt 5.3.1, channels 4.0.0, channels-redis 4.1.0, daphne 4.0.0, celery 5.3.4, django-celery-beat 2.5.0, django-celery-results 2.5.1, drf-spectacular 0.27.0, django-prometheus 2.3.1, panoramisk 1.4, psycopg2-binary 2.9.9 y redis 5.0.1. `django-allauth` está instalado pero no aparece en `INSTALLED_APPS`.

## settings.py

Hay un único módulo, `backend/config/settings.py`, sin paquete `settings/` ni separación dev/prod. Todo se lee con `python-decouple` y `DEBUG` activa o desactiva los bloques de producción.

| Tema | Comportamiento |
|---|---|
| Arranque seguro | Con `DEBUG=False`, aborta si `SECRET_KEY` es el valor inseguro por defecto o si falta `FIELD_ENCRYPTION_KEY` |
| `ALLOWED_HOSTS` | Lista separada por comas; agrega sola `VOZIPOMNI_IPV4` |
| Usuario | `AUTH_USER_MODEL = 'users.User'`; `apps.users` va antes de `django.contrib.admin` en `INSTALLED_APPS` |
| Base de datos | `DATABASE_URL` si existe; si no, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (o `POSTGRES_PASSWORD`), `DB_HOST`, `DB_PORT`. `CONN_MAX_AGE=600` |
| Idioma y zona | `es-co`, `America/Bogota`, `USE_TZ=True` |
| DRF | `JWTAuthentication` + `SessionAuthentication`; permiso por defecto `IsAuthenticated`; `PageNumberPagination` con `PAGE_SIZE=50`; filtros django-filter, búsqueda y orden |
| Throttling | `anon 20/minute`, `user 200/minute`, y alcances `login 5/minute`, `password_reset 5/hour`, `webchat 60/minute` |
| JWT | Acceso 8 h, refresco 7 días, rotación con lista negra (`BLACKLIST_AFTER_ROTATION`) |
| Channels | `channels_redis.core.RedisChannelLayer` sobre `REDIS_URL` (`capacity 1500`, `expiry 10`) |
| Caché | No hay `CACHES`: Django usa `LocMemCache`, local a cada proceso. `apps/api/health_urls.py` prueba esa caché, no Redis |
| CORS | `CORS_ALLOW_ALL` o `CORS_ORIGINS`; con `DEBUG` y sin lista permite `localhost:3000` y `127.0.0.1:3000`. No se define `CSRF_TRUSTED_ORIGINS` |
| Producción | `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, cookies seguras, HSTS, `X_FRAME_OPTIONS='DENY'` |
| Telefonía | `ASTERISK_HOST`, `ASTERISK_AMI_*`, `ASTERISK_CONFIG_DIR`, `PJSIP_CONFIG_PATH`, `TURN_*`, `SIP_WS_TICKET_TTL` |
| Celery | Broker `REDIS_URL`, resultados en `django-db`, `CELERY_BEAT_SCHEDULER` = `DatabaseScheduler`, límite de 30 min por tarea |

Rutas raíz en `backend/config/urls.py`: `admin/`, `/metrics` (django_prometheus), `api/`, `api/health/`, `api/schema/` y `api/docs/` (Swagger). `backend/config/asgi.py` combina HTTP y WebSocket con `JwtAuthMiddlewareStack` y deja fuera `AllowedHostsOriginValidator` a propósito (nginx hace de proxy).

## Apps y modelos principales

| App | Modelos | Notas |
|---|---|---|
| `users` | `User` (`role`: `admin`, `supervisor`, `agent`, `analyst`) | `VozipOmniUserManager` fuerza `role='admin'` en superusuarios |
| `agents` | `Agent`, `AgentStatusHistory`, `AgentBreakReason`, `AgentGroup` | Extensión y clave SIP, estado, métricas del día |
| `campaigns` | `Campaign`, `CampaignForm`, `CampaignDisposition` | `services.py` y tareas del marcador |
| `contacts` | `ContactList`, `Contact`, `ContactNote`, `Blacklist` | `Contact.attempts`, `status`, teléfonos alternos |
| `queues` | `Queue`, `QueueMember`, `QueueStats` | Generan `queues_dynamic.conf` |
| `telephony` | `Call`, `SIPTrunk`, `Extension`, `InboundRoute`, `OutboundRoute`, `IVR`, `Voicemail`, `MusicOnHold`, `CustomDestination`, `TimeCondition`, `CallbackRequest`, `WebhookEndpoint`, `WebhookDelivery`, `TelephonySecurityPolicy`, `TelephonySecurityEvent` | Núcleo de voz |
| `recordings` | `Recording`, `RecordingNote`, `EvaluationTemplate`, `RecordingEvaluation` | Grabaciones y calidad |
| `reports` | `Report` | Reportes generados y programados |
| `audit` | `CallDispositionAudit` | Auditoría de gestiones |
| `messaging` | `Channel`, `Conversation`, `Message`, `WhatsAppProvider`, `WhatsAppLine`, `WhatsAppTemplate`, `WhatsAppBroadcast`, `EmailAccount`, `WebChatWidget`, `MetaPage`, `QuickReply`, `ConversationTag`... | Omnicanal |
| `api` | Sin modelos | Router, viewsets transversales, serializers, consumers |

`backend/core/` no está en `INSTALLED_APPS`. Contiene permisos, `websocket_auth.py`, `fields.py` (`EncryptedCharField`), `events.py` y `event_handlers.py`, entre otros. Como `core.apps.CoreConfig.ready()` nunca se ejecuta, los receptores de `core/event_handlers.py` (por ejemplo `on_campaign_started`, que encola `queue_campaign_in_dialer`) probablemente no quedan conectados. No se verificó en ejecución; tenerlo en cuenta al depurar el inicio de campañas (ver [Marcador](./marcador.md)).

## Capa de API

Todo cuelga de `/api/` a través de `backend/apps/api/urls.py`:

- Autenticación: `auth/login/` (`CustomTokenObtainPairView`), `auth/refresh/`, `auth/me/`, `auth/logout/`, `auth/password-reset/`, `auth/password-reset/confirm/`, `auth/change-password/`.
- `webhooks/whatsapp/<app_id>/` (webhook público de Meta) va antes del router para no chocar con `/api/webhooks/`.
- Router DRF principal (ver tabla).
- `telephony/` incluye `apps/telephony/urls.py`: router propio (`calls`, `trunks`, `ivr`, `extensions`, `inbound-routes`, `outbound-routes`, `voicemail`, `music-on-hold`, `time-conditions`, `custom-destinations`, `security/events`) y rutas `webrtc-credentials/`, `sip-ws-auth/` y `security/policy/...`.
- `messaging/` incluye `apps/messaging/urls.py`.
- `cc/`: `screen-pop/`, `available-agents/`, `consultive-transfer/`, `conference/`, `dnc-check/`, `bulk-import/`, `quality-stats/`.

| Archivo | Contenido |
|---|---|
| `apps/api/viewsets.py` | `CampaignViewSet`, `CampaignFormViewSet`, `AgentViewSet`, `ContactViewSet`, `ContactListViewSet`, `QueueViewSet`, `CallViewSet`, `RecordingViewSet` |
| `apps/api/admin_viewsets.py` | Usuarios (`IsAdminUser`; el DELETE desactiva), lista negra, plantillas y evaluaciones de calidad, recuperación y cambio de contraseña |
| `apps/api/cc_viewsets.py` | Callbacks, webhooks salientes, screen pop, transferencia consultiva, conferencia, DNC, importación masiva, estadísticas de calidad |
| `apps/api/extra_viewsets.py` | Razones de pausa, grupos de agentes, auditoría |
| `apps/api/supervisor_viewsets.py` | `SupervisorViewSet`: tablero y escucha, susurro e intrusión |
| `apps/telephony/views.py` | Recursos de telefonía (incluido `SIPTrunkViewSet`, registrado también como `/api/trunks/`) |
| `apps/reports/views.py` | `ReportViewSet` registrado como `/api/reports/` |

Duplicados a tener presentes: `/api/calls/` y `/api/telephony/calls/` son viewsets distintos con el mismo `basename`, y `/api/trunks/` convive con `/api/telephony/trunks/`. `apps/reports/urls.py` existe pero nadie lo incluye.

## Permisos

`backend/core/permissions.py` define el control por rol. Todas las clases exigen usuario autenticado y, salvo las dos últimas, un superusuario pasa siempre.

| Clase | Regla |
|---|---|
| `IsAdminUser` | `role == 'admin'` |
| `IsAdminOrSupervisor` | `admin` o `supervisor` |
| `IsAdminOrSupervisorOrReadOnly` | Lectura para cualquier autenticado; escritura para `admin` o `supervisor` |
| `IsAdminSupervisorOrAnalyst` | `admin` y `supervisor` total; `analyst` solo métodos seguros; `agent` denegado |
| `IsAgentUser` | `role == 'agent'` (sin excepción para superusuario) |
| `IsOwnerAgentOrAdminSupervisor` | A nivel de objeto: `admin`/`supervisor`, o el agente dueño (`obj.user` u `obj.agent.user`) |

El frontend tiene su propia matriz de rutas por rol en `frontend/utils/navigation.ts`; es solo interfaz. La autorización real es la del backend: cada vista nueva debe declarar `permission_classes`.

## Tareas de Celery

| Módulo | Tareas |
|---|---|
| `apps/campaigns/tasks.py` | `campaigns.queue_campaign_in_dialer`, `campaigns.stop_campaign_in_dialer`, `campaigns.process_pending_calls`, `campaigns.update_campaign_statistics` |
| `apps/agents/tasks.py` | `update_prometheus_metrics`, `update_agent_statistics`, `reset_daily_agent_metrics`, `close_agent_status_history` |
| `apps/telephony/tasks.py` | `sync_all_telephony_config_to_redis`, `check_asterisk_health`, `run_ami_cdr_listener`, `deliver_webhook`, `detect_orphan_calls`, `process_pending_callbacks`, `check_fraud_alerts`, `reset_extension_rate_counters` |
| `apps/recordings/tasks.py` | `recordings.link_recording_to_call`, `recordings.scan_unlinked_recordings`, `recordings.cleanup_old_recordings`, `recordings.transcribe_recording` |
| `apps/reports/tasks.py` | `generate_report`, `generate_campaign_report`, `run_scheduled_reports`, `generate_daily_reports` |
| `apps/messaging/tasks.py` | Envío y descarga de medios de WhatsApp, `sync_all_whatsapp_templates`, `poll_email_accounts`, `process_broadcast_batch`, `dispatch_scheduled_broadcasts` |

### Programación periódica

Hay dos definiciones y conviene conocer ambas:

- `CELERY_BEAT_SCHEDULE` en `settings.py`: callbacks (60 s), `campaigns.process_pending_calls` (60 s), métricas Prometheus y de agentes (60 s), reinicio diario de métricas (00:01), cierre de historial (cada 6 h), llamadas huérfanas (300 s), salud de Asterisk (120 s), sincronización de telefonía (cada 5 min), alertas antifraude (120 s), contadores por extensión (03:15), grabaciones sin vincular (cada 15 min), reportes programados (01:30), correo y envíos masivos (60 s), plantillas de WhatsApp (cada 2 h) y retención de grabaciones (02:00).
- `app.conf.beat_schedule` en `backend/config/celery.py`, que se asigna después de `config_from_object` y en principio reemplaza al de `settings.py`. Tiene menos entradas y dos nombres que no coinciden con los registrados: `apps.campaigns.tasks.process_pending_calls` (registrada como `campaigns.process_pending_calls`) y `apps.recordings.tasks.cleanup_old_recordings` (registrada como `recordings.cleanup_old_recordings`).

Beat usa `DatabaseScheduler`, así que las entradas terminan en las tablas de `django_celery_beat` y se pueden revisar en el admin (`/admin/django_celery_beat/periodictask/`). No se confirmó en ejecución cuál de las dos definiciones queda activa; revíselo en esa tabla antes de asumir una frecuencia. Al agregar una tarea periódica, dé a la tarea un `name=` explícito y use ese mismo nombre en la programación.

## WebSockets (Channels)

`core/websocket_auth.py` (`JwtAuthMiddleware`) toma `?token=<JWT de acceso>` del query string; si no es válido, el usuario queda anónimo. Rutas en `backend/apps/api/routing.py`:

| Ruta | Consumer | Grupos | Acceso |
|---|---|---|---|
| `ws/agent/<agent_id>/` | `consumers.AgentConsumer` | `agent_<id>` | Dueño del agente, admin o supervisor; cierra con 4401 o 4403 |
| `ws/campaign/<campaign_id>/` | `consumers.CampaignConsumer` | `campaign_<id>` | Admin, supervisor, analista o agente asignado |
| `ws/dashboard/` | `consumers_enhanced.RealtimeDashboardConsumer` | `dashboard`, `asterisk_events` | Staff, superusuario o rol admin/supervisor/analista; envía datos iniciales al conectar |
| `ws/asterisk/` | `consumers_enhanced.AsteriskEventConsumer` | `asterisk_events`, `agent_<id>` | Autenticado; los agentes reciben eventos filtrados por su extensión |
| `ws/messaging/` | `consumers.MessagingConsumer` | `messaging_all`, `messaging_agent_<id>`, `messaging_unassigned` | Admin/supervisor o agente |
| cualquier otra | `NotFoundConsumer` | – | Cierra con 4404 |

Para emitir a esos grupos desde código síncrono se usa `async_to_sync(get_channel_layer().group_send)(grupo, {'type': '<handler>', ...})`, como en `_push_ws_event` de `ami_cdr_listener.py` (tipos `asterisk_event` y `dashboard_update`) y en `_push` de `apps/telephony/security.py`. El formato de mensajes para clientes está en [API](../api/README.md).

## Listener AMI

`backend/apps/telephony/ami_cdr_listener.py` es un hilo daemon dentro del worker de Celery.

1. Arranque: `config/celery.py` conecta `worker_ready` con `start_listener()`. También existe la tarea `run_ami_cdr_listener`. `start_listener()` es idempotente y no hace nada si falta `ASTERISK_AMI_PASSWORD`.
2. Configuración: lee `ASTERISK_HOST`, `ASTERISK_AMI_PORT`, `ASTERISK_AMI_USER` y `ASTERISK_AMI_PASSWORD` directo de `os.environ`, no de `settings`.
3. Conexión: socket TCP, lectura del banner (una sola línea) y `Action: Login` con `Events: system,call,agent,cdr,dialplan,user`.
4. Bucle: `Action: Ping` cada 30 s; cada 10 min limpia estados de llamada de más de 2 h; separa eventos por `\r\n\r\n` y los despacha con `_EVENT_HANDLERS`. Un error en un handler se registra y no corta el bucle.
5. Reconexión: ante error o cierre envía `Action: Logoff`, espera 5 s y duplica la espera hasta 60 s; al volver a conectar la espera vuelve a 5 s.
6. Parada: `stop_listener()` activa `_stop_event` y espera el hilo hasta 10 s.

El estado por llamada vive en memoria (`_call_state`, por `Uniqueid`): si el worker se reinicia a mitad de una llamada, se pierden la hora de entrada a cola, las retenciones y el resultado AMD de esa llamada. Cómo se convierte el evento `Cdr` en `Call` está en [Telefonía interna](./telefonia-interna.md).

Solo debe haber un worker con el listener: cada worker que arranque abrirá su propia sesión AMI y procesará los mismos eventos.

## Señales

| Archivo | Disparador | Efecto |
|---|---|---|
| `apps/telephony/signals.py` | `post_save`/`post_delete` de `SIPTrunk`, `InboundRoute`, `OutboundRoute`, `Extension`, `IVR`, `Voicemail`, `TimeCondition`, `Queue`, `QueueMember` | `sync_asterisk_now()`: hilo que regenera troncales y dialplan y recarga Asterisk por AMI; un `_sync_lock` no bloqueante evita ejecuciones simultáneas |
| `apps/telephony/signals.py` | `post_save`/`post_delete` de `Agent` | Regenera `pjsip_agents.conf` y recarga `res_pjsip.so` |
| `apps/telephony/signals.py` | `post_save` de `Call` | Suma `calls_today` y despacha webhooks (`call.initiated`, `call.answered`, `call.completed`, `call.abandoned`) con `deliver_webhook.delay` |
| `apps/agents/signals.py` | `post_save` de `Agent` (si cambian extensión, clave SIP o `webrtc_enabled`) | Crea o ajusta la `Extension` asociada y recarga PJSIP |

`TelephonyConfig.ready()` registra las señales y además lanza una sincronización inicial a los 10 s si `pjsip_wizard.conf` falta y hay troncales activas.

Consecuencias prácticas: guardar un modelo de telefonía en un bucle (por ejemplo, una importación masiva) dispara muchas regeneraciones; el candado descarta las que llegan mientras otra está en curso, así que la última escritura puede no quedar reflejada hasta la siguiente sincronización. Para cambios masivos, desactive la lógica o ejecute al final `python manage.py generate_asterisk_config`.

## Agregar un endpoint

1. Modelo y serializer en la app (`apps/<app>/models.py`, `serializers.py`).
2. ViewSet con `permission_classes` explícitas de `core.permissions` y `queryset` con `select_related`/`prefetch_related` si hay relaciones.
3. Registro:
   - Recurso de telefonía o mensajería: en `apps/telephony/urls.py` o `apps/messaging/urls.py` (queda bajo `/api/telephony/` o `/api/messaging/`).
   - Recurso transversal: `router.register(...)` en `apps/api/urls.py`, con un `basename` que no exista ya.
   - Vista puntual (`APIView`): `path(...)` en el `urlpatterns` que corresponda.
4. Si toca Asterisk, conecte la regeneración en `apps/telephony/signals.py` o llame a `sync_asterisk_now()`.
5. Documente el endpoint en `docs/api/` y pruébelo en `/api/docs/`.
6. Agregue pruebas en `apps/<app>/tests/` (ver [Pruebas y CI](./pruebas-y-ci.md)).

Endpoints públicos (`AllowAny`, como `sip-ws-auth/` o los de recuperación de contraseña) deben tener un throttle y no devolver datos sensibles.

## Agregar una migración

```powershell
docker compose exec backend python manage.py makemigrations <app>
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py showmigrations <app>
```

- Revise el archivo generado antes de confirmarlo y dele un nombre descriptivo (`--name`), como hacen `apps/agents/migrations/0003_add_performance_indexes.py` o `0008_fill_empty_sip_passwords.py`.
- Las migraciones de datos (`RunPython`) deben tener función inversa o `migrations.RunPython.noop` para poder revertir.
- En producción el contenedor `backend` ejecuta `migrate` al arrancar, así que una migración que falle deja el backend sin llegar a healthy. Pruébela con una copia de la base.
- Si agrega un campo cifrado (`EncryptedCharField`), recuerde que depende de `FIELD_ENCRYPTION_KEY`; vea el comando `encrypt_sip_passwords` como referencia.

## Comandos de gestión

| Comando | Uso |
|---|---|
| `generate_asterisk_config` | Regenera extensiones, troncales y dialplan y recarga por AMI (`--no-reload`, `--only-extensions`, `--only-trunks`) |
| `encrypt_sip_passwords` | Cifra contraseñas existentes de extensiones y troncales (`--dry-run`) |

## Ver también

- [Arquitectura](../general/arquitectura.md)
- [Glosario](../general/glosario.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [API](../api/README.md)
- [Entorno local](./entorno-local.md)
- [Estructura del código](./estructura-del-codigo.md)
- [Frontend](./frontend.md)
- [Telefonía interna](./telefonia-interna.md)
- [Marcador](./marcador.md)
- [Pruebas y CI](./pruebas-y-ci.md)
- [Contribuir](./contribuir.md)
