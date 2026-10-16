# Campañas

Este manual explica cómo crear y operar campañas en VozipOmni: tipos de campaña y de marcación, campos de configuración, cola y lista de contactos, detección de contestador (AMD), formularios de gestión, calificaciones (tipificaciones) y cómo se inicia o pausa una campaña. Se basa en `frontend/pages/campaigns/index.vue`, `frontend/pages/campaigns/[id].vue`, `frontend/pages/campaign-forms/index.vue`, los modelos de `backend/apps/campaigns/models.py`, el `CampaignSerializer` de `backend/apps/api/serializers.py`, el `CampaignViewSet` de `backend/apps/api/viewsets.py`, `backend/apps/campaigns/services.py`, `backend/apps/campaigns/tasks.py`, `dialer_engine/dialer.py` y el contexto `[outbound-queue]` de `docker/asterisk/configs/extensions.conf`.

Una **campaña** agrupa el trabajo de un equipo: qué contactos se llaman (lista), a qué cola llegan las llamadas, qué agentes participan, con qué formulario se gestionan y con qué calificaciones se cierran. Las campañas salientes las ejecuta el servicio `dialer_engine`, que recibe la configuración por Redis y origina las llamadas por AMI.

## Acceso

- **Operación → Campañas** (ruta `/campaigns`). Visible para Administrador, Supervisor y Analista. En la API (`/api/campaigns/`) la escritura es para admin o supervisor (`IsAdminOrSupervisorOrReadOnly`).
- **Operación → Formularios de campaña** (ruta `/campaign-forms`, página "Formularios y calificaciones"). Visible para Administrador y Supervisor.

La página de campañas muestra pestañas **Activas**, **Pausadas**, **Completadas** y **Todas**, y una tarjeta por campaña con tipo, progreso, **Tasa de éxito** y **Contactos restantes**.

## Tipos de campaña y de marcación

| Tipo de Campaña | Tipos de Marcación permitidos | Cómo funciona |
|---|---|---|
| Saliente (`outbound`) | Progresivo, Predictivo | El marcador llama a los contactos de la lista. |
| Entrante (`inbound`) | Ninguno (se guarda vacío) | Agrupa llamadas que llegan por DIDs y colas. |
| Manual (`manual`) | Manual | El marcador asigna un contacto al agente y el agente marca desde su consola. |
| Preview (`preview`) | Preview | El agente ve el contacto y decide aceptar o rechazar antes de marcar. |

El backend rechaza combinaciones distintas ("Combinación inválida: campaign_type=... no permite dialer_type=...").

Cómo origina cada marcador (`dialer_engine/dialer.py`):

- **Progresivo y Preview**: primero timbra la extensión del agente; cuando contesta, marca el número del contacto en `from-internal`. La llamada pasa por las rutas salientes, así que el formato del número guardado debe coincidir con algún patrón (ver [Rutas y dialplan](./rutas-y-dialplan.md)).
- **Predictivo**: marca directamente al contacto por la primera troncal activa (`PJSIP/<troncal>/<número>`), sin pasar por las rutas salientes, y envía la llamada contestada al contexto `[outbound-queue]`, que la pasa a la cola de la campaña. Antes de originar aplica la misma política antifraude de las rutas (canales por troncal, límite total, números bloqueados). La relación de llamadas por agente empieza en 1,5 y se ajusta entre 1,0 y 3,0 según el abandono, con meta de 3 %.
- **Manual**: no origina; publica el contacto para el agente disponible durante 5 minutos.

## Crear una campaña

1. Entra a **Operación → Campañas** y haz clic en **Nueva Campaña**.
2. Pestaña **Información Básica**: **Nombre de la Campaña**, **Descripción**, **Tipo de Campaña** y **Tipo de Marcación**.
3. Pestaña **Recursos**: **Cola (ACD)** y **Lista de Contactos**.
4. Pestaña **Programación**: **Fecha de Inicio** y **Fecha de Fin**.
5. Pestaña **Configuración Avanzada**: **Llamadas Simultáneas Máx.**, **Intentos por Contacto** y, en predictivas, **Detectar contestador automático (AMD)**.
6. Haz clic en **Crear Campaña**. La campaña queda en **Borrador**.

Validaciones y detalles del código revisado:

- **Fecha de Inicio** es obligatoria en el modelo. Aunque la pantalla diga que se pueden dejar vacías, si no la indicas el backend rechaza la campaña y la pantalla muestra solo "Error al crear campaña".
- Las campañas Saliente y Preview exigen **Lista de Contactos**.
- **Intentos por Contacto** se guarda como `max_retries` (0 a 10).
- **Llamadas Simultáneas Máx.** no corresponde a ningún campo del modelo y no se guarda. El límite real de llamadas lo ponen los canales de la troncal y la política antifraude.
- El nombre es único.

## Campos de configuración

Además de los del formulario, el modelo `Campaign` tiene campos que solo se cambian por API (`PATCH /api/campaigns/{id}/`) o en el administrador de Django:

| Campo | Por defecto | Uso |
|---|---|---|
| `call_timeout` | 30 | Segundos de timbre al originar (10 a 300). |
| `max_calls_per_agent` | 1 | Validado entre 1 y 5. |
| `max_retries` | 3 | Intentos por contacto. Tras cada llamada no contestada, ocupada, fallida o atendida por contestador, el contacto vuelve a Pendiente o, al llegar al tope, pasa a Fallido (ver [Contactos](./contactos.md)). |
| `retry_delay` | 300 | Segundos entre reintentos. Según el código revisado, el marcador todavía no lo usa. |
| `schedule_start_time`, `schedule_end_time` | vacío | Horario diario. El marcador no los lee; usa una ventana fija de 8:00 a 20:00, lunes a sábado, en la zona horaria del contacto o de la campaña. |
| `timezone` | `America/Bogota` | Zona horaria usada por esa ventana. |
| `dnc_enabled` | Sí | Consulta la lista negra antes de marcar. |
| `preview_timeout` | 30 | Segundos que el agente tiene para decidir en Preview. |
| `vip_priority_boost` | 10 | Prioridad extra para contactos VIP. |
| `script_template` | vacío | Guion de la llamada. |
| `is_template`, `template_name` | No | Marca la campaña como plantilla; `POST /api/campaigns/{id}/clone/` la copia con sus agentes. |
| `required_skills` | vacío | Grupos de agentes. Sin uso en el marcador revisado. |

Contadores de solo lectura: `total_contacts`, `contacted` y `successful`. Se recalculan al terminar cada llamada: contactados son las llamadas completadas, no contestadas u ocupadas; exitosas, las completadas con una calificación marcada como éxito.

## Asignar agentes, lista y cola

- **Cola**: se elige en **Recursos**. El predictivo envía las llamadas contestadas a esa cola; sin cola, el contexto `[outbound-queue]` reproduce `vm-goodbye` y cuelga. Los agentes deben ser miembros de la cola (ver [Colas](./colas.md)).
- **Lista de contactos**: se elige en **Recursos**. Al iniciar, se cargan en Redis los contactos con estado nuevo, pendiente o rellamada, ordenados por prioridad (ver [Contactos](./contactos.md)).
- **Agentes**: la pantalla no tiene control para asignarlos. Usa `PATCH /api/agents/{id}/` con `{"campaigns": [<ids>]}` o el administrador de Django (ver [Agentes](./agentes.md)). Un agente no asignado no puede guardar calificaciones en la campaña.

Según el código revisado, el marcador busca los agentes disponibles en el conjunto Redis `campaign:{id}:agents:available`, y ningún componente del repositorio lo llena. Si las campañas automáticas no originan llamadas aunque haya agentes conectados, empieza por ahí.

## Detección de contestador (AMD)

Solo para marcación predictiva. Se activa al crear la campaña o en la página de detalle (**Detectar contestador (AMD)**, **Guardar AMD**).

- Con AMD activo, `[outbound-queue]` ejecuta `AMD()` al contestar. `HUMAN` o `NOTSURE` pasan a la cola; `MACHINE` aplica la acción; `HANGUP` cuelga.
- **Si es contestador**: **Colgar**, o **Dejar mensaje grabado**, que espera 1,5 s de silencio (máximo 10 s) y reproduce el **Audio del mensaje** (por ejemplo `custom/mensaje-campana`).
- El resultado se informa con el evento `DialerAMD`. Las personas que tardan en hablar pueden detectarse como contestador; revisa los resultados en los reportes.
- La página de detalle indica que el cambio se aplica al pausar y reanudar la campaña.

## Formularios de campaña

En **Formularios de campaña**, pestaña **Formularios**:

1. Haz clic en **Nuevo**, escribe **Nombre** y **Descripción** y deja **Activo** marcado.
2. Haz clic en **Agregar campo** por cada dato. Completa **Etiqueta**, **Nombre interno** (se genera desde la etiqueta, sin espacios), **Tipo**, texto de ayuda, opciones separadas por coma (para Lista y Selección múltiple) y **Obligatorio**.
3. Ordena con las flechas y revisa la **Vista previa (como lo verá el agente)**.
4. Haz clic en **Guardar**.

Tipos disponibles: Texto, Texto largo, Número, Lista, Selección múltiple, Casilla, Fecha, Teléfono y Correo. El esquema se guarda como lista JSON; cada campo exige `name`, `label` y `type`.

Para asignarlo, ve a la pestaña **Calificaciones por campaña**, elige la **Campaña** y el **Formulario de gestión de la campaña**. Lo que el agente llena se guarda en la llamada (`metadata.form_data`) y se copia a los campos personalizados del contacto.

## Calificaciones (tipificaciones)

En la pestaña **Calificaciones por campaña**, elige la campaña y haz clic en **Nueva calificación**:

| Campo | Uso |
|---|---|
| Código | Obligatorio y único dentro de la campaña (por ejemplo `VENTA`). La consola lo envía al guardar la gestión. |
| Nombre | Texto que ve el agente (por ejemplo "Venta concretada"). |
| Orden | Posición en la consola. |
| Descripción | Informativa. |
| Formulario específico (opcional) | Reemplaza el formulario de la campaña para esta calificación. |
| Cuenta como éxito (`is_success`) | Suma en exitosos, en la tasa de éxito y en los reportes de campañas y tipificaciones. |
| Requiere rellamada (`requires_callback`) | La consola muestra "Programar callback" (fecha y hora; 09:00 si no se indica hora) y el backend intenta crear una devolución de llamada (Callback). Suma en la columna de devoluciones del reporte de campañas. |

Ejemplo para una campaña de ventas: `VENTA` (éxito), `INTERESADO` (requiere rellamada), `NO_INTERESA`, `NUMERO_ERRADO` y `BUZON`.

Dos detalles del código revisado:

- Si la campaña no tiene calificaciones, la consola del agente muestra una lista predeterminada (por ejemplo `CALLBACK`), pero el backend solo acepta códigos que existan en la campaña y responde "Disposition ... not found for campaign ...". Crea siempre las calificaciones antes de iniciar.
- Al guardar una calificación con rellamada y fecha, `save_disposition` crea el `CallbackRequest` con un campo `contact_id` que el modelo no tiene, lo que hace fallar la petición. Prueba este flujo en tu versión antes de depender de él; mientras tanto, las devoluciones se pueden crear en **Operación → Callbacks**.

## Iniciar, pausar y reanudar

- **Iniciar** (campañas en Borrador) y **Reanudar** (Pausadas) llaman a `POST /api/campaigns/{id}/start/`. Saliente y Preview no inician si la lista no tiene contactos ("has no contacts to process"). Al iniciar, el backend publica la configuración y los contactos en Redis y avisa al marcador.
- **Pausar** llama a `POST /api/campaigns/{id}/pause/` y solo funciona sobre campañas activas. Según el código revisado, la pausa cambia el estado, pero no hay un receptor que envíe la señal de parada al marcador; esa señal solo se envía al detener la campaña desde la capa de servicios, que no tiene botón. Verifica en los logs de `dialer_engine` que la campaña se detuvo.
- Una tarea periódica (cada 60 s) vuelve a publicar en Redis las campañas activas cuya fecha de inicio ya pasó y cuya fecha de fin no ha llegado.
- La pestaña **Completadas** filtra por el estado `completed`, pero el modelo usa `finished` (Finalizada). Las campañas finalizadas solo aparecen en **Todas**.

La página de detalle (**Ver detalles**) muestra contactos totales, contactados, tasa de éxito, restantes, configuración y las últimas llamadas. Según el código revisado, **Cola ACD**, **Lista contactos**, **Llamadas máx** e **Intentos máx** muestran "-" porque leen nombres de campo que el serializer no entrega.

## Buenas prácticas

- Crea primero la cola con sus miembros, la lista de contactos, el formulario y las calificaciones; después la campaña.
- Define al menos una calificación de éxito y una de rellamada antes de iniciar, o la tasa de éxito se quedará en 0.
- Guarda los teléfonos en un formato que coincida con tus rutas salientes, y prueba una llamada progresiva antes de cargar la base completa.
- En predictivo, revisa el abandono en los reportes durante la primera hora y ajusta el número de agentes.
- Usa plantillas (`is_template`) y clonación para campañas recurrentes.

## Problemas frecuentes

- **"Error al crear campaña" sin detalle.** Falta **Fecha de Inicio** o la lista de contactos en una campaña Saliente o Preview.
- **La campaña no inicia: "has no contacts to process".** La lista está vacía o su contador `total_contacts` está en 0.
- **La campaña está activa pero no marca.** Revisa los agentes disponibles para el marcador (ver arriba), la ventana horaria de 8:00 a 20:00 y los logs de `dialer_engine`.
- **Las llamadas progresivas fallan con "servicio no disponible".** El número del contacto no coincide con ninguna ruta saliente.
- **El agente no puede guardar la calificación ("Agent is not assigned to this campaign").** Asigna el agente a la campaña.
- **"Disposition ... not found for campaign ...".** La campaña no tiene esa calificación; el agente está viendo la lista predeterminada de la consola.
- **La tasa de éxito no sube.** Ninguna calificación usada tiene **Cuenta como éxito**, o la llamada no quedó como completada.

## Ver también

- [Contactos](./contactos.md)
- [Colas](./colas.md)
- [Agentes](./agentes.md)
- [Rutas y dialplan](./rutas-y-dialplan.md)
- [Seguridad y antifraude](./seguridad-antifraude.md)
- [Reportes](./reportes.md)
- [Glosario](../general/glosario.md)
- [Arquitectura](../general/arquitectura.md)
- [API: campañas y contactos](../api/campanas-y-contactos.md)
