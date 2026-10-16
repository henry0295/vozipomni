# Rutas y dialplan

Este manual explica cómo decide Asterisk por dónde sale una llamada marcada por un agente (rutas salientes), a dónde va una llamada que entra por un DID (rutas entrantes) y cómo se usan los destinos personalizados. También muestra el dialplan que genera VozipCX y cómo se aplica. Se basa en `frontend/pages/outbound-routes/index.vue`, `frontend/pages/inbound-routes/index.vue`, `frontend/pages/custom-destinations/index.vue`, los modelos `OutboundRoute`, `InboundRoute` y `CustomDestination` de `backend/apps/telephony/models.py`, `backend/apps/telephony/asterisk_config.py`, `backend/apps/telephony/security.py`, `backend/apps/telephony/signals.py` y `docker/asterisk/configs/extensions.conf`.

El dialplan tiene una parte estática (`extensions.conf`) y una dinámica (`/var/lib/asterisk/dynamic/extensions_dynamic.conf`), que el backend regenera desde la base de datos. Las rutas salientes se escriben en el contexto `[from-internal]`, que es donde entran las llamadas de agentes y extensiones. Las rutas entrantes se escriben en `[from-pstn]`, que es el contexto por defecto de las troncales.

## Acceso

- **Telefonía → Rutas Salientes** (ruta `/outbound-routes`), **Telefonía → Rutas Entrantes (DIDs)** (`/inbound-routes`) y **Telefonía → Destinos Personalizados** (`/custom-destinations`). Visibles solo para Administrador.
- API: `/api/telephony/outbound-routes/`, `/api/telephony/inbound-routes/` y la de destinos personalizados, con permiso `IsAdminUserCustom`.

## Rutas salientes

### Crear una ruta saliente

1. Entra a **Telefonía → Rutas Salientes** y haz clic en **Agregar Ruta**.
2. Pestaña **Básica**: escribe el **Nombre** (por ejemplo "Colombia Celulares") y deja marcada **Ruta Activa**.
3. Pestaña **Patrones de Marcado**: escribe el **Patrón de Discado** y, si hace falta, **Prefijo a Agregar** o **Dígitos a Eliminar**.
4. Pestaña **Troncales**: elige la **Troncal**.
5. Pestaña **Configuración**: opcionalmente, **Prefijo Caller ID**.
6. Haz clic en **Guardar**.

La tabla muestra **Nombre**, **Patrón**, **Troncal**, **Prefijo** (el prefijo a agregar) y **Estado**.

### Campos

| Campo (pantalla) | Campo del modelo | Efecto en el dialplan |
|---|---|---|
| Nombre | `name` | Texto del `NoOp` de la ruta. |
| Patrón de Discado | `pattern` | Extensión de la ruta. Si contiene `X`, `Z`, `N`, `.`, `!` o `[ ]` y no empieza por `_`, el generador le agrega el `_`. |
| Prefijo a Agregar | `prepend` | `dial_number=<prefijo>${EXTEN}`. |
| Dígitos a Eliminar | `prefix` | Quita del inicio tantos dígitos como caracteres tenga el valor: `dial_number=${EXTEN:<n>}`. Solo se aplica si **Prefijo a Agregar** está vacío. |
| Troncal | `trunk` | Troncal usada en el `Dial` y en el control de canales. |
| Prefijo Caller ID | `callerid_prefix` | `Set(CALLERID(num)=<prefijo>${CALLERID(num)})`: antepone el valor al número de origen del canal. |
| Ruta Activa | `is_active` | Las rutas inactivas no se escriben. |
| (solo API) Prioridad | `priority` | Orden en que se escriben las rutas (menor primero). Por defecto 1. |
| (solo API) Tiempo de timbre | `ring_time` | Segundos de timbre del `Dial`. Por defecto 60. |
| (solo API) Opciones Dial | `dial_options` | Opciones del `Dial`. Por defecto `trg`. |

**Prioridad**, **Tiempo de timbre** y **Opciones Dial** no aparecen en el formulario ni en el administrador de Django. Se cambian con `PATCH /api/telephony/outbound-routes/{id}/`, por ejemplo `{"priority": 2, "ring_time": 45, "dial_options": "tT"}`. Al editar desde la pantalla, el formulario reenvía los valores guardados, así que no se pierden.

Sobre la prioridad: Asterisk no evalúa las extensiones en el orden del archivo, sino del patrón más específico al menos específico. La prioridad solo decide cuál ruta queda cuando dos rutas tienen exactamente el mismo patrón: se escribe primero la de menor número y Asterisk descarta la segunda definición. Para tener troncal de respaldo no basta con duplicar el patrón.

Las opciones de `Dial` más usadas: `t` y `T` permiten transferir al llamado y al llamante, `r` genera timbre hacia el llamante, `g` continúa el dialplan cuando el otro extremo cuelga.

### Control antifraude en cada ruta

Antes de marcar, cada ruta ejecuta `GoSub(vozip-outbound-policy,s,1(...))` con el número marcado, el número final, el nombre de la troncal y su **Máx. Canales Simultáneos** (0 si en **Seguridad y antifraude** está apagado "Canales máximos por troncal"). El contexto `[vozip-outbound-policy]` revisa longitud máxima, internacionales, prefijos bloqueados, lista blanca, llamadas por extensión por hora, canales por troncal y total de salientes. Si bloquea:

- Por troncal llena, límite total o tasa por extensión: locución `all-circuits-busy-now` y rechazo con causa 34.
- Por número no permitido: locución `ss-noservice` y rechazo con causa 21.

Detalle en [Seguridad y antifraude](./seguridad-antifraude.md).

### Ejemplos para Colombia

Supongamos que el proveedor recibe los números en formato nacional de 10 dígitos:

| Nombre | Patrón | Prefijo a Agregar | Dígitos a Eliminar | Qué marca el agente |
|---|---|---|---|---|
| Colombia Celulares | `_3XXXXXXXXX` | | | `3001234567` |
| Colombia Fijos | `_60XXXXXXXX` | | | `6012345678` (60 + indicativo + 7 dígitos) |
| Celulares con 9 | `_93XXXXXXXXX` | | `9` | `93001234567`; sale `3001234567` |
| Contactos en E.164 | `_+57X.` | | `+57` | `+573001234567`; sale `3001234567` |

La última ruta es la que necesitan las campañas progresivas y preview: los contactos se guardan en formato E.164 (`+57...`) y el marcador los envía tal cual a `from-internal` (ver [Contactos](./contactos.md)).

Si el proveedor exige el indicativo de país, usa **Prefijo a Agregar** `57` en las dos primeras rutas: sale `573001234567`. No combines **Prefijo a Agregar** con **Dígitos a Eliminar** en la misma ruta: el generador aplica solo el prefijo y deja el número completo.

Evita patrones genéricos como `_X.` salvo que de verdad quieras enviar cualquier número por esa troncal; también capturan números internos que no existan como extensión.

### Dialplan generado

Para la ruta "Colombia Celulares" por la troncal `proveedor_principal` (30 canales), `extensions_dynamic.conf` queda así:

```ini
[from-internal]
exten => _3XXXXXXXXX,1,NoOp(Saliente: Colombia Celulares via proveedor_principal [prioridad=1])
 same => n,Set(__TRUNK_NAME=proveedor_principal)
 same => n,Set(dial_number=${EXTEN})
 same => n,GoSub(vozip-outbound-policy,s,1(${EXTEN},${dial_number},proveedor_principal,30))
 same => n,MixMonitor(${STRFTIME(${EPOCH},,%Y%m%d-%H%M%S)}_${UNIQUEID}_${CALLERID(num)}_${dial_number}.wav,ab)
 same => n,Dial(PJSIP/${dial_number}@proveedor_principal,60,trg)
 same => n,Hangup()
```

El `${UNIQUEID}` en el nombre del archivo permite asociar la grabación con el registro de la llamada.

### Cuando ningún patrón coincide

Si el número no coincide con ninguna extensión interna ni ruta saliente, lo atrapa el catch-all estático `_X.` de `[from-internal]` en `extensions.conf`: registra en el log "Sin ruta para <número>" con el aviso de verificar las rutas salientes, envía la locución `ss-noservice` como early media y cuelga con causa 3, que el softphone ve como 404. Es el error de configuración más común: la troncal está registrada pero falta la ruta, o el patrón no cubre el formato que marca el agente.

## Rutas entrantes (DIDs)

### Crear una ruta entrante

1. Entra a **Telefonía → Rutas Entrantes (DIDs)** y haz clic en **Agregar Ruta**.
2. Pestaña **Información Básica**: **Descripción**, **Prioridad** y **Ruta Activada**.
3. Pestaña **Identificación DID**: **DID/Número**, exacto (`6012345678`) o patrón (`_60XXXXXXXX`). Aquí el `_` no se agrega solo: escríbelo si usas comodines.
4. Pestaña **Destino**: **Tipo de Destino** y **Destino**. Para cada tipo, la lista muestra los objetos creados en el sistema.
5. Haz clic en **Crear Ruta**.

El DID debe coincidir exactamente con el número que el proveedor envía en la Request-URI (con o sin `57`, con o sin `+`). Si no hay coincidencia, la llamada entra al `_X.` estático de `[from-pstn]`, se graba y pasa al IVR 9000 de `extensions.conf`.

### Tipos de destino

| Tipo | Valor de Destino | Dialplan generado |
|---|---|---|
| IVR | Extensión del IVR | `Goto(ivr-<extensión>,s,1)` |
| Cola | Nombre de la cola | `Queue(<nombre>,tT,,,300)` |
| Extensión | Número de extensión | `Dial(PJSIP/<ext>,30,trg)` y, si no contesta, `VoiceMail(<ext>@default,u)` |
| Buzón de Voz | Número de buzón | `VoiceMail(<buzón>@default)` |
| Anuncio | Audio sin extensión (por ejemplo `custom/bienvenida`) | `Playback(<audio>)` |
| Destino Personalizado | Nombre del destino | `Goto(<context>,<extension>,<priority>)` |

El backend valida que el IVR, la cola, la extensión, el buzón o el destino personalizado existan y estén activos. Toda ruta entrante graba con MixMonitor antes de enviar al destino.

La pestaña **Destino** incluye **Condición de Horario (Opcional)**. Según el código revisado, el valor se guarda en la ruta pero el generador del dialplan no lo usa: la llamada va siempre al destino configurado.

Ejemplo generado para el DID `6012345678` hacia la cola `ventas`:

```ini
[from-pstn]
exten => 6012345678,1,NoOp(DID: Línea principal)
 same => n,Set(CALLERID(name)=${CALLERID(num)})
 same => n,Set(__DID_NUMBER=6012345678)
 same => n,MixMonitor(${STRFTIME(${EPOCH},,%Y%m%d-%H%M%S)}_${UNIQUEID}_6012345678_${CALLERID(num)}.wav,ab)
 same => n,Queue(ventas,tT,,,300)
 same => n,Hangup()
```

## Destinos personalizados

Un destino personalizado es un punto del dialplan (context, extension, priority) reutilizable desde rutas entrantes e IVR. Sirve para enviar llamadas a lógica escrita a mano en Asterisk.

1. Entra a **Telefonía → Destinos Personalizados** y haz clic en **Nuevo destino**.
2. Completa **Nombre**, **Descripción**, **Context**, **Extension** (por defecto `s`) y **Priority** (por defecto 1).
3. En **Configuración avanzada**, opcionalmente, **Context (fallo)**, **Extension (fallo)**, **Priority (fallo)** y **Destino activo**.
4. Haz clic en **Crear destino**.

Tenlo en cuenta:

- El contexto indicado debe existir en Asterisk; VozipCX no lo crea.
- Según el código revisado, el destino de fallo se guarda pero no se usa en el dialplan generado.
- El `Goto` se resuelve al generar el dialplan. Guardar un destino personalizado no regenera el dialplan; si cambias su context, extension o priority, guarda de nuevo la ruta o el IVR que lo usa, o ejecuta `generate_asterisk_config`.

## Cómo se aplica

Al guardar o eliminar una ruta entrante, una ruta saliente, una troncal, una extensión, un IVR, una cola o un miembro de cola, `backend/apps/telephony/signals.py` lanza en segundo plano la sincronización completa: regenera `pjsip_wizard.conf`, `extensions_dynamic.conf`, `queues_dynamic.conf` y demás archivos dinámicos, y recarga por AMI PJSIP, el dialplan, voicemail y colas. El cambio queda activo en pocos segundos, sin reiniciar Asterisk.

Para forzarlo o revisar el resultado:

```bash
docker exec vozipomni_backend python manage.py generate_asterisk_config
docker exec vozipomni_asterisk asterisk -rx 'dialplan show from-internal'
docker exec vozipomni_asterisk asterisk -rx 'dialplan show 3001234567@from-internal'
```

No edites `extensions_dynamic.conf` a mano: se sobrescribe en la siguiente sincronización.

## Buenas prácticas

- Crea una ruta por tipo de número (celulares, fijos, 01800) con patrones de longitud fija. Así el control antifraude y los reportes son más claros.
- Prueba cada ruta con `dialplan show <número>@from-internal` antes de salir a producción.
- Usa rangos de extensiones internas que no choquen con los patrones de las rutas salientes.
- Registra los DIDs en el mismo formato que envía el proveedor; revisa uno real en el log de Asterisk.
- Define una ruta entrante por cada DID contratado en lugar de dejar que caigan en el IVR 9000 por defecto.

## Problemas frecuentes

- **El agente marca y escucha "servicio no disponible" (404).** Ninguna ruta coincide. Revisa el patrón y que la ruta esté activa.
- **"Todos los circuitos ocupados".** Se alcanzó el límite de canales de la troncal o el total de la política antifraude.
- **La ruta existe pero sale por otra troncal.** Otra ruta tiene un patrón más específico para ese número.
- **Las llamadas entrantes van al IVR 9000.** El DID no coincide con lo que envía el proveedor.
- **La condición de horario no tiene efecto.** Es la limitación descrita arriba.
- **Un destino personalizado apunta a un contexto viejo.** Regenera el dialplan después de editarlo.

## Ver también

- [Troncales SIP](./troncales-sip.md)
- [Colas](./colas.md)
- [IVR](./ivr.md)
- [Seguridad y antifraude](./seguridad-antifraude.md)
- [Glosario](../general/glosario.md)
- [Arquitectura](../general/arquitectura.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
- [API: telefonía](../api/telefonia.md)
