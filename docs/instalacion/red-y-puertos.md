# Red y puertos

Este documento reúne todos los puertos que usa VozipCX, cuáles deben quedar expuestos a Internet y cuáles solo en el servidor, cómo configura el firewall `deploy.sh`, cómo instalar detrás de NAT y cómo funcionan `KAMAILIO_TRUST_LAN` y el servidor TURN. Los datos salen de `docker-compose.prod.yml`, `deploy.sh`, `docker/kamailio/kamailio.cfg`, `docker/asterisk/configs/` y `docker/rtpengine/`.

## Puertos por servicio

Los servicios de voz, nginx, frontend, marcador, `websocket_server`, Prometheus y Grafana usan `network_mode: host`: escuchan directo en las interfaces del servidor. PostgreSQL, Redis, backend y Daphne publican sus puertos solo en `127.0.0.1`.

### Expuestos a Internet (los abre `deploy.sh`)

| Puerto | Protocolo | Servicio | Uso |
|---|---|---|---|
| 22 | tcp | SSH | Administración del servidor. |
| 80 | tcp | nginx | Redirección a HTTPS y `/health`. |
| 443 | tcp | nginx | Web, API, WebSockets (`/ws/`) y SIP sobre WebSocket (`/sip/ws`). |
| 5060 | udp/tcp | Kamailio | SIP. Solo se confía en el propio servidor, Asterisk y (opcional) la LAN; el resto recibe 403 y se banea 1 hora. Los agentes WebRTC no lo usan: entran por 443. |
| 3478 | udp/tcp | coturn | STUN/TURN. |
| 49152-49200 | udp | coturn | Puertos de relay TURN. |
| 10000-23100 | udp | Asterisk / RTPEngine | Rango RTP que abre el firewall. |

### Troncales SIP (no los abre `deploy.sh`)

| Puerto | Protocolo | Servicio | Uso |
|---|---|---|---|
| 5161 | udp | Asterisk `trunk-transport` | Troncales sin NAT (VPS con IP pública, PBX en LAN). |
| 5162 | udp | Asterisk `trunk-nat-transport` | Troncales cuando el servidor está detrás de NAT. |

Si el proveedor le envía llamadas sin que Asterisk se registre primero (autenticación por IP), abra el puerto que use la troncal solo para las IP del proveedor, por ejemplo `sudo ufw allow from <IP_PROVEEDOR> to any port 5161 proto udp`.

### Rangos de medios

| Rango | Servicio | Fuente |
|---|---|---|
| 10000-10300/udp | Asterisk RTP (lado troncal) | `docker/asterisk/configs/rtp.conf` |
| 23000-23300/udp | RTPEngine (lado navegador) | `docker/rtpengine/entrypoint.sh` y `rtpengine.conf` |

El firewall de `deploy.sh` abre 10000-23100/udp, así que los puertos 23101-23300 de RTPEngine quedan fuera. Si ve llamadas sin audio con muchas sesiones simultáneas, abra el rango completo: `sudo ufw allow 23000:23300/udp`.

### Solo locales (no exponer)

| Puerto | Escucha | Servicio | Nota |
|---|---|---|---|
| 8000 | 127.0.0.1 | backend (Gunicorn) | Incluye `/metrics` para Prometheus. |
| 8001 | 127.0.0.1 | Daphne | WebSockets de Channels detrás de `/ws/`. |
| 3000 | 0.0.0.0 | frontend Nuxt | Detrás de nginx; el firewall no lo abre. |
| 8080 | 127.0.0.1 | Kamailio WebSocket | Solo nginx puede abrir el WebSocket. |
| 22222 | 127.0.0.1 | RTPEngine (control ng) | Lo usa Kamailio. |
| 5080 | 0.0.0.0 udp/tcp | Asterisk | SIP interno desde Kamailio. |
| 5038 | 0.0.0.0 | Asterisk AMI | `manager.conf` solo permite `127.0.0.1`, `ASTERISK_AMI_PERMIT_NETWORK` y la IP del servidor. El firewall lo bloquea. |
| 8088 / 8089 | 0.0.0.0 | Asterisk HTTP / WSS | nginx usa 8089 para `/asterisk/ws`. |
| 5432 | 127.0.0.1 | PostgreSQL | |
| 6379 | 127.0.0.1 | Redis | |
| 8765 | 0.0.0.0 | `websocket_server` | nginx no lo publica. |
| 9090 | 127.0.0.1 | Prometheus | |
| 3001 | 127.0.0.1 | Grafana | Acceda con un túnel SSH: `ssh -L 3001:127.0.0.1:3001 <usuario>@<IP_DEL_SERVIDOR>`. |

El TLS de Kamailio (5061) está deshabilitado: nginx termina TLS para WSS. `deploy.sh` elimina reglas antiguas de 8080/tcp y 5061/tcp. El mensaje final del script menciona `http://<IP>:8000/metrics`, pero ese puerto solo escucha en `127.0.0.1`.

## Firewall que configura `deploy.sh`

El script detecta la herramienta en este orden y usa la primera disponible.

| Herramienta | Qué hace |
|---|---|
| ufw | `allow` de los puertos públicos, RTP y relay TURN; `delete allow` de 8080/tcp y 5061/tcp; `deny` de 5432, 6379 y 5038/tcp; `ufw --force enable`. |
| firewalld | `--permanent --add-port` de los puertos públicos y rangos (con guion), `--remove-port` de 8080/tcp y 5061/tcp, `--reload`. |
| iptables | Agrega `ACCEPT` para loopback, conexiones establecidas y los puertos públicos; `DROP` de 5432, 6379 y 5038 si no vienen de `127.0.0.1`; guarda con `netfilter-persistent` o `iptables-save`. No cambia la política por defecto de `INPUT`. |
| ninguna | Muestra una advertencia: configure el firewall a mano. |

Precauciones:

- ufw se activa con `--force`. Si su SSH no está en el puerto 22, agregue la regla antes de instalar o perderá el acceso.
- Con iptables, los puertos no listados siguen abiertos si la política de `INPUT` es `ACCEPT`. Revísela.
- En modo `--update` solo se abren los puertos TURN (3478 y 49152-49200/udp).
- Si el servidor está en una nube (AWS, Azure, GCP, etc.), replique las reglas en el grupo de seguridad del proveedor.

`deploy.sh` también instala fail2ban con una jaula `asterisk-ami` (puerto 5038, 3 intentos en 10 minutos, bloqueo de 1 hora). Las rutas de log de esa jaula (`/var/log/asterisk/messages` y `/opt/vozipomni/logs/asterisk/*.log`) no coinciden con el volumen `asterisk_logs` que usa compose, así que no se verificó que detecte intentos. El AMI queda protegido por el firewall y por la lista `permit` de `manager.conf`.

Verificación:

```bash
sudo ufw status verbose            # o: sudo firewall-cmd --list-all
sudo ss -tulpn | grep -E ':(80|443|5060|5080|5161|5162|5038|3478|8080|22222)\b'
```

## Servidor detrás de NAT

Instale con la IP privada de la NIC y la IP pública del router:

```bash
sudo bash deploy.sh <IP_PRIVADA> --nat <IP_PUBLICA>
```

Efecto de `NAT_IPV4`:

| Componente | Comportamiento |
|---|---|
| Asterisk | El entrypoint inyecta `external_media_address` y `external_signaling_address` con la IP pública en `trunk-nat-transport` (5162). `local_net` incluye 10/8, 172.16/12, 192.168/16 y 100.64/10. Use troncales de tipo NAT. |
| RTPEngine | `interface=<IP_PRIVADA>!<IP_PUBLICA>`: escucha en la privada y anuncia la pública en el SDP hacia el navegador. |
| coturn | `--external-ip=<IP_PUBLICA>/<IP_PRIVADA>`. |
| Kamailio | Anuncia `VOZIPOMNI_IPV4`. Los agentes entran por WebSocket a través de nginx, así que no necesita la IP pública. |

En el router, reenvíe hacia la IP privada del servidor:

- 443/tcp y 80/tcp.
- 3478 udp/tcp y 49152-49200/udp (TURN).
- 23000-23300/udp (audio WebRTC con RTPEngine).
- 10000-10300/udp y 5162/udp si el proveedor SIP llega desde Internet.
- 5060 solo si usará teléfonos SIP externos.

Para agregar o cambiar la IP pública en una instalación existente: `sudo bash deploy.sh --update <IP_PRIVADA> --nat <IP_PUBLICA>`.

## `KAMAILIO_TRUST_LAN`

Por defecto (`0`) Kamailio solo confía en `127.0.0.1` (nginx), la IP del servidor y Asterisk. Con `1` también confía en orígenes RFC1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), lo que permite registrar teléfonos IP de la red local y hacer llamadas desde ellos.

Kamailio guarda los registros sin pedir usuario y contraseña; el control de acceso de los agentes WebRTC es el ticket que valida nginx. Con `KAMAILIO_TRUST_LAN=1` cualquier equipo de la LAN puede registrarse y marcar, así que actívelo solo en redes confiables y segmentadas, y mantenga la política antifraude activa.

Para activarlo, cambie la variable en `/opt/vozipomni/.env` y recree el contenedor:

```bash
cd /opt/vozipomni
sudo sed -i 's/^KAMAILIO_TRUST_LAN=.*/KAMAILIO_TRUST_LAN=1/' .env
sudo docker compose -f docker-compose.prod.yml up -d kamailio
sudo docker compose -f docker-compose.prod.yml logs kamailio | grep TRUST_LAN
```

## TURN (coturn)

- Escucha en `TURN_PORT` (3478) por UDP y TCP y retransmite por 49152-49200/udp. No hay listener TLS (`turns:`).
- Usa `--use-auth-secret` con `TURN_SECRET`: el backend entrega en `/api/telephony/webrtc-credentials/` un usuario `<expiración>:<id_usuario>` y una clave HMAC-SHA1 que vence a las 12 horas. El softphone las renueva cada 30 minutos.
- Solo retransmite hacia `VOZIPOMNI_IPV4` (`--allowed-peer-ip`) y bloquea loopback y redes privadas, así que no funciona como relay abierto.
- Cuotas: 12 asignaciones por usuario y 1200 en total.
- El host anunciado es `TURN_HOST`, o el host de `PUBLIC_BASE_URL`, o el host con el que se abrió la web.

Si un agente conecta la llamada pero no tiene audio, revise que su red permita UDP saliente o, como mínimo, TCP al 3478 del servidor. Ver [Depuración VoIP](../operacion/depuracion-voip.md).

## Ver también

- [Requisitos](requisitos.md)
- [Instalación](instalacion.md)
- [Variables de entorno](variables-entorno.md)
- [SSL y HTTPS](ssl-https.md)
- [Arquitectura](../general/arquitectura.md)
- [Troncales SIP](../administracion/troncales-sip.md)
- [Seguridad y antifraude](../administracion/seguridad-antifraude.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
