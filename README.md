# VoziPOmni Contact Center

![Version](https://img.shields.io/badge/version-2.0.0-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Django](https://img.shields.io/badge/django-4.2.9-green.svg)
![Nuxt](https://img.shields.io/badge/nuxt-3.10-00DC82.svg)
![Vue](https://img.shields.io/badge/vue-3.4-42b883.svg)
![Asterisk](https://img.shields.io/badge/asterisk-PBX-orange.svg)
![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)

Plataforma de Contact Center omnicanal con arquitectura moderna basada en Django REST Framework, Nuxt 3, Asterisk, Kamailio y RTPEngine. Incluye marcadores predictivo, progresivo y call blasting, consola de agente WebRTC, IVR, colas ACD y reportería en tiempo real.

> **v2.0.0** — Despliegue con `network_mode: host` para rendimiento VoIP óptimo, healthchecks en todos los servicios, YAML anchors, resource limits, polling HTTP inteligente y compatibilidad universal con cualquier distribución Linux.

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Stack Tecnológico](#-stack-tecnológico)
- [Arquitectura](#️-arquitectura)
- [Despliegue Rápido (Una Línea)](#-despliegue-rápido-una-línea)
- [Instalación Interactiva](#-instalación-interactiva)
- [Desarrollo Local](#-desarrollo-local)
- [Estructura de Archivos de Despliegue](#-estructura-de-archivos-de-despliegue)
- [Servicios del Sistema](#-servicios-del-sistema)
- [Módulos del Frontend](#-módulos-del-frontend)
- [API REST](#-api-rest)
- [Motor de Discado](#-motor-de-discado)
- [Configuración de Telefonía](#-configuración-de-telefonía)
- [Gestión del Sistema](#-gestión-del-sistema)
- [Credenciales](#-credenciales)
- [Seguridad](#-seguridad)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Contribuir](#-contribuir)

---

## 📋 Características

### Telefonía y Contact Center
- **Campañas**: Entrantes, salientes, manuales y preview
- **Marcadores**: Predictivo (ratio dinámico), progresivo, preview y call blasting
- **Agentes**: Consola web con WebRTC integrado (JsSIP)
- **Colas ACD**: Estrategias ringall, leastrecent, fewestcalls, random, rrmemory, linear
- **IVR**: Menús de voz interactivos configurables
- **Troncales SIP**: PJSIP Wizard con soporte NAT, no-NAT, PBX, corporativo y custom
- **Extensiones**: SIP, PJSIP e IAX2
- **Rutas**: Entrantes (DID) y salientes (patrones de marcado)
- **Grabaciones**: Almacenamiento, notas con timestamps y transcripción
- **Buzón de voz**: Configuración por extensión
- **Condiciones horarias**: Control de flujo por horario
- **Música en espera**: Personalizable por cola

### Plataforma
- **API REST** completa con documentación Swagger (drf-spectacular)
- **WebSocket**: Eventos en tiempo real (aiohttp + Redis PubSub)
- **Reportes**: Generación en PDF, Excel, CSV y JSON con programación automática
- **Roles de usuario**: Admin, Supervisor, Agente y Analista
- **Tareas asíncronas**: Celery con scheduler (celery-beat)
- **Monitoreo**: Sentry SDK integrado

---

## 🛠 Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| **Frontend** | Nuxt 3 + Vue 3 + TypeScript | 3.10 / 3.4 |
| **UI** | Nuxt UI + Tailwind CSS | 2.14 |
| **Estado** | Pinia | 2.1 |
| **WebRTC** | JsSIP | 3.10 |
| **Backend** | Django + Django REST Framework | 4.2.9 |
| **Auth** | SimpleJWT (tokens JWT) | 5.3 |
| **Base de datos** | PostgreSQL | 14 |
| **Cache / Broker** | Redis | 7 |
| **Tareas** | Celery + Celery Beat | 5.3 |
| **PBX** | Asterisk (PJSIP) | — |
| **SIP Proxy** | Kamailio | — |
| **Media Proxy** | RTPEngine | — |
| **WebSocket Server** | aiohttp + Redis PubSub | — |
| **Dialer Engine** | panoramisk (Asterisk AMI) | — |
| **Reverse Proxy** | Nginx | Alpine |
| **Contenedores** | Docker + Docker Compose | — |
| **Docs API** | drf-spectacular (Swagger) | 0.27 |

---

## 🏗️ Arquitectura

```
                    ┌───────────────────┐
                    │   Nginx (Proxy)   │
                    │   Puerto 80/443   │
                    └────────┬──────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐ ┌─────▼─────┐ ┌──────▼──────┐
        │  Nuxt 3   │ │  Django   │ │  WebSocket  │
        │ Frontend  │ │  Backend  │ │   Server    │
        │ (SSR)     │ │  (API)    │ │  (aiohttp)  │
        └───────────┘ └─────┬─────┘ └──────┬──────┘
                            │              │
              ┌─────────────┼──────────────┤
              │             │              │
        ┌─────▼────┐ ┌─────▼─────┐ ┌──────▼──────┐
        │PostgreSQL│ │   Redis   │ │   Celery    │
        │    14    │ │  7 Cache  │ │Worker + Beat│
        └──────────┘ │  Broker   │ └─────────────┘
                     │  PubSub   │
                     └─────┬─────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │ Asterisk  │ │Kamailio│ │ RTPEngine │
        │   PBX     │ │  SIP   │ │   Media   │
        │ (PJSIP)   │ │ Proxy  │ │   Proxy   │
        └─────┬─────┘ └───────┘ └───────────┘
              │
        ┌─────▼──────┐
        │   Dialer   │
        │   Engine   │
        │(panoramisk)│
        └────────────┘
```

### Flujo de producción

1. **Nginx** recibe todo el tráfico (HTTP/HTTPS) y lo enruta al frontend, backend o WebSocket server
2. **Kamailio** actúa como proxy SIP y gateway WebRTC (puertos 5060/5061)
3. **RTPEngine** maneja la transcodificación de media y proxy RTP
4. **Asterisk** procesa la lógica de PBX: colas, IVR, extensiones, grabaciones
5. **Dialer Engine** se conecta via AMI a Asterisk para originar llamadas de campañas
6. **WebSocket Server** escucha eventos de Redis PubSub y los transmite a los clientes en tiempo real

---

## 🚀 Despliegue Rápido (Una Línea)

Para desplegar VoziPOmni en cualquier servidor Linux con un solo comando:

```bash
export VOZIPOMNI_IPV4=X.X.X.X && curl -sL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh | sudo bash
```

> **Reemplaza `X.X.X.X` con la dirección IP de tu servidor.**

O descargando primero el script:

```bash
curl -o deploy.sh -L "https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh"
chmod +x deploy.sh
export VOZIPOMNI_IPV4=X.X.X.X
sudo bash deploy.sh
```

### Variables opcionales

| Variable | Descripción | Default |
|----------|-------------|---------|
| `VOZIPOMNI_IPV4` | IP pública/privada del servidor **(requerido)** | — |
| `NAT_IPV4` | IP pública si el servidor está detrás de NAT | — |
| `TZ` | Zona horaria | `America/Bogota` |
| `INSTALL_DIR` | Directorio de instalación | `/opt/vozipomni` |
| `BRANCH` | Rama Git a desplegar | `main` |

### ¿Qué hace `deploy.sh`?

1. Verifica prerequisitos (root, IP válida)
2. Prepara el sistema operativo (kernel, sysctl, SELinux, límites)
3. Instala Docker CE + Docker Compose (detección universal)
4. Clona el repositorio en `/opt/vozipomni`
5. Genera credenciales seguras (openssl rand)
6. Crea `.env` centralizado con `network_mode: host`
7. Construye e inicia todos los contenedores
8. **Polling HTTP inteligente**: espera hasta 10 min verificando que el backend responda (HTTP 200/301/302/403) en lugar de un sleep fijo
9. Ejecuta migraciones y crea superusuario
10. Guarda credenciales en `credentials.txt`
11. Configura firewall automáticamente (UFW, firewalld)

### Manejo de errores

El script usa `set -Eeuo pipefail` con `trap ERR` para capturar errores. Si algo falla, muestra:
- La línea exacta donde ocurrió el error
- El código de salida
- Sugerencias de resolución

---

## 📦 Instalación Interactiva

Para una instalación guiada con menú interactivo:

```bash
curl -o install.sh -L "https://raw.githubusercontent.com/VOZIP/vozipomni/main/install.sh"
chmod +x install.sh
sudo bash install.sh
```

El menú ofrece:

| Opción | Descripción |
|--------|-------------|
| 1 | Instalar VoziPOmni (completa) |
| 2 | Actualizar VoziPOmni (preserva datos) |
| 3 | Desinstalar VoziPOmni |
| 4 | Ver credenciales |
| 5 | Ver logs |
| 6 | Reiniciar servicios |
| 7 | Salir |

> Si la variable `VOZIPOMNI_IPV4` está definida, el instalador omite el menú y ejecuta la instalación directamente.

### Sistemas Operativos Soportados

Compatible con **cualquier distribución Linux** moderna. Detección automática de:

| Familia | Distribuciones |
|---------|---------------|
| **Debian** | Ubuntu, Debian, Linux Mint, Pop!_OS, Elementary, Zorin, Kali |
| **RHEL** | CentOS, Rocky Linux, AlmaLinux, Oracle Linux, RHEL, Scientific Linux |
| **Fedora** | Fedora |
| **SUSE** | openSUSE, SLES |
| **Arch** | Arch Linux, Manjaro, EndeavourOS |
| **Amazon** | Amazon Linux |
| **Otras** | Cualquier distro con Docker (instalación via `get.docker.com`) |

### Requisitos Mínimos

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Disco | 40 GB | 100 GB |

### Puertos Requeridos

| Puerto | Protocolo | Servicio |
|--------|-----------|----------|
| 22 | TCP | SSH |
| 80 / 443 | TCP | Nginx (HTTP/HTTPS) |
| 5060 | UDP/TCP | Kamailio (SIP) |
| 5061 | TCP | Kamailio (SIP TLS) |
| 5161 / 5162 | UDP | Asterisk (Troncales SIP) |
| 5038 | TCP | Asterisk AMI |
| 8080 | TCP | Kamailio HTTP |
| 8088 / 8089 | TCP | Asterisk WebSocket (WebRTC) |
| 8765 | TCP | WebSocket Server |
| 10000-23100 | UDP | RTP media (audio/vídeo) |

---

## 💻 Desarrollo Local

### Prerrequisitos

- Docker Desktop (Windows/Mac) o Docker + Docker Compose v2 (Linux)
- Git
- 8 GB RAM mínimo
- 50 GB espacio en disco

### 1. Clonar el repositorio

```bash
git clone https://github.com/VOZIP/vozipomni.git
cd vozipomni
```

### 2. Configurar variables de entorno

```bash
cp env.template .env
# Editar .env si es necesario (los valores por defecto funcionan para desarrollo)
```

### 3. Levantar los contenedores

```bash
# Modo producción (usa docker-compose.yml con healthchecks y resource limits)
docker compose up -d

# Modo desarrollo (incluye hot-reload del frontend en puerto 3001)
docker compose --profile dev up -d
```

> Los servicios esperan automáticamente a que sus dependencias estén saludables (PostgreSQL, Redis) gracias a `depends_on: condition: service_healthy`.

### 4. Ejecutar migraciones y crear superusuario

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

### 5. Acceder a la aplicación

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost |
| Frontend Dev (hot-reload) | http://localhost:3001 |
| Admin Django | http://localhost/admin |
| API REST | http://localhost/api |
| Documentación API (Swagger) | http://localhost/api/docs |
| Schema OpenAPI | http://localhost/api/schema |

---

## � Estructura de Archivos de Despliegue

```
vozipomni/
├── deploy.sh                    # Despliegue en una línea (set -Eeuo pipefail, trap ERR)
├── install.sh                   # Instalación interactiva con menú
├── prepare-system.sh            # Preparación universal del sistema operativo
├── env.template                 # Template centralizado de variables .env
├── docker-compose.yml           # Desarrollo (bridge network, port mappings)
├── docker-compose.prod.yml      # Producción (network_mode: host, healthchecks)
├── backend/                     # Django REST API
├── frontend/                    # Nuxt 3 + Vue 3
├── dialer_engine/               # Motor de discado (panoramisk/AMI)
├── websocket_server/            # Eventos en tiempo real (aiohttp)
└── docker/
    ├── asterisk/                # Asterisk PBX (configs, Dockerfile)
    ├── kamailio/                # Proxy SIP / WebRTC gateway
    ├── rtpengine/               # Media proxy RTP
    ├── nginx/                   # Reverse proxy (dev + prod)
    ├── postgresql/              # Init SQL
    └── redis/
```

### Archivos clave

| Archivo | Descripción |
|---------|-------------|
| `deploy.sh` | Despliegue automatizado con polling HTTP, manejo de errores y detección de compose |
| `install.sh` | Instalador interactivo v2.0 con menú (instalar, actualizar, desinstalar) |
| `prepare-system.sh` | Preparación del kernel (silencia mensajes veth/bridge), sysctl VoIP, Docker daemon |
| `env.template` | Template de todas las variables de entorno con valores por defecto |
| `docker-compose.yml` | Desarrollo: bridge network, YAML anchors, healthchecks, resource limits |
| `docker-compose.prod.yml` | Producción: `network_mode: host` en todos los servicios para rendimiento VoIP |

### YAML Anchors (Templates reutilizables)

Ambos archivos Docker Compose usan anchors para evitar duplicación:

| Anchor | Uso |
|--------|-----|
| `x-logging` | Configuración de logs JSON (`max-size: 10m`, `max-file: 3`) |
| `x-restart-policy` | `restart: unless-stopped` |
| `x-healthcheck-http` | Healthcheck HTTP (30s interval, 10s timeout) |
| `x-healthcheck-tcp` | Healthcheck TCP (15s interval, 5s timeout) |
| `x-django-env` | Variables de entorno compartidas por Django, Celery Worker y Celery Beat |
| `x-django-common` | Configuración base compartida por servicios Django |

---

## 🐳 Servicios del Sistema

### Desarrollo (`docker-compose.yml`)

Usa red bridge con port mappings. Todos los servicios tienen healthchecks y resource limits.

| Servicio | Contenedor | Puerto(s) | Healthcheck | Memoria máx. |
|----------|-----------|-----------|-------------|---------------|
| PostgreSQL 14 | `vozipomni_postgres` | 5432 | `pg_isready` | 1 GB |
| Redis 7 | `vozipomni_redis` | 6379 | `redis-cli ping` | 512 MB |
| Django Backend | `vozipomni_backend` | 8000 | `curl /api/` | 1 GB |
| Celery Worker | `vozipomni_celery_worker` | — | — | 512 MB |
| Celery Beat | `vozipomni_celery_beat` | — | — | 256 MB |
| Asterisk | `vozipomni_asterisk` | 5060, 5061, 5161, 5162, 5038, 8088, 8089, 10000-10100/udp | `asterisk -rx` | — |
| Nginx | `vozipomni_nginx` | 80, 443 | `curl /` | 256 MB |
| Nuxt 3 Frontend | `vozipomni_frontend` | 3000 | — | 512 MB |
| WebSocket Server | `vozipomni_websocket` | 8765 | — | 256 MB |
| Dialer Engine | `vozipomni_dialer` | — | — | 512 MB |
| Frontend Dev | `vozipomni_frontend_dev` | 3001 | — | — |

> El frontend dev solo se activa con el perfil `dev`: `docker compose --profile dev up -d`

### Producción (`docker-compose.prod.yml`)

**Todos los servicios usan `network_mode: host`** para rendimiento óptimo de VoIP. No hay redes Docker bridge ni port mappings — los servicios escuchan directamente en las interfaces de red del host.

| Servicio | Puerto(s) en el host | Healthcheck | Memoria máx. | `depends_on` |
|----------|---------------------|-------------|---------------|-------------|
| PostgreSQL 14 | 5432 | `pg_isready` | 1 GB | — |
| Redis 7 | 6379 | `redis-cli ping` | 512 MB | — |
| Django Backend | 8000 | `curl /api/` | 1 GB | postgres ✅, redis ✅ |
| Celery Worker | — | — | 512 MB | postgres ✅, redis ✅, backend ✅ |
| Celery Beat | — | — | 256 MB | postgres ✅, redis ✅, backend ✅ |
| Asterisk | 5161, 5162, 5038, 8088, 8089, 10000-10099/udp | `asterisk -rx` | 1 GB | — |
| Kamailio | 5060, 5061, 8080 | — | 512 MB | redis ✅, asterisk ✅, rtpengine |
| RTPEngine | 22222, 23000-23100/udp | — | 256 MB | redis ✅ |
| Nginx | 80, 443 | `curl /` | 256 MB | backend ✅, frontend |
| Nuxt 3 Frontend | 3000 | — | 512 MB | backend ✅ |
| WebSocket Server | 8765 | — | 256 MB | redis ✅ |
| Dialer Engine | — | — | 512 MB | redis ✅, asterisk ✅ |

> ✅ = `condition: service_healthy` (espera a que el servicio esté saludable antes de iniciar)

### Cadena de dependencias

```
PostgreSQL ──┐
             ├──► Backend ──► Celery Worker
Redis ───────┤              ├──► Celery Beat
             │              ├──► Nginx ◄── Frontend
             ├──► Asterisk ──► Kamailio
             │              └──► Dialer Engine
             ├──► RTPEngine
             └──► WebSocket Server
```

---

## 🖥 Módulos del Frontend

### Páginas / Rutas

| Ruta | Descripción |
|------|-------------|
| `/login` | Inicio de sesión |
| `/dashboard` | Panel principal con estadísticas |
| `/agents` | Gestión de agentes |
| `/campaigns` | Gestión de campañas |
| `/queues` | Colas ACD |
| `/contacts` | Listas de contactos |
| `/calls` | Historial de llamadas |
| `/recordings` | Grabaciones de llamadas |
| `/trunks` | Troncales SIP |
| `/extensions` | Extensiones telefónicas |
| `/ivr` | Menús de voz interactivos |
| `/inbound-routes` | Rutas entrantes (DID) |
| `/outbound-routes` | Rutas salientes |
| `/voicemail` | Buzones de voz |
| `/time-conditions` | Condiciones horarias |
| `/reports` | Reportería y analíticas |
| `/settings` | Configuración del sistema |
| `/profile` | Perfil de usuario |

### Composables

| Composable | Función |
|------------|---------|
| `useApi` | Cliente HTTP wrapper para la API |
| `useAuth` | Lógica de autenticación JWT |
| `useAgents` | Gestión de agentes |
| `useCalls` | Gestión de llamadas |
| `useExtensions` | Extensiones telefónicas |
| `useInboundRoutes` | Rutas entrantes |
| `useOutboundRoutes` | Rutas salientes |
| `useIVR` | Menús de voz |
| `useTrunks` | Troncales SIP |
| `useRecordings` | Grabaciones |
| `useVoicemail` | Buzones de voz |
| `useTimeConditions` | Condiciones horarias |
| `useWebSocket` | Conexión WebSocket en tiempo real |

### Componentes

| Componente | Descripción |
|------------|-------------|
| `WebPhone` | Teléfono WebRTC integrado en el navegador (JsSIP) |
| `DataTable` | Tabla de datos reutilizable con paginación |
| `StatCard` | Tarjeta de estadísticas para el dashboard |
| `Alert` | Notificaciones y alertas UI |
| `ConfirmModal` | Modal de confirmación de acciones |

---

## 🔌 API REST

Autenticación via JWT (SimpleJWT). Documentación interactiva disponible en `/api/docs/` (Swagger UI).

### Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/auth/login/` | Obtener token JWT |
| POST | `/api/auth/refresh/` | Refrescar token |
| GET | `/api/auth/me/` | Usuario autenticado |

### Recursos CRUD

| Endpoint | Recurso |
|----------|---------|
| `/api/users/` | Usuarios |
| `/api/agents/` | Agentes |
| `/api/campaigns/` | Campañas |
| `/api/contacts/` | Contactos |
| `/api/contact-lists/` | Listas de contactos |
| `/api/queues/` | Colas ACD |
| `/api/calls/` | Llamadas |
| `/api/recordings/` | Grabaciones |
| `/api/reports/` | Reportes |
| `/api/trunks/` | Troncales SIP |

### Telefonía

| Endpoint | Recurso |
|----------|---------|
| `/api/telephony/extensions/` | Extensiones |
| `/api/telephony/ivr/` | IVR |
| `/api/telephony/inbound-routes/` | Rutas entrantes |
| `/api/telephony/outbound-routes/` | Rutas salientes |
| `/api/telephony/voicemail/` | Buzones de voz |
| `/api/telephony/time-conditions/` | Condiciones horarias |
| `/api/telephony/trunks/statuses/` | Estado de registro de troncales (via AMI) |

### WebSocket

| Endpoint | Descripción |
|----------|-------------|
| `WS /ws/agent/{agent_id}/` | Eventos del agente en tiempo real |
| `WS /ws/dashboard/` | Eventos del dashboard |

### Ejemplo de uso

```javascript
// Login — obtener tokens JWT
const response = await fetch('/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin', password: 'tu_password' })
});
const { access, refresh } = await response.json();

// Consultar campañas
const campaigns = await fetch('/api/campaigns/', {
  headers: { 'Authorization': `Bearer ${access}` }
});
```

---

## 📞 Motor de Discado

El Dialer Engine (`dialer_engine/`) se conecta a Asterisk via AMI (panoramisk) y soporta 4 modos de operación:

| Modo | Descripción |
|------|-------------|
| **Manual** | El agente marca manualmente cada número |
| **Progresivo** | 1 llamada por agente disponible (ratio 1:1) |
| **Predictivo** | Ratio dinámico basado en tasa de abandono (target 3%), ajusta entre 1.0x y 3.0x |
| **Call Blasting** | Discado masivo sin agentes, reproduce mensaje grabado con control de concurrencia |

### Estados de llamada

`queued` → `dialing` → `ringing` → `answered` → `completed`

Estados alternativos: `busy`, `no_answer`, `failed`

### Eventos AMI monitoreados

- `Newchannel` — nueva llamada originada
- `Hangup` — llamada finalizada
- `AgentConnect` — agente conectado a la llamada
- `AgentComplete` — agente completó la llamada

---

## 📞 Configuración de Telefonía

### Troncales SIP

Las troncales se gestionan desde la interfaz web en `/trunks`. También se pueden configurar directamente en `docker/asterisk/configs/pjsip.conf`:

```ini
[mi_proveedor]
type=endpoint
context=from-external
transport=transport-udp
aors=mi_proveedor-aor
outbound_auth=mi_proveedor-auth
disallow=all
allow=ulaw,alaw

[mi_proveedor-aor]
type=aor
contact=sip:user@proveedor.com

[mi_proveedor-auth]
type=auth
auth_type=userpass
username=tu_usuario
password=tu_password
```

```bash
docker compose restart asterisk
```

### Tipos de troncal soportados

| Tipo | Descripción |
|------|-------------|
| NAT | Para proveedores detrás de NAT |
| No-NAT | Conexión directa sin NAT |
| PBX | Interconexión con otra PBX |
| Corporativo | Troncal SIP empresarial |
| Custom | Configuración personalizada |

---

## 🔧 Gestión del Sistema

### Desarrollo local

```bash
# Ver estado de servicios (con healthcheck status)
docker compose ps

# Ver logs de todos los servicios
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f backend
docker compose logs -f asterisk

# Reiniciar un servicio
docker compose restart backend

# Reiniciar todos los servicios
docker compose restart

# Detener todos los servicios
docker compose down

# Limpiar volúmenes (⚠️ elimina datos)
docker compose down -v

# Acceder al contenedor del backend
docker compose exec backend bash

# Consola de Asterisk
docker compose exec asterisk asterisk -rvvv
```

### Producción

```bash
cd /opt/vozipomni

# Ver estado de servicios
docker compose -f docker-compose.prod.yml ps

# Ver logs (filtrar por servicio)
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml logs -f backend asterisk

# Reiniciar un servicio
docker compose -f docker-compose.prod.yml restart backend

# Reiniciar todos los servicios
docker compose -f docker-compose.prod.yml restart

# Detener todos los servicios (preserva datos)
docker compose -f docker-compose.prod.yml down

# Reconstruir un servicio sin afectar otros
docker compose -f docker-compose.prod.yml up -d --build backend

# Consola de Asterisk
docker compose -f docker-compose.prod.yml exec asterisk asterisk -rvvv

# Ver registros SIP
docker compose -f docker-compose.prod.yml exec asterisk asterisk -rx "pjsip show registrations"
```

### Backup y restauración

```bash
# Backup de base de datos
docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U vozipomni_user vozipomni > backup_$(date +%Y%m%d).sql

# Restaurar backup
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T postgres psql -U vozipomni_user vozipomni

# Backup de .env y credenciales
cp /opt/vozipomni/.env /opt/vozipomni/.env.backup
cp /opt/vozipomni/credentials.txt /opt/vozipomni/credentials.backup.txt
```

---

## 🔐 Credenciales

### Instalación de producción

Las credenciales se generan automáticamente con `openssl rand` y se guardan en `/opt/vozipomni/credentials.txt` (permisos `600`).

La configuración centralizada está en `/opt/vozipomni/.env`:

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave secreta de Django (generada) |
| `POSTGRES_PASSWORD` | Password de PostgreSQL (generada) |
| `REDIS_PASSWORD` | Password de Redis (generada) |
| `ASTERISK_AMI_PASSWORD` | Password de AMI (default: `vozipomni_ami_2026`) |

### Desarrollo local

Definidas en `.env` (raíz) y `backend/.env`. El template base es `env.template`.

**Usuario Admin**:
- Usuario: `admin`
- Contraseña: generada automáticamente en producción (ver `credentials.txt`)

**Agente de prueba WebRTC**:
- Extensión SIP: `agent1000`
- Contraseña: `vozipomni_ami_2026`
- WebSocket: `wss://TU_IP:8089/ws`

---

## 🔐 Seguridad

Recomendaciones para producción:

1. **Cambiar todas las contraseñas** generadas por defecto
2. **Configurar HTTPS** con certificados SSL (Let's Encrypt o similar)
3. **Restringir CORS** solo a dominios autorizados
4. **Habilitar firewall** y limitar puertos expuestos
5. **Activar autenticación de dos factores**
6. **Configurar backups automáticos** de PostgreSQL
7. **Configurar Sentry** para monitoreo de errores en producción
8. **Cambiar `DEBUG=False`** y `SECRET_KEY` en el backend

---

## 🐛 Troubleshooting

### Mensajes del kernel inundan la consola (veth/bridge)

Esto ocurre cuando Docker crea interfaces de red y el kernel imprime mensajes en la consola. Se soluciona automáticamente con `prepare-system.sh`, pero si persiste:

```bash
# Silenciar mensajes del kernel
echo "1 4 1 7" > /proc/sys/kernel/printk
dmesg -n 1

# Persistir
echo "kernel.printk = 1 4 1 7" > /etc/sysctl.d/10-vozipomni.conf
sysctl -p /etc/sysctl.d/10-vozipomni.conf
```

### Los servicios no inician en orden correcto

Los archivos Docker Compose usan `depends_on: condition: service_healthy`. Verifique el estado de los healthchecks:

```bash
docker compose ps
# o en producción:
docker compose -f docker-compose.prod.yml ps
```

Si un servicio muestra `unhealthy`, revise sus logs:

```bash
docker compose logs postgres   # ¿pg_isready falla?
docker compose logs redis      # ¿redis-cli ping falla?
docker compose logs backend    # ¿curl /api/ falla?
```

### PostgreSQL no conecta

```bash
docker compose ps postgres
docker compose logs postgres

# En producción (network_mode: host), verificar directamente:
pg_isready -h 127.0.0.1 -U vozipomni_user -d vozipomni
```

### Asterisk no inicia

```bash
docker compose logs asterisk
docker compose exec asterisk asterisk -rx "core show settings"
docker compose exec asterisk asterisk -rx "pjsip show endpoints"
```

### Frontend no carga

```bash
# Reconstruir frontend
docker compose build frontend
docker compose up -d frontend

# O en modo desarrollo
docker compose --profile dev build frontend_dev
docker compose --profile dev up -d frontend_dev
```

### WebSocket no conecta

```bash
docker compose logs websocket_server
# Verificar health check
curl http://localhost:8765/health
```

### Troncales SIP no registran

```bash
docker compose exec asterisk asterisk -rx "pjsip show registrations"
docker compose exec asterisk asterisk -rx "pjsip show endpoints"
```

### El deploy se queda esperando (timeout)

El `wait_for_env` espera hasta 10 minutos (600s) a que el backend responda HTTP. Si el timeout se alcanza:

```bash
# Ver qué servicios están corriendo
docker compose -f docker-compose.prod.yml ps

# Ver logs del backend
docker compose -f docker-compose.prod.yml logs backend

# Verificar manualmente
curl -v http://localhost:8000/api/
```

---

## 🎯 Roadmap

- [ ] Integración con WhatsApp Business API
- [ ] Chatbot con IA
- [ ] Análisis de sentimientos en llamadas
- [ ] Transcripción automática de llamadas
- [ ] Dashboard mobile (React Native)
- [ ] Integración con CRMs populares (Salesforce, HubSpot)
- [ ] Soporte multi-idioma
- [ ] Módulo de gamificación para agentes

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/NuevaFuncionalidad`)
3. Commit tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/NuevaFuncionalidad`)
5. Abre un Pull Request

---

## 📝 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para más detalles.

## 🆘 Soporte

- **Issues**: https://github.com/VOZIP/vozipomni/issues
- **Email**: soporte@vozip.com

## ✨ Autores

- **VOZIP Colombia** — [GitHub](https://github.com/VOZIP)

---

**Desarrollado con ❤️ por VOZIP Colombia**
