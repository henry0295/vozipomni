# 🚀 GUÍA RÁPIDA DE DEPLOY

## Para Deploy Inmediato en Servidor

### Opción 1: Script Automatizado (Recomendado)

**Linux/Mac:**
```bash
chmod +x deploy-frontend.sh
./deploy-frontend.sh
```

**Windows:**
```powershell
.\deploy-frontend.ps1
```

### Opción 2: Comandos Manuales

```bash
# 1. Backup
docker commit vozipomni-frontend vozipomni-frontend:backup-$(date +%Y%m%d)

# 2. Actualizar código
git pull origin main

# 3. Detener servicios
docker-compose down

# 4. Construir nueva imagen
docker-compose build --no-cache frontend

# 5. Iniciar servicios
docker-compose up -d

# 6. Verificar
docker-compose logs -f frontend
```

## Comandos Docker Compose

```bash
# Construir solo frontend
docker-compose build frontend

# Iniciar solo frontend  
docker-compose up -d frontend

# Ver logs del frontend
docker-compose logs -f frontend

# Detener todo
docker-compose down

# Reiniciar frontend
docker-compose restart frontend

# Ver estado
docker-compose ps
```

## Variables de Entorno Críticas

Crear `frontend/.env`:

```env
NUXT_PUBLIC_API_BASE=https://api.tu-dominio.com/api
NUXT_PUBLIC_WS_BASE=wss://api.tu-dominio.com/ws
NODE_ENV=production
```

## Verificación Rápida

```bash
# ✅ Frontend responde
curl http://localhost:3000

# ✅ Backend responde  
curl http://localhost:8000/api/

# ✅ Ver contenedores
docker ps

# ✅ Ver logs
docker-compose logs --tail=100
```

## Rollback Rápido

```bash
# Opción 1: Desde backup de imagen
docker tag vozipomni-frontend:backup-YYYYMMDD vozipomni-frontend:latest
docker-compose up -d frontend

# Opción 2: Desde Git
git reset --hard HEAD~1
docker-compose build frontend
docker-compose up -d
```

## Nginx (Si aplica)

```bash
# Verificar configuración
sudo nginx -t

# Recargar
sudo systemctl reload nginx

# Ver logs
sudo tail -f /var/log/nginx/error.log
```

## Problemas Comunes

**Error al construir:**
```bash
docker builder prune -a
docker-compose build --no-cache frontend
```

**Frontend no inicia:**
```bash
docker-compose logs frontend
docker-compose restart frontend
```

**Puerto ocupado:**
```bash
sudo netstat -tlnp | grep 3000
# Cambiar puerto en docker-compose.yml
```

## Checklist Mínimo

- [ ] Backup creado
- [ ] Código actualizado
- [ ] `.env` configurado
- [ ] Build exitoso
- [ ] Contenedor corriendo
- [ ] Login funciona
- [ ] Sin errores en logs

## Ayuda

📖 Documentación completa: `DEPLOY_FRONTEND_NUXT3.md`

🚨 Emergencias: Hacer rollback inmediatamente

---

**Tiempo estimado: 10-15 minutos**
