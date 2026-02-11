# ✅ CHECKLIST DE DEPLOY - Frontend Nuxt 3

## Pre-Deploy (5 minutos)

### 1. Verificar Acceso
- [ ] SSH al servidor funcional
- [ ] Usuario tiene permisos sudo/docker
- [ ] Conexión estable

### 2. Verificar Estado Actual
```bash
cd /ruta/a/vozipomni
docker-compose ps
git status
```
- [ ] Backend corriendo
- [ ] PostgreSQL corriendo
- [ ] Redis corriendo
- [ ] No hay cambios sin commitear

### 3. Hacer Commit de Cambios Locales
Si trabajaste en local, hacer push primero:
```bash
git add .
git commit -m "Migración a Nuxt 3"
git push origin main
```
- [ ] Cambios commiteados
- [ ] Push exitoso
- [ ] Rama principal actualizada

---

## Deploy (10-15 minutos)

### OPCIÓN A: Script Automatizado ⭐ (RECOMENDADO)

```bash
# Copiar scripts al servidor si no están
scp deploy-frontend.sh usuario@servidor:/ruta/a/vozipomni/
ssh usuario@servidor

# En el servidor
cd /ruta/a/vozipomni
chmod +x deploy-frontend.sh
./deploy-frontend.sh
```

**El script hace:**
- ✅ Backup automático
- ✅ Git pull
- ✅ Docker build
- ✅ Docker up
- ✅ Verificación

**Ir a: Post-Deploy Verification**

---

### OPCIÓN B: Comandos Manuales (15 minutos)

#### 1. Conectar al Servidor
```bash
ssh usuario@tu-servidor.com
cd /ruta/a/vozipomni
```
- [ ] Conectado al servidor
- [ ] En directorio correcto

#### 2. Crear Backup
```bash
# Backup de imagen actual
docker commit vozipomni-frontend vozipomni-frontend:backup-$(date +%Y%m%d)

# Backup de archivos
tar -czf backup-frontend-$(date +%Y%m%d).tar.gz frontend/
```
- [ ] Imagen backup creada
- [ ] Archivos backup creados
- [ ] Verificar con `docker images | grep backup`

#### 3. Actualizar Código
```bash
git pull origin main
```
- [ ] Pull exitoso
- [ ] Sin conflictos
- [ ] Verificar `git log -1`

#### 4. Configurar Variables de Entorno
```bash
cd frontend
nano .env
```

**Agregar:**
```env
NUXT_PUBLIC_API_BASE=https://api.tu-dominio.com/api
NUXT_PUBLIC_WS_BASE=wss://api.tu-dominio.com/ws
NUXT_PUBLIC_APP_NAME=VozipOmni
NUXT_PUBLIC_APP_URL=https://tu-dominio.com
NODE_ENV=production
```
- [ ] .env creado
- [ ] URLs correctas
- [ ] NODE_ENV=production

#### 5. Detener Frontend Actual
```bash
cd ..
docker-compose stop frontend
```
- [ ] Servicio detenido
- [ ] Verificar con `docker-compose ps`

#### 6. Construir Nueva Imagen
```bash
docker-compose build --no-cache frontend
```
- [ ] Build exitoso
- [ ] Sin errores
- [ ] Tiempo: ~3-8 minutos

#### 7. Iniciar Servicio
```bash
docker-compose up -d frontend
```
- [ ] Servicio iniciado
- [ ] Estado: Up
- [ ] Verificar con `docker-compose ps`

---

## Post-Deploy Verification (5 minutos)

### 1. Verificar Contenedores
```bash
docker-compose ps
```

**Esperado:**
```
NAME                  STATUS
vozipomni-frontend    Up
vozipomni-backend     Up
vozipomni-postgres    Up
```
- [ ] Frontend: Up
- [ ] Backend: Up
- [ ] PostgreSQL: Up

### 2. Ver Logs (Primeros 30 segundos)
```bash
docker-compose logs -f --tail=100 frontend
```

**Buscar:**
- ✅ "Listening on http://0.0.0.0:3000"
- ✅ "Nuxt is ready"
- ❌ Sin errores de compilación
- ❌ Sin errores de conexión

- [ ] Logs sin errores
- [ ] Puerto 3000 listening
- [ ] Presionar Ctrl+C para salir

### 3. Test de Conectividad
```bash
curl http://localhost:3000
```
- [ ] Retorna HTML
- [ ] Contiene "VozipOmni" o similar
- [ ] No retorna error 502/503

### 4. Test de API Backend
```bash
curl http://localhost:8000/api/health/
```
- [ ] Retorna {"status":"ok"}
- [ ] Backend accesible

### 5. Test en Navegador
Abrir: `https://tu-dominio.com`

- [ ] Página carga
- [ ] Diseño visible
- [ ] Sin errores en consola (F12)
- [ ] Login accesible

### 6. Test de Login
Intentar login con usuario de prueba:

- [ ] Formulario funcional
- [ ] Login exitoso
- [ ] Redirección a dashboard
- [ ] Token guardado
- [ ] Header con usuario visible

### 7. Test de Navegación
Probar páginas principales:

- [ ] /dashboard - Estadísticas visibles
- [ ] /agents - Tabla de agentes
- [ ] /queues - Cards de colas
- [ ] /campaigns - Lista de campañas
- [ ] /contacts - Contactos cargados

---

## Nginx Update (5 minutos)

Si usas Nginx como reverse proxy:

### 1. Editar Configuración
```bash
sudo nano /etc/nginx/sites-available/vozipomni
```

### 2. Actualizar Location
```nginx
# Frontend Nuxt 3
location / {
    proxy_pass http://localhost:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```
- [ ] Location actualizado
- [ ] Headers agregados

### 3. Verificar Sintaxis
```bash
sudo nginx -t
```
- [ ] Syntax OK
- [ ] Test successful

### 4. Recargar Nginx
```bash
sudo systemctl reload nginx
```
- [ ] Nginx recargado
- [ ] Sin errores

### 5. Test Final
```bash
curl https://tu-dominio.com
```
- [ ] Retorna HTML
- [ ] HTTPS funcional

---

## Monitoreo Post-Deploy (24 horas)

### Inmediato (Primera hora)
```bash
# Ver logs en tiempo real
docker-compose logs -f frontend

# Verificar uso de recursos
docker stats vozipomni-frontend
```
- [ ] Sin errores en logs
- [ ] CPU < 50%
- [ ] RAM < 512MB

### Primera hora
- [ ] No hay reinicios del contenedor (`docker-compose ps`)
- [ ] Logs estables sin errores repetitivos
- [ ] Usuarios pueden acceder

### Primeras 24 horas
- [ ] Sistema estable
- [ ] Rendimiento normal
- [ ] Sin quejas de usuarios

---

## 🚨 Troubleshooting

### Problema: Contenedor no inicia

```bash
docker-compose logs frontend
```

**Causas comunes:**
- Error en .env
- Puerto 3000 en uso
- Falta espacio en disco

**Solución:**
```bash
# Verificar puerto
sudo lsof -i :3000

# Liberar espacio
docker system prune -a

# Reconstruir
docker-compose up -d --force-recreate frontend
```

### Problema: 502 Bad Gateway

**Causa:** Frontend no responde en puerto 3000

**Solución:**
```bash
# Verificar que esté escuchando
curl http://localhost:3000

# Reiniciar
docker-compose restart frontend
```

### Problema: Login no funciona

**Causa:** Backend no accesible o CORS

**Solución:**
```bash
# Verificar backend
curl http://localhost:8000/api/health/

# Ver logs backend
docker-compose logs backend | grep CORS
```

### Problema: Cambios no se ven

**Causa:** Cache del navegador o imagen antigua

**Solución:**
```bash
# Reconstruir sin cache
docker-compose build --no-cache frontend
docker-compose up -d frontend

# Limpiar cache navegador: Ctrl+Shift+R
```

---

## 🔄 Rollback

Si algo falla y necesitas volver atrás:

### Método 1: Restaurar Imagen Backup
```bash
docker tag vozipomni-frontend:backup-YYYYMMDD vozipomni-frontend:latest
docker-compose up -d frontend
```
- [ ] Imagen restaurada
- [ ] Servicio reiniciado
- [ ] Sistema funcional

### Método 2: Git Revert
```bash
git log --oneline
git revert <commit-hash>
docker-compose build frontend
docker-compose up -d frontend
```
- [ ] Commit revertido
- [ ] Imagen reconstruida
- [ ] Deploy anterior activo

### Método 3: Restaurar Archivos
```bash
tar -xzf backup-frontend-YYYYMMDD.tar.gz
docker-compose build frontend
docker-compose up -d frontend
```
- [ ] Archivos restaurados
- [ ] Imagen reconstruida
- [ ] Funcional

---

## ✅ Deploy Exitoso

**Checklist Final:**

- [ ] ✅ Contenedores corriendo
- [ ] ✅ Logs sin errores
- [ ] ✅ Frontend accesible en navegador
- [ ] ✅ Login funcional
- [ ] ✅ Navegación entre páginas funciona
- [ ] ✅ Backend comunicándose correctamente
- [ ] ✅ Nginx configurado (si aplica)
- [ ] ✅ Backup creado
- [ ] ✅ Monitoreo activo

---

## 📊 Métricas de Éxito

Después de 24 horas:

- **Uptime:** > 99%
- **Tiempo de respuesta:** < 1 segundo
- **Errores en logs:** 0 críticos
- **Usuarios activos:** Sin interrupciones
- **Memoria:** < 512MB
- **CPU:** < 30% promedio

---

## 📞 Soporte

**Si algo falla:**

1. Revisar logs: `docker-compose logs frontend`
2. Consultar: DEPLOY_FRONTEND_NUXT3.md
3. Ejecutar rollback si es crítico

**Archivos de ayuda:**
- DEPLOY_FRONTEND_NUXT3.md - Guía completa
- DEPLOY_QUICK_START.md - Comandos rápidos
- RESUMEN_DEPLOY.md - Resumen ejecutivo
- deploy-frontend.sh - Script automatizado

---

## 🎉 ¡Deploy Completado!

**Frontend Nuxt 3 desplegado exitosamente.**

**Siguiente paso:**
- Monitorear primera hora
- Comunicar a usuarios
- Documentar lecciones aprendidas

**Backup disponible en:**
- Imagen: `vozipomni-frontend:backup-YYYYMMDD`
- Archivos: `backup-frontend-YYYYMMDD.tar.gz`

---

**Fecha de deploy:** _________________  
**Desplegado por:** _________________  
**Versión:** Nuxt 3.10.3  
**Tiempo total:** _______ minutos
