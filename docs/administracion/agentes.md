# Agentes

Este manual explica cómo crear, editar y retirar agentes, qué pasa en Asterisk cuando se guarda un agente (extensión SIP, clave SIP y endpoint PJSIP), cómo se configuran los grupos de agentes y las razones de pausa, qué significa cada estado del agente y cómo se relaciona un agente con campañas y colas. Se basa en `frontend/pages/agents/index.vue`, `frontend/pages/settings/advanced.vue`, `backend/apps/agents/models.py`, `backend/apps/agents/signals.py`, `backend/apps/telephony/signals.py` y el `AgentSerializer` de `backend/apps/api/serializers.py`.

Un **agente** es un perfil (`Agent`) unido uno a uno a un usuario con rol `agent`. El perfil guarda el ID de agente, la extensión SIP, la clave SIP y la configuración de llamadas. Sin perfil de agente, un usuario con rol Agente no puede atender llamadas.

## Acceso

- Agentes: **Operación → Agentes** (ruta `/agents`). Visible para Administrador y Supervisor. En la API (`/api/agents/`) la lectura es para cualquier usuario autenticado y la escritura para admin o supervisor (`IsAdminOrSupervisorOrReadOnly`).
- Grupos y razones de pausa: **Administración → Grupos y pausas** (ruta `/settings/advanced`, página "Configuración Avanzada"). Visible para Administrador y Supervisor.

## Crear un agente

1. Entra a **Operación → Agentes** y haz clic en **Nuevo Agente**.
2. Al abrir el formulario, el sistema propone el siguiente **ID de Agente** (formato `AGT001`, `AGT002`, ...) y la siguiente **Extensión SIP** libre (desde `100` en adelante), y genera una **Contraseña SIP** aleatoria en el navegador.
3. Pestaña **Usuario**: completa **Nombre**, **Apellido**, **Email**, **Usuario** y **Contraseña** (mínimo 8 caracteres). Estas son las credenciales con las que el agente entra a VozipOmni.
4. Pestaña **Agente**: revisa **ID de Agente**, **Extensión SIP** y **Contraseña SIP**. Al escribir un ID o una extensión, el sistema verifica disponibilidad y muestra **OK** o **En uso**. El botón de flechas regenera el valor propuesto.
5. Pestaña **Configuración**: ajusta **Máx. Llamadas Simultáneas**, **Habilitar WebRTC**, **Auto-respuesta** y **Grabación de llamadas**.
6. Haz clic en **Crear Agente**. El botón queda deshabilitado mientras falte algún campo; el aviso "Completa los campos requeridos: ..." indica cuáles.

Validaciones del formulario: la contraseña de usuario debe tener al menos 8 caracteres y la Contraseña SIP al menos 6. El backend rechaza usuarios, correos, IDs o extensiones repetidos con mensajes como "La extensión SIP "101" ya está en uso".

## Qué se configura en Asterisk al guardar

Al crear el agente, el backend:

1. Crea el usuario con rol `agent` e `is_active_agent=True`. Si por la API no se envía contraseña, la cuenta queda con contraseña inutilizable (ver [Usuarios y roles](./usuarios-y-roles.md)).
2. Crea el perfil `Agent`. La clave SIP nunca queda vacía: si no se envía, el serializer genera una de 16 caracteres y, como respaldo, `Agent.save()` genera una aleatoria con `secrets.token_urlsafe(12)`.
3. Crea o actualiza el registro de **Extensión** con el mismo número (`backend/apps/agents/signals.py`): tipo `WEBRTC` y transporte `transport-wss` si WebRTC está habilitado, o `PJSIP` y `transport-udp` si no; contexto `from-internal`. Por eso la extensión del agente aparece también en **Telefonía → Extensiones**.
4. Regenera los archivos dinámicos de Asterisk y recarga PJSIP por AMI.

Para los agentes con WebRTC habilitado, `backend/apps/telephony/signals.py` escribe `/var/lib/asterisk/dynamic/pjsip_agents.conf`, incluido desde `pjsip.conf`. Cada agente queda así (la clave real se reemplaza aquí por un marcador):

```ini
[101](webrtc_endpoint)
auth=101-auth
aors=101-aor
callerid="Nombre Apellido" <101>

[101-auth]
type=auth
auth_type=userpass
username=101
password=<CLAVE_SIP_DEL_AGENTE>

[101-aor]
type=aor
max_contacts=2
remove_existing=no
contact=sip:101@<KAMAILIO_HOST>:5060
qualify_frequency=30
```

Qué significa:

- La plantilla `webrtc_endpoint` (en `pjsip.conf`) pone el endpoint en el contexto `from-internal`, con códecs `ulaw,alaw`, `direct_media=no` y opciones de NAT. No activa DTLS ni ICE en Asterisk, porque de eso se encargan Kamailio y RTPEngine.
- El navegador del agente se registra por WSS en Kamailio a través de nginx (el WebSocket exige un ticket firmado que solo entrega una sesión activa de VozipOmni). Las llamadas que el agente marca entran a Asterisk por el endpoint `kamailio-endpoint`, también en `from-internal`.
- `contact=` es un contacto estático hacia Kamailio: cuando Asterisk marca `PJSIP/101`, envía el INVITE a Kamailio y este lo entrega al navegador. `remove_existing=no` evita que un REGISTER borre ese contacto. `KAMAILIO_HOST` sale de la variable de entorno del mismo nombre (por defecto `kamailio`).
- Para no duplicar objetos, las extensiones de agentes WebRTC no se escriben en `pjsip_extensions.conf`.

En el dialplan dinámico (`extensions_dynamic.conf`, contexto `[from-internal]`) cada extensión activa recibe una entrada que graba con MixMonitor y marca `Dial(PJSIP/<extensión>,30,trg)`. Así los agentes y extensiones pueden llamarse entre sí marcando el número interno.

Si desmarcas **Habilitar WebRTC**, la extensión se trata como softphone SIP (`transport-udp`) y se escribe en `pjsip_extensions.conf` en lugar de `pjsip_agents.conf`.

## Editar un agente

1. Haz clic en el ícono de lápiz de la fila.
2. Cambia lo necesario y haz clic en **Actualizar Agente**.

Tenlo en cuenta:

- **ID de Agente** y **Extensión SIP** aparecen deshabilitados: no se cambian desde la pantalla.
- Deja **Contraseña** o **Contraseña SIP** vacías para conservar las actuales. Si escribes una nueva Contraseña SIP, se actualiza la extensión y se regenera `pjsip_agents.conf`. Pide al agente que cierre y vuelva a abrir su consola para que el softphone use la nueva clave.
- Nombre, apellido o correo solo se envían si los escribes; vacíos no cambian.
- Según el código revisado, al editar el formulario **no carga** los valores guardados de **Máx. Llamadas Simultáneas**, **Auto-respuesta** y **Grabación de llamadas**: muestra 1, desmarcado y marcado, y los envía al guardar. Revisa la pestaña **Configuración** antes de hacer clic en **Actualizar Agente** para no sobrescribir esos valores.

## Eliminar un agente

El ícono de papelera pide confirmación ("¿Estás seguro de eliminar este agente?"). Al confirmar, el backend:

- Desactiva la extensión del agente en Asterisk (el registro de Extensión queda con `is_active=False`).
- Desactiva el usuario (`is_active=False`, `is_active_agent=False`). El usuario sigue apareciendo como inactivo en **Usuarios y roles**.
- Borra el perfil de agente y regenera `pjsip_agents.conf`.

Las llamadas históricas conservan sus datos; la relación con el agente borrado queda vacía.

## Estados del agente

| Estado (valor) | Etiqueta | Significado |
|---|---|---|
| `available` | Disponible | Conectado y listo para recibir llamadas. Se asigna al iniciar sesión en la consola. |
| `busy` | Ocupado / En llamada | Ocupado. La tabla de Agentes lo muestra como "En llamada". |
| `oncall` | En Llamada | Atendiendo una llamada. |
| `break` | En Descanso / En Pausa | En pausa con una razón de pausa. |
| `wrapup` | Post-Llamada | Tiempo posterior a la llamada para cerrar la gestión. |
| `offline` | Desconectado | Sin sesión de agente. |

Efecto en las colas (`backend/core/event_handlers.py`):

- Al iniciar sesión, el agente se agrega por AMI (`QueueAdd`) a cada cola donde es miembro.
- Al cerrar sesión, se retira de esas colas.
- Al pasar a `break`, `offline` o `wrapup`, queda en pausa en sus colas; al volver a otro estado se reanuda.

Cada cambio de estado se registra en el historial (`AgentStatusHistory`), que alimenta los reportes de tiempos y pausas.

## Razones de pausa

En **Administración → Grupos y pausas**, pestaña **Razones de Pausa**:

1. Haz clic en **Nueva razón**.
2. Completa **Nombre \***, **Código (para Asterisk)**, **Duración máx. (min)**, **Orden**, **¿Es pagada?** y **¿Activa?**.
3. Haz clic en **Crear** (o **Guardar** al editar).

| Campo | Descripción |
|---|---|
| Nombre | Texto que ve el agente al elegir la pausa. Único. |
| Código | Identificador corto, único (por ejemplo `LUNCH`). El formulario no lo marca como obligatorio, pero el modelo sí lo exige. |
| Duración máx. (min) | Tope en minutos. Vacío significa sin límite (la tabla muestra "∞"). No corta la pausa: el reporte de pausas marca como excedidas las que superan el tope. |
| Orden | Posición en la lista. |
| ¿Es pagada? | Clasificación de la pausa (la tabla la muestra como "Pagada" o "No pagada"). |
| ¿Activa? | Interruptor también disponible en la columna **Activa** de la tabla. |

El agente elige la razón en su consola y el sistema guarda el nombre como motivo de la pausa. El reporte compara ese motivo con el nombre o el código de la razón para detectar excesos. Según el código revisado, la consola del agente carga todas las razones sin filtrar por **¿Activa?**; si necesitas que una razón deje de aparecer, elimínala.

## Grupos de agentes

En la pestaña **Grupos de Agentes**:

1. Haz clic en **Nuevo grupo**, completa **Nombre \***, **Descripción** y **¿Activo?**, y haz clic en **Crear**.
2. En la tarjeta del grupo, haz clic en **Agentes**. La ventana muestra dos listas: **En el grupo** y **Disponibles**. Usa **+** para agregar y **−** para retirar. Cada cambio se guarda de inmediato.
3. **Editar** cambia nombre, descripción o estado; la papelera elimina el grupo.

Un agente puede estar en varios grupos. El modelo de campaña tiene un campo "Skills requeridos" que apunta a grupos de agentes; en la interfaz revisada no encontré dónde asignarlo ni cómo lo usa el marcador, así que por ahora trata los grupos como una herramienta de organización.

## Asignación a campañas y colas

- **Campañas.** La relación agente–campaña (`Agent.campaigns`) no tiene control en la página de Agentes ni en la de Campañas. Se puede asignar desde el administrador de Django (`/admin/`, Agentes, sección Campañas) o por API con `PATCH /api/agents/{id}/` enviando `{"campaigns": [<ids>]}`. La consola del agente lista las campañas activas en las que está asignado. Al clonar una campaña se copian sus agentes.
- **Colas.** La pertenencia a colas (`QueueMember`, con penalización) tampoco tiene pantalla propia en el frontend; se administra en el administrador de Django, en la cola, sección de miembros. Ver [Colas](./colas.md).

## Campos del agente

| Campo | Pestaña | Efecto |
|---|---|---|
| Nombre, Apellido | Usuario | Nombre del usuario; se usa como nombre en el Caller ID interno (`callerid="Nombre Apellido" <ext>`). |
| Email | Usuario | Correo del usuario; necesario para recuperar la contraseña. |
| Usuario, Contraseña | Usuario | Credenciales de acceso a VozipOmni. |
| ID de Agente | Agente | Identificador único del agente (por ejemplo `AGT001`). |
| Extensión SIP | Agente | Número interno único. Es el nombre del endpoint PJSIP y el usuario de autenticación SIP. |
| Contraseña SIP | Agente | Clave de autenticación SIP del endpoint. Se genera automáticamente si no se indica. |
| Máx. Llamadas Simultáneas | Configuración | Límite de llamadas concurrentes; el agente se considera disponible solo si tiene menos llamadas activas que este valor. |
| Habilitar WebRTC | Configuración | Sí: endpoint WebRTC vía Kamailio (`pjsip_agents.conf`). No: softphone SIP por UDP. |
| Auto-respuesta | Configuración | Según la pantalla, contesta automáticamente las llamadas entrantes. En el backend y en los componentes de consola revisados no encontré lógica que use este valor; verifícalo en tu versión antes de depender de él. |
| Grabación de llamadas | Configuración | Se guarda en el perfil. El dialplan generado graba con MixMonitor en extensiones, colas y rutas sin consultar este campo, así que desmarcarlo no detiene la grabación según el código revisado. |

## Buenas prácticas

- Crea los agentes desde esta página, no desde Usuarios y roles: así se crean usuario, perfil y extensión en un solo paso.
- Usa un rango de extensiones exclusivo para agentes (por ejemplo 100–199) y deja otros rangos para colas e IVR, para evitar choques con sus extensiones.
- Deja que el sistema genere la Contraseña SIP. No la compartas: el agente no la necesita para usar la consola web.
- Define las razones de pausa con códigos cortos y estables antes de salir a producción, y fija una duración máxima para las que tienen tope (almuerzo, baño).
- Después de editar, revisa la pestaña Configuración (ver la limitación descrita arriba).

## Problemas frecuentes

- **"El nombre de usuario ... ya está en uso".** Ya existe un usuario con ese nombre, por ejemplo uno creado en Usuarios y roles. Usa otro nombre o asocia el usuario existente desde `/admin/`.
- **"La extensión SIP ... ya está en uso".** Usa el botón de regenerar o elige otro número.
- **La consola del agente no registra el softphone.** Verifica que el agente tenga **Habilitar WebRTC**, que su usuario esté activo y que `pjsip_agents.conf` contenga su extensión. Revisa también Kamailio y nginx en [Depuración VoIP](../operacion/depuracion-voip.md).
- **Las llamadas hacia el agente fallan con CHANUNAVAIL.** El AOR del agente no tiene contacto. Revisa que `KAMAILIO_HOST` resuelva desde Asterisk y que el archivo tenga la línea `contact=`.
- **El agente no recibe llamadas de la cola.** Confirma que es miembro de la cola, que inició sesión en la consola y que no está en pausa o post-llamada.
- **Una pausa no aparece como excedida en el reporte.** El motivo guardado debe coincidir con el nombre o el código de la razón, y la razón debe tener **Duración máx.**

## Ver también

- [Usuarios y roles](./usuarios-y-roles.md)
- [Colas](./colas.md)
- [Campañas](./campanas.md)
- [Rutas y dialplan](./rutas-y-dialplan.md)
- [Reportes](./reportes.md)
- [Manual del agente](../manuales/manual-agente.md)
- [Arquitectura](../general/arquitectura.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [API: usuarios y agentes](../api/usuarios-y-agentes.md)
