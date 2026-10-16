# Glosario

Este glosario reúne los términos de telefonía y de contact center que aparecen en la interfaz y en la documentación de VozipCX, y las fórmulas exactas de los indicadores (KPIs) tal como las calcula `backend/apps/reports/analytics.py`. Úselo como referencia cuando un reporte muestre un valor que no esperaba.

## Telefonía

| Término | Significado en VozipCX |
|---|---|
| SIP | Protocolo de señalización de voz sobre IP. Establece, modifica y termina las llamadas. |
| PJSIP | Pila SIP de Asterisk (`chan_pjsip`). Los agentes, Kamailio y las troncales se definen como endpoints PJSIP. |
| PJSIP Wizard | Formato abreviado de Asterisk (`type=wizard`) con el que el backend genera las troncales en `pjsip_wizard.conf`. |
| Troncal SIP | Conexión con un proveedor de telefonía o una PBX. En VozipCX llega directo a Asterisk por el puerto 5161 (sin NAT) o 5162 (con NAT). |
| DID | Número telefónico entrante. Cada ruta entrante asocia un DID a un destino (extensión, cola, IVR o buzón) en el contexto `from-pstn`. |
| Ruta saliente | Patrón de marcación (por ejemplo `_3XXXXXXXXX`) que decide por qué troncal sale una llamada y cómo se transforma el número (prefijo, dígitos antepuestos, prefijo de caller ID). |
| Dialplan | Lógica de enrutamiento de Asterisk (`extensions.conf` y `extensions_dynamic.conf`), organizada en contextos como `from-internal`, `from-pstn`, `outbound-queue` y `from-spy`. |
| Extensión | Número interno de un agente o recurso. Kamailio trata como extensión cualquier número de 6 dígitos o menos. |
| AMI | Asterisk Manager Interface, puerto TCP 5038. El backend, el listener de eventos y el marcador la usan para originar llamadas, recargar configuración y recibir eventos. No debe exponerse a Internet. |
| CDR | Registro de detalle de la llamada. Asterisk lo emite por AMI al finalizar y el listener lo convierte en un registro `Call`. |
| WebRTC | Tecnología del navegador para audio en tiempo real. El softphone de VozipCX (JsSIP) la usa; exige HTTPS para acceder al micrófono. |
| WSS | WebSocket sobre TLS. El softphone envía SIP por `wss://<servidor>/sip/ws`. |
| STUN | Protocolo para que el navegador descubra su IP pública. Se usan `stun.l.google.com:19302` y `stun1.l.google.com:19302`. |
| TURN | Retransmisión de audio cuando no hay conexión directa (NAT o firewall estricto). Lo presta coturn en el puerto 3478 con credenciales temporales firmadas por el backend. |
| ICE | Mecanismo con el que navegador y RTPEngine eligen la mejor ruta de audio a partir de candidatos STUN/TURN. |
| DTLS-SRTP | Cifrado del audio WebRTC. RTPEngine lo termina y entrega RTP plano a Asterisk. |
| RTP | Protocolo que transporta el audio. Asterisk usa 10000-10300/udp y RTPEngine 23000-23300/udp. |
| RTPEngine | Proxy de medios que traduce entre WebRTC (SRTP, ICE, DTLS) y RTP plano. |
| Kamailio | Proxy SIP que recibe a los agentes WebRTC, guarda su registro y relaciona sus llamadas con Asterisk. |
| NAT | Traducción de direcciones. Si el servidor tiene IP privada, se instala con `--nat <IP_PUBLICA>` para que Asterisk, RTPEngine y coturn anuncien la IP pública. |
| G.711 (PCMU/PCMA) | Códecs de audio usados entre navegador, Asterisk y troncales. OPUS se elimina del SDP. |
| DTMF | Tonos de teclado. Las troncales usan `rfc4733`. |
| Cola ACD | Distribución automática de llamadas: Asterisk (`Queue()`) reparte las llamadas en espera entre los agentes miembros según la estrategia de la cola. |
| IVR | Menú de voz interactivo que dirige al llamante según el dígito marcado. |
| AMD | Detección de contestador automático (`AMD()` de Asterisk) en el marcador predictivo. Resultados: `HUMAN`, `MACHINE`, `NOTSURE`, `HANGUP`; `SKIPPED` si no está activo. |
| Marcador predictivo | Llama a varios contactos por agente disponible y pasa a la cola solo las llamadas contestadas por personas. |
| Marcador progresivo | Llama un contacto por cada agente disponible. |
| Preview | El agente ve los datos del contacto y acepta o rechaza antes de que se origine la llamada. |
| ChanSpy | Aplicación de Asterisk para supervisión: escucha (`listen`), susurro (`whisper`) e irrupción (`barge`). |
| MixMonitor | Aplicación de Asterisk que graba las llamadas en WAV en `/var/spool/asterisk/monitor`. |
| Tipificación (disposición) | Resultado que el agente registra al terminar una gestión. Puede marcarse como exitosa o como que requiere callback. |
| DNC | Lista negra de números que no se deben llamar. |

## KPIs de llamadas

Convenciones del código:

- Llamada contestada: `status = 'completed'`. Entrante: `direction = 'inbound'`. Saliente: `direction = 'outbound'`.
- Los porcentajes se redondean a un decimal y valen 0 si el denominador es 0.
- `wait_time` es la espera en segundos; si la llamada pasó por cola se mide desde la entrada a la cola (`QueueCallerJoin`) hasta la contestación.
- Constantes: umbral de nivel de servicio por defecto `DEFAULT_SLA = 20` s; abandono corto `SHORT_ABANDON = 5` s; llamada corta `SHORT_CALL = 10` s.

| KPI | Fórmula |
|---|---|
| Ofrecidas | Cantidad de llamadas entrantes. |
| Nivel de servicio (SL) | Entrantes contestadas con `wait_time ≤ T` / (entrantes − abandonadas con `wait_time < 5`) × 100. `T` es 20 s en el resumen general; en el reporte de colas es el `service_level` de cada cola (o 20 s si no está definido). |
| ASA | Promedio de `wait_time` de las entrantes contestadas. |
| AHT (TMO) | (Σ conversación + Σ retención de las contestadas + tiempo total en post-llamada de los agentes) / contestadas. La tendencia diaria y el reporte de colas usan (conversación + retención) / contestadas, sin post-llamada. |
| Abandono | Llamadas con `status = 'abandoned'` / entrantes × 100. |
| Tasa de contestación | Contestadas / total × 100 (y entrantes contestadas / entrantes para la tasa entrante). |
| Ocupación | Tiempo productivo / (tiempo conectado − pausas) × 100. |
| Utilización | Tiempo productivo / tiempo conectado × 100. |
| FCR estimado | 100 − (llamantes con más de una entrante en el período / llamantes únicos) × 100. Excluye caller ID vacío o `unknown`. |
| Contactabilidad | Salientes contestadas / salientes × 100. En el reporte de campañas: contestadas / llamadas de la campaña. |
| Conversión | Llamadas con tipificación marcada como exitosa / contestadas × 100. |
| Tasa de tipificación | Llamadas con tipificación / contestadas × 100. |
| Tasa de transferencia | Llamadas transferidas / contestadas × 100. |
| Llamadas cortas | Contestadas con conversación menor a 10 s / contestadas × 100. |
| Llamadas por hora de agente | Contestadas / (tiempo conectado en horas). Solo se calcula con al menos 60 s conectados. |

Tiempos de agente usados en ocupación y utilización (de `AgentStatusHistory`):

- Tiempo conectado: suma de todos los estados excepto `offline`.
- Pausas: tiempo en estado `break`.
- Tiempo productivo: el mayor entre (tiempo en `oncall` + `busy`) y (conversación + retención de las contestadas), más el tiempo en `wrapup`.

## Ranking de agentes

El reporte de agentes calcula un puntaje de 0 a 100 como promedio ponderado de: llamadas por hora relativas al mejor agente (peso 0,35), ocupación con tope 100 (0,25), puntaje de calidad promedio si tiene evaluaciones (0,30) y 100 − tasa de transferencia (0,10). Si el agente no tiene evaluaciones, los pesos se normalizan sin ese componente.

## KPIs de chat

Se calculan sobre conversaciones del período (`started_at`), con `CHAT_FRT_TARGET = 300` s.

| KPI | Fórmula |
|---|---|
| Primera respuesta promedio | Promedio de (`first_response_at` − `started_at`) de las conversaciones respondidas. |
| Primera respuesta en meta | Conversaciones con `first_response_at ≤ started_at + 300 s` / conversaciones respondidas × 100. |
| Tasa de respuesta | Conversaciones respondidas / total × 100. |
| Resolución promedio | Promedio de (`closed_at` − `started_at`) de las conversaciones cerradas. |
| Tasa de resolución | Conversaciones cerradas / total × 100. |

## Ver también

- [Introducción](introduccion.md)
- [Arquitectura](arquitectura.md)
- [Reportes (administración)](../administracion/reportes.md)
- [Colas](../administracion/colas.md)
- [Campañas](../administracion/campanas.md)
- [Manual del analista](../manuales/manual-analista.md)
- [API de reportes](../api/reportes.md)
