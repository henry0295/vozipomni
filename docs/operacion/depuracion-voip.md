# Depuración VoIP

Este documento explica cómo capturar y leer tráfico SIP y RTP en VozipOmni: herramientas disponibles en los contenedores, comandos de `voip-debug.sh`, depuración en Asterisk, Kamailio y RTPEngine, cómo es una llamada saliente sana y cómo llevar una captura a Wireshark.

Los comandos asumen la instalación en `/opt/vozipomni`:

```bash
cd /opt/vozipomni
```

## Flujo de una llamada

```
Navegador (WSS) -> Nginx :443 /sip/ws -> Kamailio 127.0.0.1:8080 -> Asterisk :5080 -> Troncal (:5161 / :5162)
Medios: Navegador (SRTP/DTLS) <-> RTPEngine :23000-23300 <-> Asterisk RTP :10000-10300 <-> Proveedor
```

| Puerto | Servicio | Uso |
|---|---|---|
| 5060 udp/tcp | Kamailio | SIP externo |
| 127.0.0.1:8080 | Kamailio | WebSocket SIP detrás de Nginx |
| 5080 udp/tcp | Asterisk | SIP interno desde Kamailio |
| 5161/udp | Asterisk | Troncales sin NAT (`trunk-transport`) |
| 5162/udp | Asterisk | Troncales con NAT (`trunk-nat-transport`) |
| 127.0.0.1:22222/udp | RTPEngine | Control NG desde Kamailio |
| 23000-23300/udp | RTPEngine | Medios hacia el navegador |
| 10000-10300/udp | Asterisk | Medios RTP |
| 3478, 49152-49200/udp | coturn | TURN |

Asterisk, Kamailio y RTPEngine usan `network_mode: host`. Una captura hecha desde cualquiera de esos contenedores ve todas las interfaces del servidor, incluido el tráfico de los otros.

## Herramientas disponibles

Las imágenes de Kamailio y Asterisk incluyen `sngrep`, `tcpdump`, `ngrep`, `iproute2` (`ss`), `netcat`, `dig` y `ping`. La imagen de RTPEngine no instala `tcpdump`; capture el RTP desde el contenedor de Kamailio.

Si las herramientas no están en su instalación (imágenes antiguas), `install-debug-tools.sh` hace `git pull`, detiene Kamailio y Asterisk, los reconstruye con `--no-cache` y los vuelve a iniciar. Corta las llamadas en curso; ejecútelo en una ventana de mantenimiento.

```bash
sudo bash /opt/vozipomni/install-debug-tools.sh
```

## voip-debug.sh

El script entra en `/opt/vozipomni` y usa `docker compose -f docker-compose.prod.yml`.

```bash
bash /opt/vozipomni/voip-debug.sh help
```

| Comando | Qué hace |
|---|---|
| `sngrep` | `sngrep` en Kamailio sobre 5060, 5080, 5161 y 5162 |
| `sngrep-kamailio` | `sngrep` sobre el puerto 5060 |
| `sngrep-asterisk` | `sngrep` en Asterisk sobre el puerto 5080 |
| `sip` | `ngrep -W byline` sobre los puertos SIP |
| `rtp` | `tcpdump` de 23000-23100 en RTPEngine (ver nota) |
| `rtpengine-stats` | `rtpengine-ctl list numsessions`; si falla, muestra logs |
| `rtpengine-sessions` | `rtpengine-ctl list` |
| `calls-active` | `core show calls` |
| `channels` | `core show channels` |
| `pjsip-endpoints` | `pjsip show endpoints` |
| `pjsip-contacts` | `pjsip show contacts` |
| `kamailio-status` | `kamcmd stats.get_statistics all` |
| `kamailio-stats` | `kamcmd core.uptime` |
| `logs <servicio>` | Últimas 100 líneas de un servicio |
| `logs-follow` | Logs de todos los servicios en vivo |
| `network-test` | Kamailio a Asterisk (5080) y RTPEngine (22222), backend a AMI (5038) |
| `port-test` | Estado de los puertos SIP, AMI, RTPEngine, 8080 y 8000 en el host |

Nota: `rtp` ejecuta `tcpdump` dentro de RTPEngine y filtra hasta 23100, pero RTPEngine usa 23000-23300 y su imagen no trae `tcpdump`. Use el comando equivalente de la sección de RTP.

## sngrep

Captura interactiva de SIP con RTP (`-r`):

```bash
docker exec -it vozipomni_kamailio sngrep -d any -r
```

Solo el tramo de troncales:

```bash
docker exec -it vozipomni_kamailio sngrep -d any 'port 5161 or port 5162'
```

Teclas útiles: Enter abre el diagrama de la llamada, F2 guarda, F7 filtra, `q` sale.

Los archivos que guarda `sngrep` (F2 u `-O`) quedan dentro del contenedor, no en el host. Para grabar en archivo directamente:

```bash
docker exec -it vozipomni_kamailio sngrep -d any -O /tmp/captura.pcap 'port 5060 or port 5080 or port 5161 or port 5162'
```

Para listar capturas dentro del contenedor ponga el comando entre comillas; así el `*` se expande en el contenedor y no en el host:

```bash
docker exec vozipomni_kamailio sh -c 'ls -lh /tmp/*.pcap'
```

## tcpdump y ngrep

SIP a archivo, sin interfaz:

```bash
docker exec -it vozipomni_kamailio tcpdump -i any -s 0 -w /tmp/sip.pcap \
  'port 5060 or port 5080 or port 5161 or port 5162'
```

SIP en texto, en vivo:

```bash
docker exec -it vozipomni_kamailio ngrep -W byline -d any port 5060 or port 5080 or port 5161 or port 5162
```

RTP de RTPEngine y de Asterisk:

```bash
docker exec -it vozipomni_kamailio tcpdump -i any -n 'udp portrange 23000-23300'
docker exec -it vozipomni_kamailio tcpdump -i any -n 'udp portrange 10000-10300'
```

RTP de una llamada concreta, filtrando por la IP del proveedor o del agente:

```bash
docker exec -it vozipomni_kamailio tcpdump -i any -n -c 50 'udp and host <IP_REMOTA>'
```

Si ve paquetes salientes pero ninguno entrante, revise firewall y NAT (ver [solución de problemas](solucion-de-problemas.md#audio)).

## Asterisk

Consola interactiva:

```bash
docker exec -it vozipomni_asterisk asterisk -rvvv
```

Dentro de la consola:

```
core set verbose 5
pjsip set logger on
pjsip set logger host <IP_PROVEEDOR>
rtp set debug on
rtp set debug ip <IP_REMOTA>
```

Apague todo al terminar. El logger de PJSIP y el debug de RTP generan mucho volumen y exponen números y cabeceras:

```
pjsip set logger off
rtp set debug off
core set verbose 3
core set debug 0
```

Comandos de estado útiles durante una prueba:

```bash
docker exec vozipomni_asterisk asterisk -rx 'core show channels verbose'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show channels'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show identifies'
docker exec vozipomni_asterisk asterisk -rx 'pjsip show transport trunk-nat-transport'
docker exec vozipomni_asterisk asterisk -rx 'dialplan show from-internal'
```

Asterisk corre con `-f -vvv`. Sus logs de archivo están en el volumen `asterisk_logs`:

```bash
docker exec vozipomni_asterisk ls -lh /var/log/asterisk
docker logs --since 10m vozipomni_asterisk
```

## Kamailio

Kamailio registra en stderr (`log_stderror=yes`, `debug=2`):

```bash
docker logs -f vozipomni_kamailio
docker logs --since 1h vozipomni_kamailio 2>&1 | grep -E 'RTPEngine|location|SECURITY'
```

Mensajes útiles:

- `RTPEngine OFFER failed`: Kamailio no pudo hablar con RTPEngine en 22222.
- `RTPEngine ANSWER (<código> -> browser)`: el SDP de respuesta se procesó.
- `Agente <ext> no encontrado en location`: el agente no está registrado; Kamailio responde 480.
- `SECURITY FLOOD`, `SECURITY SCANNER`, `SECURITY UNTRUSTED`: IP baneada una hora.
- `HTTP request received on <puerto> from <IP>`: intento de WebSocket que no viene de Nginx.

Subir el nivel de log temporalmente y volver al valor del archivo:

```bash
docker exec vozipomni_kamailio kamcmd cfg.set_now_int core debug 3
docker exec vozipomni_kamailio kamcmd cfg.set_now_int core debug 2
```

Estado interno:

```bash
docker exec vozipomni_kamailio kamcmd ul.dump
docker exec vozipomni_kamailio kamcmd htable.dump ipban
docker exec vozipomni_kamailio kamcmd stats.get_statistics all
```

## RTPEngine

```bash
docker logs --tail=100 vozipomni_rtpengine
docker logs vozipomni_rtpengine 2>&1 | grep -E 'NAT detectado|IP directa|Interface|listen-ng'
bash /opt/vozipomni/voip-debug.sh rtpengine-stats
ss -ulnp | grep rtpengine | wc -l
```

El entrypoint arranca RTPEngine en modo userspace (`--table=-1`), con `--interface=<IP_privada>!<IP_publica>` cuando hay NAT y `--log-level=6`. `rtpengine-ctl` puede no responder si la interfaz CLI no está habilitada; en ese caso `voip-debug.sh` muestra los logs. El número de sockets UDP abiertos por `rtpengine` da una idea aproximada de las sesiones activas.

## Cómo leer una traza SIP

Una llamada saliente sana desde un agente WebRTC tiene dos tramos.

Tramo del agente (navegador, Kamailio y Asterisk en 5080):

```
Navegador -> Kamailio      INVITE (SDP WebRTC)
Kamailio  -> Asterisk:5080 INVITE (SDP convertido por RTPEngine a RTP/AVP)
Asterisk  -> Kamailio      100 Trying
Asterisk  -> Kamailio      180 Ringing o 183 Session Progress (con SDP)
Asterisk  -> Kamailio      200 OK (SDP)
Kamailio  -> Navegador     200 OK (SDP convertido a WebRTC)
Navegador -> Kamailio      ACK
Kamailio  -> Asterisk:5080 ACK
... conversación ...
BYE (cualquiera de los dos lados) -> 200 OK
```

Tramo de la troncal (Asterisk en 5161/5162 y proveedor):

```
Asterisk  -> Proveedor INVITE
Proveedor -> Asterisk  401 o 407 (desafío de autenticación, normal)
Asterisk  -> Proveedor ACK
Asterisk  -> Proveedor INVITE (con Authorization)
Proveedor -> Asterisk  100 Trying
Proveedor -> Asterisk  180 / 183
Proveedor -> Asterisk  200 OK
Asterisk  -> Proveedor ACK
... conversación ...
BYE -> 200 OK
```

Qué revisar:

- ACK en ambos tramos. Si el 200 OK se repite varias veces sin ACK y la llamada termina a los 32 segundos con 408 o BYE, el ACK se está perdiendo. En este proyecto se corrigió con `record_route()` y `alias=<IP>:5060` en Kamailio.
- `Record-Route` en el INVITE que Kamailio reenvía, con la IP anunciada del servidor (no `0.0.0.0`).
- SDP del 200 OK de la troncal: `c=` debe traer la IP pública del proveedor. En el INVITE saliente de Asterisk por 5162, `c=` debe ser su IP pública (`external_media_address`).
- 183 con SDP: Kamailio lo pasa por RTPEngine; así se oye el tono de llamada del destino.

Códigos frecuentes:

| Código | Significado habitual en VozipOmni |
|---|---|
| 401 / 407 | Desafío de autenticación. Solo es un problema si se repite tras enviar credenciales |
| 403 | Credenciales rechazadas por el proveedor, o IP baneada o no confiable en Kamailio |
| 404 | Número sin ruta (catch-all de `from-internal`) o destino desconocido |
| 408 | Sin respuesta o ACK perdido |
| 480 | Agente no registrado en Kamailio |
| 486 | Destino ocupado |
| 488 | SDP incompatible; con frecuencia, RTPEngine caído |
| 503 | Proveedor o troncal no disponible |

## Llevar una captura a Wireshark

1. Copie el archivo del contenedor al host:

```bash
docker cp vozipomni_kamailio:/tmp/sip.pcap /tmp/sip.pcap
```

2. Descárguelo a su equipo:

```bash
scp <usuario>@<IP_SERVIDOR>:/tmp/sip.pcap .
```

3. En Wireshark use Telefonía > Llamadas VoIP, Flujo SIP y Flujos RTP para ver el diagrama y reproducir el audio si capturó RTP.

4. Borre las copias al terminar. Las capturas contienen números de teléfono, cabeceras y, si incluyen RTP, el audio de la conversación:

```bash
docker exec vozipomni_kamailio sh -c 'rm -f /tmp/*.pcap'
rm -f /tmp/sip.pcap
```

## Ver también

- [Solución de problemas](solucion-de-problemas.md)
- [Monitoreo](monitoreo.md)
- [Red y puertos](../instalacion/red-y-puertos.md)
- [Troncales SIP](../administracion/troncales-sip.md)
- [Telefonía interna](../desarrollo/telefonia-interna.md)
