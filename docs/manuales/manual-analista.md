# Manual del analista

Este manual explica cómo leer los indicadores de **Reportes y KPIs** en VozipOmni: qué mide cada KPI, qué significan sus colores, cómo interpretar la comparación con el período anterior, cómo exportar y programar reportes, y algunas recetas prácticas para el trabajo de análisis. Se basa en `frontend/pages/reports/index.vue`, `frontend/components/ReportKpi.vue`, `frontend/pages/reports/saved.vue`, `backend/apps/reports/analytics.py`, `backend/apps/reports/tasks.py`, `frontend/pages/dashboard.vue` y `frontend/utils/navigation.ts`.

El rol **Analista** entra al **Dashboard** y ve, en solo lectura, **Métricas de chat**, **Campañas**, **Llamadas**, **Evaluaciones**, **Grabaciones**, **KPIs y métricas** y **Exportar / programados**. No puede crear evaluaciones ni cambiar la configuración.

## Filtros y pestañas

**Reportes → KPIs y métricas** abre **Reportes y KPIs**. Los filtros aplican a todas las pestañas:

| Filtro | Opciones |
|---|---|
| **Período** | Hoy, Ayer, Esta semana, Semana pasada, Últimos 7 días, Últimos 30 días, Este mes, Mes pasado, Personalizado (con **Desde** y **Hasta**). |
| **Campaña**, **Cola**, **Agente** | Todas/Todos o uno específico. |
| **Dirección** | Todas, Entrantes, Salientes. |
| **Umbral SL (s)** | Segundos para el nivel de servicio (por defecto 20, entre 1 y 600). |

Haz clic en **Aplicar** o **Actualizar** después de cambiar filtros. Con **Personalizado**, si falta una fecha aparece "Selecciona las fechas desde y hasta". Bajo el título se muestra el rango exacto consultado.

Pestañas: **Resumen**, **Agentes**, **Colas y abandono**, **Campañas**, **Omnicanal** y **Calidad**. Cada una se carga al abrirla.

## Cómo leer una tarjeta de KPI

Cada tarjeta tiene nombre, valor, un ícono de información con la definición (al pasar el mouse) y, debajo, la variación y un dato complementario.

### Colores del valor

| Tono | Color |
|---|---|
| Bueno | Verde |
| Alerta | Ámbar |
| Malo | Rojo |
| Sin meta | Negro (el KPI no tiene umbral definido) |

### Comparación con el período anterior

Solo la pestaña **Resumen** compara, y el subtítulo lo indica ("comparado con el período anterior"). El período anterior es el tramo de la misma duración que termina justo antes del inicio del período elegido. Al pasar el mouse sobre la variación ves el valor anterior ("Período anterior: ...").

- **Porcentajes** (nivel de servicio, abandono, ocupación, FCR, conversión, etc.): la variación se da en puntos porcentuales, por ejemplo "+3.5 pp". Pasar de 70% a 73,5% es +3,5 pp, no +5%.
- **Cantidades y tiempos**: la variación es relativa, por ejemplo "+12.4%". Si el período anterior fue cero, aparece "nuevo".
- **"sin cambio"** en gris: la variación es cero.
- **Flecha y color**: la flecha indica si el número subió o bajó; el color indica si eso es bueno. En los KPIs donde menos es mejor (Abandonadas, No contestadas, Abandono, ASA, AHT, Transferencias) la lógica se invierte: una bajada sale en verde.

## Pestaña Resumen

### Volumen

| KPI | Qué mide |
|---|---|
| **Llamadas** | Total del período, con entrantes y salientes. |
| **Atendidas** | Llamadas completadas y su porcentaje del total. |
| **Abandonadas** | El cliente colgó esperando. Debajo, cuántas fueron cortas (< 5 s). |
| **No contestadas** | Ocupado, sin respuesta o canceladas. |
| **Clientes únicos** | Números distintos que llamaron y cuántos volvieron a llamar. |
| **Agentes conectados** | Agentes que trabajaron y su tiempo conectado. |

### Servicio y experiencia

| KPI | Fórmula | Colores |
|---|---|---|
| **Nivel de servicio** | Entrantes contestadas dentro del umbral ÷ (entrantes − abandonos de menos de 5 s). | Verde ≥ 80%, ámbar ≥ 60%, rojo < 60%. |
| **Abandono** | Abandonadas ÷ entrantes. | Verde ≤ 5%, ámbar ≤ 10%, rojo > 10%. |
| **ASA** | Espera promedio de las entrantes contestadas. Debajo, la espera máxima. | Sin meta; menos es mejor. |
| **AHT (TMO)** | (Conversación + retención + post-llamada) ÷ atendidas. Debajo, conversación y ACW. | Sin meta; menos es mejor. |
| **FCR estimado** | Porcentaje de clientes que no volvieron a llamar en el período (100 − % de rellamadas). | Verde ≥ 80%, ámbar ≥ 70%, rojo < 70%. |
| **Espera al abandonar** | Cuánto esperan en promedio los clientes antes de colgar. | Sin meta. |

Los abandonos de menos de 5 segundos no penalizan el nivel de servicio (suelen ser marcaciones equivocadas). El FCR es una estimación: un cliente que vuelve a llamar por otro tema cuenta como rellamada.

### Productividad y gestión

| KPI | Fórmula | Colores |
|---|---|---|
| **Ocupación** | (En llamada + post-llamada) ÷ (tiempo conectado − pausas). | Verde entre 70% y 90%, ámbar < 70%, rojo > 90%. La tarjeta indica "Meta 75–85%". |
| **Utilización** | (En llamada + post-llamada) ÷ tiempo conectado total. Debajo, el total de pausas. | Sin meta. |
| **Llamadas / hora** | Atendidas por hora conectada. | Sin meta. |
| **Contactabilidad** | Salientes contestadas ÷ salientes. Debajo, cuántas fueron contestadores. | Sin meta. |
| **Conversión** | Llamadas tipificadas como exitosas ÷ atendidas. Debajo, éxitos y % tipificadas. | Sin meta. |
| **Transferencias** | Porcentaje transferido. Debajo, % de llamadas de menos de 10 s. | Sin meta; menos es mejor. |

Una ocupación mayor a 90% sale en rojo a propósito: indica agentes sin respiro entre llamadas, con riesgo de desgaste y errores. Por debajo de 70% hay capacidad ociosa.

### Gráficos

- **Tendencia diaria**: barras por día (verde atendidas, rojo abandonadas, gris otras). El tooltip muestra SL, abandono y AHT del día.
- **Resultado de las llamadas**: distribución por estado final.
- **Llamadas por hora**: volumen por hora con SL y ASA en el tooltip.
- **Duración de las conversaciones**: distribución por tramos.
- **Mapa de calor: día de la semana × hora**: más oscuro, más llamadas.
- **Detalle por día**: tabla con SL y % abandono coloreados con los mismos umbrales.

## Pestaña Agentes

**Ranking y KPIs por agente** incluye **#**, **Agente**, **Puntaje**, **Atendidas**, **Chats**, **AHT**, **Conv. prom.**, **ACW**, **Llam./h**, **Conectado**, **Pausas**, **Ocupación**, **% transf.**, **Conversión** y **Calidad**. Todas las columnas se pueden ordenar. Los tres primeros puestos se resaltan.

Fórmula del **Puntaje** (tooltip "¿Cómo se calcula el puntaje?"):

| Componente | Peso | Valor |
|---|---|---|
| Llamadas por hora | 35% | Relativo al mejor agente del período (el mejor vale 100). |
| Ocupación | 25% | La ocupación del agente, con tope en 100. |
| Calidad | 30% | Puntaje promedio de evaluaciones. Solo si el agente tiene evaluaciones. |
| Sin transferencias | 10% | 100 − % de transferencias. |

Si el agente no tiene evaluaciones, el backend reparte el peso entre los otros tres componentes (divide por 70% en lugar de 100%). El puntaje se pinta verde desde 75, ámbar desde 50 y rojo por debajo. La ocupación sigue el esquema 70–90 y la calidad el esquema 85/70 (verde ≥ 85, ámbar ≥ 70); un guion significa que no hay evaluaciones.

Además:

- **Distribución del tiempo conectado**: por agente (hasta 15), barras de Disponible, En llamada, Post-llamada y Pausa.
- **Pausas por motivo**: tiempo total, cantidad, promedio y excedidas por motivo.
- **Pausas que excedieron el tiempo permitido**: **Inicio**, **Agente**, **Motivo**, **Duración**, **Permitido** y **Exceso**. Solo aparece si hay excesos; depende de que la razón de pausa tenga duración máxima.

## Pestaña Colas y abandono

- **Nivel de servicio por cola**: **Ofrecidas**, **Atendidas**, **Abandonadas**, **Nivel de servicio** (con el umbral de la cola), **% abandono**, **ASA**, **Espera máx.**, **Espera al abandonar** y **AHT**. SL y abandono usan los umbrales 80/60 y 5/10.
- **Tiempo de espera**: atendidas y abandonadas por tramo de espera. Si los abandonos se concentran en un tramo, ahí se agota la paciencia del cliente.
- Tarjetas: **Llamadas perdidas**, **Devueltas** (verde ≥ 80% recuperadas, ámbar ≥ 50%), **Sin devolver** (rojo si hay pendientes) y **Tiempo de devolución**.
- Tabla **Llamadas perdidas**: **Fecha**, **Número**, **Cola**, **Estado**, **Espera**, **Intentos** (en rojo si llamó más de una vez) y **Devolución** ("En ..." o **Pendiente**).

Una llamada perdida cuenta como devuelta si después hubo una saliente a ese número o una entrante contestada del mismo número.

## Pestaña Campañas

**KPIs por campaña**: **Llamadas**, **Contactadas**, **Contactab.**, **Contestador**, **Éxitos**, **Conversión**, **Rellamadas**, **Chats**, **Barrido de base** (porcentaje de la base trabajada y pendientes), **Intentos prom.** y **Conv. prom.**

Debajo: **Gestiones tipificadas**, **Resultados exitosos**, **Llamadas sin tipificar** (ámbar si hay) y el gráfico **Tipificaciones** (verde las exitosas). Muchas llamadas sin tipificar distorsionan la conversión.

## Pestaña Omnicanal

Tarjetas **Conversaciones**, **Sin asignar**, **1ª respuesta**, **1ª resp. ≤ 5 min** (nivel de servicio de chat, verde ≥ 80%, ámbar ≥ 60%), **Resolución** y **Mensajes**. Tablas **Por canal** y **Conversaciones por agente**, y el gráfico **Conversaciones por hora**. Ver [Omnicanal](../administracion/omnicanal.md).

## Pestaña Calidad

Tarjetas **Evaluaciones**, **Puntaje promedio** (verde ≥ 85, ámbar ≥ 70), **Mínimo / máximo**, **Cobertura** (evaluaciones ÷ llamadas grabadas; meta típica 2–5%), **Con feedback** y **Bajo 60** (requieren plan de mejora). Gráficos **Distribución de puntajes** y **Por evaluador**, y tabla **Calidad por agente**. Ver [Grabaciones y calidad](../administracion/grabaciones-y-calidad.md).

## Exportar

El botón **Exportar** de **Reportes y KPIs** ofrece los datos de la pestaña abierta, con los filtros aplicados:

| Pestaña | Conjuntos |
|---|---|
| Resumen | Resumen diario, Llamadas por hora, Detalle de llamadas |
| Agentes | KPIs y ranking de agentes, Pausas por agente y motivo, Llamadas por agente |
| Colas y abandono | Nivel de servicio por cola, Llamadas perdidas y devoluciones |
| Campañas | KPIs de campañas, Tipificaciones |
| Omnicanal | Omnicanal por canal, Detalle de conversaciones |
| Calidad | Calidad por agente |

Todos están en Excel; en CSV solo el primero de cada pestaña.

## Reportes guardados y programados

**Reportes → Exportar / programados** abre **Exportar y programar reportes**:

- **Exportación inmediata**: elige **Datos** (Detalle de llamadas, Rendimiento de agentes, Resumen diario, Resumen por cola, entre otros), período y filtros, y haz clic en **Descargar Excel** o **Descargar CSV**.
- **Nuevo reporte**: **Nombre**, **Tipo**, **Formato** (Excel o CSV) y filtros. Sin programar, pide **Desde** y **Hasta** y se genera con **Generar**.
- **Programar**: marca "Programar (se genera automáticamente y se envía por correo)" y elige **Frecuencia**: Diario (01:30, día anterior), Semanal (lunes, semana anterior) o Mensual (día 1, mes anterior). Confirma con **Programar**.

El archivo programado se envía por correo al usuario que lo creó, si tiene email registrado y el servidor tiene correo configurado. La pestaña **Generados** permite descargar o **Regenerar**; **Programados** permite editar.

## Recetas prácticas

### Dimensionar turnos con el mapa de calor

1. Período **Últimos 30 días**, **Dirección** Entrantes, sin filtro de agente.
2. En **Resumen**, revisa **Mapa de calor: día de la semana × hora** y ubica las celdas más oscuras.
3. Cruza con **Llamadas por hora**: las horas con SL bajo (tooltip) y volumen alto necesitan más agentes.
4. Exporta **Llamadas por hora** para calcular cuántos agentes necesitas por franja con tu AHT.

### Recuperar llamadas perdidas

1. Período **Hoy** o **Ayer**, pestaña **Colas y abandono**.
2. En **Llamadas perdidas**, marca **Solo sin devolver**.
3. Prioriza los números con más **Intentos** (en rojo).
4. Exporta **Llamadas perdidas y devoluciones** y entrégalo al supervisor para devolverlas.
5. Al día siguiente, revisa que **Devueltas** suba y **Tiempo de devolución** baje.

### Revisar pausas excedidas

1. Período **Ayer** o **Semana pasada**, pestaña **Agentes**.
2. Revisa **Pausas por motivo** (cantidad y excedidas) y la tabla **Pausas que excedieron el tiempo permitido**.
3. Si una razón de pausa no tiene tope, no aparecerá como excedida. Pide al supervisor fijar **Duración máx.** en **Grupos y pausas**.

### Comparar agentes con el ranking

1. Usa un período de al menos una semana para evitar ruido.
2. Ordena por **Puntaje** y revisa sus componentes: **Llam./h**, **Ocupación**, **Calidad** y **% transf.**
3. Un puntaje bajo por **Llam./h** con **AHT** alto sugiere capacitación en manejo de llamadas; uno bajo por **Calidad** sugiere retroalimentación sobre evaluaciones.
4. Compara solo agentes de la misma campaña o cola (usa los filtros): los tiempos varían mucho entre tipos de servicio.
5. Recuerda que un agente sin evaluaciones se califica sin el componente de calidad.

## Buenas prácticas

- Compara períodos equivalentes (semana contra semana), no un lunes contra un sábado.
- Mantén el mismo **Umbral SL (s)** en todos los reportes de una misma cola para que las cifras sean comparables.
- Antes de concluir sobre conversión, revisa **Llamadas sin tipificar**.
- Documenta los filtros usados cuando compartas un export.

## Ver también

- [Reportes](../administracion/reportes.md)
- [Manual del supervisor](./manual-supervisor.md)
- [Manual del agente](./manual-agente.md)
- [Campañas](../administracion/campanas.md)
- [Grabaciones y calidad](../administracion/grabaciones-y-calidad.md)
- [Omnicanal](../administracion/omnicanal.md)
- [Glosario](../general/glosario.md)
