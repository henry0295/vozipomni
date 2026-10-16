# Reportes

Este manual explica las dos pantallas de reportes de VozipCX: **Reportes y KPIs**, con sus seis pestañas de indicadores, y **Exportar y programar reportes**, donde se descargan datos en Excel o CSV, se generan reportes guardados y se programan envíos por correo. Describe qué muestra cada pestaña, cómo funcionan los filtros y qué datos trae cada exportación. Se basa en `frontend/pages/reports/index.vue`, `frontend/pages/reports/saved.vue`, `backend/apps/reports/analytics.py`, `backend/apps/reports/exporters.py`, `backend/apps/reports/views.py` y `backend/apps/reports/tasks.py`.

Las fórmulas exactas de cada indicador (nivel de servicio, ASA, AHT, ocupación, FCR, conversión, etc.) están en el [Glosario](../general/glosario.md). Este documento no las repite: explica dónde aparecen y cómo leerlas.

## Acceso

| Pantalla | Menú | Ruta | Roles |
|---|---|---|---|
| Reportes y KPIs | Reportes → KPIs y métricas | `/reports` | Administrador, Supervisor, Analista |
| Exportar y programar reportes | Reportes → Exportar / programados | `/reports/saved` | Administrador, Supervisor, Analista |

En la API, `ReportViewSet` usa `IsAdminSupervisorOrAnalyst`. En **Exportar y programar reportes**, el ícono de papelera solo se muestra a Administrador y Supervisor.

## Filtros

La barra de filtros de **Reportes y KPIs** aplica a todas las pestañas:

| Filtro | Opciones | Notas |
|---|---|---|
| Período | **Hoy**, **Ayer**, **Esta semana**, **Semana pasada**, **Últimos 7 días**, **Últimos 30 días**, **Este mes**, **Mes pasado**, **Personalizado** | Por defecto **Hoy**. Con **Personalizado** aparecen **Desde** y **Hasta**; ambas son obligatorias ("Selecciona las fechas desde y hasta"). |
| Campaña | **Todas** o una campaña | |
| Cola | **Todas** o una cola | Aplica a los indicadores de llamadas. |
| Agente | **Todos** o un agente (nombre y extensión) | |
| Dirección | **Todas**, **Entrantes**, **Salientes** | Aplica a los indicadores de llamadas. |
| Umbral SL (s) | 1 a 600, por defecto 20 | Segundos para el nivel de servicio del **Resumen**. El reporte por cola usa el nivel de servicio configurado en cada cola (o 20 s si no tiene). |

Los datos de una pestaña se cargan al abrirla. Después de cambiar filtros, haz clic en **Actualizar**. Debajo del título se muestra el período consultado. Las pestañas **Omnicanal** y **Calidad** solo usan período, campaña y agente según corresponda; **Cola** y **Dirección** son filtros de llamadas.

## Pestaña Resumen

Compara el período elegido con el período anterior de la misma duración (cada indicador muestra el valor anterior y la variación). Está organizada en tres bloques:

- **Volumen**: **Llamadas** (entrantes y salientes), **Atendidas** (y porcentaje del total), **Abandonadas** (y cuántas fueron cortas, de menos de 5 s), **No contestadas** (ocupado, sin respuesta o canceladas), **Clientes únicos** (y cuántos volvieron a llamar) y **Agentes conectados** (con el tiempo conectado).
- **Servicio y experiencia**: **Nivel de servicio** (contestadas dentro del umbral), **Abandono** (sobre entrantes), **ASA** (con la espera máxima), **AHT (TMO)** (con conversación y ACW promedio), **FCR estimado** (con el porcentaje de rellamadas) y **Espera al abandonar**.
- **Productividad y gestión**: **Ocupación** (meta 75–85%), **Utilización** (con el tiempo en pausa), **Llamadas / hora**, **Contactabilidad** (con los contestadores detectados), **Conversión** (con éxitos y porcentaje tipificado) y **Transferencias** (con el porcentaje de llamadas de menos de 10 s).

Cada indicador se colorea según metas de referencia del código (por ejemplo, nivel de servicio verde desde 80%, abandono verde por debajo de 5%). Al pasar el cursor sobre el ícono de ayuda se ve la definición.

Gráficos y tablas: **Tendencia diaria** (atendidas, abandonadas y otras), **Resultado de las llamadas** (por estado), **Llamadas por hora**, **Duración de las conversaciones** (tramos de menos de 30 s a más de 10 min), **Mapa de calor: día de la semana × hora** (útil para dimensionar turnos) y **Detalle por día** con **Fecha**, **Total**, **Entrantes**, **Salientes**, **Atendidas**, **Abandonadas**, **SL**, **% abandono**, **ASA** y **AHT**. En la tendencia diaria y en el detalle por día, el AHT no incluye la post-llamada (ver glosario).

## Pestaña Agentes

- **Ranking y KPIs por agente**: una fila por agente con actividad (llamadas, tiempo conectado o chats) y columnas **#**, **Agente** (con extensión), **Puntaje**, **Atendidas** (sobre el total), **Chats**, **AHT**, **Conv. prom.**, **ACW**, **Llam./h**, **Conectado**, **Pausas**, **Ocupación**, **% transf.**, **Conversión** y **Calidad**. Todas las columnas se pueden ordenar. **¿Cómo se calcula el puntaje?** explica la ponderación: 35% llamadas por hora relativas al mejor, 25% ocupación, 30% calidad si tiene evaluaciones y 10% sin transferencias.
- **Distribución del tiempo conectado**: barras por agente (hasta 15) con **Disponible**, **En llamada**, **Post-llamada** y **Pausa**.
- **Pausas por motivo**: total de pausas y tiempo por motivo.
- **Pausas que excedieron el tiempo permitido**: aparece si hay excesos, con **Inicio**, **Agente**, **Motivo**, **Duración**, **Permitido** y **Exceso**. El tope sale de la **Duración máx. (min)** de cada razón de pausa (ver [Agentes](./agentes.md)).

Los tiempos de agente salen del historial de estados (`AgentStatusHistory`), así que un agente que no inició sesión en la consola aparece sin tiempo conectado.

## Pestaña Colas y abandono

- **Nivel de servicio por cola**: **Cola** (las llamadas sin cola aparecen como "Directas (sin cola)"), **Ofrecidas**, **Atendidas**, **Abandonadas**, **Nivel de servicio** (con el umbral de la cola), **% abandono**, **ASA**, **Espera máx.**, **Espera al abandonar** y **AHT**. Solo cuenta llamadas entrantes.
- **Tiempo de espera**: atendidas frente a abandonadas por tramo de espera (0–10 s hasta más de 120 s). Si los abandonos se concentran en un tramo, conviene anunciar la posición u ofrecer devolución de llamada antes.
- Indicadores de llamadas perdidas: **Llamadas perdidas** (con números distintos), **Devueltas** (porcentaje recuperado), **Sin devolver** y **Tiempo de devolución**. Una llamada se considera devuelta si después hubo una saliente a ese número o una entrante contestada del mismo número; se comparan los últimos 10 dígitos.
- **Llamadas perdidas**: **Fecha**, **Número**, **Cola**, **Estado**, **Espera**, **Intentos** y **Devolución** (tiempo y quién devolvió, o **Pendiente**). **Solo sin devolver** filtra las pendientes. La tabla muestra hasta 300 filas.

## Pestaña Campañas

- **KPIs por campaña**: **Campaña** (con tipo y marcador), **Estado**, **Llamadas**, **Contactadas**, **Contactab.**, **Contestador**, **Éxitos**, **Conversión**, **Rellamadas**, **Chats**, **Barrido de base** (porcentaje de la base trabajada y pendientes), **Intentos prom.** y **Conv. prom.**. Sin filtro de campaña se listan las campañas activas y las que tuvieron actividad.
- **Gestiones tipificadas**, **Resultados exitosos** y **Llamadas sin tipificar** (atendidas sin disposición).
- **Tipificaciones**: conteo por calificación, sumando llamadas y conversaciones de chat.

Ver [Campañas](./campanas.md) para configurar calificaciones y marcadores.

## Pestaña Omnicanal

- Indicadores: **Conversaciones** (y abiertas), **Sin asignar**, **1ª respuesta** (promedio), **1ª resp. ≤ 5 min** (nivel de servicio de chat), **Resolución** (tiempo promedio y porcentaje cerradas) y **Mensajes** (recibidos y enviados).
- **Por canal**: **Canal**, **Conversaciones**, **Cerradas**, **Sin asignar**, **% respondidas**, **1ª respuesta**, **En meta**, **Resolución**, **% cerradas**, **Msj. recibidos** y **Msj. enviados**.
- **Conversaciones por agente** y **Conversaciones por hora**.

Se cuentan las conversaciones iniciadas en el período. Las creadas por un envío masivo sin respuesta del cliente se excluyen. Ver [Omnicanal](./omnicanal.md).

## Pestaña Calidad

- Indicadores: **Evaluaciones**, **Puntaje promedio** (sobre 100), **Mínimo / máximo**, **Cobertura** (evaluaciones sobre llamadas grabadas; meta típica 2–5%), **Con feedback** y **Bajo 60** (evaluaciones que requieren plan de mejora).
- **Distribución de puntajes** y **Por evaluador**.
- **Calidad por agente**: **Agente**, **Evaluaciones**, **Promedio**, **Mín.**, **Máx.** y **Bajo 60**.

Ver [Grabaciones y calidad](./grabaciones-y-calidad.md).

## Exportar desde Reportes y KPIs

El botón **Exportar** ofrece los datos de la pestaña abierta, con los filtros actuales, en Excel. El primer dataset de cada pestaña también se puede bajar en CSV.

| Pestaña | Datasets (clave) |
|---|---|
| Resumen | Resumen diario (`daily`), Llamadas por hora (`hourly`), Detalle de llamadas (`calls`) |
| Agentes | KPIs y ranking de agentes (`agent_kpis`), Pausas por agente y motivo (`breaks`), Llamadas por agente (`agents`) |
| Colas y abandono | Nivel de servicio por cola (`queue_sla`), Llamadas perdidas y devoluciones (`abandoned`) |
| Campañas | KPIs de campañas (`campaign_kpis`), Tipificaciones (`dispositions`) |
| Omnicanal | Omnicanal por canal (`omnichannel`), Detalle de conversaciones (`chats`) |
| Calidad | Calidad por agente (`quality`) |

La exportación usa `GET /api/reports/export/?dataset=<clave>&format=xlsx|csv` con los mismos parámetros de filtro. Cada exportación tiene un tope de 100.000 filas.

## Exportación inmediata

En **Reportes → Exportar / programados**, el bloque **Exportación inmediata** tiene **Datos**, **Período** (mismas opciones que arriba, por defecto **Últimos 7 días**), **Desde** y **Hasta** si es personalizado, **Campaña**, **Agente**, **Cola** y **Dirección**. Usa **Descargar Excel** o **Descargar CSV**.

La lista **Datos** se carga desde `GET /api/reports/datasets/` e incluye los 14 datasets de `exporters.py`:

| Clave | Nombre |
|---|---|
| `calls` | Detalle de llamadas |
| `agents` | Rendimiento de agentes |
| `daily` | Resumen diario |
| `queues` | Resumen por cola |
| `chats` | Conversaciones (WhatsApp, email, chat web, redes) |
| `hourly` | Llamadas por hora (nivel de servicio / ASA) |
| `agent_kpis` | KPIs y ranking de agentes (AHT, ocupación, calidad) |
| `breaks` | Pausas por agente y motivo |
| `queue_sla` | Nivel de servicio y abandono por cola |
| `abandoned` | Llamadas perdidas y devoluciones |
| `campaign_kpis` | KPIs de campañas (contactabilidad, conversión) |
| `dispositions` | Tipificaciones |
| `omnichannel` | Omnicanal por canal (primera respuesta, resolución) |
| `quality` | Calidad por agente |

## Reportes guardados y programados

Haz clic en **Nuevo reporte** y completa **Nombre**, **Tipo**, **Formato** (**Excel (.xlsx)** o **CSV**), **Campaña**, **Agente**, **Cola** y **Dirección**.

| Tipo | Dataset que genera |
|---|---|
| Llamadas (detalle) | `calls` |
| Agentes | `agents` |
| Colas | `queues` |
| Campaña (detalle) | `calls`, con el filtro de campaña |
| Resumen diario | `daily` |

Dos modos:

- **Reporte generado**: sin marcar **Programar**, elige **Desde** y **Hasta** y haz clic en **Generar**. El reporte aparece en la pestaña **Generados** como **Pendiente**, **Procesando** y luego **Listo** (la lista se refresca sola mientras hay reportes en proceso). Descárgalo con el ícono de descarga o vuelve a generarlo con **Regenerar**. Si falla, el estado **Fallido** muestra el error.
- **Reporte programado**: marca **Programar (se genera automáticamente y se envía por correo)**, elige la **Frecuencia** y haz clic en **Programar**. Aparece en la pestaña **Programados** y se puede editar; la casilla **Programar** no se puede cambiar después de crear el reporte.

La tarea `run_scheduled_reports` corre todos los días a la 1:30 y, para cada reporte programado que corresponda, crea una copia con el período anterior, la genera y la envía por correo:

| Frecuencia | Cuándo se ejecuta | Período que cubre |
|---|---|---|
| Diario | Todos los días a la 1:30 | Día anterior |
| Semanal | Los lunes a la 1:30 | Los 7 días anteriores (lunes a domingo) |
| Mensual | El día 1 a la 1:30 | Mes anterior |

Cada ejecución queda también en **Generados** con el nombre del reporte y la fecha de inicio. El correo tiene el asunto `VozipCX — <nombre>` y el archivo adjunto, y se envía solo al usuario que creó el reporte. Requisitos: que ese usuario tenga email en su perfil y que el servidor tenga `EMAIL_HOST` configurado; sin `EMAIL_HOST`, el correo solo se escribe en el log. Si el envío falla, el reporte se genera igual y el error queda en el log del worker.

## Problemas frecuentes

- **Los indicadores de agentes salen en cero.** Los tiempos vienen del historial de estados; el agente debe iniciar sesión en la consola. Revisa también el filtro **Agente**.
- **El nivel de servicio del Resumen no coincide con el de una cola.** El Resumen usa **Umbral SL (s)**; cada cola usa su propio nivel de servicio.
- **No llega el reporte programado.** Revisa el email del creador, `EMAIL_HOST` y los logs del worker de Celery. Confirma que existe la ejecución en **Generados** con estado **Listo**. Ver [Solución de problemas](../operacion/solucion-de-problemas.md).
- **La exportación viene incompleta.** Hay un tope de 100.000 filas; reduce el período o agrega filtros.
- **Un reporte generado no se puede descargar.** Solo se descargan los **Listo** en Excel o CSV; los antiguos en formato JSON no tienen descarga.

## Ver también

- [Glosario](../general/glosario.md)
- [Agentes](./agentes.md)
- [Campañas](./campanas.md)
- [Omnicanal](./omnicanal.md)
- [Grabaciones y calidad](./grabaciones-y-calidad.md)
- [Manual del analista](../manuales/manual-analista.md)
- [Manual del supervisor](../manuales/manual-supervisor.md)
- [API: reportes](../api/reportes.md)
