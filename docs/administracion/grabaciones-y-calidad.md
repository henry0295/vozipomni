# Grabaciones y calidad

Este manual explica cómo se graban las llamadas de principio a fin (dónde queda el archivo, cómo se llama y cómo se asocia a la llamada), cómo se reproducen y descargan desde la web, qué política de retención se aplica, quién puede ver y evaluar grabaciones, cómo se crean plantillas de evaluación y cómo se evalúa una llamada. También describe el estado de la transcripción. Se basa en `backend/apps/telephony/asterisk_config.py`, `docker/asterisk/configs/extensions.conf`, `backend/apps/telephony/ami_cdr_listener.py`, `backend/apps/recordings/` (`models.py`, `tasks.py`), `backend/config/recording_config.py`, `RecordingViewSet` en `backend/apps/api/viewsets.py`, `backend/apps/api/admin_viewsets.py`, `frontend/pages/recordings/index.vue` y `frontend/pages/quality/`.

## Acceso

| Pantalla | Menú | Ruta | Roles en el menú |
|---|---|---|---|
| Grabaciones | Calidad → Grabaciones | `/recordings` | Administrador, Supervisor, Analista |
| Evaluaciones | Calidad → Evaluaciones | `/quality` | Administrador, Supervisor, Analista |
| Plantillas de evaluación | Calidad → Plantillas de evaluación | `/quality/templates` | Administrador, Supervisor |

En la API, grabaciones, evaluaciones y plantillas usan `IsAdminSupervisorOrAnalyst`. Diferencias que conviene conocer:

- El botón **Nueva evaluación** solo aparece para Administrador y Supervisor.
- Las estadísticas de calidad (`/api/cc/quality-stats/`) exigen Administrador o Supervisor. Un Analista ve la lista de evaluaciones, pero los indicadores le aparecen vacíos.
- La API de grabaciones permite borrar (`DELETE`) a los tres roles; en la pantalla, el ícono de papelera está visible para todos los que entran.
- Los agentes no tienen acceso a estas pantallas.

## Cómo se graba una llamada

La grabación la hace Asterisk con `MixMonitor(<archivo>.wav,ab)` en el dialplan. La opción `a` agrega al archivo si ya existe y `b` graba solo mientras la llamada está puenteada (es decir, desde que alguien contesta). Como el nombre es relativo, el archivo queda en el directorio de monitor de Asterisk: `/var/spool/asterisk/monitor`.

Dónde se activa y cómo se llama el archivo (`FECHA` es `AAAAMMDD-HHMMSS`):

| Tipo de llamada | Contexto | Nombre del archivo |
|---|---|---|
| Llamada a una extensión o agente | `[from-internal]` dinámico | `FECHA_UNIQUEID_<extensión>.wav` |
| Llamada que entra a una cola | `[from-internal]` dinámico | `FECHA_UNIQUEID_<cola>_<número que llama>.wav` |
| Ruta entrante (DID) | `[from-pstn]` dinámico | `FECHA_UNIQUEID_<DID>_<número que llama>.wav` |
| Ruta saliente | `[from-internal]` dinámico | `FECHA_UNIQUEID_<origen>_<número marcado>.wav` |
| Contextos estáticos de `extensions.conf` (entrada desde troncal o PBX) | varios | `FECHA_UNIQUEID_<origen>_<destino>.wav` |

El `UNIQUEID` de Asterisk en el nombre es lo que permite asociar el archivo a la llamada. Según el código revisado, el dialplan graba siempre en estos puntos; la casilla **Grabación de llamadas** del agente no detiene la grabación (ver [Agentes](./agentes.md)). Las colas usan `monitor-type = MixMonitor` en `queues.conf`. Cada llamada tiene como máximo un registro de grabación (`Recording` es uno a uno con la llamada).

## Cómo se asocia el archivo a la llamada

1. Al procesar el CDR de la llamada, el listener AMI encola la tarea `recordings.link_recording_to_call` con un retraso de 30 segundos, para que MixMonitor termine de cerrar el WAV.
2. La tarea busca en `/var/spool/asterisk/monitor` y `/app/recordings` un archivo con extensión `.wav`, `.wav49`, `.gsm`, `.mp3` u `.ogg`, de más de 100 bytes, cuyo nombre contenga el `UNIQUEID` exacto de la llamada.
3. Si lo encuentra, crea o actualiza el registro `Recording` (nombre, ruta, tamaño, duración igual al tiempo hablado, agente, campaña, estado **Completada**) y marca la llamada como grabada. Si no, reintenta cada 30 segundos, hasta 3 veces.
4. Como red de seguridad, la tarea `recordings.scan_unlinked_recordings` corre cada 15 minutos, revisa las últimas 500 llamadas sin grabación y vincula los archivos que encuentre.

Para que esto funcione, el volumen `asterisk_spool` debe estar montado en `/var/spool/asterisk` en los contenedores `asterisk`, `backend` y `celery_worker`, como está en `docker-compose.prod.yml`. El backend lo necesita para reproducir y descargar; el worker, para vincular y aplicar la retención.

## Página Grabaciones

**Calidad → Grabaciones** muestra una tabla con **ID Llamada**, **Cliente** (en salientes, el número marcado; en entrantes, quien llama), **Agente**, **Duración**, **Fecha**, **Estado** y **Acciones**.

Filtros:

- **Fecha Desde** y **Fecha Hasta** filtran por fecha de creación de la grabación en el servidor.
- **Búsqueda** busca por nombre de archivo o ID de llamada.
- **Agente** filtra solo las filas de la página cargada, y sus opciones salen de esa misma página.

Acciones por fila:

- **Reproducir** (ícono de play) abre **Reproducir Grabación** con llamada, fecha, duración y un reproductor. El audio se pide autenticado a `/api/recordings/<id>/download/?inline=1` y se reproduce desde el navegador.
- **Descargar** baja el archivo con su nombre original desde `/api/recordings/<id>/download/`.
- **Eliminar** pide confirmación ("¿Estás seguro de eliminar esta grabación?"), borra el archivo del disco y el registro. No se puede deshacer.

El endpoint de descarga solo entrega archivos que estén dentro de `/var/spool/asterisk/monitor` o `/app/recordings`; si el archivo no existe responde "El archivo de la grabación no está disponible". Cada descarga o reproducción suma uno al contador de reproducciones. El botón **Descargar Seleccionadas** de la cabecera no tiene acción asociada en el código revisado.

Estados de una grabación: **Grabando** (`recording`), **Completada** (`completed`), **Fallida** (`failed`) y **Archivada** (`archived`). La tabla muestra el valor interno (por ejemplo `completed`).

## Retención

La tarea `recordings.cleanup_old_recordings` corre todos los días a las 2:00 con los valores de `backend/config/recording_config.py`:

| Variable de entorno | Por defecto | Efecto |
|---|---|---|
| `RECORDING_ARCHIVE_DAYS` | 90 | Las grabaciones **Completada** con más días pasan a **Archivada**. El archivo sigue en disco y se puede reproducir. |
| `RECORDING_DELETE_DAYS` | 180 | Las grabaciones **Archivada** con más días pierden el archivo físico. El registro se conserva con la ruta vacía, así que ya no se puede reproducir. |

Los días se cuentan desde la creación del registro. `recording_config.py` también define `RECORDING_DELETE_LOW_PRIORITY`, `RECORDING_BASE_DIR`, `RECORDING_FORMAT`, `RECORDING_QUALITY` y `RECORDING_COMPRESSION`, pero en el código revisado ninguna tarea los usa. Las grabaciones archivadas no aparecen como pendientes de evaluar.

Ajusta los días a la política de tu empresa y a la normativa de protección de datos que aplique, y respalda el volumen `asterisk_spool` si necesitas conservar audio más tiempo. Ver [Respaldos](../operacion/respaldos.md).

## Plantillas de evaluación

En **Calidad → Plantillas de evaluación**:

1. Haz clic en **Nueva plantilla**.
2. Completa **Nombre** y **Descripción**.
3. En **Criterios**, cada fila tiene la etiqueta (por ejemplo "Saludo"), una **Guía para el evaluador (opcional)** y el puntaje máximo (de 1 a 100). Usa **Agregar criterio** para sumar filas. Debajo se ve el total de puntos.
4. Marca **Activa** y, si corresponde, **Plantilla por defecto**. Solo puede haber una por defecto; al marcar una se desmarca la anterior.
5. Haz clic en **Guardar**.

El backend genera el identificador de cada criterio a partir de la etiqueta y rechaza plantillas sin criterios, etiquetas vacías o criterios repetidos. Cada tarjeta muestra cuántos criterios tiene, el puntaje máximo y cuántas evaluaciones la usan. **Usar por defecto** la marca como predeterminada. Si eliminas una plantilla con evaluaciones, no se borra: queda inactiva ("Plantilla desactivada (tiene evaluaciones)").

Sin plantillas se usa la **Estándar (5 criterios, 0-5)**: Saludo, Claridad, Profesionalismo, Resolución y Cierre.

## Evaluar una llamada

En **Calidad → Evaluaciones**:

1. Haz clic en **Nueva evaluación**.
2. En **Grabación a evaluar**, elige una de las grabaciones **Completada** sin evaluar (se listan hasta 200, con agente, llamada y fecha).
3. En **Plantilla**, se propone la plantilla por defecto; puedes elegir otra activa o la estándar.
4. Puntúa cada criterio entre 0 y su máximo. **Puntaje resultante** muestra el total normalizado a 100.
5. Escribe **Comentarios / retroalimentación** y haz clic en **Guardar evaluación**.

Cada grabación admite una sola evaluación. El puntaje total es la suma de puntos dividida por el máximo de la plantilla, por 100. El backend valida que estén todos los criterios y que cada valor esté en rango.

La página muestra, para el período elegido (**Últimos 7 días**, **Últimos 15 días**, **Últimos 30 días**, **Últimos 90 días**) y la plantilla filtrada:

- **Evaluaciones**, **Puntaje promedio (0-100)**, **Agentes evaluados** y **Aprobación (≥ 80)**: porcentaje de evaluaciones con 80 o más.
- **Top agentes por calidad** y **Tendencia diaria**, con colores verde (80 o más), amarillo (60 a 79) y rojo (menos de 60).
- **Puntaje por criterio (plantilla estándar)**, visible sin filtro de plantilla.
- **Evaluaciones recientes**, con búsqueda por grabación o llamada y el detalle de cada evaluación (ícono de ojo).

## Transcripción

La transcripción es opcional y no viene activa en producción. Existe la tarea `recordings.transcribe_recording`, que usa Whisper local (`openai-whisper`) con el modelo de la variable `WHISPER_MODEL` (por defecto `base`) y el idioma de `WHISPER_LANGUAGE` (vacío = detección automática), y guarda el texto en la grabación.

- `openai-whisper` se quitó de `backend/requirements/prod.txt` porque instala torch (unos 2 GB) y necesita setuptools. Si no está instalado, la tarea marca la transcripción como fallida y registra una advertencia.
- Para habilitarla, el comentario de `prod.txt` indica instalarlo en el worker: `docker exec vozipomni_celery_worker pip install openai-whisper`. El modelo se descarga al primer uso. Esa instalación se pierde al recrear el contenedor.
- En el código revisado nada lanza la tarea automáticamente ni hay botón en la interfaz. `TRANSCRIPTION_CONFIG` de `recording_config.py` y la opción `WHISPER_BACKEND=cloud` que menciona `prod.txt` no se usan en el código.

## Problemas frecuentes

- **La llamada no tiene grabación.** Espera al menos 30 segundos después de colgar, o hasta 15 minutos por el escaneo. Revisa que el archivo exista con `docker exec vozipomni_backend ls /var/spool/asterisk/monitor | grep <UNIQUEID>` y que la llamada tenga `unique_id`. Si nadie contestó, MixMonitor con la opción `b` no graba audio.
- **"El archivo de la grabación no está disponible".** La retención borró el archivo, alguien lo eliminó o el volumen `asterisk_spool` no está montado en el backend.
- **El disco se llena.** Baja `RECORDING_DELETE_DAYS` o mueve grabaciones antiguas a otro almacenamiento después de respaldarlas.
- **Un Analista ve los indicadores vacíos.** Es el comportamiento esperado: las estadísticas de calidad son solo para Administrador y Supervisor.
- **No aparece una grabación para evaluar.** Solo se listan las **Completada** sin evaluación; las archivadas no aparecen.

## Ver también

- [Agentes](./agentes.md)
- [Rutas y dialplan](./rutas-y-dialplan.md)
- [Campañas](./campanas.md)
- [Reportes](./reportes.md)
- [Manual del analista](../manuales/manual-analista.md)
- [Manual del supervisor](../manuales/manual-supervisor.md)
- [Respaldos](../operacion/respaldos.md)
- [API: grabaciones y calidad](../api/grabaciones-y-calidad.md)
- [Glosario](../general/glosario.md)
