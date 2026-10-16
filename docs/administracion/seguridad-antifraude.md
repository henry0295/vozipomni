# Seguridad y antifraude

Este manual explica la política antifraude de llamadas salientes (a dónde se puede llamar y cuántas llamadas pueden salir a la vez), qué ve quien marca cuando una llamada se bloquea, cómo se registran los eventos y se envían las alertas por correo, y qué protecciones de red trae la plataforma (Kamailio, ticket del WebSocket SIP, TURN y firewall). Se basa en `frontend/pages/settings/security.vue`, `backend/apps/telephony/models.py` (`TelephonySecurityPolicy`, `TelephonySecurityEvent`), `backend/apps/telephony/security.py`, `backend/apps/telephony/security_views.py`, `backend/apps/telephony/tasks.py`, `dialer_engine/dialer.py` y `docker/kamailio/kamailio.cfg`.

La política es **una sola** para todo el sistema (registro único en la tabla `telephony_security_policy`). Se aplica en dos lugares con la misma lógica: en el dialplan, mediante el contexto `[vozip-outbound-policy]` que cada ruta saliente llama con `GoSub` antes de marcar, y en el marcador automático antes de originar cada llamada de campaña.

## Acceso

- Página: **Telefonía → Seguridad y antifraude** (ruta `/settings/security`). Solo la ve el rol Administrador.
- API: todos los endpoints exigen administrador (`IsAdminUser`):
  - `GET` / `PUT /api/telephony/security/policy/`: leer y guardar la política.
  - `POST /api/telephony/security/policy/test/`: probar un número (`{"number": "..."}`).
  - `POST /api/telephony/security/policy/apply/`: regenerar el dialplan y recargar Asterisk sin cambiar la política.
  - `GET /api/telephony/security/events/`: eventos (filtros `event_type`, `severity`, `days` entre 1 y 90; por defecto 7).
  - `GET /api/telephony/security/summary/`: contadores de las últimas 24 horas.

La cabecera de la página muestra cuatro indicadores de las últimas 24 horas: **Salientes 24 h**, **Internacionales 24 h**, **Eventos 24 h** y **Críticos 24 h**. El botón **Actualizar** recarga política, indicadores y eventos.

## Qué llamadas controla

Todas las llamadas que salen por una **ruta saliente**: las que marcan los agentes desde la consola WebRTC, click-to-call, callbacks, conferencias y el marcador automático de campañas. Las llamadas entre extensiones internas no pasan por una ruta saliente y no se evalúan. Ver [Rutas y dialplan](./rutas-y-dialplan.md).

## Campos de la política

### Destinos permitidos

| Campo en pantalla | Campo del modelo | Por defecto | Efecto | Valor recomendado |
|---|---|---|---|---|
| Bloquear llamadas internacionales | `block_international` | Activado | Bloquea números que empiezan por `00`, o por `+` seguido de un indicativo distinto al del país. | Activado, salvo que la operación llame al exterior. |
| Indicativo del país | `home_country_code` | `57` | Indicativo que se considera nacional para los números con `+`. Solo dígitos; el backend rechaza un valor vacío ("Indicativo numérico, ej: 57"). | `57` para Colombia. |
| Longitud máxima del número | `max_number_length` | `15` | Bloquea números con más dígitos. `0` = sin límite. Si no es 0, debe estar entre 7 y 20. | `15`. Un celular colombiano con `57` tiene 12 dígitos; deja margen para prefijos de operador. |
| Prefijos bloqueados | `blocked_prefixes` | `01900` y `1900` | Uno por línea. Bloquea si el número marcado o el número final enviado a la troncal empieza por alguno. | Mantén `01900` y `1900` y agrega destinos satelitales o de tarifa especial que no uses. |
| Lista blanca (opcional) | `allowed_prefixes` | Vacía | Si tiene valores, **solo** se permiten números que empiecen por alguno de ellos (por ejemplo `3`, `60`, `57`, `01800`). | Úsala en operaciones que solo llaman a celulares y fijos nacionales. |

Los prefijos se limpian al guardar: se quitan caracteres que no sean dígitos, se aceptan comas como separador y se eliminan repetidos.

### Límites de uso

| Campo en pantalla | Campo del modelo | Por defecto | Efecto | Valor recomendado |
|---|---|---|---|---|
| Canales máximos por troncal | `enforce_trunk_channels` | Activado | Usa el valor **Canales** (`max_channels`) de cada troncal. La llamada que supera ese número se rechaza como "todos los circuitos ocupados". Ver [Troncales SIP](./troncales-sip.md). | Activado, con los canales contratados en cada troncal. |
| Llamadas salientes simultáneas (total) | `max_concurrent_outbound` | `0` | Tope de llamadas salientes simultáneas sumando todas las troncales. `0` = sin límite. | La suma de canales contratados, o un poco menos. |
| Llamadas por extensión por hora | `max_calls_per_extension_hour` | `0` | Tope de intentos por número de origen (Caller ID) en cada hora del reloj. `0` = sin límite. | Un valor por encima del ritmo real de un agente manual (por ejemplo 60–100). Mide primero en [Reportes](./reportes.md). |

Detalles del límite por extensión: el dialplan guarda un contador en AstDB (`vozip_rate/<origen>_<AAAAMMDDHH>`) y lo incrementa en cada intento que pasa las reglas de destino. La tarea `reset_extension_rate_counters` borra esos contadores todos los días a las 3:15 (`database deltree vozip_rate`).

### Alertas

| Campo en pantalla | Campo del modelo | Por defecto | Se dispara cuando |
|---|---|---|---|
| Llamadas salientes en 10 min | `alert_calls_per_10min` | `150` | Hay más llamadas salientes que el umbral en los últimos 10 minutos. |
| Internacionales por hora | `alert_international_per_hour` | `5` | Hay más llamadas internacionales que el umbral en la última hora. |
| Intentos bloqueados en 10 min | `alert_blocked_per_10min` | `10` | Hay igual o más intentos bloqueados que el umbral en los últimos 10 minutos. |
| Correos de alerta | `alert_emails` | Vacío | Destinatarios, uno por línea. Vacío = administradores y superusuarios activos con email. El backend valida cada dirección ("Correo inválido: ..."). |

En todas, `0` desactiva la alerta. Ajusta el umbral de pico al volumen normal de la operación: con un marcador predictivo activo, 150 llamadas en 10 minutos puede ser tráfico legítimo.

## Guardar y aplicar

Haz clic en **Guardar y aplicar**. El backend guarda la política y ejecuta `apply_policy()`:

1. Regenera los archivos de Asterisk, incluido el contexto `[vozip-outbound-policy]`.
2. Recarga el dialplan por AMI.
3. Publica la política en Redis (`telephony:dial_policy`) para el marcador, que la relee como máximo cada 30 segundos.

Si todo sale bien verás "Política aplicada: Asterisk recargó el dialplan con las nuevas reglas". Si AMI no respondió verás "Política guardada: No se pudo recargar Asterisk ahora; se aplicará en la próxima sincronización". En ese caso puedes forzar la aplicación con `POST /api/telephony/security/policy/apply/`. Debajo del formulario se muestra la última actualización y quién la hizo.

## Probar un número

En el panel **Probar un número** escribe un número (por ejemplo `+34912345678`) y haz clic en **Probar**. El resultado usa la política **guardada**, no la que está en pantalla sin guardar, y muestra **Permitida** o **Bloqueada: <motivo>**. Esta prueba evalúa solo las reglas de destino (internacional, prefijos, lista blanca, longitud); no evalúa canales ni límites por hora.

## Qué ve quien marca

La llamada bloqueada no se contesta. Asterisk envía la locución como early media (183 Session Progress) y luego rechaza con un código SIP para que el softphone muestre el motivo:

| Motivo | Locución | Código de colgado | SIP que recibe el origen |
|---|---|---|---|
| Internacional, prefijo bloqueado, fuera de la lista blanca, número demasiado largo | `ss-noservice` ("servicio no disponible") | `Hangup(21)` | 403 (llamada rechazada) |
| Troncal sin canales, límite total, límite por extensión | `all-circuits-busy-now` ("todos los circuitos ocupados") | `Hangup(34)` | 503 (sin circuitos) |

En el marcador automático no hay audio: un número bloqueado por destino se descarta y queda como evento `dialer_blocked`; si la troncal o el total no tienen canales libres, el contacto vuelve a la cola de pendientes de la campaña y se intenta después. Ver [Campañas](./campanas.md).

## Eventos de seguridad

Cada bloqueo en el dialplan emite un `UserEvent(VozipFraud)` que el listener AMI guarda como evento. Los bloqueos del marcador llegan por Redis (`telephony:security_events`) y se pasan a la base de datos cada 2 minutos. Cada evento también se envía por WebSocket al grupo `dashboard`.

| Tipo | Etiqueta | Severidad |
|---|---|---|
| `international` | Internacional bloqueada | Crítico |
| `blocked_prefix` | Prefijo bloqueado | Crítico |
| `not_allowed` | Fuera de la lista blanca | Crítico |
| `too_long` | Número demasiado largo | Advertencia |
| `trunk_full` | Troncal sin canales | Advertencia |
| `global_limit` | Límite total de llamadas | Advertencia |
| `extension_rate` | Límite por extensión | Advertencia |
| `dialer_blocked` | Bloqueada en el marcador | Advertencia |
| `alert_spike` | Alerta: pico de llamadas | Crítico |
| `alert_international` | Alerta: llamadas internacionales | Crítico |
| `alert_blocked` | Alerta: muchos intentos bloqueados | Advertencia |

La tabla **Eventos de seguridad** muestra **Fecha**, **Evento**, **Número**, **Troncal**, **Origen** y **Detalle**. Filtra por tipo (**Todos los eventos** y cada tipo) y por período (**Últimas 24 h**, **7 días**, **30 días**). El filtro de tipo de la pantalla no incluye "Número demasiado largo"; esos eventos aparecen con **Todos los eventos** o por API con `event_type=too_long`.

## Alertas por correo

La tarea `check_fraud_alerts` corre cada 2 minutos (`CELERY_BEAT_SCHEDULE`, 120 s). En cada ejecución vuelve a publicar la política en Redis, pasa los bloqueos del marcador a la base de datos y evalúa los tres umbrales. Cada tipo de alerta se envía como máximo una vez cada 30 minutos. El correo sale con asunto `[VozipOmni] <tipo de alerta>` e incluye el conteo, el umbral y, según el caso, una muestra de destinos u orígenes. Requiere `EMAIL_HOST` configurado en el servidor: sin él, Django usa el backend de consola y el correo solo se escribe en el log del worker. Si el envío SMTP falla, el evento queda registrado con `notified=False`.

## Protecciones de la red SIP

El panel **Protección de la red SIP** resume lo que ya viene activo:

- **Kamailio solo confía en orígenes conocidos.** En `route[REQINIT]` son confiables `127.0.0.1` (nginx, por donde llega todo el WebSocket), la IP del servidor y Asterisk. Cualquier otro origen que intente iniciar un diálogo (INVITE, REGISTER, etc.) recibe `403 Forbidden` y su IP queda en la tabla `ipban` durante 1 hora (`autoexpire=3600`). Las troncales no pasan por Kamailio: llegan directo a Asterisk.
- **Anti-flood y escáneres.** El módulo `pike` banea 1 hora a una IP no confiable que envíe más de 30 peticiones en 2 segundos. Los User-Agent de escáneres conocidos (`friendly-scanner`, `sipvicious`, `sipcli`, `sipsak` y otros) también se banean 1 hora. En estos casos Kamailio no responde.
- **Ticket del WebSocket SIP.** El WebSocket de Kamailio escucha solo en `127.0.0.1:8080`. El acceso público es `wss://<dominio>/sip/ws`, y nginx valida con `auth_request` un ticket firmado que entrega `/api/telephony/webrtc-credentials/` a un usuario con sesión activa (vigencia `SIP_WS_TICKET_TTL`, 24 horas por defecto). Sin sesión en VozipOmni no se puede registrar ni marcar.
- **TURN temporal.** coturn usa credenciales temporales por agente (`TURN_CREDENTIAL_TTL`, 12 horas por defecto), generadas por el mismo endpoint. La clave TURN no queda en el JavaScript público.
- **Firewall.** `deploy.sh` abre solo los puertos públicos, cierra 8080/tcp y 5061/tcp, y deniega 5432, 6379 y 5038 desde fuera. Ver [Red y puertos](../instalacion/red-y-puertos.md).

### `KAMAILIO_TRUST_LAN`

Con `KAMAILIO_TRUST_LAN=1` el entrypoint activa `TRUST_LAN` y Kamailio confía también en direcciones RFC1918 (10.x, 172.16–31.x, 192.168.x), lo que permite registrar teléfonos IP de la red local. Esas direcciones no pasan por pike ni por el baneo, y Kamailio no pide usuario y contraseña al registrar: cualquier equipo de la LAN podría marcar. Actívalo solo en redes segmentadas y con la política antifraude activa. El procedimiento está en [Red y puertos](../instalacion/red-y-puertos.md).

### Ver y levantar baneos

Cada baneo deja una línea `L_ALERT` con el texto `SECURITY`:

```bash
docker logs vozipomni_kamailio 2>&1 | grep SECURITY
```

Verás `SECURITY FLOOD from <IP>`, `SECURITY SCANNER <IP> ua=[...]` o `SECURITY UNTRUSTED <método> desde <IP>:<puerto>`, siempre con "baneada 1 hora".

Para levantar un baneo antes de que expire:

- **Reiniciar Kamailio** vacía la tabla `ipban`, que vive en memoria: `docker restart vozipomni_kamailio`. También borra los registros de los agentes (`usrloc` con `db_mode=0`); los softphones se vuelven a registrar solos en unos 30 segundos. Hazlo fuera de horas pico.
- **Borrar una sola IP.** La configuración carga los módulos `ctl` y `htable`, que exponen el comando RPC `htable.delete`. Sería `docker exec vozipomni_kamailio kamcmd htable.delete ipban <IP>`. Verificar en tu imagen que `kamcmd` esté disponible y responda (por ejemplo con `kamcmd htable.dump ipban`) antes de depender de este método.

Si una IP legítima se banea con frecuencia (por ejemplo un teléfono de la oficina), no la desbloquees a mano cada vez: agrega la red a los orígenes confiables con `KAMAILIO_TRUST_LAN` o revisa por qué envía peticiones a Kamailio.

## Lista de verificación

- La política tiene **Bloquear llamadas internacionales** activado y **Indicativo del país** en `57`, o la operación documentó por qué no.
- **Prefijos bloqueados** contiene al menos `01900` y `1900`.
- Cada troncal tiene su valor **Canales** real y **Canales máximos por troncal** está activado.
- **Llamadas salientes simultáneas (total)** está definido si hay más de una troncal.
- Los umbrales de alertas están ajustados al volumen normal y **Correos de alerta** apunta a un buzón que alguien revisa.
- `EMAIL_HOST` está configurado y se recibió al menos una alerta de prueba.
- **Probar un número** devuelve **Bloqueada** para un número internacional y **Permitida** para un celular nacional.
- Tras guardar apareció "Política aplicada".
- `KAMAILIO_TRUST_LAN` está en `0`, salvo que haya teléfonos IP en una LAN confiable.
- El firewall del servidor y el grupo de seguridad de la nube solo exponen los puertos documentados.
- Alguien revisa **Eventos de seguridad** y `docker logs vozipomni_kamailio | grep SECURITY` al menos una vez por semana.

## Problemas frecuentes

- **Una llamada nacional sale con "servicio no disponible".** Prueba el número en **Probar un número**. Si hay lista blanca, el número debe empezar por uno de sus prefijos. Revisa también que el número no supere **Longitud máxima del número**.
- **Las llamadas fallan con "todos los circuitos ocupados" y hay canales libres.** Revisa el valor **Canales** de la troncal y **Llamadas salientes simultáneas (total)**. Un valor bajo en cualquiera de los dos corta la llamada.
- **Un agente queda bloqueado por el límite por hora.** El contador es por hora de reloj; se libera al cambiar la hora. Sube el valor o déjalo en `0`.
- **No llegan los correos de alerta.** Confirma `EMAIL_HOST` (sin él, el correo solo queda en el log), que haya destinatarios (o administradores con email) y revisa los logs del worker de Celery. Ver [Solución de problemas](../operacion/solucion-de-problemas.md).
- **Guardé y la política no aplica.** Si viste "Política guardada", AMI no respondió. Usa el endpoint `apply/` o revisa Asterisk.

## Ver también

- [Troncales SIP](./troncales-sip.md)
- [Rutas y dialplan](./rutas-y-dialplan.md)
- [Campañas](./campanas.md)
- [Red y puertos](../instalacion/red-y-puertos.md)
- [Arquitectura](../general/arquitectura.md)
- [Glosario](../general/glosario.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
