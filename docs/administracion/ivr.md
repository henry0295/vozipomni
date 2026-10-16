# IVR

Este manual explica cómo crear menús de voz interactivos (IVR) en VozipOmni: qué audios usa, cómo se asigna cada tecla a un destino, cómo funcionan el tiempo de espera, las opciones inválidas y sus reintentos, y qué dialplan genera. Se basa en `frontend/pages/ivr/index.vue`, el modelo `IVR` de `backend/apps/telephony/models.py`, el `IVRSerializer` de `backend/apps/telephony/serializers.py`, el `IVRViewSet` (catálogo y carga de audios) de `backend/apps/telephony/views.py` y la sección de IVR de `generate_extensions_conf()` en `backend/apps/telephony/asterisk_config.py`.

Cada IVR activo se escribe en `extensions_dynamic.conf` como un contexto propio `[ivr-<extensión>]`. Las llamadas llegan a él desde una ruta entrante, otro IVR o un destino de timeout o inválido con tipo **IVR**. Aparte existe el IVR estático 9000 de `extensions.conf`, al que caen las llamadas entrantes sin ruta DID; ese no se administra desde esta pantalla.

## Acceso

- **Telefonía → IVR Menus** (ruta `/ivr`, página "IVR - Menús Interactivos"). Visible solo para Administrador.
- API: `/api/telephony/ivr/` con permiso `IsAdminUserCustom`, más `GET /api/telephony/ivr/audio_catalog/` y `POST /api/telephony/ivr/upload_audio/`.

La tabla muestra **Nombre**, **Extensión**, **Mensaje de Bienvenida**, **Opciones** (cantidad de teclas), **Estado** y **Acciones**.

## Crear un IVR

1. Entra a **Telefonía → IVR Menus** y haz clic en **Crear IVR**.
2. **Sección 1**: **Nombre**, **Extensión**, **Descripción**, **Fuente de Audio Principal** y el audio principal. Si el audio no existe, súbelo con **Subir audio**.
3. **Sección 2**: **Spoken (Audio adicional)**, **Mensaje - Opción Inválida**, **Mensaje - Timeout**, y los bloques **Timeout** y **Opción Inválida** con sus reintentos y destinos.
4. **Sección 3**: haz clic en **Agregar Opción** por cada tecla y elige **DTMF**, **Tipo Destino** y **Destino**.
5. **Estado**: **IVR Activado**.
6. Haz clic en **Crear IVR** (o **Guardar Cambios**).

Validaciones del backend:

- "Debes configurar un audio principal para el IVR." si falta el audio principal.
- **Time out** entre 1 y 60 segundos; **Time out retries** e **Invalid retries** entre 1 y 10.
- Destino de timeout y destino de opción inválida son obligatorios (tipo y valor).
- Al menos una opción DTMF. Las teclas válidas son `0`–`9`, `*` y `#`.
- Cada destino debe existir y estar activo ("La cola ... no existe o está inactiva", etc.). Un IVR no puede apuntar a sí mismo.

## Campos

| Campo (pantalla) | Campo del modelo | Uso en el dialplan |
|---|---|---|
| Nombre | `name` | Único. Aparece en el `NoOp`. |
| Extensión | `extension` | Única. Da nombre al contexto `[ivr-<extensión>]` y es el valor que se elige como destino tipo IVR. |
| Descripción | `description` | Informativa. |
| Archivo Interno / Externo Principal | `welcome_message` | `Playback(<audio>)` al entrar. Obligatorio. |
| Spoken (Audio adicional) | `spoken` | Segundo `Playback(<audio>)`, opcional, antes del menú. |
| Mensaje - Opción Inválida | `invalid_message` | `Playback` al marcar una tecla no configurada. Vacío usa `invalid`. |
| Mensaje - Timeout | `timeout_message` | `Playback` cuando no se marca nada. Vacío usa `vm-goodbye`. |
| Time out (segundos) | `timeout` | `TIMEOUT(response)` y `WaitExten(<segundos>)`. Por defecto 5. |
| Time out retries | `timeout_retries` | Veces sin respuesta antes de ir al destino de timeout. |
| Tipo de destino / Destino timeout | `timeout_destination_type`, `timeout_destination` | Destino final por silencio. |
| Invalid retries | `invalid_retries` | Veces con tecla inválida antes de ir al destino inválido. |
| Tipo de destino / Destino inválido | `invalid_destination_type`, `invalid_destination` | Destino final por teclas inválidas. |
| Opciones DTMF | `menu_options` | Una extensión por tecla dentro del contexto del IVR. |
| IVR Activado | `is_active` | Los IVR inactivos no se escriben. |

El backend calcula `max_attempts` como el mayor entre los dos reintentos; se conserva por compatibilidad.

### Opciones DTMF

`menu_options` se guarda como un objeto JSON por tecla:

```json
{
  "1": {"type": "queue", "destination": "ventas", "spoken": "Ventas"},
  "2": {"type": "queue", "destination": "soporte", "spoken": "Soporte"},
  "0": {"type": "extension", "destination": "101", "spoken": "Operador"}
}
```

El formato antiguo `{"1": "100"}` se sigue aceptando y se convierte a tipo **Extensión**. El campo **Spoken de la opción** es solo una referencia operativa: no se reproduce.

### Tipos de destino

| Tipo | Valor | Dialplan |
|---|---|---|
| Cola | Nombre de la cola | `Queue(<nombre>,tT,,,300)` |
| Extensión | Número de extensión | `Dial(PJSIP/<ext>,30,trg)` |
| IVR | Extensión de otro IVR | `Goto(ivr-<extensión>,s,1)` |
| Buzón de Voz | Número del buzón | `VoiceMail(<buzón>@default)` |
| Anuncio | Audio (por ejemplo `custom/horario`) | `Playback(<audio>)` |
| Destino Personalizado | Nombre del destino | `Goto(<context>,<extension>,<priority>)` |

## Timeout, opciones inválidas y reintentos

El flujo es el mismo para los dos casos:

1. Tras los audios, el IVR espera una tecla durante **Time out** segundos.
2. Si no llega nada, reproduce **Mensaje - Timeout** y suma un intento de timeout. Si hay tecla no configurada, reproduce **Mensaje - Opción Inválida** y suma un intento inválido.
3. Mientras el contador sea menor que los reintentos configurados, vuelve al menú (etiqueta `start`).
4. Al llegar al número de reintentos, envía la llamada al destino de timeout o inválido.

Con **Time out retries** en 3, el llamante escucha el menú tres veces en total antes de ir al destino de timeout. Cada contador es independiente.

## Audio

- El selector **Archivo interno** lista los audios encontrados en `/var/lib/asterisk/sounds` y `/usr/share/asterisk/sounds` (y sus carpetas `custom`), más los ya usados en otros IVR. Los valores van sin extensión, como los espera `Playback()`.
- **Archivo externo** permite escribir el nombre a mano.
- **Subir audio** acepta `.wav`, `.gsm`, `.ulaw`, `.alaw`, `.sln` y `.mp3`. El nombre se normaliza (minúsculas, guiones) y queda como `custom/<nombre>` en el volumen de sonidos que comparten backend y Asterisk.

Tenlo en cuenta, según el código revisado:

- **Mensaje - Opción Inválida** y **Mensaje - Timeout** se reproducen con `Playback`, así que deben ser nombres de audio. El formulario propone textos ("Opción no válida, intente nuevamente", "Se agotó el tiempo") que Asterisk no puede reproducir. Reemplázalos por un audio (por ejemplo `custom/ivr-invalida`) o déjalos vacíos para usar `invalid` y `vm-goodbye`.
- El audio principal y el Spoken se reproducen con `Playback`, que no se puede interrumpir con una tecla. Después, el menú ejecuta `Background(main-menu)` con el audio fijo `main-menu`. Graba tu mensaje sabiendo que ese audio suena a continuación, o reemplaza el archivo `main-menu` en el volumen de sonidos.
- Prefiere WAV mono de 8 kHz y 16 bits. Si subes MP3, verifica que Asterisk pueda reproducirlo en tu instalación.

## Ejemplo generado

IVR "Principal", extensión 700, audio `custom/bienvenida`, timeout 5 s, 3 reintentos de cada tipo, destino de timeout e inválido a la cola `soporte`, teclas 1 (`ventas`) y 2 (`soporte`):

```ini
[ivr-700]
exten => s,1,NoOp(IVR: Principal)
 same => n,Answer()
 same => n,Playback(custom/bienvenida)
 same => n,Set(TIMEOUT(response)=5)
 same => n,Set(INVALID_ATTEMPTS=0)
 same => n,Set(TIMEOUT_ATTEMPTS=0)
 same => n(start),Background(main-menu)
 same => n,WaitExten(5)
exten => 1,1,Queue(ventas,tT,,,300)
 same => n,Hangup()
exten => 2,1,Queue(soporte,tT,,,300)
 same => n,Hangup()
exten => i,1,Playback(invalid)
 same => n,Set(INVALID_ATTEMPTS=$[${INVALID_ATTEMPTS}+1])
 same => n,GotoIf($[${INVALID_ATTEMPTS}<3]?s,start)
 same => n,Queue(soporte,tT,,,300)
 same => n,Hangup()
exten => t,1,Playback(vm-goodbye)
 same => n,Set(TIMEOUT_ATTEMPTS=$[${TIMEOUT_ATTEMPTS}+1])
 same => n,GotoIf($[${TIMEOUT_ATTEMPTS}<3]?s,start)
 same => n,Queue(soporte,tT,,,300)
 same => n,Hangup()
```

Para publicarlo, crea una ruta entrante con tipo de destino **IVR** y destino `700` (ver [Rutas y dialplan](./rutas-y-dialplan.md)). Al guardar el IVR se regenera el dialplan y se recarga Asterisk automáticamente.

## Buenas prácticas

- Usa un rango de extensiones exclusivo para IVR (por ejemplo 700–799). La extensión propuesta en el formulario (`100`) choca con el rango de agentes.
- Crea primero las colas, extensiones y buzones de destino; el IVR no se guarda si alguno no existe.
- Mantén menús cortos (tres o cuatro opciones) y ofrece siempre una tecla hacia una persona.
- Define como destino de timeout una cola o un buzón, no un anuncio que cuelgue.
- Nombra los audios de forma descriptiva (`custom/ivr-principal-bienvenida`) para encontrarlos en el catálogo.

## Problemas frecuentes

- **Al marcar la extensión del IVR desde un softphone, suena "servicio no disponible".** Según el código revisado, el generador no crea una entrada para la extensión del IVR en `[from-internal]`; el IVR solo se alcanza como destino de rutas entrantes y de otros IVR.
- **No se escucha el mensaje de opción inválida o de timeout.** El campo tiene un texto en lugar de un nombre de audio.
- **La tecla no responde mientras suena la bienvenida.** `Playback` no admite interrupción; la tecla se captura durante `main-menu` y la espera.
- **"Debes configurar al menos una opción DTMF."** Agrega una tecla en la Sección 3.
- **El audio subido no aparece.** Recarga el catálogo abriendo de nuevo el formulario y revisa el nombre normalizado que devolvió la carga.

## Ver también

- [Rutas y dialplan](./rutas-y-dialplan.md)
- [Colas](./colas.md)
- [Agentes](./agentes.md)
- [Glosario](../general/glosario.md)
- [Arquitectura](../general/arquitectura.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [API: telefonía](../api/telefonia.md)
