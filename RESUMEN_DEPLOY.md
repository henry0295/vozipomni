# 📦 RESUMEN DE ARCHIVOS PARA DEPLOY

## Archivos Creados para el Deploy

### 📖 Documentación (4 archivos)
1. **DEPLOY_FRONTEND_NUXT3.md** - Guía completa paso a paso (40 min)
2. **DEPLOY_QUICK_START.md** - Comandos rápidos (5 min)
3. **deploy-frontend.sh** - Script automatizado Linux/Mac
4. **deploy-frontend.ps1** - Script automatizado Windows

### ⚙️ Configuración Actualizada (2 archivos)
1. **docker-compose.yml** - Servicio frontend de producción agregado
2. **frontend/Dockerfile.dev** - Dockerfile para desarrollo actualizado

---

## 🚀 Cómo Hacer el Deploy

### Opción 1: Script Automatizado (MÁS FÁCIL)

**En el servidor (Linux/Mac):**
```bash
# Dar permisos de ejecución
chmod +x deploy-frontend.sh

# Ejecutar
./deploy-frontend.sh
```

**En el servidor (Windows):**
```powershell
.\deploy-frontend.ps1
```

El script automáticamente:
- ✅ Crea backups
- ✅ Actualiza código desde Git
- ✅ Construye la nueva imagen
- ✅ Despliega el frontend
- ✅ Verifica que funcione
- ✅ Muestra logs

### Opción 2: Comandos Manuales (RÁPIDO)

```bash
# 1. Conectar al servidor
ssh usuario@tu-servidor.com
cd /ruta/a/vozipomni

# 2. Actualizar código
git pull origin main

# 3. Construir y desplegar
docker-compose build frontend
docker-compose up -d frontend

# 4. Verificar
docker-compose logs -f frontend
```

### Opción 3: Guía Completa (DETALLADO)

Sigue: **DEPLOY_FRONTEND_NUXT3.md**

---

## 📋 Pre-requisitos

Antes de hacer el deploy, asegúrate de tener:

1. ✅ **Acceso SSH** al servidor
2. ✅ **Git configurado** en el servidor
3. ✅ **Docker y Docker Compose** instalados
4. ✅ **Código actualizado** en el repositorio Git
5. ✅ **Variables de entorno** configuradas en `frontend/.env`

---

## 🔧 Configuración Necesaria

### 1. Variables de Entorno

Crear `frontend/.env` en el servidor:

```env
NUXT_PUBLIC_API_BASE=https://api.tu-dominio.com/api
NUXT_PUBLIC_WS_BASE=wss://api.tu-dominio.com/ws
NUXT_PUBLIC_APP_NAME=VozipOmni
NUXT_PUBLIC_APP_URL=https://tu-dominio.com
NODE_ENV=production
```

### 2. Docker Compose

El archivo `docker-compose.yml` ya está actualizado con:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: vozipomni-frontend
  ports:
    - "3000:3000"
  environment:
    - NODE_ENV=production
    - NUXT_PUBLIC_API_BASE=http://backend:8000/api
    - NUXT_PUBLIC_WS_BASE=ws://backend:8000/ws
```

### 3. Nginx (Si usas reverse proxy)

Actualizar `/etc/nginx/sites-available/vozipomni`:

```nginx
# Frontend Nuxt 3
location / {
    proxy_pass http://localhost:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
}
```

---

## ✅ Verificación Post-Deploy

```bash
# 1. Contenedores corriendo
docker-compose ps
# Debe mostrar: vozipomni-frontend Up

# 2. Frontend responde
curl http://localhost:3000
# Debe retornar HTML

# 3. Sin errores en logs
docker-compose logs --tail=50 frontend
# No debe haber errores críticos

# 4. Probar en navegador
# Abrir: https://tu-dominio.com
# Login debe funcionar
```

---

## 🚨 Rollback Rápido

Si algo sale mal:

```bash
# Opción 1: Restaurar imagen backup
docker tag vozipomni-frontend:backup-YYYYMMDD vozipomni-frontend:latest
docker-compose up -d frontend

# Opción 2: Volver a commit anterior
git reset --hard HEAD~1
docker-compose build frontend
docker-compose up -d
```

---

## 📞 Soporte

Si tienes problemas:

1. **Ver logs:**
   ```bash
   docker-compose logs frontend
   ```

2. **Consultar documentación:**
   - DEPLOY_FRONTEND_NUXT3.md (completa)
   - DEPLOY_QUICK_START.md (rápida)

3. **Verificar:**
   - Variables de entorno en `.env`
   - Backend está corriendo
   - Puerto 3000 disponible
   - Espacio en disco suficiente

---

## 🎯 Tiempo Estimado

- **Script automatizado:** 10-15 minutos
- **Comandos manuales:** 5-10 minutos
- **Guía completa:** 30-40 minutos

---

## 📚 Archivos de Referencia

```
vozipomni/
├── DEPLOY_FRONTEND_NUXT3.md    ← Guía completa
├── DEPLOY_QUICK_START.md       ← Comandos rápidos
├── deploy-frontend.sh          ← Script Linux/Mac
├── deploy-frontend.ps1         ← Script Windows
├── docker-compose.yml          ← Configuración actualizada
└── frontend/
    ├── Dockerfile              ← Para producción
    ├── Dockerfile.dev          ← Para desarrollo
    ├── .env.example            ← Template de variables
    └── README.md               ← Documentación frontend
```

---

## 🎉 ¡Todo Listo!

El sistema está preparado para hacer el deploy del nuevo frontend Nuxt 3.

**Siguiente paso:** Ejecutar el script de deploy o seguir los comandos manuales.

**Repositorio:** Asegúrate de hacer `git push` si hiciste cambios locales.

**Backup:** El script automáticamente crea backups antes de desplegar.

---

**¿Necesitas ayuda?** Consulta DEPLOY_FRONTEND_NUXT3.md para más detalles.
