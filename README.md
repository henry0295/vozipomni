# VoziPOmni Contact Center

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Django](https://img.shields.io/badge/django-4.2.9-green.svg)
![React](https://img.shields.io/badge/react-18.2.0-blue.svg)

Sistema de Contact Center omnicanal desarrollado con Django, React y Asterisk. Similar a OmniLeads pero con arquitectura propia y moderna.

## 🚀 Instalación Rápida (Recomendada)

### Método 1: Instalación con Un Solo Comando (Producción)

Para instalar VoziPOmni en un servidor Linux (VPS, Cloud o VM), ejecuta:

```bash
curl -o install.sh -L "https://raw.githubusercontent.com/VOZIP/vozipomni/main/install.sh" && chmod +x install.sh
```

Luego ejecuta el instalador indicando la IP pública de tu servidor:

```bash
export VOZIPOMNI_IPV4=X.X.X.X && ./install.sh
```

**Reemplaza X.X.X.X con tu dirección IP pública**

#### Sistemas Operativos Soportados:
- Ubuntu 20.04 / 22.04 LTS
- Debian 11 / 12
- CentOS Stream 8 / 9
- Rocky Linux 8 / 9
- RHEL 8 / 9
- AlmaLinux 8 / 9

#### Requisitos Mínimos:
- **RAM**: 4 GB (Recomendado: 8 GB)
- **CPU**: 2 cores (Recomendado: 4 cores)
- **Disco**: 40 GB libres (Recomendado: 100 GB)
- **Puertos**: 80, 443, 5060, 5061, 10000-20000 UDP

### Método 2: Desarrollo Local (Docker Desktop)

#### Prerrequisitos

- Docker Desktop (Windows/Mac) o Docker + Docker Compose (Linux)
- Git
- 8GB RAM mínimo
- 50GB espacio en disco

#### 1. Clonar el repositorio

```bash
git clone https://github.com/VOZIP/vozipomni.git
cd vozipomni
```

#### 2. Configurar variables de entorno

Copia el archivo de ejemplo y edita según tus necesidades:

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Para desarrollo local, los valores por defecto son suficientes.

#### 3. Levantar los contenedores

```bash
docker-compose up -d
```

Este comando iniciará todos los servicios necesarios.

#### 4. Ejecutar migraciones

```bash
docker-compose exec backend python manage.py migrate
```

#### 5. Crear superusuario

```bash
docker-compose exec backend python manage.py createsuperuser
```

#### 6. Acceder a la aplicación

- **Frontend**: http://localhost
- **Admin Django**: http://localhost/admin
- **API REST**: http://localhost/api
- **Documentación API**: http://localhost/api/docs

## 📋 Características

- **Campañas**: Entrantes, salientes, manuales y preview
- **Marcadores**: Predictivo, progresivo y preview
- **Agentes**: Consola web con WebRTC
- **Colas (ACD)**: Distribución automática de llamadas
- **IVR**: Menús de voz interactivos
- **Reportes**: Analíticas en tiempo real
- **Grabaciones**: Almacenamiento y evaluación de llamadas
- **API REST**: Integración con sistemas externos
- **WebSocket**: Comunicación en tiempo real

## 🏗️ Arquitectura

```
┌─────────────────┐
│   Nginx Proxy   │
│   (Port 80/443) │
└────────┬────────┘
         │
    ┌────┴─────┐
    │          │
┌───▼───┐  ┌──▼──────┐     ┌──────────┐
│ React │  │ Django  │────▶│PostgreSQL│
│  UI   │  │ Backend │     │    DB    │
└───────┘  └────┬────┘     └──────────┘
                │
           ┌────┴────┐
           │         │
      ┌────▼────┐ ┌─▼─────┐
      │ Celery  │ │ Redis │
      │ Workers │ │ Cache │
      └─────────┘ └───────┘
           │
      ┌────▼──────┐
      │ Asterisk  │
      │  PBX      │
      │ (WebRTC)  │
      └───────────┘
```

## 🔧 Gestión del Sistema

### Ver estado de servicios
```bash
docker-compose ps
```

### Ver logs
```bash
# Todos los servicios
docker-compose logs -f

# Un servicio específico
docker-compose logs -f backend
```

### Reiniciar servicios
```bash
docker-compose restart
```

### Detener servicios
```bash
docker-compose down
```

## 🔐 Credenciales por Defecto

Después de la instalación automática, las credenciales se guardan en:
- Instalación de producción: `/opt/vozipomni/credentials.txt`
- Desarrollo local: Definidas en `backend/.env`

**Usuario Admin Predeterminado**:
- Usuario: `admin`
- Contraseña: Se genera automáticamente (ver credentials.txt)

**Agente de Prueba WebRTC**:
- Usuario SIP: `agent1000`
- Contraseña: `VoziPOmni2026!`
- WebSocket: `wss://TU_IP:8089/ws`

## 📱 Configuración de Agentes

### Crear un agente

1. Accede al admin de Django: http://localhost/admin
2. Ve a **Usuarios** y crea un nuevo usuario
3. Ve a **Agentes** y crea un agente asociado al usuario
4. Configura:
   - ID de Agente (único)
   - Extensión SIP (ej: 1000, 1001, etc.)
   - Habilitar WebRTC
   - Campañas asignadas

### Configurar WebRTC

Los agentes con WebRTC habilitado pueden realizar llamadas directamente desde el navegador.

**Credenciales por defecto**:
- Usuario SIP: agent1000
- Contraseña: VoziPOmni2026!
- Servidor WebSocket: wss://localhost:8089/ws

## 🔧 Configuración de Campañas

### Crear una campaña

1. Ve a **Campañas** en el admin
2. Crea una nueva campaña:
   - Nombre y descripción
   - Tipo: Entrante/Saliente/Manual
   - Marcador: Predictivo/Progresivo/Preview
   - Cola asociada
   - Lista de contactos

### Importar contactos

```bash
docker-compose exec backend python manage.py import_contacts --file=/path/to/contacts.csv --list=NombreLista
```

## 📊 Arquitectura

```
┌─────────────────┐
│  Nginx (Proxy)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼────┐
│React │  │Django │
│Front │  │ API   │
└──────┘  └───┬───┘
              │
         ┌────┴────┬────────┬─────────┐
         │         │        │         │
    ┌────▼───┐ ┌──▼───┐ ┌──▼────┐ ┌─▼──────┐
    │Postgres│ │Redis │ │Celery│ │Asterisk│
    └────────┘ └──────┘ └───────┘ └────────┘
```

## 🔌 API REST

### Endpoints principales

- `POST /api/auth/login/` - Autenticación
- `GET /api/campaigns/` - Listar campañas
- `GET /api/agents/` - Listar agentes
- `GET /api/calls/` - Historial de llamadas
- `GET /api/recordings/` - Grabaciones
- `WS /ws/agent/{agent_id}/` - WebSocket agente
- `WS /ws/dashboard/` - WebSocket dashboard

### Ejemplo de uso

```javascript
// Autenticación
const response = await fetch('http://localhost/api/auth/login/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin', password: 'password' })
});
const { access, refresh } = await response.json();

// Obtener campañas
const campaigns = await fetch('http://localhost/api/campaigns/', {
  headers: { 'Authorization': `Bearer ${access}` }
});
```

## 📞 Configuración de Telefonía

### Troncales SIP

Edita `docker/asterisk/configs/pjsip.conf` para agregar tu proveedor SIP:

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

Reinicia Asterisk:
```bash
docker-compose restart asterisk
```

## 🔐 Seguridad

### Para producción:

1. **Cambiar todas las contraseñas** en `docker-compose.yml`
2. **Configurar HTTPS** con certificados SSL
3. **Restringir CORS** a dominios específicos
4. **Habilitar firewall** y limitar puertos
5. **Activar autenticación de dos factores**
6. **Configurar backups automáticos**

## 📦 Comandos útiles

```bash
# Ver logs
docker-compose logs -f backend
docker-compose logs -f asterisk

# Reiniciar servicio
docker-compose restart backend

# Detener todo
docker-compose down

# Limpiar volúmenes (¡cuidado!)
docker-compose down -v

# Acceder a contenedor
docker-compose exec backend bash
docker-compose exec asterisk asterisk -rvvv

# Ver estado de servicios
docker-compose ps

# Backup de base de datos
docker-compose exec postgres pg_dump -U vozipomni_user vozipomni_db > backup.sql

# Restaurar backup
cat backup.sql | docker-compose exec -T postgres psql -U vozipomni_user vozipomni_db
```

## 🐛 Troubleshooting

### Error al conectar a la base de datos

```bash
# Verificar que PostgreSQL esté corriendo
docker-compose ps postgres

# Ver logs
docker-compose logs postgres
```

### Asterisk no inicia

```bash
# Ver logs detallados
docker-compose logs asterisk

# Verificar configuración
docker-compose exec asterisk asterisk -rx "core show settings"
```

### Frontend no carga

```bash
# Reconstruir frontend
docker-compose build frontend_dev
docker-compose up -d frontend_dev
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para más detalles.

## 🆘 Soporte

- **Documentación**: https://docs.vozipomni.local
- **Issues**: https://github.com/vozip/vozipomni/issues
- **Email**: soporte@vozip.com

## 🎯 Roadmap

- [ ] Integración con WhatsApp Business API
- [ ] Chatbot con IA
- [ ] Análisis de sentimientos en llamadas
- [ ] Transcripción automática de llamadas
- [ ] Dashboard mobile (React Native)
- [ ] Integración con CRMs populares (Salesforce, HubSpot)
- [ ] Soporte multi-idioma
- [ ] Módulo de gamificación para agentes

## ✨ Autores

- **VOZIP Colombia** - *Desarrollo inicial* - [VOZIP](https://github.com/vozipcolombia)

## 🙏 Agradecimientos

- Inspirado en OmniLeads
- Comunidad de Asterisk
- Django y React communities

---

**Desarrollado con ❤️ por VOZIP Colombia**
