# Bots de autoatención y conectores

Los bots responden automáticamente en WhatsApp, chat web, Messenger e Instagram antes de que la conversación llegue a un asesor. Se diseñan con un editor visual en **Omnicanal › Bots de autoatención** (administrador y supervisor).

## Cómo funciona

1. Llega un mensaje a un canal que tiene un bot **activo** y la conversación no tiene asesor asignado.
2. El bot ejecuta el flujo **publicado**: envía mensajes, botones o listas, hace preguntas y guarda las respuestas en variables.
3. Si el flujo llega a **Pasar a asesor**, la conversación se asigna como siempre (campaña del canal o la indicada en el bloque). El asesor ve en la conversación los datos capturados y el recorrido.
4. Si el cliente envía un archivo o audio, si el bot no entiende tras varios intentos, o si ocurre cualquier error, la conversación pasa a un asesor. El bot nunca deja al cliente sin atención.

Si el cliente no responde durante el tiempo configurado (30 minutos por defecto), la próxima vez que escriba el bot empieza de nuevo. Los datos que el bot capturó se borran a los 7 días.

En WhatsApp se usan botones (hasta 3) y listas (hasta 10 opciones) nativos. En los demás canales las opciones se envían numeradas y el cliente puede responder con el número o con el texto.

## El designer

| Bloque | Uso | Salidas |
|---|---|---|
| Mensaje | Envía un texto | Siguiente |
| Botones | Hasta 3 opciones | Una por opción |
| Lista / Menú | Hasta 10 opciones con descripción | Una por opción |
| Pregunta | Pide un dato y lo valida (texto, número, email, teléfono, documento, fecha o expresión regular) | Respuesta válida · Intentos agotados |
| Condición | Compara variables (igual, contiene, vacía, mayor que…) | Se cumple · No se cumple |
| Horario | Usa la condición horaria del canal o una elegida | En horario · Fuera de horario |
| Asignar variable | Guarda un valor | Siguiente |
| Conector | Llama a un sistema externo (GLPI, API) | Éxito · Sin resultados · Error |
| Lista dinámica | Convierte una lista devuelta por un conector en un menú | Elemento elegido · Lista vacía |
| Pasar a asesor | Asigna a un agente, opcionalmente a otra campaña, con una nota | — |
| Fin | Despide y cierra la conversación | — |

- Los textos aceptan variables: `{{contact.name}}`, `{{contact.phone}}`, `{{contact.email}}` y las que defina el flujo, incluidos campos de resultados de conectores (`{{ticket.id}}`, `{{solicitante.name}}`).
- **Guardar** guarda el borrador. **Publicar** valida el flujo y crea una versión. Las conversaciones en curso terminan con la versión con la que empezaron. En **Versiones** se puede cargar una versión anterior en el borrador.
- **Simulador**: chat de prueba que recorre el borrador sin enviar nada. Los conectores devuelven el "resultado simulado" del bloque. Un administrador puede marcar **Conectores reales** para llamarlos de verdad.
- Para que el bot atienda: en la lista de bots, ⚙ › elegir los canales y activar el interruptor. Un canal solo puede tener un bot activo.

## Conectores

**Administración › Conectores**. Solo el administrador crea o edita conectores. Las credenciales se guardan cifradas y nunca se vuelven a mostrar. Cada llamada queda en el registro del conector (acción, resultado, duración y error, sin los datos enviados).

### GLPI

1. En GLPI: *Configuración › General › API* → habilitar la API REST y el inicio de sesión con token externo. Crear un **cliente de API** y copiar su App-Token.
2. Crear un usuario técnico (por ejemplo `bot-whatsapp`) con un perfil que pueda crear tickets y consultar usuarios. Copiar su token desde *Preferencias › Token de API remota*.
3. En VozipCX: Nuevo conector › tipo GLPI, URL `https://su-glpi/apirest.php`, App-Token y token de usuario. Opcional: tipo, urgencia y categoría por defecto, y el id del origen "WhatsApp".
4. **Probar conexión**, y luego **Probar acción** › *Buscar solicitante* con un email real.
5. En Bots › Nuevo bot › plantilla **Soporte con GLPI**. Revise las categorías y textos, publique, asigne el canal de WhatsApp y active.

Acciones disponibles: buscar solicitante (por email o teléfono), crear ticket, consultar ticket, tickets abiertos del solicitante, agregar seguimiento y listar categorías.

### API HTTP genérica

Para sistemas con API REST (agendas de citas, CRM, ERP). La configuración define cabeceras y acciones:

```json
{
  "headers": {"Authorization": "Bearer {{secret.token}}"},
  "actions": [
    {"name": "consultar_citas", "label": "Consultar citas", "method": "GET",
     "path": "/pacientes/{{documento}}/citas", "query": {"estado": "activa"},
     "inputs": ["documento"], "result_path": "data", "returns_list": true},
    {"name": "cancelar_cita", "label": "Cancelar cita", "method": "POST",
     "path": "/citas/{{cita_id}}/cancelar", "body": {"motivo": "{{motivo}}"},
     "inputs": ["cita_id", "motivo"]}
  ]
}
```

- `{{parametro}}` toma el valor que el bloque Conector envía. `{{secret.x}}` toma una credencial.
- `result_path` extrae una parte de la respuesta (`data.items`). Si queda vacía, el bloque sale por **Sin resultados**. Un HTTP 404 también cuenta como sin resultados, y otros errores HTTP salen por **Error**.

## Notas de voz: transcripción local

Los audios que envían los clientes se transcriben **en el propio servidor** con el servicio `transcriber` (faster-whisper, modelo `small` en CPU). Ningún audio sale a terceros.

- El texto aparece debajo del audio en la bandeja omnicanal.
- Si la conversación está en un bot, el flujo continúa con la transcripción como si el cliente hubiera escrito. Si no se pudo transcribir, pasa a un asesor.
- El primer arranque descarga el modelo (unos 500 MB) en el volumen `whisper_models`. Las siguientes veces carga desde ahí.
- Variables en `/opt/vozipomni/.env`:
  - `WHISPER_MODEL`: `base` (más rápido) · `small` (por defecto) · `medium` (más preciso, más RAM y CPU).
  - `WHISPER_MAX_SECONDS`: duración máxima (600 s).
  - `TRANSCRIBE_INBOUND_AUDIO=false`: desactiva la transcripción.
  - `TRANSCRIBER_URL=` (vacío): desactiva el servicio para el backend.
- Referencia en CPU: un audio de 30 s tarda entre 3 y 10 s con `small`, según el servidor. El servicio procesa un audio a la vez.

## Inteligencia artificial: bloque «Entender intención»

En **Administración › Inteligencia artificial** se configuran los proveedores: OpenAI, Azure OpenAI o cualquier API compatible con OpenAI (Ollama o vLLM en su red, Gemini, LM Studio). La API key se guarda cifrada.

El bloque **Entender intención (IA)** del designer:

1. Pregunta al cliente y espera su respuesta, o analiza el texto de una variable.
2. Clasifica el mensaje en una de las intenciones definidas (id, nombre, descripción y ejemplos). Cada intención es una salida del bloque, más **No entendí** y **Error de IA**.
3. Extrae datos opcionales (por ejemplo `ticket_id` o `documento`), que quedan como variables (`{{ticket_id}}`). El resultado completo queda en `{{ia.intent}}` y `{{ia.confidence}}`.
4. Si la confianza es menor que el mínimo configurado, sale por **No entendí**.

La IA solo decide por qué salida sigue el flujo: no responde al cliente ni ejecuta acciones por su cuenta.

**Privacidad:** con «Ocultar datos personales» activo, antes de enviar el texto se reemplazan documentos, teléfonos, emails y tarjetas por marcadores (`[DOC_1]`). Los valores que la IA extraiga con esos marcadores se restauran en el servidor, así que el dato real no sale. Para datos de salud se recomienda un modelo local o Azure con residencia de datos. Cada uso queda registrado (intención, tokens y tiempo, sin el texto del cliente), y se puede fijar un límite mensual de tokens.

**Simulador:** sin «Conectores reales», el bloque de IA usa una clasificación aproximada por palabras clave (no consume tokens). Con la opción marcada (solo administrador) llama al proveedor real.
