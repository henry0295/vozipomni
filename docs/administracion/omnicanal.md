# Omnicanal

Este manual explica cómo conectar los canales digitales de VozipCX (WhatsApp Business por la Cloud API de Meta, email, chat web, Facebook Messenger e Instagram), cómo se enrutan y asignan las conversaciones, y cómo se configuran plantillas, respuestas rápidas, etiquetas, tipificaciones al cierre, mensajes fuera de horario y envíos masivos. Se basa en `frontend/pages/settings/whatsapp.vue`, `frontend/pages/settings/channels.vue`, `frontend/pages/messaging/`, `frontend/components/messaging/`, `backend/apps/messaging/` (`models.py`, `views.py`, `views_omni.py`, `routing.py`, `whatsapp.py`, `email_channel.py`, `meta_pages.py`, `broadcasts.py`) y `frontend/public/webchat/widget.js`.

Cada canal configurado crea un registro `Channel` y todas sus conversaciones (`Conversation`) y mensajes (`Message`) usan el mismo modelo. Por eso la bandeja, las métricas y la tipificación funcionan igual para todos los canales.

## Acceso

| Pantalla | Menú | Ruta | Roles |
|---|---|---|---|
| WhatsApp Business | Administración → WhatsApp Business | `/settings/whatsapp` | Administrador |
| Canales digitales (email, chat web, Messenger e Instagram) | Administración → Email, chat web y redes | `/settings/channels` | Administrador |
| Bandeja omnicanal | Omnicanal → Bandeja omnicanal | `/messaging` | Administrador, Supervisor |
| Métricas de chat | Omnicanal → Métricas de chat | `/messaging/metrics` | Administrador, Supervisor, Analista |
| Envíos masivos | Omnicanal → Envíos masivos | `/messaging/broadcasts` | Administrador, Supervisor |
| Respuestas y etiquetas | Omnicanal → Respuestas y etiquetas | `/messaging/settings` | Administrador, Supervisor |

Los agentes atienden los chats desde su consola. Las credenciales de los canales (token de Meta, App Secret, contraseñas IMAP/SMTP, token de página) se guardan cifradas y los formularios de edición no las muestran: deja el campo vacío para conservarlas.

## Requisito: URL pública con HTTPS

Meta solo entrega mensajes a un dominio público con HTTPS y certificado válido. La URL del webhook se arma con `PUBLIC_BASE_URL` del `.env`; si no está definida, se usa la dirección con la que se abrió la web. Define `PUBLIC_BASE_URL=https://<tu-dominio>` y redespliega antes de conectar WhatsApp, Messenger o Instagram. El mismo valor se usa en el código del widget de chat web. Ver [Red y puertos](../instalacion/red-y-puertos.md).

## WhatsApp Business (Cloud API)

La pantalla tiene cuatro pestañas: **Conexión**, **Números**, **Plantillas** y **Guía**. El recuadro **Estado de la conexión** muestra cuántos pasos llevas completados.

### 1. Preparar Meta

1. En business.facebook.com, crea o usa una cuenta de Business Manager y completa la verificación del negocio para superar los límites de prueba.
2. En developers.facebook.com → Mis apps → Crear app, elige el tipo "Negocios" y asóciala a tu Business Manager.
3. Agrega el producto "WhatsApp". Meta crea una cuenta de WhatsApp Business (WABA) y un número de prueba.
4. Copia el **App ID** y el **App Secret** (Configuración → Básica).
5. Agrega tu número en WhatsApp → Configuración de la API → "Agregar número de teléfono". El número no debe estar activo en la app de WhatsApp. Verifícalo por SMS o llamada.
6. Crea un token permanente: Business Manager → Usuarios → Usuarios del sistema → Agregar (rol Administrador). Asigna la App y la cuenta de WhatsApp con control total y genera un token sin caducidad con los permisos `whatsapp_business_messaging` y `whatsapp_business_management`.

### 2. Conectar la App de Meta (pestaña Conexión)

1. Haz clic en **Conectar App de Meta**.
2. Completa **Nombre**, **App ID**, **Versión Graph API** (por defecto `v21.0`), **Token de acceso (Usuario del Sistema)**, **App Secret** y, opcional, **Business Manager ID (opcional)**. Deja **Activo** marcado.
3. Guarda y usa **Probar token** para validar el token contra Meta.

Cada conexión muestra lo que debes pegar en Meta: **Callback URL** (`https://<dominio>/api/webhooks/whatsapp/<APP_ID>/`), **Verify token** (generado al azar por el servidor, con botón para regenerarlo) y el **Campo** `messages`. Si la URL usa HTTP o una IP, la pantalla muestra una advertencia.

### 3. Configurar el webhook en Meta

1. En la conexión, haz clic en **Probar webhook** (o en la pestaña **Guía**, **Probar que Meta pueda llegar**). El servidor llama a su propia URL pública con HTTPS estricto y el desafío de Meta. Respuestas posibles: "La URL no usa HTTPS", certificado inválido, "No se pudo conectar a la URL (DNS, puerto 443 o firewall)", sin respuesta en 10 s, o "La URL responde correctamente con HTTPS válido. Ya puedes verificarla en Meta". La prueba sale desde el mismo servidor, así que no garantiza que el firewall acepte tráfico entrante desde Internet.
2. En developers.facebook.com → tu App → WhatsApp → Configuración → Webhook → Editar, pega la URL y el token de verificación y guarda. Meta llama a la URL; la conexión pasa a "Verificado por Meta".
3. En "Campos del webhook" suscribe `messages`.

Cada evento se valida con la firma `X-Hub-Signature-256` usando el App Secret; los eventos sin firma válida se rechazan. Meta permite una sola URL por App: usa una App distinta por instalación. Un servidor sí puede atender varias Apps, porque el `APP_ID` de la URL identifica cuál es. La ruta anterior `/api/messaging/webhooks/meta/<APP_ID>/` se conserva para Apps que ya la tenían registrada.

### 4. Agregar números (pestaña Números)

1. Haz clic en **Agregar número**.
2. Elige el **Proveedor**, escribe un **Nombre** (por ejemplo "Ventas") y el **WhatsApp Business Account ID (WABA)**. Con **Buscar números** puedes listar los números de la WABA y elegir uno; se completa el **Phone Number ID** (el identificador del número, no el teléfono).
3. Ajusta el enrutamiento (ver [Enrutamiento y asignación](#enrutamiento-y-asignación)) y las palabras de baja y alta.
4. Haz clic en **Guardar**. Al crear la línea se suscribe el webhook automáticamente.

Cada tarjeta de número muestra **Chats abiertos**, **Plantillas**, **Calidad** (según Meta), si recibe mensajes ("Recibe mensajes (webhook suscrito)") y el resumen de asignación, campaña y horario. Las acciones rápidas son **Verificar número en Meta**, **Suscribir webhook**, **Sincronizar plantillas** y **Enviar mensaje de prueba**. Para la prueba, "hello_world" (en_US) viene aprobada en las cuentas nuevas; en números de prueba el destino debe estar en la lista de destinatarios permitidos de Meta. El número destino va en formato internacional sin `+` (por ejemplo `573001234567`).

Si eliminas un número que ya tiene conversaciones, no se borra: queda deshabilitado junto con su canal.

### 5. Plantillas (pestaña Plantillas)

Pasadas 24 horas desde el último mensaje del cliente, WhatsApp solo permite enviar plantillas aprobadas. Filtra por línea y por estado (**Aprobadas**, **Pendientes**, **Rechazadas**).

- **Sincronizar con Meta** trae las plantillas de la línea elegida. El sistema también las sincroniza cada 2 horas.
- **Nueva plantilla**: elige **Línea**, **Nombre** (minúsculas, números y `_`), **Categoría** (**Utilidad**, **Marketing**, **Autenticación**), **Idioma**, **Encabezado (opcional)**, **Cuerpo** (variables `{{1}}`, `{{2}}`…), los ejemplos de cada variable (Meta los exige) y **Pie (opcional)**. Haz clic en **Enviar a revisión**. Meta la revisa en minutos u horas.

## Email

En **Administración → Email, chat web y redes**, pestaña **Email**, haz clic en **Nueva cuenta**:

| Sección | Campos |
|---|---|
| Datos | **Nombre**, **Dirección**, **Nombre del remitente** |
| Entrada (IMAP) | **Servidor**, **Puerto** (993 por defecto), **Carpeta** (`INBOX`), **Usuario**, **Contraseña**, **SSL/TLS** |
| Salida (SMTP) | **Servidor**, **Puerto** (587 por defecto), **STARTTLS (587)**, **SSL (465)**, **Usuario** y **Contraseña** (vacíos = los de IMAP) |
| Firma | Texto que se agrega a las respuestas |
| Enrutamiento y horario | Campos comunes (ver abajo) |

En Gmail y Outlook usa una contraseña de aplicación. Cada buzón se revisa por IMAP cada minuto (tarea `poll_email_accounts`, hasta 50 correos por revisión) y las respuestas salen por SMTP en el mismo hilo. El historial citado se recorta para no duplicar el hilo; los adjuntos entrantes tienen un tope de 20 MB. En la tabla, **Probar** valida IMAP y SMTP, el botón de flechas revisa el buzón de inmediato y la columna **Estado** muestra **Conectada**, **Error** (con el detalle) o **Sin revisar**.

## Chat web

En la pestaña **Chat web**, haz clic en **Nuevo widget** y completa **Nombre interno**, **Color**, **Título**, **Subtítulo**, **Texto de inicio**, **Posición** (**Abajo a la derecha** o **Abajo a la izquierda**), **Pedir nombre**, **Pedir email** y **Dominios permitidos** (uno por línea, con `https://`). Deja los dominios vacíos solo para pruebas: cualquier sitio podría usar el widget. Desde otro origen, la API pública responde "Origen no autorizado".

Al guardar, la tarjeta muestra el **Código para insertar**. Pégalo en tu sitio antes de `</body>`:

```html
<script src="https://<tu-dominio>/webchat/widget.js"
        data-key="<CLAVE_DEL_WIDGET>"
        data-api="https://<tu-dominio>/api/messaging/webchat/public" async></script>
```

El widget (`frontend/public/webchat/widget.js`) no tiene dependencias, aísla sus estilos en un Shadow DOM y guarda la sesión del visitante en `localStorage`. **Regenerar clave** invalida el código anterior: tendrás que actualizarlo en el sitio. Fuera del horario configurado, el widget muestra el mensaje fuera de horario.

## Messenger e Instagram

Usan la misma App de Meta de WhatsApp:

1. En la App agrega los productos **Messenger** e **Instagram** y pide los permisos `pages_messaging`, `pages_manage_metadata` e `instagram_manage_messages`.
2. Asigna la página al Usuario del Sistema del proveedor y genera su token con esos permisos.
3. En Messenger → Webhooks e Instagram → Webhooks usa la misma Callback URL y Verify token del proveedor y suscribe `messages`, `messaging_postbacks`, `message_deliveries` y `message_reads`.
4. En la pestaña **Messenger e Instagram**, elige el proveedor y haz clic en **Buscar páginas**. En cada página encontrada usa **Conectar Messenger** o **Conectar Instagram**. También puedes usar **Agregar manualmente** con **ID de la página de Facebook**, **ID de la cuenta de Instagram** y **Token de acceso de la página**.
5. En la tabla, usa **Suscribir** y **Probar**. El estado pasa a **Suscrita**.

Para responder entre 24 horas y 7 días después del último mensaje del cliente, Meta exige el permiso Human Agent. Según el panel de chat revisado, en Instagram no se pueden adjuntar archivos.

## Enrutamiento y asignación

Todos los canales comparten estos campos (en WhatsApp están en el formulario del número):

| Campo | Efecto |
|---|---|
| Campaña por defecto | Las conversaciones nuevas quedan en esta campaña. Define las tipificaciones al cierre y las respuestas rápidas disponibles. |
| Máx. chats simultáneos por agente | Tope de conversaciones abiertas o en espera por agente (por defecto 5, entre 1 y 50). |
| Asignar automáticamente al agente disponible con menos chats | Activa la asignación automática. |
| Activo / Activa | Habilita el canal. |
| Mensaje de bienvenida (opcional) | Se envía al primer mensaje de una conversación nueva, dentro del horario. |
| Horario de atención | Una condición horaria de telefonía; **Siempre abierto** = 24/7. Ver **Gestionar horarios →** (`/time-conditions`). |
| Mensaje fuera de horario | Se responde automáticamente fuera del horario, como máximo una vez cada 4 horas por conversación. |

Cómo asigna el sistema (`routing.auto_assign`): toma los agentes con usuario activo que no estén desconectados; si la campaña del canal tiene agentes asignados, se limita a ellos; descarta a quienes ya tienen el máximo de chats; elige primero al agente **Disponible** con menos chats y, si no hay, a cualquiera que no esté en pausa. Si nadie cumple, la conversación queda **Sin asignar**. En la bandeja, un supervisor puede cambiar la asignación con **Asignada a:** y **Reasignar**, y un agente puede usar **Tomar** en una conversación sin asignar.

## Respuestas rápidas y etiquetas

En **Omnicanal → Respuestas y etiquetas**:

- **Respuestas rápidas** → **Nueva respuesta**: **Título**, **Atajo** (opcional, por ejemplo `/saludo`), **Texto**, **Campaña** (**Global (todas)** o una campaña), **Canal** (**Todos** o uno) y **Orden**. En el chat, el agente escribe el atajo o usa el botón de respuestas rápidas. Variables: `{nombre}` (cliente) y `{agente}`.
- **Etiquetas** → **Nueva etiqueta**: **Nombre** (hasta 50 caracteres) y **Color**. Se asignan desde el chat o al cerrar y aparecen en métricas y reportes. Al eliminar una etiqueta se quita de las conversaciones que la tenían.

## Cierre con tipificación

Al hacer clic en **Cerrar** en el chat se abre **Cerrar conversación** con **Tipificación**, **Etiquetas** y **Notas**. Las tipificaciones son las calificaciones de la campaña de la conversación. Si la campaña tiene calificaciones, elegir una es obligatorio ("Selecciona una tipificación para cerrar la conversación."); si no, se muestra "La campaña de esta conversación no tiene calificaciones configuradas." Si la calificación elegida requiere rellamada y la conversación tiene contacto, el contacto pasa a estado callback. Una conversación cerrada se puede **Reabrir** desde el chat. Si el cliente vuelve a escribir después del cierre, el sistema abre una conversación nueva (salvo las cerradas por un envío masivo, que se retoman durante 7 días). Ver [Campañas](./campanas.md).

## Envíos masivos de WhatsApp

En **Omnicanal → Envíos masivos** → **Nuevo envío**:

1. Completa **Nombre**, **Línea**, **Plantilla aprobada** y **Lista de contactos**.
2. Deja marcado **Solo contactos con consentimiento (recomendado)**. El resumen indica cuántos contactos recibirán el mensaje, cuántos tienen opt-in y cuántos están en DNC.
3. Completa las variables de la plantilla con datos del contacto (`{first_name}`, `{last_name}`, `{full_name}`, `{company}`, `{city}`, `{custom.campo}`) o texto fijo. La vista previa usa datos de ejemplo.
4. Ajusta **Mensajes por minuto** (por defecto 60; el límite real depende del nivel de la línea en Meta) y, si quieres, **Programar (opcional)**.
5. Haz clic en **Guardar borrador** o **Programar**. Desde la tabla usa **Enviar ahora**, **Pausar**, **Reanudar** o cancelar.

Al iniciar se excluyen contactos marcados como no contactar (`dnc_opt_out`), en lista negra (DNC) o sin teléfono, los duplicados y, si se exige consentimiento, los que no tienen **Acepta WhatsApp**. Los omitidos se cuentan en el progreso. Cada minuto una tarea envía el siguiente lote y otra arranca los envíos programados. Si un cliente responde dentro de 7 días, se retoma la conversación del envío.

Consentimiento por palabra clave: en cada número, **Palabras de baja (opt-out)** (por defecto `BAJA,STOP,CANCELAR`) y **Palabras de alta (opt-in)** (`ALTA,SUSCRIBIR`) actualizan el consentimiento de los contactos con ese número y responden con **Respuesta a la baja** o **Respuesta al alta**. El mensaje debe ser solo la palabra; no distingue mayúsculas.

## Problemas frecuentes

- **Meta no verifica el webhook.** Usa **Probar webhook**. Revisa `PUBLIC_BASE_URL`, el certificado, el puerto 443 y que el Verify token sea el actual (si lo regeneraste, actualízalo en Meta).
- **El número no recibe mensajes.** Confirma "Recibe mensajes (webhook suscrito)"; si no, usa **Suscribir webhook** y revisa que el campo `messages` esté suscrito en Meta.
- **No se puede escribir texto libre.** La ventana de 24 horas está cerrada ("Ventana cerrada"); envía una plantilla aprobada.
- **Una cuenta de email muestra Error.** Revisa el detalle; suele ser la contraseña de aplicación o el puerto y el cifrado de SMTP.
- **El widget no carga en el sitio.** El dominio del sitio debe estar en **Dominios permitidos**, exactamente con `https://`.
- **Las conversaciones quedan Sin asignar.** No hay agentes conectados con cupo, o todos están en pausa. Revisa también los agentes de la campaña.

## Ver también

- [Campañas](./campanas.md)
- [Glosario](../general/glosario.md)
- [Arquitectura](../general/arquitectura.md)
- [Red y puertos](../instalacion/red-y-puertos.md)
- [Manual del supervisor](../manuales/manual-supervisor.md)
- [API: mensajería](../api/mensajeria.md)
- [API: webhooks](../api/webhooks.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
