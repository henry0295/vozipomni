# VozipCX Contact Center

Plataforma de Contact Center omnicanal basada en Django REST Framework, Nuxt 3, Asterisk, Kamailio y RTPEngine. Incluye marcadores predictivo, progresivo y call blasting, consola de agente WebRTC, IVR, colas ACD, grabaciones, mensajería (WhatsApp, email, chat web) y reportería en tiempo real.

## Contenido

- [Características](#características)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
  - [Con dominio (Let's Encrypt)](#con-dominio-lets-encrypt)
  - [Sin dominio (on-premise / IP)](#sin-dominio-on-premise--ip)
  - [Servidor detrás de NAT](#servidor-detrás-de-nat)
- [Opciones de deploy.sh](#opciones-de-deploysh)
- [Actualizar, reinstalar y cambiar el dominio](#actualizar-reinstalar-y-cambiar-el-dominio)
- [Después de instalar](#después-de-instalar)
- [Operación](#operación)
- [Solución de problemas](#solución-de-problemas)
- [Desarrollo local](#desarrollo-local)
- [Documentación](#documentación)

---

## Características

- **Campañas** entrantes, salientes, manuales y preview; marcador predictivo, progresivo y call blasting.
- **Consola de agente** web con softphone WebRTC (JsSIP), sin instalar nada en el PC.
- **Telefonía**: troncales SIP (PJSIP), extensiones, rutas entrantes/salientes, IVR, colas ACD, buzón de voz, condiciones horarias y música en espera.
- **Grabaciones** y evaluación de calidad.
- **Omnicanal**: WhatsApp Cloud API, email, chat web y Messenger/Instagram.
- **Reportes** en PDF, Excel, CSV y JSON, con programación automática.
- **Roles**: administrador, supervisor, agente y analista.
- **API REST** documentada con Swagger (`/api/docs/`) y eventos en tiempo real por WebSocket.
- **Seguridad**: HTTPS automático, firewall, fail2ban, servicios internos solo en `127.0.0.1` y política antifraude para llamadas salientes.

| Capa | Tecnología |
|------|-----------|
| Frontend | Nuxt 3, Vue 3, Nuxt UI, Pinia, JsSIP |
| Backend | Django 4.2, Django REST Framework, Channels, Celery |
| Datos | PostgreSQL 14, Redis 7 |
| Telefonía | Asterisk (PJSIP), Kamailio, RTPEngine, coturn |
| Infraestructura | Docker Compose, Nginx, Prometheus, Grafana |

---

## Requisitos

| Recurso | Mínimo | Recomendado (producción) |
|---------|--------|--------------------------|
| CPU | 2 núcleos | 4 núcleos |
| RAM | 4 GB | 8 GB |
| Disco | 40 GB | 100 GB |

- **Sistema operativo**: Linux con acceso root. Probado en Rocky Linux 9; soporta AlmaLinux, RHEL, CentOS, Fedora, Amazon Linux, Ubuntu, Debian y openSUSE. Funciona sobre imágenes mínimas: `deploy.sh` instala por sí mismo git, curl, Docker y todo lo necesario.
- **Puertos de entrada** (abrirlos también en el Security Group / firewall externo si lo hay):

| Puerto | Protocolo | Uso |
|--------|-----------|-----|
| 22 | TCP | SSH |
| 80, 443 | TCP | Web (HTTP redirige a HTTPS). El 80 es obligatorio para Let's Encrypt |
| 5060 | UDP/TCP | SIP (Kamailio) |
| 3478 | UDP/TCP | TURN (coturn) |
| 49152-49200 | UDP | Relay TURN |
| 10000-23100 | UDP | Audio RTP |

PostgreSQL, Redis, AMI y el backend escuchan solo en `127.0.0.1`; `deploy.sh` bloquea su acceso externo.

---

## Instalación

Todo se hace con un único script, `deploy.sh`. Descárguelo en el servidor y ejecútelo como root:

```bash
curl -fsSL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh -o deploy.sh
```

El script instala dependencias y Docker, clona el proyecto en `/opt/vozipomni`, genera credenciales aleatorias, configura firewall, fail2ban y HTTPS, construye las imágenes y levanta todos los servicios. La primera instalación tarda entre 10 y 20 minutos.

### Con dominio (Let's Encrypt)

Use esta opción si el servidor tiene un dominio público. El navegador no mostrará advertencias de seguridad y el softphone WebRTC funciona sin aceptar certificados.

**1. Antes de instalar**

- Cree un registro DNS **tipo A** que apunte el dominio a la IP pública del servidor (en AWS use una Elastic IP para que no cambie al reiniciar).
- Verifique que el DNS ya resuelve: `getent hosts pbx.ejemplo.com` debe devolver la IP pública.
- Abra el puerto **80/TCP** desde Internet: Let's Encrypt lo usa para validar el dominio.

**2. Instalar**

```bash
sudo bash deploy.sh <IP_DEL_SERVIDOR> --domain pbx.ejemplo.com --email admin@ejemplo.com
```

Ejemplo en AWS (la IP es la privada de la instancia y `--nat` la pública):

```bash
sudo bash deploy.sh 10.21.0.36 --nat 3.227.243.29 --domain pbx.ejemplo.com --email admin@ejemplo.com
```

**Qué hace el script con el dominio**

1. Comprueba que el dominio resuelve a la IP pública del servidor.
2. Instala certbot y obtiene el certificado de Let's Encrypt.
3. Lo instala en nginx y agrega el dominio a `ALLOWED_HOSTS` y CORS.
4. Guarda el dominio en `/opt/vozipomni/.env`: no hace falta repetir `--domain` en futuras ejecuciones ni en `--update`.
5. Programa la **renovación automática** (cada certificado dura 90 días). La renovación usa la propia web de nginx (webroot), así que **no detiene el servicio ni corta llamadas**.

`--email` es opcional pero recomendado: Let's Encrypt avisa ahí si un certificado está por vencer.

**Si algo falla con el dominio** (DNS mal configurado, puerto 80 cerrado, sin salida a Internet), la instalación **no se detiene**: muestra una advertencia y continúa con un certificado autofirmado para la IP. Corrija la causa y vuelva a ejecutar el mismo comando.

Acceso: `https://pbx.ejemplo.com`

### Sin dominio (on-premise / IP)

Para instalaciones en red local o sin dominio público. Se genera un certificado **autofirmado** para la IP.

```bash
sudo bash deploy.sh 192.168.1.50
```

Acceso: `https://192.168.1.50`. El navegador mostrará una advertencia de seguridad la primera vez: pulse **Avanzado → Continuar**. Cada usuario debe aceptarla una vez para que el softphone WebRTC funcione.

### Servidor detrás de NAT

Si la IP de la tarjeta de red no es la IP pública (AWS, Azure, router con port forwarding), indique ambas:

```bash
sudo bash deploy.sh <IP_PRIVADA> --nat <IP_PUBLICA>
```

Sin `--nat` el audio de las llamadas puede llegar en una sola dirección.

---

## Opciones de deploy.sh

```
sudo bash deploy.sh [--clean|--update] <IP> [--nat <IP_PUBLICA>] [--domain <DOMINIO> [--email <EMAIL>]]
```

| Opción | Descripción |
|--------|-------------|
| `<IP>` | IP del servidor (de la tarjeta de red). **Requerida** |
| `--nat IP` | IP pública cuando el servidor está detrás de NAT |
| `--domain FQDN` | Dominio público: obtiene certificado Let's Encrypt. Opcional |
| `--domain none` | Quita el dominio guardado y vuelve al certificado autofirmado |
| `--email EMAIL` | Email para avisos de Let's Encrypt. Opcional |
| `--update` | Actualiza el código y reconstruye sin borrar datos |
| `--clean` | Borra la instalación completa (base de datos, grabaciones, credenciales) y reinstala |
| `--help` | Muestra la ayuda |

También se aceptan como variables de entorno: `VOZIPOMNI_IPV4`, `NAT_IPV4`, `VOZIPOMNI_DOMAIN`, `LETSENCRYPT_EMAIL`, `TZ` (por defecto `America/Bogota`), `INSTALL_DIR` (por defecto `/opt/vozipomni`) y `BRANCH` (por defecto `main`).

---

## Actualizar, reinstalar y cambiar el dominio

```bash
cd /opt/vozipomni

# Actualizar a la última versión (conserva datos, credenciales y dominio)
sudo bash deploy.sh --update <IP>

# Agregar o cambiar el dominio en una instalación existente
sudo bash deploy.sh --update <IP> --domain nuevo.ejemplo.com --email admin@ejemplo.com

# Quitar el dominio (vuelve al certificado autofirmado)
sudo bash deploy.sh --update <IP> --domain none

# Reinstalar desde cero (⚠️ BORRA base de datos, grabaciones y credenciales)
sudo bash deploy.sh --clean <IP>
```

Al cambiar o quitar el dominio, el certificado del dominio anterior se elimina para que la renovación automática no siga intentando renovarlo.

---

## Después de instalar

Las credenciales quedan en `/opt/vozipomni/credentials.txt` (solo root):

```bash
sudo cat /opt/vozipomni/credentials.txt
```

- Usuario web: `admin` con la contraseña generada. Cámbiela en el primer ingreso.
- `/opt/vozipomni/.env` contiene todos los secretos (base de datos, Redis, AMI, claves de cifrado). No lo comparta ni lo suba al repositorio.

| URL | Uso |
|-----|-----|
| `https://<dominio o IP>` | Aplicación |
| `https://<dominio o IP>/admin` | Admin de Django |
| `https://<dominio o IP>/api/docs/` | Documentación de la API |

Primeros pasos recomendados: configurar una troncal SIP, crear agentes y colas, revisar la política antifraude y programar respaldos. La guía completa está en [docs/instalacion/instalacion.md](docs/instalacion/instalacion.md).

---

## Operación

```bash
cd /opt/vozipomni

docker compose -f docker-compose.prod.yml ps                 # estado de los servicios
docker compose -f docker-compose.prod.yml logs -f backend    # logs de un servicio
docker compose -f docker-compose.prod.yml restart backend    # reiniciar un servicio
docker compose -f docker-compose.prod.yml exec asterisk asterisk -rvvv   # consola de Asterisk

sudo certbot certificates                                    # estado del certificado (con dominio)
```

Scripts de apoyo incluidos:

| Script | Uso |
|--------|-----|
| `backup-production.sh` | Respaldo de base de datos y archivos ([Respaldos](docs/operacion/respaldos.md)) |
| `fix-db-password.sh` | Resincroniza la contraseña de PostgreSQL con `.env` |
| `voip-debug.sh` | Diagnóstico SIP/RTP ([Depuración VoIP](docs/operacion/depuracion-voip.md)) |

---

## Solución de problemas

**El certificado de Let's Encrypt no se obtuvo.** El script muestra la causa. Verifique que `getent hosts <dominio>` devuelva la IP pública, que el puerto 80/TCP esté abierto desde Internet y vuelva a ejecutar `sudo bash deploy.sh --update <IP>`.

**Error `password authentication failed` en el backend.** El volumen de PostgreSQL es de una instalación anterior con otra contraseña. Ejecute `cd /opt/vozipomni && sudo bash fix-db-password.sh`, o en un servidor de pruebas reinstale con `--clean`.

**Un servicio queda `unhealthy`.** Revise sus logs con `docker compose -f docker-compose.prod.yml logs <servicio>`.

**Audio en una sola dirección.** Normalmente falta `--nat <IP_PUBLICA>` o los puertos UDP 10000-23100 están cerrados en el firewall externo.

**Las troncales SIP no registran.**

```bash
docker compose -f docker-compose.prod.yml exec asterisk asterisk -rx "pjsip show registrations"
```

Más casos en [docs/operacion/solucion-de-problemas.md](docs/operacion/solucion-de-problemas.md).

---

## Desarrollo local

```bash
git clone https://github.com/henry0295/vozipomni.git
cd vozipomni
cp env.template .env
docker compose up -d
docker compose exec backend python manage.py createsuperuser
```

La aplicación queda en `http://localhost`. Detalles en [docs/desarrollo/entorno-local.md](docs/desarrollo/entorno-local.md).

---

## Documentación

La documentación completa está en [`docs/`](docs/README.md):

- [Instalación](docs/instalacion/instalacion.md), [requisitos](docs/instalacion/requisitos.md), [red y puertos](docs/instalacion/red-y-puertos.md), [SSL/HTTPS](docs/instalacion/ssl-https.md) y [actualización](docs/instalacion/actualizacion.md)
- [Administración](docs/administracion/): troncales, rutas, IVR, colas, campañas, agentes y usuarios
- [Manuales](docs/manuales/) para agente, supervisor y analista
- [Operación](docs/operacion/): monitoreo, respaldos, mantenimiento y depuración VoIP
- [API](docs/api/README.md) y [desarrollo](docs/desarrollo/)

---

Desarrollado por **VOZIP Colombia** · soporte@vozip.com
