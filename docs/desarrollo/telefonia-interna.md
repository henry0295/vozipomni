# Telefonía interna

Este documento baja al nivel del código de la telefonía de VozipCX: qué archivos de Asterisk genera el backend y cómo los recarga, qué hace cada contexto del dialplan, cómo enruta Kamailio los mensajes SIP de los agentes WebRTC, cómo se protege el WebSocket SIP con un ticket y cómo se emiten las credenciales TURN, y cómo los eventos AMI terminan en registros `Call` y grabaciones vinculadas. La vista de componentes y los diagramas de secuencia están en [Arquitectura](../general/arquitectura.md); aquí se explica qué tocar y qué efectos tiene cada cambio.

## Archivos generados en /var/lib/asterisk/dynamic

El directorio sale de `ASTERISK_CONFIG_DIR` (`backend/config/settings.py`, por defecto `/var/lib/asterisk/dynamic`). Es un volumen compartido entre el backend, el worker de Celery y Asterisk. `/etc/asterisk` (montado desde `docker/asterisk/configs/`) no se escribe nunca desde Django.

| Archivo | Lo escribe | Lo incluye |
|---|---|---|
| `pjsip_wizard.conf` | `PJSIPConfigGenerator.write_config_file()` en `apps/telephony/pjsip_config_generator.py` (ruta `PJSIP_CONFIG_PATH`) | `#tryinclude` al final de `pjsip.conf` |
| `pjsip_extensions.conf` | `AsteriskConfigGenerator.generate_pjsip_extensions_conf()` | `#include` en `pjsip.conf` |
| `pjsip_agents.conf` | `_sync_agent_pjsip()` en `apps/telephony/signals.py` (ruta fija en el código) | `#tryinclude` en `pjsip.conf` |
| `extensions_dynamic.conf` | `AsteriskConfigGenerator.generate_extensions_conf()` | `#include` al inicio de `extensions.conf` |
| `queues_dynamic.conf` | `generate_queues_dynamic_conf()` | `#include` en `queues.conf` |
| `voicemail_dynamic.conf` | `generate_voicemail_conf()` | `#include` en `voicemail.conf` |
| `musiconhold_dynamic.conf` | `generate_musiconhold_conf()` | `#include` en `musiconhold.conf` |
| `kamailio_identify.conf` | `docker/asterisk/entrypoint.sh` al arrancar Asterisk | `#tryinclude` en `pjsip.conf` |

Detalles que importan al editar:

- Los `#tryinclude` de `pjsip.conf` van al final a propósito: los agentes heredan de la plantilla `[webrtc_endpoint](!)` y la herencia falla si el include aparece antes de declararla.
- `pjsip_agents.conf` crea por agente con `webrtc_enabled=True` un endpoint `[<ext>](webrtc_endpoint)`, un `auth` `userpass` y un AOR con `max_contacts=2`, `remove_existing=no`, `qualify_frequency=30` y el contacto estático `sip:<ext>@${KAMAILIO_HOST}:5060`. Sin ese contacto el AOR queda vacío y `Dial(PJSIP/<ext>)` falla con `CHANUNAVAIL`. `KAMAILIO_HOST` vale `kamailio` por defecto (nombre del servicio en bridge); con `network_mode: host` debe ser la IP del servidor o `localhost`.
- `kamailio_identify.conf` contiene `[kamailio-endpoint-identify]` con `match=${VOZIPOMNI_IPV4}/32`. Se genera en el entrypoint porque `res_pjsip_endpoint_identifier_ip` no expande `${ENV()}`. Si la IP del servidor cambia, hay que reiniciar Asterisk.
- `docker/asterisk/configs/extensions_dynamic.conf` en el repositorio es solo un marcador; el real se escribe en el volumen.
- Todo lo generado lleva la cabecera "NO EDITAR MANUALMENTE": cualquier cambio a mano se pierde en la siguiente sincronización.

## Recarga por AMI

El cliente es `AsteriskAMI` en `apps/telephony/asterisk_ami.py` (socket TCP, se niega a conectar si la clave está vacía):

- `reload_module(nombre)` envía `Action: ModuleLoad` con `LoadType: reload`.
- `reload_dialplan()` envía `Action: Command` con `Command: dialplan reload`.

Quién recarga qué:

| Origen | Secuencia |
|---|---|
| `_sync_asterisk_config()` en `signals.py` (troncales, rutas, extensiones, IVR, buzones, condiciones de horario, colas y miembros) | `PJSIPConfigGenerator().save_and_reload()` → `AsteriskConfigGenerator().write_all_configs()` → recarga `res_pjsip.so`, `chan_pjsip.so`, dialplan, `app_voicemail.so`, `app_queue.so` |
| `PJSIPConfigGenerator.reload_pjsip()` | `res_pjsip_config_wizard.so` (pausa 2 s) → `res_pjsip.so` (1 s) → `pjsip reload` → `res_pjsip_outbound_registration.so` |
| `_sync_agent_pjsip()` (guardar o borrar `Agent`) | Solo `res_pjsip.so` |
| `security.apply_policy()` | `write_all_configs()` → `reload_dialplan()` → publica la política en Redis |
| `QueueViewSet` (`apps/api/viewsets.py`) | `app_queue.so` y dialplan |
| `python manage.py generate_asterisk_config` | Regeneración completa; `--no-reload` para solo escribir |

Las sincronizaciones de `signals.py` corren en un hilo daemon para no bloquear la petición HTTP, y un candado no bloqueante descarta la siguiente si ya hay una en curso. Para verificar lo que quedó cargado:

```bash
docker exec vozipomni_asterisk asterisk -rx "dialplan show from-internal"
docker exec vozipomni_asterisk asterisk -rx "pjsip show endpoints"
docker exec vozipomni_asterisk asterisk -rx "queue show"
```

## Contextos del dialplan

`docker/asterisk/configs/extensions.conf` define los contextos estáticos y hace `#include` de `extensions_dynamic.conf` al inicio. El archivo generado vuelve a abrir `[from-internal]` y `[from-pstn]`; Asterisk fusiona las entradas de contextos con el mismo nombre.

### from-internal

Es el contexto de `kamailio-endpoint` y de los endpoints de agentes (`pjsip.conf`).

- Generado, por cada `Extension` activa: `MixMonitor(<fecha>_${UNIQUEID}_<ext>.wav,ab)`, `Dial(PJSIP/<ext>,30,trg)` y `VoiceMail` opcional.
- Generado, por cada `Queue` activa: `Answer`, `MixMonitor(<fecha>_${UNIQUEID}_<cola>_${CALLERID(num)}.wav,ab)` y `Queue(<nombre>,tT,,,<max_wait_time o 300>)`.
- Generado, por cada `OutboundRoute`: patrón con `_` forzado (`_ensure_pattern_prefix`), `Set(__TRUNK_NAME=...)`, prefijo de caller ID, cálculo de `dial_number` (anteponer o quitar prefijo), `GoSub(vozip-outbound-policy,s,1(${EXTEN},${dial_number},<troncal>,<máx. canales>))`, `MixMonitor(..._${UNIQUEID}_${CALLERID(num)}_${dial_number}.wav,ab)` y `Dial(PJSIP/${dial_number}@<troncal>,<ring_time o 60>,<dial_options o trg>)`.
- Estático: `9000` (IVR de ejemplo) y un comodín `_X.` que responde con `Progress()`, `Playback(ss-noservice,noanswer)` y `Hangup(3)`. Los patrones de las rutas salientes son más específicos y ganan; si una llamada termina en el comodín es que no hay ruta para ese número.

### from-pstn

Llamadas que entran por las troncales. El comodín estático fija `__TRUNK_NAME`, graba y manda al IVR `9000`. Cada `InboundRoute` activa genera su DID con `Set(__DID_NUMBER=...)`, `MixMonitor(..._${UNIQUEID}_<did>_${CALLERID(num)}.wav,ab)` y el destino: extensión, IVR (`Goto(ivr-<ext>,s,1)`), cola (`Queue(<cola>,tT,,,300)`), buzón, anuncio o destino personalizado. `from-trunk` y `from-external` redirigen a `from-pstn`; `from-pbx` atiende PBX en LAN.

### from-spy

Lo usa el supervisor. El backend origina hacia `PJSIP/<ext_supervisor>` con `SPY_CHANNEL` y `SPY_MODE`. Modos: escucha `ChanSpy(${SPY_CHANNEL},q)`, susurro `ChanSpy(...,qw)` e intrusión `ChanSpy(...,B)`. Sin `SPY_CHANNEL` reproduce `vm-goodbye`.

### confbridge

`exten => _X.` con `Answer` y `ConfBridge(${EXTEN})`: la extensión es el identificador de sala que genera el backend para conferencias de tres vías.

### outbound-queue

Destino del `Originate` del marcador predictivo. Recibe `CAMPAIGN_ID`, `CONTACT_ID`, `QUEUE_NAME`, `AMD_ENABLED`, `AMD_ACTION`, `AMD_MESSAGE` y opcionalmente `QUEUE_MAX_WAIT`. Escribe `CDR(userfield)=campaign:<id>;contact:<id>`, ejecuta `AMD()` si corresponde, emite `UserEvent(DialerAMD,...)` y pasa HUMAN/NOTSURE a `Queue(${QUEUE_NAME},tT,,,${QUEUE_MAX_WAIT:-180})`. El detalle está en [Marcador](./marcador.md).

### vozip-outbound-policy

Lo genera `outbound_policy_dialplan()` en `apps/telephony/security.py` a partir del singleton `TelephonySecurityPolicy` y se agrega al final de `extensions_dynamic.conf`. Argumentos: `ARG1` número marcado, `ARG2` número final, `ARG3` troncal, `ARG4` máximo de canales de la troncal (`SIPTrunk.max_channels` si `enforce_trunk_channels`).

Validaciones en orden:

1. Longitud mayor que `max_number_length` → `too_long`.
2. `block_international`: empieza por `00`, o por `+` sin el `home_country_code` → `international`.
3. Prefijos de `blocked_list` sobre el marcado o el final → `blocked_prefix`.
4. `allowed_list` no vacía y sin coincidencia → `not_allowed`.
5. `max_calls_per_extension_hour`: contador en AstDB `vozip_rate/<origen>_<AAAAMMDDHH>` → `extension_rate`.
6. `Set(GROUP(vozip_trunk)=${ARG3})` y `GROUP_COUNT(${ARG3}@vozip_trunk) > ARG4` → `trunk_full`.
7. `Set(GROUP(vozip_out)=total)` y `GROUP_COUNT(total@vozip_out) > max_concurrent_outbound` → `global_limit`.
8. `Return()`.

Al bloquear emite `UserEvent(VozipFraud,Reason,Number,Dialed,Trunk,Source)` y rechaza sin contestar: `trunk_full`, `global_limit` y `extension_rate` con `all-circuits-busy-now` y `Hangup(34)`; el resto con `ss-noservice` y `Hangup(21)`. Si la tabla de la política no existe (sin migrar), el contexto solo hace `Return()`. No hay validación por franja horaria: "hora" solo se refiere al límite por extensión. La tarea `reset_extension_rate_counters` limpia `vozip_rate` a diario. La administración funcional está en `docs/administracion/seguridad-antifraude.md`.

## Kamailio

`docker/kamailio/kamailio.cfg`; `docker/kamailio/entrypoint.sh` reemplaza `VOZIPOMNI_HOST_PLACEHOLDER` por `VOZIPOMNI_IPV4` y `ASTERISK_HOST_PLACEHOLDER` por `ASTERISK_HOST` (o la misma IP), y con `KAMAILIO_TRUST_LAN=1` activa `#!define TRUST_LAN`.

Escucha en `udp/tcp 0.0.0.0:5060` con `advertise <IP>:5060` (sin `advertise`, Via y Record-Route saldrían con `0.0.0.0`) y en `tcp:127.0.0.1:8080` para el WebSocket. El orden de `request_route` es REQINIT → NATDETECT → WITHINDLG → REGISTRAR → TOAGENT → RELAY.

### route[REQINIT]

- Marca `FLT_TRUSTED` (flag 8) si `$si` es `127.0.0.1`, la IP del servidor o Asterisk; con `TRUST_LAN`, también redes RFC1918.
- Para orígenes no confiables: sale en silencio si la IP está en `ipban`; `pike_check_req()` (más de 30 peticiones en 2 s) o un User-Agent de escáner conocido banean una hora (`htable` con `autoexpire=3600`); cualquier diálogo nuevo recibe 403 y baneo, salvo OPTIONS de keepalive y ACK; peticiones dentro de diálogo reciben 403.
- Para orígenes confiables: `mf_process_maxfwd_header("10")`, respuesta a OPTIONS y `sanity_check`.

Todo el WebSocket llega desde nginx (`127.0.0.1`), por eso no se aplica pike a esa IP: un baneo dejaría sin servicio a todos los agentes a la vez.

### route[REGISTRAR]

Los REGISTER (WS o SIP) van a `save("location")` y terminan ahí. `usrloc` usa `db_mode=0`: la tabla es solo memoria (el comentario "Store in Redis" del archivo es anterior; `db_redis.so` está comentado). Asterisk no recibe los REGISTER de los agentes.

### route[TOAGENT]

Solo para INVITE y MESSAGE sin to-tag:

- Si `$(rU{s.len}) > 6`, es un número externo: retorna y sigue a RELAY, que lo envía a Asterisk.
- Si no, `lookup("location")`: sin registro responde `480 Temporarily Unavailable`; con registro pone `FLT_TOAGENT` (flag 9) y llama a RELAY.

No se puede distinguir por `$si` porque todo el WebSocket entra desde `127.0.0.1`. Consecuencia para el diseño: las extensiones deben tener 6 dígitos o menos, y los números externos de 6 dígitos o menos (códigos cortos) no llegarán a Asterisk desde el softphone.

### route[RELAY]

1. Arma `t_on_branch("MANAGE_BRANCH")`, `t_on_reply("MANAGE_REPLY")` y `t_on_failure("MANAGE_FAILURE")`.
2. `record_route()` en INVITE y SUBSCRIBE iniciales. Sin Record-Route, el ACK del navegador y el BYE de Asterisk se descartan con "404 Not here", Asterisk retransmite el 200 OK y corta a los 32 s con 408.
3. Si no hay to-tag y no está `FLT_TOAGENT`, fija `$du = sip:<ASTERISK_HOST>:5080`.
4. `t_relay()`.

`alias=<IP>:5060` lleva el puerto a propósito: sin él, `myself` coincidía también con el 5080 de Asterisk, `loose_route()` tomaba el ACK dirigido a Asterisk como propio y lo perdía (mismo síntoma de 408).

### RTPEngine

`route[NATMANAGE]` se invoca desde `branch_route[MANAGE_BRANCH]` (oferta) y `onreply_route[MANAGE_REPLY]` (respuestas 183 y 2xx con SDP). No se llama desde RELAY para INVITE porque generaría una doble oferta. Banderas exactas:

```text
rtpengine_offer("replace-origin replace-session-connection ICE=remove DTLS=off SDES-off RTP/AVP codec-strip=OPUS codec-offer=PCMU,PCMA rtcp-mux=demux")
rtpengine_answer("replace-origin replace-session-connection ICE=force DTLS=passive RTP/SAVPF SDES-off generate-mid rtcp-mux=offer")
```

ACK, BYE y CANCEL usan `rtpengine_manage()`. La oferta quita OPUS porque Asterisk no carga `codec_opus`; si se agrega un códec, hay que ajustar a la vez estas banderas, `allow=` de los endpoints en `pjsip.conf` y las troncales. Procesar el 183 con SDP es necesario para el audio temprano (tono y mensajes del operador).

### WebSocket

`event_route[xhttp:request]` responde 403 si la petición no llega por el puerto 8080 desde `127.0.0.1`, y solo acepta `GET` con `Upgrade: websocket`. Con eso el único camino al WebSocket es nginx.

## Ticket del WebSocket SIP

En `docker/nginx/default.https.conf` (y `default.prod.conf`), `location /sip/ws` y `location /asterisk/ws` tienen `auth_request /_sip_ws_auth`. Ese `location` interno llama a `/api/telephony/sip-ws-auth/` sin cuerpo y con `X-Original-URI: $request_uri`.

En `apps/telephony/webrtc_views.py`:

- `WebRTCCredentialsView` (autenticada) firma el ticket con `django.core.signing.dumps({'u': user.pk}, salt='vozipomni.sip-ws')`.
- `validate_ws_ticket()` lo verifica con `signing.loads(..., max_age=SIP_WS_TICKET_TTL)` (24 h por defecto) y exige que el usuario exista y esté activo.
- `SipWsAuthView` (sin autenticación ni throttle, porque solo la llama nginx desde `127.0.0.1`) lee `ticket` del query de `X-Original-URI`; responde 204 con `X-Vozip-User` o 401 y registra la IP (`X-Real-IP`).

Desactivar un usuario invalida sus tickets en el siguiente handshake; un WebSocket ya abierto sigue vivo hasta que se cierre. Como el ticket se firma con `SECRET_KEY`, rotar esa clave invalida todos los tickets emitidos. `docker/nginx/default.conf` (desarrollo) no tiene `auth_request`.

## Credenciales TURN

`turn_credentials(user_id, ttl)` implementa el esquema de secreto compartido de coturn (`use-auth-secret`):

```text
usuario   = "<epoch actual + ttl>:<user_id>"
clave     = base64(HMAC-SHA1(TURN_SECRET, usuario))
```

`TURN_CREDENTIAL_TTL` es 12 h por defecto. `WebRTCCredentialsView` devuelve siempre los STUN públicos y, solo si `TURN_SECRET` está definido, `turn:<host>:<TURN_PORT>?transport=udp` y `?transport=tcp` con esas credenciales. El host sale de `TURN_HOST`, luego de `PUBLIC_BASE_URL` y por último del host de la petición. Respuesta completa: `ice_servers`, `turn_enabled`, `turn_ttl`, `ws_ticket`, `ws_ticket_ttl`. El valor de `TURN_SECRET` debe ser el mismo en el backend y en coturn; nunca va al frontend.

## De eventos AMI a Call

`apps/telephony/ami_cdr_listener.py` (ciclo de vida en [Backend](./backend.md)) acumula estado por `Uniqueid` con los eventos de cola, agente, retención, transferencia, buzón y `UserEvent`, y lo consume al llegar `Cdr` (habilitado en `docker/asterisk/configs/cdr_manager.conf`). `_process_cdr_event()` hace `Call.objects.update_or_create(call_id=f"ast-{uniqueid}")`:

| Campo | Origen |
|---|---|
| `direction` | `_determine_direction()`: `DestinationContext` en `from-pstn`/`from-trunk`/`from-external` es entrante; `from-internal`/`outbound`/`to-pstn` es saliente; si no, heurística por longitud de origen y destino |
| `status` | `final_status` del estado (`voicemail`, `machine`, `abandoned`, `transferred`) o `_map_disposition()`: ANSWERED → `completed`, NO ANSWER → `no_answer`, BUSY → `busy`, FAILED y CONGESTION → `failed`, otro → `completed` |
| `caller_id`, `called_number`, `channel` | `Source`, `Destination`, `Channel` |
| `start_time`, `answer_time`, `end_time` | `StartTime`, `AnswerTime`, `EndTime` |
| `talk_time` | `BillableSeconds` |
| `wait_time` | Desde `QueueCallerJoin` hasta la respuesta o el fin; si no hubo cola, respuesta menos inicio |
| `hold_time`, `queue`, `transferred`, `transfer_to` | Estado acumulado |
| `agent` | Estado; si no, extensión extraída de `PJSIP/<ext>-` del canal destino; para `kamailio-endpoint` se usa el origen |
| `metadata` | Canal, contexto, disposición y duración AMI, cola, número de retenciones y de timbres sin respuesta |

Luego suma métricas al agente si la llamada se completó, aplica el resultado del marcador (`_apply_dialer_result`), encola la vinculación de la grabación y publica `call.completed` o `call.ended` en `asterisk_events` y `dashboard`. `UserEvent(VozipFraud)` crea un `TelephonySecurityEvent` con `record_event()` (severidad crítica para `international`, `blocked_prefix` y `not_allowed`).

## Vinculación de grabaciones

Todas las líneas `MixMonitor` usan nombres relativos del tipo `<AAAAMMDD-HHMMSS>_${UNIQUEID}_<origen>_<destino>.wav`, que Asterisk escribe en su directorio de monitor. En `apps/recordings/tasks.py`:

- `RECORDING_DIRS = ('/var/spool/asterisk/monitor', '/app/recordings')`, extensiones `.wav`, `.wav49`, `.gsm`, `.mp3`, `.ogg`.
- `_id_in_name()` busca el `Uniqueid` completo con una expresión que evita coincidencias parciales (`1727630981.12` no coincide con `1727630981.123`). `find_recording_file()` prueba también `call_id` sin `ast-` y exige más de 100 bytes.
- `recordings.link_recording_to_call`: el listener la encola con `countdown=30` para que MixMonitor cierre el archivo; reintenta hasta 3 veces cada 30 s. Crea o actualiza `Recording` (archivo, ruta, tamaño, duración = `talk_time`, formato, agente, campaña) y marca `Call.recording_file` y `Call.is_recorded`.
- `recordings.scan_unlinked_recordings`: red de seguridad periódica sobre hasta 500 llamadas sin grabación.
- `recordings.cleanup_old_recordings`: archiva tras `RECORDING_ARCHIVE_DAYS` (90) y borra el archivo físico tras `RECORDING_DELETE_DAYS` (180), conservando la fila (`backend/config/recording_config.py`).

Si cambia el formato del nombre en `asterisk_config.py` o `extensions.conf`, mantenga `${UNIQUEID}` completo y separado por `_`; de lo contrario las grabaciones dejarán de vincularse.

## Checklist al tocar telefonía

- Cambió un generador: ejecute `generate_asterisk_config --no-reload` y revise el archivo en el volumen antes de recargar.
- Cambió `kamailio.cfg`: reconstruya la imagen (`docker/kamailio/Dockerfile` copia el archivo) y reinicie; los agentes se vuelven a registrar solos.
- Cambió `pjsip.conf` o `extensions.conf` estáticos: `docker/asterisk/configs` está montado en `/etc/asterisk`, basta con recargar el módulo o el dialplan.
- `docker/asterisk/entrypoint.sh` aplica `sed -i` sobre `pjsip.conf` (`external_*_address`) y `manager.conf` (`secret` y `permit`) dentro de ese directorio montado. Antes de hacer commit desde una máquina donde corrió Asterisk, revise `git diff docker/asterisk/configs/` y no suba la clave AMI.
- Pruebe una llamada saliente, una entrante a cola y una transferencia, y siga [Depuración VoIP](../operacion/depuracion-voip.md) para capturar SIP y RTP.

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
- [Marcador](./marcador.md)
- [Pruebas y CI](./pruebas-y-ci.md)
- [Contribuir](./contribuir.md)
