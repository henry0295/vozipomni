# VoziPOmni Contact Center

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Django](https://img.shields.io/badge/django-4.2.9-green.svg)
![Nuxt](https://img.shields.io/badge/nuxt-3.10-00DC82.svg)
![Vue](https://img.shields.io/badge/vue-3.4-42b883.svg)
![Asterisk](https://img.shields.io/badge/asterisk-PBX-orange.svg)

Plataforma de Contact Center omnicanal con arquitectura moderna basada en Django REST Framework, Nuxt 3, Asterisk, Kamailio y RTPEngine. Incluye marcadores predictivo, progresivo y call blasting, consola de agente WebRTC, IVR, colas ACD y reportería en tiempo real.

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Stack Tecnológico](#-stack-tecnológico)
- [Arquitectura](#️-arquitectura)
- [Instalación Rápida (Producción)](#-instalación-rápida-producción)
- [Desarrollo Local](#-desarrollo-local)
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

## 🚀 Instalación Rápida (Producción)

Para instalar VoziPOmni en un servidor Linux (VPS, Cloud o VM):

```bash
curl -o install.sh -L "https://raw.githubusercontent.com/VOZIP/vozipomni/main/install.sh" && chmod +x install.sh
```

Ejecuta el instalador indicando la IP pública de tu servidor:

```bash
export VOZIPOMNI_IPV4=X.X.X.X && ./install.sh
```

> **Reemplaza `X.X.X.X` con tu dirección IP pública.**

El instalador realiza automáticamente:
- Detección y validación de sistema operativo
- Verificación de requisitos mínimos (4 GB RAM, 40 GB disco, 2 CPU)
- Instalación de Docker CE + Docker Compose
- Configuración de firewall (UFW o firewalld)
- Clonado del repositorio en `/opt/vozipomni`
- Generación de credenciales seguras (openssl rand)
- Build y despliegue de todos los contenedores
- Migraciones de base de datos y creación de superusuario
- Guardado de credenciales en `credentials.txt`

### Sistemas Operativos Soportados

| Distribución | Versiones |
|---|---|
| Ubuntu | 20.04 / 22.04 LTS |
| Debian | 11 / 12 |
| CentOS Stream | 8 / 9 |
| Rocky Linux | 8 / 9 |
| RHEL | 8 / 9 |
| AlmaLinux | 8 / 9 |

### Requisitos Mínimos

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 4 GB | 8 GB |
| CPU | 2 cores | 4 cores |
| Disco | 40 GB | 100 GB |

### Puertos requeridos

| Puerto | Protocolo | Servicio |
|--------|-----------|----------|
| 80 / 443 | TCP | Nginx (HTTP/HTTPS) |
| 5060 | UDP/TCP | Kamailio (SIP) |
| 5061 | TCP | Kamailio (SIP TLS) |
| 5161 / 5162 | UDP | Asterisk (Troncales SIP) |
| 8089 | TCP | Asterisk WebSocket (WebRTC) |
| 10000-20000 | UDP | RTP (media de audio/video) |

---

## 💻 Desarrollo Local

### Prerrequisitos

- Docker Desktop (Windows/Mac) o Docker + Docker Compose (Linux)
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
cp backend/.env.example backend/.env
```

Para desarrollo local, los valores por defecto son suficientes.

### 3. Levantar los contenedores

```bash
# Modo producción
docker-compose up -d

# Modo desarrollo (con hot-reload del frontend)
docker-compose --profile dev up -d
```

### 4. Ejecutar migraciones y crear superusuario

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
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

## 🐳 Servicios del Sistema

### Desarrollo (docker-compose.yml)

| Servicio | Contenedor | Puerto(s) | Descripción |
|----------|-----------|-----------|-------------|
| PostgreSQL 14 | `vozipomni_postgres` | 5432 | Base de datos principal |
| Redis 7 | `vozipomni_redis` | 6379 | Cache, broker Celery, PubSub |
| Django Backend | `vozipomni_backend` | 8000 | API REST + Admin |
| Celery Worker | `vozipomni_celery_worker` | — | 4 workers para tareas asíncronas |
| Celery Beat | `vozipomni_celery_beat` | — | Scheduler de tareas periódicas |
| Asterisk | `vozipomni_asterisk` | 5060, 5061, 5161, 5162, 5038, 8088, 8089, 10000-10100/udp | PBX central |
| Nginx | `vozipomni_nginx` | 80, 443 | Reverse proxy |
| Nuxt 3 Frontend | `vozipomni-frontend` | 3000 | Frontend producción (SSR) |
| Nuxt 3 Frontend Dev | `vozipomni-frontend-dev` | 3001 | Frontend desarrollo (perfil `dev`) |

### Producción (docker-compose.prod.yml)

Incluye servicios adicionales:

| Servicio | Puerto(s) | Descripción |
|----------|-----------|-------------|
| Kamailio | 5060/udp+tcp, 5061/tcp, 8080/tcp | Proxy SIP + Gateway WebRTC |
| RTPEngine | 22222/udp, 23000-23100/udp | Media proxy / transcodificación RTP |
| WebSocket Server | 8765 | Eventos en tiempo real (aiohttp) |
| Dialer Engine | — | Motor de discado de campañas |

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
docker-compose restart asterisk
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

```bash
# Ver estado de servicios
docker-compose ps

# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f backend
docker-compose logs -f asterisk

# Reiniciar un servicio
docker-compose restart backend

# Reiniciar todos los servicios
docker-compose restart

# Detener todos los servicios
docker-compose down

# Limpiar volúmenes (⚠️ elimina datos)
docker-compose down -v

# Acceder al contenedor del backend
docker-compose exec backend bash

# Consola de Asterisk
docker-compose exec asterisk asterisk -rvvv

# Backup de base de datos
docker-compose exec postgres pg_dump -U vozipomni_user vozipomni_db > backup.sql

# Restaurar backup
cat backup.sql | docker-compose exec -T postgres psql -U vozipomni_user vozipomni_db
```

---

## 🔐 Credenciales

### Instalación de producción

Las credenciales se generan automáticamente y se guardan en `/opt/vozipomni/credentials.txt`.

### Desarrollo local

Definidas en `backend/.env` y `docker-compose.yml`.

**Usuario Admin**:
- Usuario: `admin`
- Contraseña: generada automáticamente en producción (ver `credentials.txt`)

**Agente de prueba WebRTC**:
- Extensión SIP: `agent1000`
- Contraseña: `VoziPOmni2026!`
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

### PostgreSQL no conecta

```bash
docker-compose ps postgres
docker-compose logs postgres
```

### Asterisk no inicia

```bash
docker-compose logs asterisk
docker-compose exec asterisk asterisk -rx "core show settings"
docker-compose exec asterisk asterisk -rx "pjsip show endpoints"
```

### Frontend no carga

```bash
# Reconstruir frontend
docker-compose build frontend
docker-compose up -d frontend

# O en modo desarrollo
docker-compose --profile dev build frontend_dev
docker-compose --profile dev up -d frontend_dev
```

### WebSocket no conecta

```bash
docker-compose logs websocket_server
# Verificar health check
curl http://localhost:8765/health
```

### Troncales SIP no registran

```bash
docker-compose exec asterisk asterisk -rx "pjsip show registrations"
docker-compose exec asterisk asterisk -rx "pjsip show endpoints"
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
