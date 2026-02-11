# =============================================================================
#                       CONFIGURACIÓN DE PRODUCCIÓN
# =============================================================================

## 1. SEGURIDAD CRÍTICA

### SSL/HTTPS (OBLIGATORIO)
- [ ] Certificado SSL válido (Let's Encrypt o comercial)
- [ ] Redireccionamiento automático HTTP → HTTPS
- [ ] Headers de seguridad (HSTS, CSP, etc.)

### Configuración Django
- [ ] DEBUG = False en producción  
- [ ] SECRET_KEY segura y única para producción
- [ ] ALLOWED_HOSTS configurado correctamente
- [ ] CORS_ORIGINS restringido a dominios permitidos
- [ ] Configuración de cookies seguras (SESSION_COOKIE_SECURE = True)

### Base de Datos
- [ ] PostgreSQL con contraseñas seguras
- [ ] Backup automático configurado
- [ ] Conexiones limitadas y monitoreo

## 2. RENDIMIENTO Y ESCALABILIDAD

### Backend
- [ ] Gunicorn con múltiples workers (configurado)
- [ ] Cache Redis configurado correctamente
- [ ] Logs estructurados y rotación
- [ ] Celery workers para tareas asíncronas
- [ ] Rate limiting en APIs críticas

### Frontend
- [ ] Build optimizado de Nuxt 3 (SSR/Static)
- [ ] Compresión gzip/brotli en nginx
- [ ] Cache de assets estáticos
- [ ] CDN para assets (opcional)
- [ ] Service Workers para PWA (opcional)

### Nginx
- [ ] Compresión habilitada
- [ ] Cache de archivos estáticos
- [ ] Límites de rate limiting
- [ ] Timeout configurados correctamente

## 3. MONITOREO Y LOGGING

### Logs
- [ ] Logs centralizados (ELK Stack o similar)
- [ ] Rotación automática de logs
- [ ] Niveles de log apropiados (INFO en prod)
- [ ] Logs de nginx, Django, y Celery

### Monitoreo
- [ ] Health checks automáticos
- [ ] Métricas de sistema (CPU, RAM, Disk)
- [ ] Métricas de aplicación (requests, errores, latencia)
- [ ] Alertas automatizadas

## 4. INFRAESTRUCTURA

### Docker
- [ ] Imágenes optimizadas para producción
- [ ] Multi-stage builds configurados
- [ ] Límites de recursos por contenedor
- [ ] Networks aisladas
- [ ] Volumes persistentes para datos

### Backup y Recuperación
- [ ] Backup automático de BD
- [ ] Backup de archivos media
- [ ] Plan de recuperación ante desastres
- [ ] Pruebas de restauración

### Red y Firewall
- [ ] Firewall configurado (solo puertos necesarios)
- [ ] Fail2ban para protección SSH
- [ ] VPN o acceso restringido para administración
- [ ] Dominio y DNS configurados

## 5. ASTERISK / TELEFONÍA

### Configuración Asterisk
- [ ] Codecs optimizados para producción
- [ ] SIP trunk configurados y probados
- [ ] Dialplan optimizado
- [ ] Logs de llamadas configurados
- [ ] Grabaciones automáticas funcionando

### Seguridad Telefónica
- [ ] SIP credentials seguros
- [ ] Firewall RTP configurado
- [ ] Rate limiting llamadas
- [ ] Detección de fraude básica

## 6. VARIABLES DE ENTORNO CRÍTICAS

### Backend (.env)
```env
# Producción
DEBUG=False
ENVIRONMENT=production

# Seguridad
SECRET_KEY=tu_clave_super_secreta_de_50_caracteres_minimo
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
CORS_ORIGINS=https://tu-dominio.com

# Base de Datos
DATABASE_URL=postgresql://usuario:password@postgres:5432/vozipomni_prod

# Redis
REDIS_URL=redis://:password@redis:6379/0

# Email (para notificaciones)
EMAIL_HOST=smtp.tuproveedor.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@tu-dominio.com
EMAIL_HOST_PASSWORD=password

# Asterisk
ASTERISK_HOST=asterisk
ASTERISK_USERNAME=admin
ASTERISK_PASSWORD=password_seguro
```

### Frontend (.env)
```env
# APIs
NUXT_PUBLIC_API_BASE=https://tu-dominio.com/api
NUXT_PUBLIC_WS_BASE=wss://tu-dominio.com/ws

# Analítica (opcional)
NUXT_PUBLIC_ANALYTICS_ID=G-XXXXXXXXX
```

## 7. COMANDOS DE DEPLOYMENT

### Primera vez (setup inicial):
```bash
# 1. Clonar y configurar
git clone https://github.com/tu-usuario/vozipomni.git
cd vozipomni

# 2. Configurar variables
cp .env.example .env
nano .env  # Configurar para producción

# 3. Construir y lanzar
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Migrar base de datos
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 5. Crear superusuario
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

### Updates/Deployments:
```bash
# 1. Actualizar código
git pull origin main

# 2. Reconstruir servicios modificados
docker-compose -f docker-compose.prod.yml build --no-cache backend frontend

# 3. Aplicar migraciones
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 4. Restart servicios
docker-compose -f docker-compose.prod.yml up -d --force-recreate backend frontend nginx
```