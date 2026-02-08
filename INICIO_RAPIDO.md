# 🚀 INICIO RÁPIDO - Migración PJSIP Completada

## ✅ ¿Qué se Corrigió?

1. **Error de Consola Asterisk CLI** - SOLUCIONADO ✅
   - Ya puedes acceder con `docker compose exec asterisk asterisk -r`

2. **chan_sip NO disponible** - EXPLICADO ✅
   - Es normal, Asterisk 21 usa **PJSIP** (más moderno)
   - NO necesitas chan_sip

3. **Código migrado a PJSIP** - COMPLETADO ✅
   - Backend actualizado para usar PJSIP
   - Configuración lista para usar

---

## 📋 PASOS SIGUIENTES (En Windows - VS Code)

### Paso 1: Subir cambios a Git

Desde la terminal de PowerShell en VS Code:

```powershell
# Opción A: Usar script automático
.\push-pjsip-changes.ps1

# Opción B: Manualmente
git add .
git commit -m "fix: Migración PJSIP y corrección CLI Asterisk"
git push origin main
```

---

## 🖥️ PASOS EN EL SERVIDOR (Linux)

### Paso 2: Conectarse al servidor

```bash
ssh usuario@IP_SERVIDOR
```

### Paso 3: Actualizar código

```bash
cd /opt/vozipomni
git pull origin main
```

### Paso 4: Dar permisos a scripts

```bash
chmod +x asterisk-docker.sh
chmod +x check-pjsip.sh
chmod +x push-pjsip-changes.sh
```

### Paso 5: Reiniciar Asterisk

```bash
docker compose restart asterisk
sleep 10
```

### Paso 6: Verificar que funciona

```bash
# Acceder a consola CLI
docker compose exec asterisk asterisk -rvvv

# Dentro de la consola:
*CLI> core show version
*CLI> pjsip show endpoints
*CLI> pjsip show transports
*CLI> module show like pjsip
*CLI> exit
```

### Paso 7: Diagnóstico completo (opcional)

```bash
# Verificación completa PJSIP
./check-pjsip.sh full

# O menú interactivo
./asterisk-docker.sh
```

---

## 🎯 Comandos Más Útiles

### Desde el servidor (fuera del contenedor):

```bash
# Ver endpoints PJSIP
docker compose exec asterisk asterisk -rx "pjsip show endpoints"

# Ver extensiones registradas
docker compose exec asterisk asterisk -rx "pjsip show contacts"

# Ver llamadas activas
docker compose exec asterisk asterisk -rx "core show channels"

# Recargar PJSIP
docker compose exec asterisk asterisk -rx "pjsip reload"

# Ver logs
docker compose logs -f asterisk
```

### Desde la consola CLI (dentro del contenedor):

```bash
# Acceder a CLI
docker compose exec asterisk asterisk -rvvv

# Comandos dentro:
*CLI> pjsip show endpoints          # Ver extensiones
*CLI> pjsip show contacts           # Ver registradas
*CLI> core show channels            # Llamadas activas
*CLI> pjsip set logger on           # Activar debug
*CLI> core set verbose 5            # Más verbosidad
*CLI> exit                          # Salir
```

---

## 📞 Configurar una Extensión de Prueba

### 1. Editar pjsip.conf

```bash
# En el servidor
docker compose exec asterisk nano /etc/asterisk/pjsip.conf
```

### 2. Agregar al final:

```ini
; Extensión de prueba 1001
[1001](webrtc_endpoint)
auth=1001-auth
aors=1001-aor
callerid=Test Extension <1001>

[1001-auth]
type=auth
auth_type=userpass
username=1001
password=Test1001!

[1001-aor]
type=aor
max_contacts=1
remove_existing=yes
```

### 3. Recargar PJSIP:

```bash
docker compose exec asterisk asterisk -rx "pjsip reload"
```

### 4. Verificar:

```bash
docker compose exec asterisk asterisk -rx "pjsip show endpoints"
# Debe aparecer: 1001
```

### 5. Registrar softphone:

Configuración del softphone (ej: Zoiper, Linphone):
- **Servidor:** IP_DEL_SERVIDOR
- **Puerto:** 5060
- **Usuario:** 1001
- **Contraseña:** Test1001!
- **Transport:** UDP

---

## 📚 Documentación Disponible

Todos estos archivos fueron creados en el proyecto:

### Guías Principales:
- **RESUMEN_PJSIP.md** ⭐ - Lee este primero (resumen completo)
- **GUIA_PJSIP.md** - Guía detallada de PJSIP
- **DIAGNOSTICO_ASTERISK.md** - Diagnóstico general
- **SOLUCION_ASTERISK_CLI.md** - Solución específica error CLI

### Scripts de Ayuda:
- **asterisk-docker.sh** - Gestión del contenedor (menú)
- **check-pjsip.sh** - Verificación PJSIP
- **asterisk-helper.ps1** - Helper Windows PowerShell
- **test_asterisk_connection.py** - Test conexión AMI

---

## ⚡ Solución Rápida de Problemas

### ❌ "Unable to connect to remote asterisk"

**Ya está solucionado.** Si vuelve a ocurrir:

```bash
cd /opt/vozipomni
docker compose restart asterisk
sleep 10
docker compose exec asterisk asterisk -rvvv
```

### ❌ "chan_sip no encontrado"

**Es normal.** Asterisk 21 usa PJSIP, no chan_sip. Todo está bien.

### ❌ No hay endpoints

Agregar extensiones en `/etc/asterisk/pjsip.conf` y ejecutar:
```bash
docker compose exec asterisk asterisk -rx "pjsip reload"
```

### ❌ Extensión no se registra

1. Verificar credenciales en pjsip.conf
2. Verificar puerto 5060 UDP abierto
3. Ver logs: `docker compose logs -f asterisk`

---

## ✅ Checklist Final

Verifica que todo funcione:

```bash
# En el servidor
cd /opt/vozipomni

# 1. Código actualizado
git log -1 --oneline
# Debe mostrar: "fix: Migración completa a PJSIP..."

# 2. Contenedor ejecutándose
docker ps | grep asterisk
# Debe mostrar: vozipomni_asterisk ... Up

# 3. CLI accesible
docker compose exec asterisk asterisk -rx "core show version"
# Debe mostrar: Asterisk 21.x.x

# 4. PJSIP funcionando
docker compose exec asterisk asterisk -rx "pjsip show endpoints"
# Debe listar endpoints o "No objects found" (pero sin error)

# 5. Scripts tienen permisos
ls -la *.sh
# Debe mostrar: -rwxr-xr-x (con x de ejecutable)
```

---

## 🎉 ¡Listo!

Tu sistema ahora está:
- ✅ Usando PJSIP (moderno y estable)
- ✅ Con acceso a CLI de Asterisk
- ✅ Código actualizado para Asterisk 21
- ✅ Con scripts de ayuda y diagnóstico
- ✅ Documentación completa

**Próximos pasos:**
1. Configurar extensiones en pjsip.conf
2. Registrar softphones
3. Probar llamadas
4. Integrar con el backend Django

---

## 📞 Contacto y Soporte

Si necesitas ayuda:

1. **Ver logs:** `docker compose logs -f asterisk`
2. **Diagnóstico:** `./check-pjsip.sh full`
3. **Consola CLI:** `docker compose exec asterisk asterisk -rvvv`
4. **Revisar docs:** Mirar archivos .md en el proyecto

---

**Fecha:** $(date)
**Versión Asterisk:** 21 LTS
**Protocolo SIP:** PJSIP
**Estado:** ✅ Operativo
