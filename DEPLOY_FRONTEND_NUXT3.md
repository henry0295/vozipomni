# 🚀 Guía de Deploy - Actualización Frontend Nuxt 3

## 📋 Pre-requisitos

✅ Servidor con Docker y Docker Compose instalados
✅ Acceso SSH al servidor
✅ Git configurado
✅ Backend Django funcionando
✅ Backup reciente de la base de datos

---

## 🔄 Proceso de Actualización Completo

### Paso 1: Backup y Preparación (5 minutos)

```bash
# Conectar al servidor
ssh usuario@tu-servidor.com

# Ir al directorio del proyecto
cd /ruta/a/vozipomni

# Crear backup del frontend actual
sudo docker-compose stop frontend
sudo docker commit vozipomni-frontend vozipomni-frontend:backup-$(date +%Y%m%d)

# Backup de la configuración actual
cp docker-compose.yml docker-compose.yml.backup
cp -r frontend frontend.backup.$(date +%Y%m%d)

# Verificar backups creados
docker images | grep vozipomni-frontend
ls -la | grep backup
```

### Paso 2: Actualizar Código desde Git (2 minutos)

```bash
# Verificar branch actual
git branch

# Guardar cambios locales si existen
git stash

# Actualizar código
git fetch origin
git pull origin main  # o tu branch principal

# Si hay conflictos, resolverlos manualmente
git status
```

### Paso 3: Verificar Archivos del Nuevo Frontend (1 minuto)

```bash
# Verificar que los archivos de Nuxt 3 existen
ls -la frontend/

# Deberías ver:
# - nuxt.config.ts
# - package.json (con Nuxt 3)
# - app.vue
# - pages/
# - layouts/
# - components/
# - etc.

# Verificar package.json
cat frontend/package.json | grep "nuxt"
```

### Paso 4: Actualizar Variables de Entorno (3 minutos)

```bash
# Crear/actualizar archivo .env en frontend
cd frontend

# Si existe .env, respaldarlo
cp .env .env.backup 2>/dev/null || true

# Crear nuevo .env basado en .env.example
cat > .env << 'EOF'
# Backend API Configuration
NUXT_PUBLIC_API_BASE=https://api.tu-dominio.com/api
NUXT_PUBLIC_WS_BASE=wss://api.tu-dominio.com/ws

# App Configuration
NUXT_PUBLIC_APP_NAME=VozipOmni
NUXT_PUBLIC_APP_URL=https://tu-dominio.com

# Environment
NODE_ENV=production
EOF

# Verificar archivo creado
cat .env

# Volver al directorio raíz
cd ..
```

### Paso 5: Actualizar docker-compose.yml (3 minutos)

```bash
# Editar docker-compose.yml
nano docker-compose.yml
```

**Actualizar la sección del frontend:**

```yaml
services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: vozipomni-frontend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NUXT_PUBLIC_API_BASE=${FRONTEND_API_BASE:-http://backend:8000/api}
      - NUXT_PUBLIC_WS_BASE=${FRONTEND_WS_BASE:-ws://backend:8000/ws}
    depends_on:
      - backend
    networks:
      - vozipomni-network
    restart: unless-stopped
```

Guardar con `Ctrl+X`, `Y`, `Enter`

### Paso 6: Detener Servicios Actuales (1 minuto)

```bash
# Detener todos los servicios
sudo docker-compose down

# Verificar que todos los contenedores estén detenidos
sudo docker ps -a | grep vozipomni

# Opcional: Limpiar contenedores antiguos
sudo docker-compose rm -f frontend
```

### Paso 7: Construir Nueva Imagen del Frontend (5-10 minutos)

```bash
# Construir imagen del frontend con Nuxt 3
sudo docker-compose build --no-cache frontend

# Verificar que la construcción fue exitosa
echo $?  # Debe retornar 0

# Ver la nueva imagen
sudo docker images | grep vozipomni-frontend
```

**Si hay errores en la construcción:**
```bash
# Ver logs detallados
sudo docker-compose build frontend 2>&1 | tee build.log

# Verificar espacio en disco
df -h

# Limpiar imágenes antiguas si es necesario
sudo docker image prune -a
```

### Paso 8: Iniciar Servicios (2 minutos)

```bash
# Iniciar todos los servicios
sudo docker-compose up -d

# Verificar que los contenedores estén corriendo
sudo docker-compose ps

# Deberías ver algo como:
# NAME                    STATUS              PORTS
# vozipomni-frontend      Up X seconds       0.0.0.0:3000->3000/tcp
# vozipomni-backend       Up X seconds       0.0.0.0:8000->8000/tcp
# vozipomni-postgresql    Up X seconds       5432/tcp
# vozipomni-redis         Up X seconds       6379/tcp
```

### Paso 9: Verificar Logs del Frontend (2 minutos)

```bash
# Ver logs del frontend en tiempo real
sudo docker-compose logs -f frontend

# Deberías ver:
# ✔ Nuxt built in XXX ms
# Nuxt is listening on http://0.0.0.0:3000

# Presiona Ctrl+C para salir de los logs

# Ver últimas 50 líneas de logs
sudo docker-compose logs --tail=50 frontend
```

### Paso 10: Verificar Funcionamiento (5 minutos)

```bash
# Prueba 1: Verificar que el frontend responde
curl -I http://localhost:3000

# Debería retornar: HTTP/1.1 200 OK

# Prueba 2: Verificar página de login
curl http://localhost:3000/login

# Debería retornar HTML de la página

# Prueba 3: Verificar conexión con backend
curl http://localhost:8000/api/

# Debería retornar respuesta del backend
```

**Verificación desde navegador:**
1. Abrir: `https://tu-dominio.com`
2. Verificar que se carga la página de login
3. Probar hacer login con credenciales válidas
4. Verificar que el dashboard se carga
5. Probar navegación entre páginas
6. Verificar que la consola del navegador no tenga errores

### Paso 11: Configurar Nginx/Reverse Proxy (si aplica)

Si usas Nginx como reverse proxy:

```bash
# Editar configuración de Nginx
sudo nano /etc/nginx/sites-available/vozipomni
```

**Configuración recomendada:**

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    # Redirigir a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com;

    # Certificados SSL
    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;

    # Frontend Nuxt 3
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Static files
    location /static/ {
        alias /ruta/a/vozipomni/backend/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /ruta/a/vozipomni/backend/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

```bash
# Verificar configuración de Nginx
sudo nginx -t

# Si está OK, recargar Nginx
sudo systemctl reload nginx
```

### Paso 12: Monitoreo Post-Deploy (10 minutos)

```bash
# Monitorear logs de todos los servicios
sudo docker-compose logs -f

# En otra terminal, monitorear recursos
sudo docker stats

# Verificar memoria y CPU
htop

# Verificar espacio en disco
df -h
```

---

## 🔍 Verificación Completa del Sistema

### Checklist de Verificación

```bash
# 1. Contenedores corriendo
sudo docker-compose ps
# ✅ Todos los servicios deben estar "Up"

# 2. Frontend accesible
curl -I http://localhost:3000
# ✅ HTTP/1.1 200 OK

# 3. Backend accesible
curl -I http://localhost:8000/api/
# ✅ HTTP/1.1 200 OK

# 4. Base de datos conectada
sudo docker-compose exec backend python manage.py check
# ✅ System check identified no issues

# 5. Redis funcionando
sudo docker-compose exec redis redis-cli ping
# ✅ PONG

# 6. Logs sin errores críticos
sudo docker-compose logs --tail=100 | grep -i error
# ✅ Sin errores críticos
```

### Pruebas Funcionales

1. **Login**
   - ✅ Página de login carga correctamente
   - ✅ Login con credenciales válidas funciona
   - ✅ Error con credenciales inválidas
   - ✅ Redirección a dashboard después de login

2. **Navegación**
   - ✅ Todas las páginas cargan sin errores
   - ✅ Breadcrumbs se actualizan correctamente
   - ✅ Sidebar funciona
   - ✅ Logout funciona

3. **API**
   - ✅ Llamadas a API funcionan
   - ✅ Tokens JWT se envían correctamente
   - ✅ Errores 401 redirigen a login

4. **UI/UX**
   - ✅ Diseño responsive funciona
   - ✅ Iconos se muestran correctamente
   - ✅ Colores y estilos correctos
   - ✅ Sin errores en consola del navegador

---

## 🚨 Rollback - Si Algo Sale Mal

### Opción 1: Restaurar desde Backup de Imagen

```bash
# Detener servicios actuales
sudo docker-compose down

# Etiquetar backup como latest
sudo docker tag vozipomni-frontend:backup-YYYYMMDD vozipomni-frontend:latest

# Iniciar con la versión anterior
sudo docker-compose up -d

# Verificar
sudo docker-compose logs -f frontend
```

### Opción 2: Restaurar desde Backup de Archivos

```bash
# Detener servicios
sudo docker-compose down

# Restaurar archivos
rm -rf frontend
cp -r frontend.backup.YYYYMMDD frontend

# Restaurar docker-compose.yml
cp docker-compose.yml.backup docker-compose.yml

# Reconstruir e iniciar
sudo docker-compose build frontend
sudo docker-compose up -d
```

### Opción 3: Rollback con Git

```bash
# Ver historial de commits
git log --oneline

# Volver a commit anterior
git reset --hard COMMIT_HASH

# Reconstruir
sudo docker-compose build frontend
sudo docker-compose up -d
```

---

## 🔧 Solución de Problemas Comunes

### Problema: Error al construir la imagen

```bash
# Verificar espacio en disco
df -h

# Limpiar caché de Docker
sudo docker builder prune -a

# Construir sin caché
sudo docker-compose build --no-cache frontend
```

### Problema: Frontend no inicia

```bash
# Ver logs detallados
sudo docker-compose logs frontend

# Verificar puerto 3000 disponible
sudo netstat -tlnp | grep 3000

# Reiniciar contenedor
sudo docker-compose restart frontend
```

### Problema: Error de conexión con backend

```bash
# Verificar red de Docker
sudo docker network ls
sudo docker network inspect vozipomni-network

# Verificar que backend está corriendo
sudo docker-compose ps backend

# Probar conexión desde frontend a backend
sudo docker-compose exec frontend ping backend
```

### Problema: Página en blanco

```bash
# Ver consola del navegador (F12)
# Buscar errores de JavaScript

# Verificar variables de entorno
sudo docker-compose exec frontend env | grep NUXT

# Reconstruir sin caché
sudo docker-compose build --no-cache frontend
sudo docker-compose up -d frontend
```

---

## 📊 Monitoreo Continuo

### Configurar Logs Permanentes

```bash
# Crear directorio de logs
mkdir -p /var/log/vozipomni

# Configurar rotación de logs en docker-compose.yml
```

Agregar a cada servicio en docker-compose.yml:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Script de Monitoreo

```bash
# Crear script de monitoreo
cat > /usr/local/bin/vozipomni-health-check.sh << 'EOF'
#!/bin/bash

# Verificar servicios
docker-compose ps | grep -q "Up" || echo "ERROR: Servicios caídos"

# Verificar frontend
curl -f http://localhost:3000 > /dev/null 2>&1 || echo "ERROR: Frontend no responde"

# Verificar backend
curl -f http://localhost:8000/api/ > /dev/null 2>&1 || echo "ERROR: Backend no responde"

echo "Health check completado: $(date)"
EOF

# Dar permisos de ejecución
chmod +x /usr/local/bin/vozipomni-health-check.sh

# Agregar a cron (cada 5 minutos)
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/vozipomni-health-check.sh >> /var/log/vozipomni/health.log 2>&1") | crontab -
```

---

## 📝 Comandos Útiles de Mantenimiento

```bash
# Ver estado de todos los servicios
sudo docker-compose ps

# Ver logs en tiempo real
sudo docker-compose logs -f

# Ver logs de un servicio específico
sudo docker-compose logs -f frontend

# Reiniciar un servicio
sudo docker-compose restart frontend

# Detener todos los servicios
sudo docker-compose down

# Iniciar todos los servicios
sudo docker-compose up -d

# Reconstruir un servicio
sudo docker-compose build frontend
sudo docker-compose up -d frontend

# Ver uso de recursos
sudo docker stats

# Limpiar contenedores detenidos
sudo docker container prune

# Limpiar imágenes sin usar
sudo docker image prune -a

# Ver volúmenes
sudo docker volume ls

# Backup de volumen de base de datos
sudo docker run --rm -v vozipomni_postgres_data:/data -v $(pwd):/backup ubuntu tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz /data
```

---

## ✅ Checklist Final

- [ ] Backup realizado
- [ ] Código actualizado desde Git
- [ ] Variables de entorno configuradas
- [ ] docker-compose.yml actualizado
- [ ] Imagen construida sin errores
- [ ] Servicios iniciados correctamente
- [ ] Frontend accesible en navegador
- [ ] Login funciona
- [ ] Dashboard carga correctamente
- [ ] Navegación funciona
- [ ] API responde correctamente
- [ ] WebSocket configurado (si aplica)
- [ ] Nginx configurado y recargado
- [ ] SSL funcionando
- [ ] Logs sin errores críticos
- [ ] Monitoreo configurado
- [ ] Documentación actualizada
- [ ] Equipo notificado

---

## 🎯 Tiempo Total Estimado

- **Preparación y Backup:** 5 minutos
- **Actualización de código:** 5 minutos
- **Configuración:** 5 minutos
- **Construcción:** 10 minutos
- **Deploy:** 5 minutos
- **Verificación:** 10 minutos
- **Total:** ~40 minutos

---

## 📞 En Caso de Emergencia

Si necesitas ayuda urgente durante el deploy:

1. **No entrar en pánico** - Tienes backups
2. **Documentar el error** - Capturar logs y screenshots
3. **Hacer rollback** - Usar una de las opciones de rollback
4. **Contactar soporte** - Con logs y descripción del problema

---

**¡Deploy completado! El frontend Nuxt 3 está en producción. 🚀**
