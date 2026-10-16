# Requisitos de instalación

Este documento lista lo que necesita el servidor antes de instalar VozipOmni en producción: hardware, sistema operativo, software, red y, de forma opcional, un dominio. Los mínimos y las distribuciones soportadas salen de `deploy.sh`, `prepare-system.sh`, `install.sh` y de los límites de recursos de `docker-compose.prod.yml`.

## Hardware

### Mínimos que validan los scripts

| Recurso | Mínimo | Fuente |
|---|---|---|
| RAM | 4 GB (advertencia si hay menos) | `prepare-system.sh`, `install.sh` |
| CPU | 2 núcleos (advertencia si hay menos) | `prepare-system.sh`, `install.sh` |
| Disco libre en `/` | 20 GB (advertencia) / 40 GB (`install.sh` aborta con menos) | `prepare-system.sh`, `install.sh` |
| Swap | 2 GB recomendado | `prepare-system.sh` |

`deploy.sh` no valida recursos; conviene revisar estos mínimos antes de ejecutarlo.

### Recursos reservados y límites en Docker

`docker-compose.prod.yml` define reservas y límites por servicio. Sumados:

| Concepto | Memoria | CPU |
|---|---|---|
| Reservas (lo que se garantiza a los contenedores) | aprox. 3,3 GB | aprox. 2,2 vCPU |
| Límites máximos (si todos llegan al tope) | aprox. 14 GB | aprox. 16 vCPU |

Los servicios más grandes son Asterisk (límite 4 GB / 4 CPU), PostgreSQL y backend (2 GB / 2 CPU cada uno) y el worker de Celery (1 GB / 2 CPU).

### Dimensionamiento orientativo por concurrencia

El repositorio no incluye pruebas de carga, así que esta tabla es una estimación inicial que conviene validar con su propio tráfico:

| Escenario | Agentes simultáneos | vCPU | RAM | Disco |
|---|---|---|---|---|
| Pruebas o piloto | hasta 10 | 4 | 8 GB | 50 GB SSD |
| Operación pequeña | 10 a 30 | 8 | 16 GB | 100 GB SSD + grabaciones |
| Operación mediana | 30 a 80 | 16 | 32 GB | 200 GB SSD + grabaciones |

Límites de la configuración actual que conviene tener presentes:

- RTPEngine usa 23000-23300/udp; el propio `rtpengine.conf` indica que ese rango alcanza para unas 150 llamadas simultáneas.
- Asterisk usa 10000-10300/udp para RTP (`rtp.conf`).
- Crecer por encima de esos valores requiere ampliar los rangos de puertos y el firewall. Todo corre en un solo host.

### Almacenamiento de grabaciones

Las grabaciones se guardan en WAV (MixMonitor). Con G.711 a 8 kHz y 16 bits, calcule aproximadamente 1 MB por minuto grabado (unos 57 MB por hora). Por defecto la tarea de retención archiva a los 90 días (`RECORDING_ARCHIVE_DAYS`) y elimina el archivo a los 180 (`RECORDING_DELETE_DAYS`). Ver [Grabaciones y calidad](../administracion/grabaciones-y-calidad.md).

## Sistema operativo

Se requiere Linux x86_64 con systemd y acceso root (o `sudo`). `deploy.sh` detecta la distribución por `/etc/os-release` para instalar Docker:

| Familia | `ID` detectados | Cómo instala Docker |
|---|---|---|
| Debian | `debian` | Repositorio oficial `download.docker.com/linux/debian` |
| Ubuntu y derivados | `ubuntu`, `linuxmint`, `pop` | Repositorio oficial `download.docker.com/linux/ubuntu` |
| RHEL y derivados | `rocky`, `almalinux`, `centos`, `ol`, `rhel` | Repositorio `docker-ce` de CentOS/RHEL con `dnf` |
| Fedora | `fedora` | Repositorio `docker-ce` de Fedora |
| Amazon Linux | `amzn` | `amazon-linux-extras` o `yum install docker` |
| openSUSE / SLES | `opensuse*`, `sles` | `zypper install docker docker-compose` |
| Arch / Manjaro | `arch`, `manjaro` | `pacman -S docker docker-compose` |
| Alpine | `alpine` | `apk add docker docker-compose` |
| Otras | según `ID_LIKE` (`rhel`/`centos`/`fedora` o `debian`/`ubuntu`) | Repositorio de CentOS o de Ubuntu |

Recomendación: use Ubuntu LTS, Debian o Rocky/AlmaLinux, que instalan Docker CE con el plugin `docker compose` desde el repositorio oficial. Las demás ramas usan paquetes de la distribución y no se han verificado para esta documentación.

Cambios que hace el instalador sobre el sistema:

- Parámetros de kernel en `/etc/sysctl.d/10-vozipomni.conf` (buffers de red, `ip_forward`, `somaxconn`, `swappiness`, etc.) y límites de archivos en `/etc/security/limits.d/99-vozipomni.conf`.
- SELinux pasa a modo `permissive` si estaba en `enforcing`.
- Crea `/etc/docker/daemon.json` (rotación de logs, `overlay2`, `live-restore`) solo si no existe.
- Activa el firewall disponible (ufw, firewalld o iptables) e instala fail2ban para el AMI.

## Software

| Software | Requisito | Notas |
|---|---|---|
| Docker Engine | Lo instala `deploy.sh` si falta | Debe quedar funcionando (`docker info`). |
| Docker Compose | Plugin `docker compose` o `docker-compose` | Si no hay ninguno, `deploy.sh` descarga el binario standalone desde GitHub. |
| git | Necesario | `deploy.sh` clona el repositorio con `git clone` pero no instala git; instálelo antes si su imagen no lo trae. |
| curl, openssl | Necesarios | Para descargar el script, generar secretos y certificados. |
| python3 | Opcional | Solo como alternativa para generar `FIELD_ENCRYPTION_KEY` si falla dentro del contenedor. |

La primera construcción compila Asterisk 21 desde el código fuente (etiqueta `21.12.3`) y construye todas las imágenes, así que tarda varios minutos y necesita salida a Internet.

## Red

- IP fija en el servidor. `deploy.sh` exige la IP como argumento (`VOZIPOMNI_IPV4`); se usa en `ALLOWED_HOSTS`, en los certificados autofirmados, en Kamailio, Asterisk, RTPEngine y coturn. Si la IP cambia hay que volver a ejecutar el despliegue.
- Servidor detrás de NAT: pase la IP privada como IP del servidor y la pública con `--nat <IP_PUBLICA>`. El router debe reenviar al servidor los puertos públicos (80, 443, 5060, 3478, 49152-49200/udp y los rangos RTP).
- Puertos abiertos hacia Internet: 22, 80 y 443/tcp; 5060 tcp/udp; 3478 tcp/udp; 49152-49200/udp (relay TURN); RTP 10000-23100/udp según el firewall que configura `deploy.sh`. Las troncales usan 5161/5162 udp. La tabla completa está en [Red y puertos](red-y-puertos.md).
- Salida a Internet desde el servidor: GitHub (código y Compose), Docker Hub y `download.docker.com` (imágenes y paquetes), los proveedores SIP, y `graph.facebook.com` si usa WhatsApp, Messenger o Instagram.
- Los navegadores de los agentes usan STUN de Google (`stun.l.google.com:19302`) y deben alcanzar el servidor por 443/tcp, 3478 y los puertos UDP de medios.

## Dominio y DNS (opcional)

El sistema funciona con la IP del servidor y un certificado autofirmado, pero cada agente debe aceptar la advertencia del navegador. Un dominio con registro DNS `A` hacia la IP pública es necesario si quiere:

- Un certificado de confianza (Let's Encrypt u otra CA). Ver [SSL y HTTPS](ssl-https.md).
- Webhooks de Meta (WhatsApp, Messenger, Instagram): `PUBLIC_BASE_URL` debe ser HTTPS con certificado válido en un dominio público.
- Enlaces correctos en correos de recuperación de contraseña (`FRONTEND_URL`).

## Puestos de agente

- Navegador actual con soporte WebRTC y permiso de micrófono. El acceso debe ser por HTTPS; sin HTTPS el navegador no entrega el micrófono (salvo en `localhost`).
- Diadema USB o con cancelación de ruido.
- Red con UDP saliente permitido; si la red del agente bloquea UDP, el audio usará TURN.

## Ver también

- [Instalación](instalacion.md)
- [Red y puertos](red-y-puertos.md)
- [SSL y HTTPS](ssl-https.md)
- [Variables de entorno](variables-entorno.md)
- [Arquitectura](../general/arquitectura.md)
- [Servicios Docker](../operacion/servicios-docker.md)
