# Configuración para Producción - VozipOmni

## 🚀 Guía de Configuración para Producción

### 1. Variables de Entorno

#### Copiar y configurar .env
```bash
# Copiar el archivo de ejemplo
cp .env.production .env

# Editar con valores reales
nano .env
```

#### Variables CRÍTICAS que DEBES cambiar:

1. **SECRET_KEY**: Clave secreta de Django
   ```bash
   # Generar una nueva:
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

2. **POSTGRES_PASSWORD / DB_PASSWORD**: Contraseña de la base de datos
   - Usar una contraseña fuerte (mínimo 16 caracteres)

3. **REDIS_PASSWORD**: Contraseña de Redis
   - Usar una contraseña fuerte (mínimo 16 caracteres)

4. **ASTERISK_AMI_PASSWORD**: Contraseña de Asterisk AMI
   - Usar una contraseña fuerte

5. **ALLOWED_HOSTS**: Dominios permitidos
   ```env
   ALLOWED_HOSTS=localhost,127.0.0.1,backend,tudominio.com,www.tudominio.com,172.21.207.121
   ```

6. **CORS_ORIGINS**: Orígenes CORS permitidos
   ```env
   CORS_ORIGINS=https://tudominio.com,https://www.tudominio.com,http://172.21.207.121
   CORS_ALLOW_ALL=False
   ```

### 2. Problemas Solucionados

#### ✅ Problema 1: Iconos no cargan (404)
**Solución implementada:**
- Agregado `serverBundle` en nuxt.config.ts para pre-bundle de iconos
- Configuración de Nginx actualizada para manejar `/_nuxt_icon/`

#### ✅ Problema 2: Errores 401 en API
**Solución implementada:**
- Middleware de autenticación mejorado para cargar token desde localStorage
- useApi mejorado para manejar errores 401 correctamente
- El token ahora se carga antes de hacer peticiones

#### ✅ Problema 3: CORS inseguro
**Solución implementada:**
- `CORS_ALLOW_ALL` cambiado a `False` por defecto
- Configuración explícita de orígenes permitidos

### 3. Configuración de Nginx

El archivo `docker/nginx/default.prod.conf` ya está configurado correctamente:

- ✅ Redirección HTTP → HTTPS
- ✅ Headers de seguridad
- ✅ Rate limiting para API y autenticación
- ✅ Manejo de iconos de Nuxt
- ✅ Compresión gzip
- ✅ Cache para assets estáticos

### 4. SSL/TLS (HTTPS)

#### Opción A: Certificados auto-firmados (desarrollo/testing)
```bash
# Crear directorio para certificados
mkdir -p ssl

# Generar certificados auto-firmados
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem \
  -out ssl/fullchain.pem \
  -subj "/C=CO/ST=Bogota/L=Bogota/O=VozipOmni/CN=tudominio.com"
```

#### Opción B: Let's Encrypt (producción real)
```bash
# Instalar certbot
sudo apt-get install certbot

# Obtener certificados
sudo certbot certonly --standalone -d tudominio.com -d www.tudominio.com

# Copiar certificados a la carpeta ssl/
sudo cp /etc/letsencrypt/live/tudominio.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/tudominio.com/privkey.pem ssl/
```

### 5. Despliegue

#### Paso 1: Preparar entorno
```bash
# Asegurarse de que .env esté configurado
cat .env

# Verificar que los certificados SSL existan
ls -la ssl/
```

#### Paso 2: Construir imágenes
```bash
# Construir todas las imágenes
docker-compose -f docker-compose.prod.yml build
```

#### Paso 3: Iniciar servicios
```bash
# Iniciar en modo daemon
docker-compose -f docker-compose.prod.yml up -d

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### Paso 4: Ejecutar migraciones
```bash
# Ejecutar migraciones de Django
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Crear superusuario
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Recolectar archivos estáticos
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### 6. Verificación

#### Verificar servicios
```bash
# Ver estado de contenedores
docker-compose -f docker-compose.prod.yml ps

# Verificar logs
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend
docker-compose -f docker-compose.prod.yml logs nginx
```

#### Verificar endpoints
```bash
# Health check
curl http://localhost/health

# API (debería retornar 401 sin autenticación)
curl http://localhost/api/telephony/inbound-routes/

# Frontend (debería retornar HTML)
curl http://localhost/
```

### 7. Monitoreo

#### Logs en tiempo real
```bash
# Todos los servicios
docker-compose -f docker-compose.prod.yml logs -f

# Solo backend
docker-compose -f docker-compose.prod.yml logs -f backend

# Solo nginx
docker-compose -f docker-compose.prod.yml logs -f nginx
```

#### Métricas de recursos
```bash
# Ver uso de recursos
docker stats

# Ver logs de nginx
tail -f logs/nginx/vozipomni_access.log
tail -f logs/nginx/vozipomni_error.log
```

### 8. Backup

#### Base de datos
```bash
# Backup manual
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U vozipomni_user vozipomni > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U vozipomni_user vozipomni < backup_20260212.sql
```

#### Archivos de medios
```bash
# Backup de archivos
tar -czf media_backup_$(date +%Y%m%d).tar.gz -C /var/lib/docker/volumes/vozipomni_media_files/_data .

# Restaurar
tar -xzf media_backup_20260212.tar.gz -C /var/lib/docker/volumes/vozipomni_media_files/_data
```

### 9. Troubleshooting

#### Error: Iconos no cargan
```bash
# Verificar que el frontend tenga las dependencias
docker-compose -f docker-compose.prod.yml exec frontend npm list @iconify-json/heroicons

# Reconstruir frontend
docker-compose -f docker-compose.prod.yml build frontend
docker-compose -f docker-compose.prod.yml up -d frontend
```

#### Error: 401 en todas las peticiones
```bash
# Verificar que el token se esté cargando
# Abrir DevTools del navegador → Application → Local Storage
# Verificar que exista 'auth_token'

# Limpiar localStorage y volver a hacer login
localStorage.clear()
```

#### Error: CORS
```bash
# Verificar configuración de CORS en .env
grep CORS .env

# Verificar logs del backend
docker-compose -f docker-compose.prod.yml logs backend | grep CORS
```

### 10. Seguridad

#### Checklist de seguridad:
- [ ] SECRET_KEY cambiada a valor seguro
- [ ] Contraseñas de base de datos cambiadas
- [ ] DEBUG=False en producción
- [ ] CORS_ALLOW_ALL=False
- [ ] CORS_ORIGINS configurado con dominios reales
- [ ] ALLOWED_HOSTS configurado correctamente
- [ ] Certificados SSL válidos
- [ ] Firewall configurado
- [ ] Rate limiting habilitado en Nginx
- [ ] Headers de seguridad configurados

### 11. Actualización

```bash
# Detener servicios
docker-compose -f docker-compose.prod.yml down

# Actualizar código
git pull

# Reconstruir imágenes
docker-compose -f docker-compose.prod.yml build

# Iniciar servicios
docker-compose -f docker-compose.prod.yml up -d

# Ejecutar migraciones
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

## 📞 Soporte

Para problemas o preguntas, revisar:
- [DEPLOY_CHECKLIST.md](DEPLOY_CHECKLIST.md)
- [DIAGNOSTICO_ASTERISK.md](DIAGNOSTICO_ASTERISK.md)
- Logs del sistema: `docker-compose -f docker-compose.prod.yml logs`
