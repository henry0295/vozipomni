# Solución a Errores 502 Bad Gateway y 404 en Iconos

## 🔴 Problemas Identificados

1. **Error 502 Bad Gateway** en `/api/auth/login/`
   - El backend Django no está respondiendo
   - Posiblemente no está en ejecución o tiene errores

2. **Error 404 Not Found** en `/api/_nuxt_icon/heroicons.json`
   - Nginx estaba devolviendo 204 No Content para iconos
   - Las rutas de iconos no estaban configuradas correctamente

## ✅ Correcciones Aplicadas

### 1. Configuración de Nginx Corregida
- ✅ Agregadas rutas para `/api/_nuxt_icon/` y `/_nuxt_icon/`
- ✅ Iconos ahora se envían correctamente al frontend
- ✅ Configuración HTTP habilitada por defecto (sin SSL)
- ✅ HTTPS comentado para configurar después con Let's Encrypt

### 2. Script de Corrección Rápida
- ✅ Creado `fix-server.sh` para aplicar correcciones automáticamente

## 📋 Pasos para Aplicar la Solución en Producción

### Opción A: Corrección Rápida (Recomendada si ya tienes VoziPOmni instalado)

Conéctate al servidor de producción y ejecuta:

```bash
# Ir al directorio de instalación
cd /opt/vozipomni

# Actualizar código desde GitHub
git pull origin main

# Ejecutar script de corrección
chmod +x fix-server.sh
./fix-server.sh
```

El script `fix-server.sh` hará:
1. ✅ Actualizar el código desde GitHub
2. ✅ Reconstruir el contenedor de Nginx con la nueva configuración
3. ✅ Reiniciar todos los servicios
4. ✅ Verificar que todo esté funcionando

### Opción B: Instalación Limpia (Si la corrección rápida no funciona)

Si persisten los errores, haz una instalación completamente limpia:

```bash
# Detener y eliminar instalación anterior
cd /opt/vozipomni
docker compose down -v

# Eliminar directorio
cd /opt
rm -rf vozipomni

# Hacer instalación limpia
export VOZIPOMNI_IPV4=172.21.207.121
curl -o install.sh -L "https://raw.githubusercontent.com/henry0295/vozipomni/main/install.sh"
chmod +x install.sh
./install.sh
```

## 🔍 Verificación Después de Aplicar Corrección

### 1. Verificar que los servicios están corriendo

```bash
cd /opt/vozipomni
docker compose ps
```

Deberías ver todos los servicios en estado **Up**:
- nginx
- frontend
- backend
- postgres
- redis
- asterisk
- celery
- websocket

### 2. Verificar logs del backend

Si el error 502 persiste, revisa los logs:

```bash
docker compose logs backend | tail -50
```

Busca errores como:
- ❌ Errores de base de datos
- ❌ Errores de migración
- ❌ Errores de conexión

### 3. Verificar que el backend está escuchando

```bash
docker compose exec backend python manage.py check
```

Este comando debe retornar: `System check identified no issues (0 silenced).`

### 4. Probar el endpoint de salud

```bash
curl http://172.21.207.121/health
```

Debe retornar: `healthy`

### 5. Probar los iconos

Abre el navegador y ve a:
```
http://172.21.207.121/_nuxt_icon/heroicons.json
```

Debe cargar un archivo JSON con los iconos, NO un error 404.

## 🐛 Diagnóstico de Error 502 (Backend no responde)

Si después de aplicar la corrección de Nginx, **aún tienes error 502**, el problema está en el backend Django:

### Paso 1: Ver logs del backend

```bash
docker compose logs backend -f
```

### Paso 2: Verificar que las migraciones están aplicadas

```bash
docker compose exec backend python manage.py showmigrations
```

Todas las migraciones deben tener una `[X]` (aplicadas).

### Paso 3: Verificar conexión a base de datos

```bash
docker compose exec backend python manage.py dbshell
```

Si conecta correctamente, escribe `\q` para salir.

### Paso 4: Intentar correr el backend manualmente

```bash
docker compose exec backend python manage.py runserver 0.0.0.0:8000
```

Observa si hay errores en el inicio del servidor.

## 📊 Estado Esperado Después de la Corrección

### ✅ Iconos Funcionando
```
GET http://172.21.207.121/_nuxt_icon/heroicons.json [200 OK]
```

### ✅ API Funcionando
```
POST http://172.21.207.121/api/auth/login/ [200 OK]
```

### ✅ Frontend Cargando
```
GET http://172.21.207.121/ [200 OK]
```

## 🔧 Comandos Útiles Post-Corrección

```bash
# Ver todos los logs en tiempo real
docker compose logs -f

# Reiniciar solo nginx (si cambias configuración)
docker compose restart nginx

# Reiniciar solo backend
docker compose restart backend

# Reiniciar todo
docker compose restart

# Ver estado de contenedores
docker compose ps

# Ver uso de recursos
docker stats
```

## 📞 Si Aún Hay Problemas

1. **Captura los logs completos:**
   ```bash
   docker compose logs > ~/logs_vozipomni.txt
   ```

2. **Verifica la configuración de Nginx:**
   ```bash
   docker compose exec nginx cat /etc/nginx/conf.d/default.conf
   ```

3. **Verifica las variables de entorno:**
   ```bash
   docker compose config
   ```

4. **Comparte los logs** para análisis detallado.

## 🎯 Resumen

**Problema:** Nginx no estaba enviando las peticiones de iconos al frontend, y el backend no estaba respondiendo.

**Solución:** 
1. ✅ Nginx configurado correctamente para enrutar iconos al frontend
2. ✅ Script `fix-server.sh` para aplicar correcciones rápidamente
3. ⚠️ Backend 502 requiere diagnóstico adicional (ver sección de diagnóstico)

**Siguiente paso:** Ejecuta `fix-server.sh` en el servidor de producción y verifica el estado.
