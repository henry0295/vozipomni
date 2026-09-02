# VoziPOmni - Deploy Rápido 🚀

> Instalación simplificada al estilo [OmniLeads](https://docs.omnileads.net) - Una línea y listo

## 📦 Instalación (Primera vez)

### Opción 1: Script Simple (Recomendado)

```bash
# 1. Descargar script
curl -o deploy.sh -L https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy-simple.sh && chmod +x deploy.sh

# 2. Ejecutar instalación
export DOCKER_ENGINE_IPV4=X.X.X.X && ./deploy.sh -i
```

Reemplaza `X.X.X.X` con la IP de tu servidor.

### Opción 2: Servidor detrás de NAT

Si tu servidor tiene IP privada (192.168.x.x) y está detrás de un router con IP pública:

```bash
export DOCKER_ENGINE_IPV4=192.168.1.100 NAT_IPV4=190.159.139.176 && ./deploy.sh -i
```

- `DOCKER_ENGINE_IPV4`: IP privada del servidor
- `NAT_IPV4`: IP pública del router

---

## 🔄 Actualización

Para actualizar VoziPOmni a la última versión:

```bash
cd /opt/vozipomni
./deploy.sh -u
```

---

## 🗑️ Reinstalación

Para borrar todo y reinstalar desde cero:

```bash
cd /opt/vozipomni
./deploy.sh -c
```

**⚠️ Advertencia:** Esto eliminará TODOS los datos (base de datos, grabaciones, configuraciones).

---

## 🔐 Acceso al Sistema

Después de la instalación, accede a:

**URL:** `http://X.X.X.X`

**Credenciales por defecto:**
- Usuario: `admin`  
- Contraseña: *(generada automáticamente, ver abajo)*

### Ver credenciales

```bash
cat /opt/vozipomni/credentials.txt
```

Este archivo contiene:
- ✅ Usuario y contraseña de administrador
- ✅ Credenciales de PostgreSQL
- ✅ Credenciales de Redis
- ✅ Credenciales de Asterisk AMI
- ✅ Acceso a Grafana

---

## 📊 Servicios Incluidos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **Web UI** | 80 | Interfaz principal |
| **API** | 8000 | API REST |
| **WebSocket** | 8765 | Eventos en tiempo real |
| **PostgreSQL** | 5432 | Base de datos |
| **Redis** | 6379 | Cache y mensajería |
| **Asterisk AMI** | 5038 | Gestión de Asterisk |
| **Kamailio SIP** | 5060 | Proxy SIP |
| **Prometheus** | 9090 | Métricas |
| **Grafana** | 3000 | Dashboards |

---

## 🔒 Habilitar HTTPS

Para usar certificados SSL/TLS:

```bash
cd /opt/vozipomni
./quick-https.sh X.X.X.X
```

Esto configurará certificados Let's Encrypt automáticamente.

---

## 🛠️ Comandos Útiles

### Ver estado de servicios
```bash
cd /opt/vozipomni
docker compose -f docker-compose.prod.yml ps
```

### Ver logs
```bash
# Todos los servicios
docker compose -f docker-compose.prod.yml logs -f

# Solo backend
docker compose -f docker-compose.prod.yml logs -f backend

# Solo Asterisk
docker compose -f docker-compose.prod.yml logs -f asterisk
```

### Reiniciar servicios
```bash
docker compose -f docker-compose.prod.yml restart
```

### Detener servicios
```bash
docker compose -f docker-compose.prod.yml down
```

### Iniciar servicios
```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## 🔧 Variables de Entorno Opcionales

Puedes personalizar la instalación con estas variables:

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DOCKER_ENGINE_IPV4` | IP del servidor (obligatorio) | - |
| `NAT_IPV4` | IP pública si está detrás de NAT | - |
| `TZ` | Zona horaria | `America/Bogota` |
| `INSTALL_DIR` | Directorio de instalación | `/opt/vozipomni` |
| `BRANCH` | Rama Git a desplegar | `main` |

**Ejemplo:**
```bash
export DOCKER_ENGINE_IPV4=192.168.1.100
export TZ=America/Mexico_City
export INSTALL_DIR=/home/vozipomni
./deploy.sh -i
```

---

## 📞 Configuración VoIP

### Configurar Troncal SIP

1. Accede a la interfaz web
2. Ve a **Telefonía → Troncales SIP**
3. Clic en **Nueva Troncal**
4. Completa:
   - Nombre: Proveedor VoIP
   - Host: sip.proveedor.com
   - Usuario: tu_usuario
   - Contraseña: tu_contraseña
5. Guardar

### Crear Extensiones

1. Ve a **Telefonía → Extensiones**
2. Clic en **Nueva Extensión**
3. Completa:
   - Número: 1001
   - Contraseña: contraseña_segura
   - Tipo: Softphone o WebRTC
4. Guardar

---

## 🐛 Solución de Problemas

### El sistema no arranca

```bash
# Ver logs de todos los servicios
docker compose -f docker-compose.prod.yml logs

# Verificar estado
docker compose -f docker-compose.prod.yml ps
```

### Error de conexión a base de datos

```bash
# Verificar que PostgreSQL esté corriendo
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Reiniciar PostgreSQL
docker compose -f docker-compose.prod.yml restart postgres
```

### No hay audio en llamadas WebRTC

Verifica que `DOCKER_ENGINE_IPV4` esté configurado con la IP correcta:

```bash
# Ver configuración actual
cat /opt/vozipomni/.env | grep VOZIPOMNI_IPV4

# Si está mal, edita .env y reinicia
vi /opt/vozipomni/.env
docker compose -f docker-compose.prod.yml restart
```

### Asterisk no responde

```bash
# Ver logs de Asterisk
docker compose -f docker-compose.prod.yml logs asterisk

# Conectarse a CLI de Asterisk
docker compose -f docker-compose.prod.yml exec asterisk asterisk -rvvv
```

---

## 📚 Documentación Completa

- [Guía de Instalación Detallada](INICIO_RAPIDO.md)
- [Configuración de Agentes](GUIA_CREACION_AGENTES.md)
- [Seguridad](CORRECCIONES_SEGURIDAD_2026.md)
- [Despliegue](README_DEPLOY.md)

---

## 🆘 Soporte

Si tienes problemas:

1. Revisa los logs: `docker compose -f docker-compose.prod.yml logs`
2. Verifica el archivo `.env` tiene todas las variables
3. Consulta la documentación completa
4. Abre un issue en GitHub

---

## ✨ Características

- ✅ **Instalación en 1 línea** (como OmniLeads)
- ✅ **Generación automática de contraseñas**
- ✅ **Configuración automática** de todos los servicios
- ✅ **Soporte NAT** para servidores detrás de router
- ✅ **Actualización simple** con `-u`
- ✅ **Credenciales guardadas** automáticamente
- ✅ **HTTPS opcional** con Let's Encrypt
- ✅ **Monitoring** incluido (Prometheus + Grafana)

---

**Versión:** 3.0.0  
**Compatible con:** Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+

