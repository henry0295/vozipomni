# 🚀 Guía de Deployment - VoziPOmni

## Resumen de Cambios Implementados

✅ **Backend:**
- Agregado método `pjsip_show_registrations()` en `asterisk_ami.py`
- Agregado método `get_trunk_registration_status()` en `asterisk_ami.py`
- Agregados campos `registration_status` y `registration_detail` en `SIPTrunkSerializer`

✅ **Frontend:**
- Nueva columna "Registro" en la tabla de troncales (`Trunks.jsx`)
- Estilos para badges de estado (.registered, .error, .warning, .info)
- Muestra estado en tiempo real desde Asterisk

---

## 📋 Proceso Completo de Deployment

### PASO 1: Subir Cambios a Git (Desde Windows)

Opción A - Script Automático (Recomendado):
```powershell
# En PowerShell de VS Code
.\deploy.ps1
```

Opción B - Manual:
```powershell
# Ver cambios
git status

# Agregar todos los archios
git add .

# Crear commit
git commit -m "feat: Agregar columna de estado de registro en troncales SIP"

# Subir a GitHub
git push origin main
```

---

### PASO 2: Actualizar en el Servidor (Linux)

#### Opción A - Script Automático (Recomendado):

```bash
# Conectar al servidor
ssh usuario@IP_SERVIDOR

# Ir al directorio del proyecto
cd /opt/vozipomni

# Dar permisos al script
chmod +x deploy-server.sh

# Ejecutar deployment
./deploy-server.sh
```

#### Opción B - Manual:

```bash
# Conectar al servidor
ssh usuario@IP_SERVIDOR

# Ir al directorio del proyecto
cd /opt/vozipomni

# Guardar cambios locales si existen
git stash

# Obtener últimos cambios
git pull origin main

# Reiniciar servicios backend
docker compose restart backend celery_worker

# Verificar logs
docker compose logs backend -f
```

---

## 🔍 Verificación del Deployment

### 1. Verificar que el Backend se reinició correctamente:

```bash
# Ver logs del backend
docker compose logs backend --tail=50

# Buscar mensaje de inicio
docker compose logs backend | grep "Starting"
```

### 2. Verificar la API:

```bash
# Desde el servidor o desde navegador
curl http://localhost:8000/api/telephony/trunks/
```

Deberías ver en la respuesta el campo `registration_detail`:

```json
{
  "id": 1,
  "name": "trunk_principal",
  "registration_status": "registered",
  "registration_detail": {
    "text": "Registrado",
    "class": "success",
    "icon": "✓"
  }
}
```

### 3. Verificar la Interfaz:

1. Abrir navegador en: `http://IP_SERVIDOR:5173`
2. Ir a **Configuración → Troncales SIP**
3. Verificar que aparece la columna **"Registro"**
4. Verificar que muestra badges de estado (verde, rojo, amarillo)

---

## 🐛 Solución de Problemas

### Problema: La columna "Registro" no aparece en la UI

**Solución 1 - Limpiar caché del navegador:**
```
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)
```

**Solución 2 - Reiniciar Frontend en el servidor:**
```bash
ssh usuario@IP_SERVIDOR
cd /opt/vozipomni
docker compose restart frontend
```

**Solución 3 - Frontend en desarrollo local:**
```powershell
# En Windows (VS Code)
.\restart-frontend.ps1
```

---

### Problema: El estado muestra "Desconocido"

**Causa:** Asterisk no tiene configuradas las troncales con registro

**Solución:**
```bash
# Verificar registros en Asterisk
docker compose exec asterisk asterisk -rx "pjsip show registrations"

# Si está vacío, configurar troncal con registro
docker compose exec asterisk asterisk -rvvv
```

Agregar en `/etc/asterisk/pjsip.conf`:
```ini
[trunk_voip_provider]
type=registration
transport=transport-udp
outbound_auth=trunk_voip_provider-auth
server_uri=sip:provider.com
client_uri=sip:tu_usuario@provider.com
retry_interval=60

[trunk_voip_provider-auth]
type=auth
auth_type=userpass
username=tu_usuario
password=tu_contraseña
```

Luego recargar:
```bash
docker compose exec asterisk asterisk -rx "pjsip reload"
docker compose exec asterisk asterisk -rx "pjsip show registrations"
```

---

### Problema: Error 500 en la API

**Solución:**
```bash
# Ver logs detallados
docker compose logs backend --tail=100

# Verificar que Asterisk responde
docker compose exec backend python manage.py shell

# En la shell de Python
from apps.telephony.asterisk_ami import AsteriskAMI
ami = AsteriskAMI()
ami.connect()
ami.pjsip_show_registrations()
ami.disconnect()
```

---

## 📊 Comandos Útiles Post-Deployment

```bash
# Ver estado de contenedores
docker compose ps

# Ver logs en tiempo real
docker compose logs -f backend

# Reiniciar solo backend
docker compose restart backend

# Reiniciar todo
docker compose restart

# Ver uso de recursos
docker stats

# Acceder a consola Asterisk
docker compose exec asterisk asterisk -rvvv
```

---

## 🔄 Rollback (Si algo sale mal)

```bash
# Conectar al servidor
ssh usuario@IP_SERVIDOR
cd /opt/vozipomni

# Ver commits recientes
git log --oneline -5

# Volver al commit anterior
git reset --hard HEAD~1

# Reiniciar servicios
docker compose restart backend celery_worker

# O volver a un commit específico
git reset --hard <commit_hash>
docker compose restart backend celery_worker
```

---

## ✅ Checklist Final

- [ ] Cambios subidos a Git desde Windows
- [ ] Git pull ejecutado en servidor
- [ ] Backend reiniciado correctamente
- [ ] API responde con campo `registration_detail`
- [ ] Columna "Registro" visible en la interfaz
- [ ] Estados se muestran correctamente (verde/rojo/amarillo)
- [ ] Logs del backend sin errores

---

## 📞 Contacto

Si encuentras problemas durante el deployment, verifica:

1. ✅ Logs del backend: `docker compose logs backend`
2. ✅ Conexión AMI a Asterisk: `docker compose exec backend python manage.py shell`
3. ✅ Estado de Asterisk: `docker compose exec asterisk asterisk -rvvv`
4. ✅ Configuración PJSIP: `docker compose exec asterisk cat /etc/asterisk/pjsip.conf`
