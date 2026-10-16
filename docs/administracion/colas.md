# Colas

Este manual explica cómo crear y ajustar las colas de llamadas (ACD) de VozipCX: qué hace cada campo, cómo se escribe la cola en Asterisk, cómo se asignan los agentes como miembros y cómo el nivel de servicio configurado alimenta los reportes. Se basa en `frontend/pages/queues/index.vue`, los modelos `Queue`, `QueueMember` y `QueueStats` de `backend/apps/queues/models.py`, `backend/apps/queues/admin.py`, el `QueueViewSet` de `backend/apps/api/viewsets.py`, `generate_queues_dynamic_conf()` y `generate_extensions_conf()` de `backend/apps/telephony/asterisk_config.py`, y `queues_report()` de `backend/apps/reports/analytics.py`.

Una **cola** recibe llamadas y las reparte entre los agentes que son sus miembros según una estrategia. Cada cola activa se escribe como una sección `[nombre]` en `/var/lib/asterisk/dynamic/queues_dynamic.conf` (incluido desde `queues.conf`) y tiene una extensión en `[from-internal]` para poder marcarla o transferir a ella. Las rutas entrantes, los IVR y las campañas entrantes o predictivas envían llamadas a la cola por su **nombre**.

## Acceso

- **Telefonía → Colas** (ruta `/queues`, página "Colas de Llamadas"). Visible para Administrador y Supervisor.
- API: `/api/queues/`, con permiso `IsAdminOrSupervisorOrReadOnly` (lectura para cualquier usuario autenticado, escritura para admin o supervisor). Acciones extra: `GET /api/queues/{id}/stats/`, `GET /api/queues/{id}/members/` y `POST /api/queues/{id}/reload_config/`.

La tabla muestra **Nombre**, **Extensión**, **Estrategia**, **Timeout**, **Máx. Espera**, **Estado** y **Acciones**, con filtros por estrategia y estado.

## Crear una cola

1. Entra a **Telefonía → Colas** y haz clic en **Nueva Cola**.
2. Pestaña **Información Básica**: **Nombre de la Cola**, **Extensión**, **Descripción**, **Estrategia de Distribución** y **Cola Activa**.
3. Pestaña **Tiempos y Límites**: **Timeout (segundos)**, **Reintentar (segundos)**, **Tiempo Máximo de Espera (seg)**, **Máximo de Llamadas en Cola**, **Nivel de Servicio (seg)** y **Wrap-up Time (seg)**.
4. Pestaña **Anuncios y Música**: **Frecuencia de Anuncios (seg)**, **Anuncios Periódicos (seg)**, **Anunciar tiempo de espera estimado** y **Clase de MOH**.
5. Haz clic en **Crear Cola** (o **Guardar Cambios** al editar).

Al guardar, la señal de la cola regenera los archivos dinámicos y recarga `app_queue.so` y el dialplan por AMI. El nombre y la extensión deben ser únicos.

## Campos

| Campo (pantalla) | Campo del modelo | Valor en Asterisk |
|---|---|---|
| Nombre de la Cola | `name` | Nombre de la sección `[nombre]` y argumento de `Queue(nombre,...)`. |
| Extensión | `extension` | `exten => <extensión>` en `[from-internal]`. |
| Descripción | `description` | Solo informativa. |
| Estrategia de Distribución | `strategy` | `strategy = ...` (ver tabla siguiente). |
| Timeout (segundos) | `timeout` | `timeout`: segundos que timbra cada agente antes de pasar al siguiente. Por defecto 30. |
| Reintentar (segundos) | `retry` | `retry`: pausa antes de volver a intentar con los agentes. Por defecto 5. |
| Tiempo Máximo de Espera (seg) | `max_wait_time` | Quinto argumento de `Queue()` en la extensión de la cola: tiempo máximo que espera el llamante. Por defecto 300. |
| Máximo de Llamadas en Cola | `max_callers` | `maxlen`: 0 es ilimitado. |
| Nivel de Servicio (seg) | `service_level` | `servicelevel` y umbral del reporte de colas. Por defecto 60. |
| Wrap-up Time (seg) | `wrap_up_time` | `wrapuptime`: segundos que Asterisk espera tras una llamada antes de ofrecer otra al mismo agente. |
| Frecuencia de Anuncios (seg) | `announce_frequency` | `announce-frequency` (posición en cola). |
| Anunciar tiempo de espera estimado | `announce_holdtime` | `announce-holdtime = yes/no`. |
| Anuncios Periódicos (seg) | `periodic_announce_frequency` | `periodic-announce-frequency`. |
| Clase de MOH | `music_on_hold` | `musicclass`. Por defecto `default`. |
| Cola Activa | `is_active` | Las colas inactivas no se escriben ni tienen extensión. |

El generador fija además `ringinuse = no` (no timbra a un agente que ya está en llamada), `weight = 0` y `monitor-type = MixMonitor`.

Según el código revisado, el generador sustituye los valores 0 por los predeterminados en varios campos (usa `valor or predeterminado`): un **Tiempo Máximo de Espera** de 0 se escribe como 300, un **Nivel de Servicio** de 0 como 60, una **Frecuencia de Anuncios** de 0 como 30 y unos **Anuncios Periódicos** de 0 como 60. Aunque la pantalla diga "0 = sin límite" o "0 = sin anuncios", el 0 no desactiva nada.

### Estrategias

| Valor | Etiqueta | Comportamiento |
|---|---|---|
| `ringall` | Ring All - Timbran todos | Timbran todos los agentes libres; atiende el primero que contesta. |
| `leastrecent` | Least Recent - Menos reciente | Timbra el agente que lleva más tiempo sin atender. |
| `fewestcalls` | Fewest Calls - Menos llamadas | Timbra el agente con menos llamadas atendidas. |
| `random` | Random - Aleatorio | Agente al azar. |
| `rrmemory` | Round Robin Memory | Turno circular que recuerda el último agente. |
| `linear` | Linear - Lineal | Siempre en el mismo orden de la lista de miembros. |

## Miembros de la cola

La pantalla de colas no tiene control para asignar agentes. Los miembros (`QueueMember`) se administran en el administrador de Django (`/admin/`), en la cola, sección de miembros en línea, con los campos **agente**, **Penalización** y **Pausado**. `GET /api/queues/{id}/members/` los lista.

Cada miembro activo se escribe como:

```ini
member => PJSIP/101,0
```

El número final es la **Penalización**: Asterisk ofrece primero las llamadas a los miembros con penalización menor. Solo se escriben los agentes activos que tienen extensión SIP. Agregar o retirar un miembro regenera la configuración.

Además, al iniciar sesión en la consola el agente se agrega por AMI (`QueueAdd`) a cada cola donde es miembro, y queda en pausa en ellas mientras está en descanso, post-llamada o desconectado. Ver los estados en [Agentes](./agentes.md).

## Ejemplo

Cola "soporte", extensión 500, `leastrecent`, timeout 20 s, espera máxima 180 s, nivel de servicio 20 s, post-llamada 10 s, con dos agentes. Archivo generado:

```ini
[soporte]
strategy = leastrecent
timeout = 20
retry = 5
maxlen = 0
wrapuptime = 10
announce-frequency = 30
announce-holdtime = yes
periodic-announce-frequency = 60
ringinuse = no
servicelevel = 20
musicclass = default
weight = 0
monitor-type = MixMonitor
member => PJSIP/101,0
member => PJSIP/102,1
```

Extensión en el dialplan dinámico:

```ini
exten => 500,1,NoOp(Cola: soporte)
 same => n,Answer()
 same => n,MixMonitor(${STRFTIME(${EPOCH},,%Y%m%d-%H%M%S)}_${UNIQUEID}_500_${CALLERID(num)}.wav,ab)
 same => n,Queue(soporte,tT,,,180)
 same => n,Hangup()
```

Para que las llamadas de un DID lleguen a la cola, crea una ruta entrante con tipo de destino **Cola** y destino `soporte` (ver [Rutas y dialplan](./rutas-y-dialplan.md)). Esa ruta usa su propio tope de espera de 300 s.

## Nivel de servicio y reportes

El **Nivel de Servicio (seg)** es la meta de tiempo de respuesta. El reporte de colas (`queues_report`) lo usa así, por cada cola y rango de fechas:

- Toma las llamadas entrantes asociadas a la cola.
- Cuenta como "dentro del nivel" las contestadas (`completed`) cuyo tiempo de espera es menor o igual al umbral de la cola.
- Divide entre las llamadas ofrecidas, descontando los abandonos cortos (menos de 5 s), que no penalizan el indicador.
- Si la cola no tiene umbral, usa 20 s. Las llamadas sin cola aparecen como "Directas (sin cola)".

El mismo reporte entrega ofrecidas, contestadas, abandonadas, tasa de respuesta y de abandono, ASA (espera promedio de las contestadas), espera máxima, espera promedio de abandono y AHT (conversación más retención entre contestadas). Hay otra vista del reporte de colas en `backend/apps/reports/views.py` que calcula el porcentaje sobre el total de llamadas sin descontar abandonos cortos, con 60 s como umbral por defecto; por eso dos pantallas pueden mostrar valores distintos para el mismo período. Ver [Reportes](./reportes.md).

## Buenas prácticas

- Usa nombres cortos, en minúscula y sin espacios (`soporte`, `ventas`). El nombre se usa tal cual en Asterisk y en los destinos de rutas e IVR.
- Reserva un rango de extensiones para colas (por ejemplo 500–599) distinto del de agentes y de IVR.
- Fija el **Nivel de Servicio** según la meta real del contrato (por ejemplo 20 s) antes de empezar a medir.
- Usa **Wrap-up Time** corto en la cola y deja que el agente controle su post-llamada desde la consola.
- Usa penalizaciones para escalar: agentes expertos con 0 y apoyo con 1 o más.
- No cambies el nombre de una cola en producción: rompe las rutas entrantes, IVR y campañas que la usan.

## Problemas frecuentes

- **La cola no timbra a nadie.** Revisa que tenga miembros, que los agentes hayan iniciado sesión y que no estén en pausa. Comprueba con `docker exec vozipomni_asterisk asterisk -rx 'queue show'`.
- **Un agente no aparece como miembro en Asterisk.** El agente está inactivo o no tiene extensión SIP, o la configuración no se recargó. Usa `POST /api/queues/{id}/reload_config/`.
- **El 0 en tiempo máximo o anuncios no tiene efecto.** Es la sustitución por valores predeterminados descrita arriba.
- **La ruta entrante rechaza la cola con "La cola seleccionada no existe o está inactiva".** El destino debe ser el nombre exacto de una cola activa.
- **El nivel de servicio no coincide entre pantallas.** Ver la diferencia de cálculo descrita en la sección de reportes.

## Ver también

- [Agentes](./agentes.md)
- [Rutas y dialplan](./rutas-y-dialplan.md)
- [IVR](./ivr.md)
- [Campañas](./campanas.md)
- [Reportes](./reportes.md)
- [Glosario](../general/glosario.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
- [API: colas](../api/colas.md)
