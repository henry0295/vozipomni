# Marcador

Este documento describe el motor de marcación de VozipCX (`dialer_engine/dialer.py`) para quien lo va a mantener: cómo recibe órdenes del backend, qué hace cada bucle según el modo de campaña, cómo calcula el ritmo del predictivo, cómo origina llamadas por AMI, cómo interpreta el resultado AMD, cómo aplica la política antifraude antes de marcar y cuándo reencola contactos. Cierra con las variables de entorno y una guía de depuración. La ubicación del marcador en la plataforma está en [Arquitectura](../general/arquitectura.md); el contexto `outbound-queue` del dialplan está en [Telefonía interna](./telefonia-interna.md).

## Componentes

| Pieza | Ubicación |
|---|---|
| Motor | `dialer_engine/dialer.py`, clase `DialerEngine` y `main()` |
| Imagen | `dialer_engine/Dockerfile` (`python:3.11-slim`, copia solo `dialer.py`, `CMD ["python", "dialer.py"]`) |
| Dependencias | `dialer_engine/requirements.txt`: `redis==5.0.1`, `panoramisk==1.4`, `aiohttp==3.9.5`, entre otras. El código usa `redis.asyncio`; `aioredis` y `python-dotenv` están listados pero no se importan |
| Servicio | `dialer_engine` en `docker-compose.prod.yml` (`vozipomni_dialer`, `network_mode: host`, depende de `redis` sano y de `asterisk`) |
| Lado Django | `backend/apps/campaigns/tasks.py` (configuración, contactos y órdenes), `backend/apps/telephony/security.py` (política), `backend/apps/telephony/ami_cdr_listener.py` (resultados) |

`backend/config/dialer_config.py` define parámetros como `DIALER_PREDICTIVE_RATIO` y `DIALER_ABANDON_TARGET`, pero ningún módulo lo importa y el motor no lo lee: los valores reales están fijos en `DialerEngine.__init__`.

## Arranque y bucles

`main()` crea un `DialerEngine`, llama `initialize()` y lanza `listen_control_channel()` como tarea asyncio. Cada 5 s hace `ping` a Redis; si falla, cancela la tarea y reconecta. Ante excepciones espera con retroceso exponencial (se duplica antes de dormir, tope 60 s).

`initialize()`:

1. Conecta a Redis (`redis.asyncio.from_url(REDIS_URL, decode_responses=True)`).
2. Conecta a AMI con `panoramisk.Manager(..., ping_delay=10)`.
3. Registra eventos: `Newchannel`, `Hangup`, `AgentConnect`, `AgentComplete` y `UserEvent`.

Cualquier error se reporta como `AMIConnectionError`, incluso si el que falló fue Redis.

`listen_control_channel()` se suscribe a `dialer:control`:

```json
{"action": "start_campaign", "campaign_id": 12, "campaign_type": "predictive"}
{"action": "stop_campaign", "campaign_id": 12}
```

Si falta `campaign_type`, usa `progressive`. `start_campaign()` lee `campaign:<id>:config`, guarda contadores en `active_campaigns` y crea la tarea del modo:

| Modo | Bucle | Espera por ciclo |
|---|---|---|
| `manual` | `manual_dialer_loop` | 2 s (3 s sin agentes) |
| `progressive` | `progressive_dialer_loop` | 2 s |
| `predictive` | `predictive_dialer_loop` | 1 s |
| `preview` | `preview_dialer_loop` | 1 s (2 s sin agentes) |
| `call_blasting` | `call_blasting_loop` | `batch_delay` entre lotes (5 s) |

`stop_campaign()` solo marca `stopped=True`; la entrada sigue en `active_campaigns`, y el canal de control ignora un `start_campaign` para un id que ya está ahí. En la práctica, una campaña detenida no se puede volver a iniciar sin reiniciar el contenedor del marcador.

## Del backend al marcador

`CampaignService.start_campaign()` (`apps/campaigns/services.py`) pone la campaña en `active` y emite la señal `campaign_started`. Su receptor, `on_campaign_started` en `core/event_handlers.py`, encola `campaigns.queue_campaign_in_dialer`. Como `core` no está en `INSTALLED_APPS`, ese receptor probablemente no está conectado (ver [Backend](./backend.md)); el camino que sí existe es la red de seguridad periódica:

- `campaigns.process_pending_calls` recorre las campañas activas dentro de su rango de fechas; si falta `campaign:<id>:config` encola `queue_campaign_in_dialer`, y si existe renueva el TTL de la lista de pendientes.
- `queue_campaign_in_dialer` escribe la configuración (`setex` 24 h), carga contactos con `_push_contacts_to_redis()` y publica `start_campaign` con `campaign_type = dialer_type`.
- `stop_campaign_in_dialer` publica `stop_campaign`.

Ojo con la programación: `settings.py` programa `campaigns.process_pending_calls` cada 60 s, pero `config/celery.py` la programa cada 10 s con el nombre `apps.campaigns.tasks.process_pending_calls`, que no coincide con el registrado. Revise en `/admin/django_celery_beat/periodictask/` cuál quedó activa; si solo está la de nombre incorrecto, las campañas no llegan al marcador.

## Claves de Redis

| Clave | Tipo | Escribe | Lee |
|---|---|---|---|
| `dialer:control` | pub/sub | backend | marcador |
| `campaign:<id>:config` | JSON, TTL 24 h | `queue_campaign_in_dialer` | `get_campaign_config` |
| `campaign:<id>:contacts:pending` | lista de JSON, TTL 24 h | backend (`RPUSH`), marcador al reencolar | marcador (`LPOP`; `LRANGE` en call blasting) |
| `campaign:<id>:agents:available` | set de ids | – | `get_available_agents` |
| `agent:<id>` | JSON con `id` y `extension` | – | `get_available_agents` |
| `call:<call_id>`, `uniqueid:<uid>:call_id`, `channel:<canal>:call_id` | TTL 1 h | marcador | marcador (`on_hangup`, `on_agent_connect`) |
| `campaign:<id>:stats` | hash | marcador | sin lector en el repositorio |
| `calls:completed` | lista | marcador | sin lector en el repositorio |
| `calls:events` | pub/sub | marcador | `websocket_server/server.py` |
| `campaign:<id>:manual:agent:<agent_id>` | TTL 300 s | marcador | – |
| `campaign:<id>:preview:agent:<agent_id>` y `:ts`, `:accepted`, `:rejected` | – | marcador y `CampaignViewSet` (aceptar/rechazar, TTL 120 s) | marcador |
| `telephony:dial_policy` | JSON | `security.publish_policy()` | `_dial_policy()` |
| `telephony:security_events` | lista | marcador | `security._drain_dialer_events()` |
| `dnc:<últimos 10 dígitos>` | `'0'`/`'1'`, TTL 300 s (60 s si hubo error) | marcador | marcador |

Una búsqueda en el repositorio no encontró quién escribe `campaign:<id>:agents:available` ni `agent:<id>`. Sin esas claves, los modos que dependen de agentes (manual, progresivo, predictivo y preview) ven cero agentes y solo duermen. Es lo primero que hay que revisar si una campaña activa no marca.

## Contactos

`_push_contacts_to_redis()` es idempotente: si la lista ya tiene elementos no hace nada. Carga los `Contact` de la lista de la campaña con estado `new`, `pending` o `callback`, ordenados por `-priority, id`, con `id`, `phone_number`, `phone_2`, `phone_3`, `name`, `email`, `company`, `priority`, `is_vip`, `timezone` y `custom_fields`.

`get_next_contact()` revisa hasta 10 contactos por llamada:

1. Elige el primer teléfono no vacío desde `_retry_phone_index` (nunca se incrementa, así que en la práctica siempre es `phone_number` si existe).
2. Con `dnc_enabled`, consulta `POST <BACKEND_URL>/api/cc/dnc-check/` con `Bearer DIALER_API_TOKEN` (caché en `dnc:*`). Si la consulta falla, no bloquea. Un bloqueado se descarta y se publica `contact_skipped_dnc`.
3. `_is_callable_now()` solo permite lunes a sábado de 08:00 a 20:00 en la zona del contacto o de la campaña; fuera de horario lo devuelve al final de la lista (`RPUSH`).
4. Los VIP suben `priority` en `vip_priority_boost`.

## Modos y ritmo

- Manual: asigna el siguiente contacto a cada agente libre (clave con TTL 5 min) y publica `manual_contact_assigned`; el agente marca desde el softphone.
- Preview: asigna un contacto, espera `:accepted` o `:rejected` y, si acepta, origina con el agente. Un rechazo o el vencimiento de `preview_timeout` descartan el contacto sin reencolarlo.
- Progresivo: un contacto por agente disponible, originando primero hacia la extensión del agente.
- Predictivo: `calls_to_make = int(agentes * ratio)`, originando directo al contacto sin agente.
- Call blasting: toma una foto de la lista con `LRANGE` (no la vacía), origina en lotes de `max_concurrent_calls` (50) con `Playback` del `audio_file` y termina tras una pasada. No aplica DNC ni horario.

`calculate_predictive_ratio()`:

- Empieza en 1,5 mientras `calls_made == 0`.
- `abandon_rate = calls_abandoned / calls_answered`.
- Si supera 0,03 baja 0,1 (mínimo 1,0); si es menor que 0,015 sube 0,1 (máximo 3,0).
- Se ajusta en cada ciclo de 1 s y el valor se guarda en `self.predictive_ratio`, compartido por todas las campañas predictivas del proceso.

Limitaciones del conteo: `calls_answered` se incrementa en `on_agent_connect` y otra vez en `on_hangup`, y el abandono se cuenta como cuelgue normal (causa 16 o 17) sin estado `answered`. No hay tope de concurrencia en el bucle; el límite real lo pone `_guard_outbound`.

## Originate

Parámetros comunes: `trunk` (primera `SIPTrunk` activa o `default_trunk`), `CallerID` (`caller_id` de la cola o `1000`), `Timeout` = `call_timeout` limitado a 10–120 s, `Async='true'`, y variables `CAMPAIGN_ID`, `CONTACT_ID`, `CONTACT_NAME`, enviadas como lista de encabezados `Variable`.

| Modo | Channel | Context / Exten | Variables adicionales | Antifraude en el marcador |
|---|---|---|---|---|
| Progresivo, preview | `PJSIP/<extensión del agente>` | `config.context` (`from-internal`) / número del contacto | `AGENT_ID`, `QUEUE_NAME` | No; la llamada pasa por las rutas salientes y `vozip-outbound-policy` |
| Predictivo | `PJSIP/<troncal>/<número>` | `outbound-queue` / `s` | `GROUP(vozip_trunk)`, `GROUP(vozip_out)=total`, `QUEUE_NAME`, `AMD_ENABLED`, `AMD_ACTION`, `AMD_MESSAGE` | Sí, `_guard_outbound` |
| Call blasting | `PJSIP/<troncal>/<número>` | `Application=Playback`, `Data=<audio>` | `GROUP(...)` | Sí |

Las variables `GROUP(...)` hacen que las llamadas del marcador cuenten en los mismos `GROUP_COUNT` que usa el dialplan. Si `Response` es `Success`, guarda la llamada en `active_calls` con `ActionID` como `call_id`. Un `Originate` asíncrono no devuelve el `Uniqueid` real: el mapeo correcto llega después con `UserEvent(DialerAMD)`. Una respuesta distinta lanza `CallOriginationError`; los bucles progresivo y predictivo no la capturan, así que la tarea de esa campaña termina aunque siga en `active_campaigns`.

## AMD y UserEvent DialerAMD

El contexto `outbound-queue` emite siempre:

```text
UserEvent(DialerAMD,CampaignID: <id>,ContactID: <id>,Status: <HUMAN|MACHINE|NOTSURE|HANGUP|SKIPPED>,Cause: <causa>,Uniqueid: ${UNIQUEID})
```

`SKIPPED` cuando AMD está desactivado. En el marcador, `on_user_event()` busca la llamada activa por campaña y contacto, guarda `amd_status`, registra `uniqueid:<uid>:call_id` y `channel:<Channel>:call_id`, y con `MACHINE` marca la llamada como `machine` y suma `calls_machine` (esas llamadas no cuentan como abandono). En el backend, `_process_user_event()` guarda campaña, contacto y resultado en el estado del `Uniqueid`, y `_apply_dialer_result()` los aplica al `Call` cuando llega el `Cdr` (`metadata.amd_status`, `metadata.amd_cause`).

## Antifraude: _guard_outbound

La política la publica `security.publish_policy()` en `telephony:dial_policy` al aplicarla desde la interfaz y cada 120 s desde `check_fraud_alerts`. Campos: `block_international`, `home_country_code`, `blocked_prefixes`, `allowed_prefixes`, `max_number_length`, `max_concurrent_outbound`, `enforce_trunk_channels`, `trunk_limits` (`{nombre_troncal: max_channels}` de troncales activas) y `updated_at`.

`_dial_policy()` la cachea 30 s; si la lectura falla conserva la anterior. `_guard_outbound()`:

1. Si la política está vacía (no publicada), permite todo.
2. `_number_reason()` replica el dialplan: `invalid`, `too_long`, `international`, `blocked_prefix`, `not_allowed`. Si hay motivo, registra `[Antifraude] ... bloqueado`, agrega un evento `dialer_blocked` a `telephony:security_events` (el backend lo pasa a `TelephonySecurityEvent`) y descarta el contacto.
3. Concurrencia: pide por AMI `Getvar GROUP_COUNT(<troncal>@vozip_trunk)` y `GROUP_COUNT(total@vozip_out)`. Si alguno alcanza su límite, marca `_requeued`, devuelve el contacto al frente de la lista (`LPUSH`) y el bucle predictivo espera al siguiente ciclo. Si `Getvar` falla, cuenta 0.

## Reencolado y reintentos

| Situación | Qué pasa |
|---|---|
| Troncal o límite total lleno | `LPUSH` al frente, se reintenta en el siguiente ciclo |
| Fuera de horario | `RPUSH` al final |
| Número bloqueado por política, DNC o sin teléfono | Se descarta |
| Preview rechazado o vencido | Se descarta |
| No contesta, ocupado, falla o contestador | El marcador no reencola. En el backend `_apply_dialer_result()` suma `attempts` y deja el contacto en `pending` mientras `attempts < max_retries` (por defecto 3), o `failed` |

Los contactos en `pending` solo vuelven a Redis cuando la lista queda vacía y `_push_contacts_to_redis()` la recarga. `retry_delay` y `max_retries` viajan en la configuración pero el motor no los usa.

## Variables de entorno

| Variable | Por defecto en el código | En `docker-compose.prod.yml` |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | `redis://:<REDIS_PASSWORD>@<VOZIPOMNI_IPV4>:6379/0` |
| `ASTERISK_HOST` | `asterisk` | `VOZIPOMNI_IPV4` |
| `ASTERISK_AMI_PORT` | `5038` | `5038` |
| `ASTERISK_AMI_USER` | `admin` | `ASTERISK_AMI_USER` |
| `ASTERISK_AMI_PASSWORD` | vacío | obligatoria |
| `BACKEND_URL` | `http://backend:8000` | no se define |
| `DIALER_API_TOKEN` | vacío | no se define |
| `TZ` | – | `America/Bogota` |

Con `network_mode: host` el nombre `backend` no resuelve y no se define token, así que la consulta DNC falla y no bloquea: la lista negra no se aplica desde el marcador. Ver [Variables de entorno](../instalacion/variables-entorno.md).

## Depuración

```bash
docker logs -f vozipomni_dialer
docker exec vozipomni_redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning GET campaign:<id>:config
docker exec vozipomni_redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning LLEN campaign:<id>:contacts:pending
docker exec vozipomni_redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning SMEMBERS campaign:<id>:agents:available
docker exec vozipomni_redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning GET telephony:dial_policy
docker exec vozipomni_redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning SUBSCRIBE dialer:control
docker exec vozipomni_asterisk asterisk -rx "group show channels"
```

Tome `REDIS_PASSWORD` del `.env` del servidor sin copiarla en tickets. Qué buscar:

- `[Control] start_campaign ...`: la orden llegó. Si no aparece, revise la tarea periódica de campañas.
- `Campaña <id> no encontrada`: falta la configuración en Redis.
- Sin `Llamada originada` y sin errores: casi siempre cero agentes disponibles.
- `[Antifraude] ... bloqueado` o `sin canales disponibles; contacto re-encolado`: política o `GROUP_COUNT`.
- `AMI originate failed`: troncal inexistente o sin registro; revise `pjsip show endpoints`.
- `No call_id found for channel ...`: normal en progresivo; en predictivo la correlación depende del `UserEvent(DialerAMD)`.

El nivel es `INFO` (`logging.basicConfig`); el ratio predictivo y los resultados AMD distintos de `MACHINE` salen en `DEBUG`. Para seguir la llamada en Asterisk y Kamailio use [Depuración VoIP](../operacion/depuracion-voip.md).

## Ver también

- [Arquitectura](../general/arquitectura.md)
- [Glosario](../general/glosario.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [API](../api/README.md)
- [Entorno local](./entorno-local.md)
- [Estructura del código](./estructura-del-codigo.md)
- [Backend](./backend.md)
- [Frontend](./frontend.md)
- [Telefonía interna](./telefonia-interna.md)
- [Pruebas y CI](./pruebas-y-ci.md)
- [Contribuir](./contribuir.md)
