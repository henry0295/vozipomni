# Manual del agente

Este manual explica el trabajo diario del agente en la **Consola de Agente** de VozipOmni: cómo entrar, cómo está organizada la pantalla, cómo cambiar de estado y tomar pausas, cómo hacer y recibir llamadas, cómo calificar cada llamada, y cómo usar las pestañas de campaña, marcador, contactos y chats. Al final hay una sección de problemas frecuentes. Se basa en `frontend/pages/agent/console.vue`, los componentes `AgentSoftphone.vue`, `AgentStatusPanel.vue`, `AgentCallDisposition.vue`, `AgentCampaignsPanel.vue`, `AgentDialerPanel.vue`, `AgentContactsList.vue`, `AgentWhatsAppPanel.vue`, el store `frontend/stores/agent.ts` y el composable `frontend/composables/useWebRTC.ts`.

La consola funciona en el navegador. No hay que instalar un softphone: el teléfono va integrado en la página (WebRTC). Solo necesitas un navegador actualizado (Chrome, Edge o Firefox), diadema con micrófono y la dirección HTTPS de la plataforma.

## Entrar a la consola

1. Abre la dirección de VozipOmni que te dio tu supervisor (siempre con `https://`).
2. En la pantalla **VozipOmni / Inicia sesión en tu cuenta** escribe **Usuario** y **Contraseña** y haz clic en **Iniciar sesión**. Si olvidaste la contraseña usa el enlace **Recuperar**.
3. Con rol Agente, el sistema te lleva directo a la **Consola de Agente** (ruta `/agent/console`). Los agentes no ven el menú lateral ni otros módulos.
4. El navegador pide permiso para usar el micrófono. Acepta: sin él no puedes hablar.
5. Si tu usuario tiene un solo perfil de agente, la sesión de agente se inicia sola. Si tiene varios, aparece la tarjeta **Iniciar Sesión de Agente**: elige tu perfil en **Seleccionar agente** (se ve el nombre y la extensión, por ejemplo "Ext: 101") y haz clic en **Iniciar Sesión**.

Solo aparecen los perfiles con WebRTC habilitado. Si ves el aviso **Sin perfiles de agente** ("Este usuario no tiene perfiles de agente asignados"), pide al supervisor o administrador que revise tu perfil en **Operación → Agentes**.

Al iniciar la sesión de agente quedas en estado **Disponible** y el sistema te agrega a las colas donde eres miembro.

## Cómo está organizada la pantalla

| Zona | Contenido |
|---|---|
| Encabezado | Título **Consola de Agente**, fecha y hora, botón de modo claro/oscuro, botón de estado (tu nombre y estado actual) y **Cerrar Sesión**. |
| Columna izquierda | Tarjeta **Teléfono**: indicador de conexión, marcador, teclado, **Llamada Rápida** y, durante la llamada, los controles. |
| Columna central | Pestañas **Campaña**, **Dialer**, **Contactos** y **WhatsApp**. |
| Columna derecha | **Resultado de la llamada \*** (disposición) y **Notas Rápidas** (esta última solo cuando no hay llamada). |

Debajo del encabezado pueden aparecer dos avisos de micrófono:

- Amarillo: "Se necesita acceso al micrófono para las llamadas." con el botón **Permitir micrófono**.
- Rojo: "El micrófono está bloqueado. Para recibir y realizar llamadas, permite el acceso al micrófono en la configuración del navegador y recarga la página."

El indicador de la tarjeta **Teléfono** muestra **Conectado** (verde), **Conectando...** (amarillo) o **Desconectado** (rojo). Solo con **Conectado** puedes llamar y recibir llamadas.

## Estados y pausas

Haz clic en el botón de estado del encabezado (tu nombre con un punto de color). Se abre un panel con:

- **Cambiar Estado**: **Disponible**, **Ocupado** y **Post-llamada**. El estado actual tiene una marca de verificación.
- **Iniciar Pausa** o, si ya estás en pausa, **Terminar Pausa**.
- **Estadísticas de Hoy**: **Llamadas**, **Hablando**, **Disponible** y **En Pausa**.
- **Sesión activa**: tiempo desde que iniciaste la sesión de agente.

| Estado | Color | Qué significa para ti |
|---|---|---|
| Disponible | Verde | Recibes llamadas de las colas y puedes marcar. |
| Ocupado | Amarillo | No estás listo. El marcador del teléfono queda deshabilitado. |
| En Llamada | Azul | Estás en una llamada. No puedes cambiar de estado hasta colgar. |
| Post-llamada | Morado | Tiempo para calificar la llamada. Quedas en pausa en las colas. |
| En Pausa | Amarillo | Pausa con motivo. Quedas en pausa en las colas. |
| Desconectado | Gris | Sin sesión de agente. |

Importante: el teléfono solo permite marcar en estado **Disponible**. En Ocupado, Post-llamada o En Pausa el teclado y el botón **Llamar** aparecen deshabilitados.

### Tomar una pausa

1. Abre el panel de estado y haz clic en **Iniciar Pausa**.
2. En **Seleccionar Motivo de Pausa** elige el motivo (la lista la define el supervisor en **Grupos y pausas**). **Cancelar** cierra la ventana sin cambiar nada.
3. El panel muestra el motivo y un contador de tiempo.
4. Para volver, abre el panel y haz clic en **Terminar Pausa**. Quedas en **Disponible**.

Algunos motivos tienen duración máxima. El sistema no corta la pausa al llegar al tope, pero el reporte de pausas marca como excedidas las que lo superan. Vuelve a tiempo.

## Hacer una llamada

1. Verifica que estás en **Disponible** y que el teléfono dice **Conectado**.
2. Escribe el número en **Número a marcar** o usa el teclado numérico. **Borrar** elimina el último dígito.
3. Haz clic en **Llamar** o presiona Enter.
4. Mientras timbra, la tarjeta muestra el número, "Llamada saliente" y el botón **Colgar**.
5. Cuando contestan aparece el aviso **Llamada conectada** ("En línea con ...") y el contador de duración.

### Llamada Rápida

Debajo del teclado, la sección **Llamada Rápida** lista las extensiones activas de la plataforma (nombre y "Ext: ..."). Un clic marca esa extensión. Úsala para llamar a un compañero o a un supervisor.

## Recibir una llamada

Cuando entra una llamada, la tarjeta **Teléfono** muestra el número, "Llamada entrante" y dos botones: **Contestar** y **Rechazar**. Al contestar arrancan el contador y los controles.

Mantén la pestaña de la consola abierta. Si la cierras o cierras el navegador, el teléfono se desconecta y no recibes llamadas.

## Durante la llamada

| Control | Qué hace |
|---|---|
| **Silenciar** / **Activar** | Corta o reanuda tu micrófono. El botón se pone rojo mientras estás silenciado. |
| **Retener** / **Reanudar** | Pone al cliente en espera y lo recupera. El botón se pone amarillo en espera. |
| **DTMF** | Muestra un teclado para enviar tonos (por ejemplo, para navegar el menú de otra empresa). |
| **Colgar** | Termina la llamada. |

### Transferir

En el recuadro **Transferir a:**:

- **Rápida**: escribe la extensión o el número en **Extensión o número** y haz clic en **Rápida**. La llamada pasa de inmediato al destino (transferencia ciega) y tú quedas libre.
- **Agentes**: abre **Agentes disponibles**, con los compañeros en estado Disponible y cuántas llamadas llevan hoy. Un clic en un agente pide la transferencia. Según el código revisado, la consola no envía el canal de Asterisk en esta petición y el servidor puede responder **Error al transferir** ("channel y extension requeridos"). Si pasa, usa **Rápida** con la extensión del compañero.

### Conferencia a 3

En **Conferencia a 3:** escribe el **Número del 3er participante** y haz clic en **Conferencia**. Tiene la misma limitación que la transferencia por **Agentes**: si aparece **Error al crear conferencia**, avisa a tu supervisor.

## Calificar la llamada (disposición)

Al colgar pasas a **Post-llamada** y la columna derecha muestra **Resultado de la llamada \***:

1. Elige una disposición. Si la campaña seleccionada tiene disposiciones propias, se usan esas. Si no, la consola ofrece las predeterminadas: **Contactado**, **No Disponible**, **No Contesta**, **Ocupado**, **Venta**, **No Interesado**, **Callback** y **Número Erróneo**.
2. Si la disposición requiere volver a llamar (por ejemplo **Callback**, **No Disponible** u **Ocupado**), aparece **Programar callback** con fecha y hora. Si dejas la hora vacía se usa 09:00.
3. Escribe en **Notas de la llamada** lo importante de la conversación.
4. Si la campaña tiene formulario, completa los campos de **Información del Contacto**.
5. Haz clic en **Guardar y Continuar**. Verás **Disposición guardada exitosamente** y vuelves a **Disponible**.

### Contador de post-llamada

Debajo del botón aparece **Tiempo restante: 10s**. El contador es de 10 segundos en la consola, sin importar el tiempo de post-llamada configurado en el perfil del agente.

- Si al llegar a cero ya elegiste una disposición, la consola la guarda sola (con las notas que hayas escrito) y te pasa a **Disponible**.
- Si no elegiste ninguna, no se guarda nada y sigues en **Post-llamada** hasta que guardes o cambies de estado. Mientras tanto no recibes llamadas de las colas.

Si la llamada falla o nadie contesta, la consola también pasa a **Post-llamada**: califícala igual (por ejemplo **No Contesta**).

**Notas Rápidas** (visible cuando no hay llamada) es un bloc de apoyo. No se guarda en el sistema y se limpia al guardar una disposición.

## Pestaña Campaña

**Campañas Activas** lista las campañas activas en las que estás asignado, con **Contactos**, **Contactados**, **Exitosos** y **Avance**. Se actualiza cada 30 segundos, salvo durante una llamada. La primera campaña queda seleccionada por defecto; haz clic en otra para cambiarla. La campaña seleccionada muestra su **Script:** y define qué disposiciones, contactos y formulario ves.

Durante una llamada iniciada desde **Dialer** o **Contactos**, esta pestaña muestra **Información del Contacto** (Nombre, Teléfono, Email, Empresa) e **Historial de Llamadas**. En llamadas entrantes el nombre aparece como "Desconocido".

Si no tienes campañas asignadas verás "No hay campañas activas". La asignación la hace el supervisor o el administrador.

## Pestaña Dialer

**Marcación Automática** muestra la campaña de marcador, su tipo (**Preview**, **Progresivo** o **Predictivo**), **Contactos marcados**, contadores (**Llamadas Contestadas**, **Sin Respuesta**, **Ocupado**, **Transferencias**) y el **Script de Campaña**.

- **Preview**: ves el **Próximo Contacto** con sus datos y **Notas previas:**. Haz clic en **Marcar Ahora** para llamar o en **Siguiente** para saltarlo.
- **Progresivo**: aparece "Marcación automática en:" con una cuenta regresiva de 10 segundos. Al llegar a cero marca solo. **Cancelar** salta ese contacto.
- **Predictivo**: aparece **Marcación Predictiva Activa** / "Esperando llamada conectada...". El sistema te pasa las llamadas ya contestadas.

**Pausar Dialer** y **Reanudar Dialer** detienen o retoman la marcación en tu consola. Si sales de **Disponible** el dialer se pausa solo. Cuando no quedan contactos aparece **No hay más contactos**.

Según el código revisado, el encabezado de esta pestaña (nombre, tipo y avance de la campaña) todavía usa datos de ejemplo, no los de tu campaña real. El **Próximo Contacto** sí viene del servidor. Guíate por la pestaña **Campaña** para el nombre y el avance reales.

## Pestaña Contactos

**Contactos de Campaña** lista los contactos pendientes o con callback de la campaña seleccionada (hasta 100, 10 por página).

- Busca con **Buscar por nombre, teléfono o email...**.
- Filtra por **Estado**: Todos, Pendiente, Contactado, Callback, No Interesado, Venta.
- **Actualizar** recarga la lista.
- **Llamar** marca al contacto (solo en **Disponible**) y muestra "Llamando a ...".
- **WhatsApp** (si el contacto lo tiene) te lleva a la pestaña WhatsApp.
- Un clic en la tarjeta abre **Detalle del Contacto** con historial, **Información Adicional** y el botón **Llamar**.

## Pestaña WhatsApp (chats)

La tarjeta **Chats** reúne WhatsApp, email, chat web y redes. Arriba ves los mensajes **sin leer**, el indicador **En vivo** o **Reconectando…** y el botón **Nueva** para iniciar una conversación.

1. Usa las pestañas **Mis chats**, **Sin asignar** y **Sin leer**, y el buscador **Buscar nombre o número…**.
2. En una conversación **Sin asignar**, haz clic en **Tomar** para quedártela. Pasa a **Mis chats**.
3. Haz clic en una conversación para abrirla, responder y volver a la lista.
4. La etiqueta **Ventana cerrada** indica que la ventana de respuesta de WhatsApp venció; en ese caso normalmente solo se pueden enviar plantillas aprobadas. Consulta a tu supervisor.
5. Desde el chat puedes llamar al contacto con el softphone.

## Avisos y notificaciones

- Avisos en pantalla: **Llamada conectada**, **Llamada fallida**, **Disposición guardada exitosamente**, **Error al transferir**, **Error cargando campañas**, entre otros.
- Notificaciones del navegador: si ya diste permiso de notificaciones, verás **Sesión Iniciada** al entrar y **Nuevo mensaje de WhatsApp** (o del canal que corresponda) cuando llega un chat. La consola no pide ese permiso por sí sola; actívalo desde la configuración del sitio en el navegador.

## Cerrar sesión

Haz clic en **Cerrar Sesión** (arriba a la derecha) y confirma "¿Está seguro que desea cerrar la sesión de agente?". La consola desconecta el teléfono, cierra la sesión de agente (sales de las colas y quedas **Desconectado**) y cierra tu sesión en VozipOmni. Vuelves a la pantalla de ingreso.

Cierra siempre con este botón antes de irte. Cerrar la pestaña desconecta el teléfono, pero puede dejarte como conectado en los tableros del supervisor.

## Problemas frecuentes

- **El teléfono se queda en "Conectando...".** Recarga la página sin caché con Ctrl+F5. Confirma que la dirección empieza por `https://` (el teléfono no funciona por `http://`). Si llevas mucho tiempo con la pestaña abierta, tu sesión pudo vencer: haz clic en **Cerrar Sesión** y vuelve a entrar. La consola reintenta la conexión sola hasta 5 veces. Si sigue igual, avisa al supervisor. Ver [Solución de problemas](../operacion/solucion-de-problemas.md).
- **El teléfono dice "Desconectado".** Igual que el caso anterior. Revisa también tu conexión a internet o a la red de la empresa.
- **No puedo marcar: el botón Llamar está gris.** Debes estar en **Disponible**, con el teléfono en **Conectado** y sin otra llamada en curso.
- **No me escuchan.** Revisa el aviso rojo de micrófono bloqueado. En la barra de direcciones, abre el ícono del candado, permite el micrófono y recarga. Verifica que el navegador use la diadema correcta como micrófono y que no estés en **Silenciar** (botón rojo).
- **No escucho al cliente.** Revisa el volumen y que la salida de audio del sistema sea la diadema. Si otra pestaña o programa tomó el audio, ciérralo y recarga la consola.
- **"Llamada rechazada (404 ...)".** El número no tiene ruta: no existe una ruta saliente que lo cubra o la extensión no existe. Revisa el número; si está bien, avisa al supervisor.
- **"Llamada rechazada (403 ...)".** La llamada fue bloqueada por seguridad: destino internacional, prefijo bloqueado, número fuera de la lista blanca o límite de llamadas por extensión. Antes del rechazo se escucha el mensaje de servicio no disponible. No insistas; avisa al supervisor.
- **"Llamada rechazada (503 ...)".** No hay canales: la troncal o el límite total de llamadas salientes está lleno ("todos los circuitos ocupados"). Espera un momento y vuelve a intentar.
- **"Llamada fallida: ...".** La llamada terminó sin código SIP (por ejemplo, se perdió la conexión). Revisa tu red y vuelve a intentar.
- **Me quedé en Post-llamada.** Elige una disposición y haz clic en **Guardar y Continuar**, o cambia a **Disponible** desde el panel de estado.
- **No veo campañas ni contactos.** No tienes campañas activas asignadas o no hay contactos pendientes. Avisa al supervisor.

## Ver también

- [Glosario](../general/glosario.md)
- [Agentes](../administracion/agentes.md)
- [Campañas](../administracion/campanas.md)
- [Omnicanal](../administracion/omnicanal.md)
- [Manual del supervisor](./manual-supervisor.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
- [SSL y HTTPS](../instalacion/ssl-https.md)
