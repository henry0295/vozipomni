# Manual del supervisor

Este manual explica las tareas diarias del supervisor en VozipOmni: seguir la operación en vivo, leer el estado de los agentes y las colas, escuchar, susurrar o entrar a una llamada, forzar pausas o desconexiones, evaluar la calidad, auditar las gestiones y revisar los reportes. Se basa en `frontend/pages/supervisor/index.vue`, `backend/apps/api/supervisor_viewsets.py`, el contexto `[from-spy]` de `docker/asterisk/configs/extensions.conf`, `frontend/pages/quality/index.vue`, `frontend/pages/audit/index.vue`, `frontend/pages/settings/security.vue`, `frontend/pages/dashboard.vue`, `frontend/pages/reports/index.vue` y `frontend/utils/navigation.ts`.

El rol **Supervisor** entra por defecto al **Monitor en vivo** (ruta `/supervisor`). La consola de agente (`/agent/console`) es exclusiva del rol Agente: un supervisor que la abre es redirigido al Dashboard.

## Qué ve el supervisor en el menú

| Grupo | Opciones para Supervisor |
|---|---|
| Dashboard | **Dashboard** |
| Supervisión | **Monitor en vivo**, **Auditoría de gestiones** |
| Omnicanal | **Bandeja omnicanal**, **Métricas de chat**, **Envíos masivos**, **Respuestas y etiquetas** |
| Operación | **Agentes**, **Campañas**, **Formularios de campaña**, **Contactos**, **Lista negra (DNC)**, **Callbacks**, **Llamadas** |
| Calidad | **Evaluaciones**, **Plantillas de evaluación**, **Grabaciones** |
| Reportes | **KPIs y métricas**, **Exportar / programados** |
| Telefonía | **Colas** |
| Administración | **Grupos y pausas**, **Webhooks** |

Las troncales, rutas, IVR, extensiones y **Seguridad y antifraude** son solo para Administrador. Si entras a una de esas rutas por URL, el sistema te devuelve.

## Monitor en vivo

**Supervisión → Monitor en vivo** abre el **Panel de Supervisión**.

- Bajo el título se indica el modo de actualización: "Tiempo real (eventos de Asterisk)" cuando el WebSocket está conectado, o "Actualización cada 10 s" si no. A la derecha, la insignia **En vivo** o **Desconectado** y el botón **Actualizar**.
- Con el WebSocket activo, cada cambio de estado de un agente se refleja en su fila al instante y el panel recarga las cifras poco después. Además recarga todo cada 30 segundos.

### Indicadores superiores

| Tarjeta | Qué muestra |
|---|---|
| **Agentes Online** | Agentes con estado distinto de Desconectado, "de N total". |
| **En Llamada** | Agentes en llamada y, debajo, cuántos están en post-llamada. |
| **Llamadas Hoy** | Llamadas desde la medianoche y cuántas están activas ahora. |
| **Tasa Respuesta** | Llamadas completadas ÷ total del día. Verde desde 80%, amarillo desde 60%, rojo por debajo. Debajo, el **TMO** (conversación promedio de las completadas). |

### Estado de Agentes

La tabla lista a todos los agentes con **Agente**, **Ext.**, **Estado**, **Llamadas**, **T. Hab.** (tiempo hablado hoy), **Ocupación** y las acciones. En el encabezado hay un contador por estado: **Disponible**, **En llamada**, **Post-llamada**, **Pausa** y **Desconectado**. La tarjeta **Distribución** repite esos totales.

| Estado | Lectura para el supervisor |
|---|---|
| Disponible | Listo para recibir llamadas. Si hay llamadas esperando y muchos agentes disponibles, revisa la pertenencia a colas. |
| En llamada | Atendiendo. Solo en este estado se habilitan Escuchar, Susurrar y Entrar a llamada. |
| Post-llamada | Calificando la llamada. Queda en pausa en las colas. Una post-llamada larga suele indicar que el agente no ha guardado la disposición. |
| Pausa | En pausa con motivo. Queda en pausa en las colas. |
| Desconectado | Sin sesión de agente. |
| Ocupado | Estado manual del agente; la tabla lo muestra con su valor en inglés (`busy`) porque no está en la lista de etiquetas del panel. |

La barra de **Ocupación** se pinta verde desde 80%, amarillo desde 60% y rojo por debajo.

### Colas en Vivo

Cada cola activa muestra su nombre, **N esperando** (rojo si hay llamadas esperando) y **Agentes listos** (agentes disponibles, miembros de la cola y no pausados en ella). "Sin colas activas" indica que no hay colas habilitadas.

## Escuchar, susurrar y entrar a una llamada

Las tres acciones usan tu propia extensión: Asterisk te llama y, cuando contestas, te conecta a la llamada del agente.

| Acción (ícono) | Modo | Quién te escucha |
|---|---|---|
| **Escuchar** (ojo) | `listen` | Nadie. Solo escuchas. |
| **Susurrar** (globo de diálogo) | `whisper` | Solo el agente. El cliente no te oye. |
| **Entrar a llamada** (teléfono con flecha) | `barge` | Agente y cliente. |

Pasos:

1. Ubica al agente en estado **En llamada** (las acciones están deshabilitadas en otros estados).
2. Haz clic en la acción. Se abre la ventana **Escuchar llamada**, **Susurrar al agente** o **Entrar a llamada** con el nombre del agente.
3. Escribe **Tu extensión SIP** (por ejemplo `1099`) y haz clic en **Conectar**.
4. Tu teléfono timbra. Contesta. Tras un segundo quedas conectado a la llamada.
5. Para salir, cuelga tu teléfono.

Cómo funciona: el backend ordena por AMI una llamada a `PJSIP/<tu extensión>` en el contexto `[from-spy]`, con las variables `SPY_MODE` y `SPY_CHANNEL` (el canal de la llamada del agente). El contexto contesta, espera un segundo y ejecuta `ChanSpy` con las opciones `q` (escuchar), `qw` (susurrar) o `B` (entrar). Si el canal llega vacío, escuchas una despedida y la llamada se corta.

Requisitos y mensajes:

- Tu extensión debe existir y estar registrada en un teléfono o softphone SIP. Como la consola de agente no admite el rol Supervisor, pide al administrador una extensión en **Telefonía → Extensiones**.
- "El agente no tiene una llamada activa": el panel no encontró una llamada en curso asociada al agente. Pulsa **Actualizar** y vuelve a intentar.
- "Llamada activa no encontrada": la llamada terminó antes de conectarte.
- "No se pudo conectar a Asterisk AMI": el backend no llegó a Asterisk. Avisa al administrador (ver [Monitoreo](../operacion/monitoreo.md)).
- Informa a los agentes y clientes sobre la supervisión de llamadas según las políticas de tu empresa.

## Forzar pausa y desconectar

- **Forzar pausa** (ícono de pausa, deshabilitado si el agente está en pausa o desconectado): pone al agente en estado **Pausa** y muestra "... puesto en pausa".
- **Desconectar** (ícono de círculo con X, deshabilitado si ya está desconectado): pide confirmación "¿Desconectar a ...?", deja al agente en **Desconectado** y muestra "... desconectado".

Según el código revisado, ambas acciones cambian el estado directamente en la base de datos. No pasan por el servicio de agentes, así que no emiten el evento de cambio de estado: no pausan ni retiran al agente de las colas en Asterisk, no quedan en el historial de estados y la consola abierta del agente no se entera. Úsalas como marca en el tablero y confirma con el agente, que debe tomar la pausa o cerrar sesión desde su consola.

## Colas

**Telefonía → Colas** (página **Colas de Llamadas**) lista las colas con **Nombre**, **Extensión**, **Estrategia**, **Timeout**, **Máx. Espera** y **Estado** (Activa o Inactiva). Puedes buscar, filtrar por estrategia y estado, crear con **Nueva Cola**, editar y eliminar. Los detalles de configuración están en la documentación de administración de colas.

Para el día a día, el seguimiento en vivo se hace en **Colas en Vivo** del Monitor, y el análisis histórico en la pestaña **Colas y abandono** de los reportes.

## Evaluaciones de calidad

**Calidad → Evaluaciones** abre **Gestión de Calidad**. Supervisores y administradores pueden evaluar; los analistas solo consultan.

Arriba están **Evaluaciones**, **Puntaje promedio (0-100)**, **Agentes evaluados** y **Aprobación (≥ 80)**, además de **Top agentes por calidad**, **Tendencia diaria**, **Puntaje por criterio (plantilla estándar)** y **Evaluaciones recientes**. Los filtros superiores permiten elegir el período (7, 15, 30 o 90 días) y la plantilla.

Para evaluar:

1. Haz clic en **Nueva evaluación**.
2. En **Grabación a evaluar** elige una grabación pendiente. Si no hay, aparece "No hay grabaciones pendientes de evaluar."
3. En **Plantilla** elige una plantilla activa o **Estándar (5 criterios, 0-5)**: Saludo, Claridad, Profesionalismo, Resolución y Cierre.
4. Califica cada criterio. **Puntaje resultante** muestra el total sobre 100.
5. Escribe **Comentarios / retroalimentación** y haz clic en **Guardar evaluación**.

El ícono de ojo de cada fila abre el detalle con el puntaje por criterio, el total y los comentarios. En la tabla, el puntaje se pinta verde desde 80, amarillo desde 60 y rojo por debajo. Las plantillas se crean en **Calidad → Plantillas de evaluación**. Ver [Grabaciones y calidad](../administracion/grabaciones-y-calidad.md).

## Auditoría de gestiones

**Supervisión → Auditoría de gestiones** (página **Auditoría de Gestiones**) sirve para revisar las disposiciones que guardan los agentes.

- Indicadores: **Total**, **Pendientes**, **Aprobadas** y **Puntuación media**.
- Filtros: **Estado** (Pendientes, Aprobados, Rechazados, Corregidos), **Agente**, **Campaña** y **Filtrar**.
- Acciones por registro pendiente:
  - **Aprobar**: acepta la calificación del agente.
  - **Rechazar**: pide **Motivo de rechazo \*** y se confirma con **Rechazar**.
  - **Corregir**: muestra la calificación original, pide **Nueva calificación \***, **Puntuación de calidad (0-100)** y **Notas del supervisor**, y se confirma con **Aplicar corrección**.
  - **Ver detalle**: muestra calificación original y corregida, puntuación, quién auditó y las notas.

## Eventos de seguridad

La sección **Eventos de seguridad** está en **Telefonía → Seguridad y antifraude** (`/settings/security`), visible solo para Administrador. Si necesitas revisar por qué se bloqueó una llamada, pide acceso o el dato al administrador.

La tabla muestra **Fecha**, **Evento**, **Número**, **Troncal**, **Origen** y **Detalle**, y se filtra por tipo y por período (**Últimas 24 h**, **7 días**, **30 días**). Tipos de evento: **Internacional bloqueada**, **Prefijo bloqueado**, **Fuera de la lista blanca**, **Troncal sin canales**, **Límite total**, **Límite por extensión**, **Bloqueada en el marcador**, **Alerta: pico de llamadas**, **Alerta: internacionales** y **Alerta: muchos bloqueos**.

Relación con lo que ve el agente:

| Mensaje en la consola del agente | Eventos relacionados |
|---|---|
| Llamada rechazada (403 ...) | Internacional bloqueada, Prefijo bloqueado, Fuera de la lista blanca |
| Llamada rechazada (503 ...) | Troncal sin canales, Límite total, Límite por extensión |

## Dashboard

**Dashboard** muestra un resumen rápido: **Agentes Activos** (con disponibles), **Llamadas en Cola** (con activas), **Llamadas Hoy** (entrantes y salientes), **Tasa Respuesta** (con tiempo promedio), **Contestadas Hoy**, **Perdidas Hoy**, **Espera Promedio**, y las listas **Agentes en Línea** y **Llamadas Recientes**. La **Tasa Respuesta** usa los mismos colores que el Monitor (80/60).

## Reportes

**Reportes → KPIs y métricas** (página **Reportes y KPIs**) tiene las pestañas **Resumen**, **Agentes**, **Colas y abandono**, **Campañas**, **Omnicanal** y **Calidad**, con filtros de período, campaña, cola, agente, dirección y umbral de nivel de servicio. **Exportar** descarga los datos de la pestaña en Excel o CSV. **Reportes → Exportar / programados** permite programar envíos por correo.

Revisiones útiles para el supervisor:

- Al cierre del turno: pestaña **Colas y abandono**, tabla **Llamadas perdidas** con **Solo sin devolver**, para asignar devoluciones.
- Cada día: pestaña **Agentes**, tabla **Pausas que excedieron el tiempo permitido**.
- Cada semana: ranking de agentes y pestaña **Calidad** para planear retroalimentación.

La lectura detallada de cada indicador y sus colores está en el [Manual del analista](./manual-analista.md). Ver también [Reportes](../administracion/reportes.md).

## Rutina sugerida

1. Al inicio del turno: abre el Monitor, verifica **En vivo** y que los agentes programados estén conectados.
2. Durante el turno: vigila **Colas en Vivo** (llamadas esperando frente a agentes listos) y agentes con post-llamada o pausa prolongada.
3. Usa **Escuchar** o **Susurrar** para acompañar a agentes nuevos.
4. Evalúa llamadas grabadas y audita gestiones pendientes.
5. Al cierre: revisa llamadas perdidas sin devolver y pausas excedidas.

## Problemas frecuentes

- **El panel dice "Desconectado".** El WebSocket de tiempo real no está conectado; el panel sigue actualizando cada 10 segundos. Recarga la página. Si persiste, avisa al administrador.
- **Las acciones de escucha están grises.** El agente no está **En llamada**.
- **Hice clic en Conectar y mi teléfono no timbra.** Tu extensión no está registrada o no existe. Verifica tu softphone con el administrador.
- **Un agente aparece conectado pero no contesta.** Pudo cerrar la pestaña sin **Cerrar Sesión**. Contáctalo y pídele entrar de nuevo.
- **Forcé la pausa y el agente sigue recibiendo llamadas.** Ver la limitación de **Forzar pausa** descrita arriba.

## Ver también

- [Manual del agente](./manual-agente.md)
- [Manual del analista](./manual-analista.md)
- [Agentes](../administracion/agentes.md)
- [Campañas](../administracion/campanas.md)
- [Grabaciones y calidad](../administracion/grabaciones-y-calidad.md)
- [Omnicanal](../administracion/omnicanal.md)
- [Reportes](../administracion/reportes.md)
- [Glosario](../general/glosario.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
