# 🔧 Solución: Error "Unable to connect to remote asterisk"

## ❌ Error que estás viendo:
```bash
root@DESKTOP-3D49LMT:/opt/vozipomni# docker compose exec asterisk asterisk -r
'alwaysfork' is not compatible with console or remote console mode; ignored
Unable to connect to remote asterisk (does /var/run/asterisk/asterisk.ctl exist?)
```

## ✅ SOLUCIÓN RÁPIDA (3 pasos)

### Paso 1: Reiniciar el contenedor de Asterisk
```bash
cd /opt/vozipomni
docker compose restart asterisk
```

### Paso 2: Esperar 5-10 segundos
```bash
sleep 10
```

### Paso 3: Acceder a la consola CLI
```bash
docker compose exec asterisk asterisk -rvvv
```

---

## 📋 SOLUCIÓN DETALLADA

### 1. Verificar estado del contenedor
```bash
# Ver si el contenedor está ejecutándose
docker ps | grep asterisk

# Ver logs del contenedor
docker compose logs asterisk
```

### 2. Si el contenedor no está ejecutándose:
```bash
# Iniciar el contenedor
docker compose up -d asterisk

# Ver logs en tiempo real
docker compose logs -f asterisk
```

### 3. Verificar que Asterisk esté ejecutándose dentro del contenedor:
```bash
# Ver procesos de Asterisk
docker compose exec asterisk ps aux | grep asterisk

# Verificar socket de control
docker compose exec asterisk ls -la /var/run/asterisk/
```

### 4. Si necesitas reconstruir el contenedor:
```bash
# Detener contenedor
docker compose stop asterisk

# Eliminar contenedor
docker compose rm -f asterisk

# Reconstruir imagen
docker compose build --no-cache asterisk

# Iniciar contenedor
docker compose up -d asterisk
```

---

## 🚀 USAR EL SCRIPT DE GESTIÓN

He creado un script para facilitar la gestión de Asterisk:

```bash
# Dar permisos de ejecución
chmod +x asterisk-docker.sh

# Ejecutar menú interactivo
./asterisk-docker.sh

# O usar comandos directos:
./asterisk-docker.sh status     # Verificar estado
./asterisk-docker.sh cli        # Acceder a CLI
./asterisk-docker.sh logs       # Ver logs
./asterisk-docker.sh restart    # Reiniciar
./asterisk-docker.sh rebuild    # Reconstruir
```

---

## 🔍 COMANDOS ÚTILES EN LA CONSOLA ASTERISK CLI

Una vez dentro de la consola (`CLI>`):

### Comandos Básicos
```asterisk
core show version          # Ver versión de Asterisk
core show uptime          # Tiempo de actividad
core show channels        # Canales/llamadas activas
core reload               # Recargar configuración
exit                      # Salir de la consola
```

### Comandos PJSIP/SIP
```asterisk
pjsip show endpoints      # Ver extensiones PJSIP
pjsip show contacts       # Ver extensiones registradas
pjsip reload              # Recargar configuración PJSIP
```

### Comandos AMI
```asterisk
manager show connected    # Ver conexiones AMI activas
manager show users        # Ver usuarios AMI configurados
manager reload            # Recargar configuración AMI
```

### Comandos de Dialplan
```asterisk
dialplan show             # Ver dialplan completo
dialplan reload           # Recargar dialplan
```

### Comandos de Debug
```asterisk
core set verbose 5        # Aumentar verbosidad (0-10)
core set debug 5          # Aumentar debug (0-10)
pjsip set logger on       # Activar logs PJSIP
```

---

## 🐛 DIAGNÓSTICO DE PROBLEMAS

### Si `asterisk -r` sigue sin funcionar:

1. **Verificar que Asterisk esté ejecutándose:**
   ```bash
   docker compose exec asterisk pgrep asterisk
   ```
   - Debe mostrar un número (PID)
   - Si no muestra nada, Asterisk no está corriendo

2. **Verificar socket de control:**
   ```bash
   docker compose exec asterisk test -S /var/run/asterisk/asterisk.ctl && echo "OK" || echo "FALTA"
   ```
   - Debe mostrar "OK"
   - Si muestra "FALTA", el socket no existe

3. **Ver errores en los logs:**
   ```bash
   docker compose logs asterisk | grep -i error
   docker compose logs asterisk | grep -i warning
   ```

4. **Entrar al contenedor y verificar manualmente:**
   ```bash
   # Entrar al contenedor
   docker compose exec asterisk bash
   
   # Dentro del contenedor:
   ps aux | grep asterisk
   ls -la /var/run/asterisk/
   cat /var/log/asterisk/messages
   
   # Salir
   exit
   ```

---

## 🔧 QUÉ SE CORRIGIÓ

He modificado el archivo `docker/asterisk/configs/asterisk.conf`:

**ANTES (❌ Causaba el error):**
```ini
alwaysfork = yes
nofork = no
```

**AHORA (✅ Permite acceso a CLI):**
```ini
alwaysfork = no
nofork = yes
```

Esto permite que:
- Asterisk se ejecute en **foreground** dentro del contenedor
- Se pueda acceder a la consola con `asterisk -r`
- El socket de control `/var/run/asterisk/asterisk.ctl` se cree correctamente

---

## ⚡ ACCESO RÁPIDO A LA CONSOLA

### Opción 1: Desde el servidor Linux
```bash
cd /opt/vozipomni
docker compose exec asterisk asterisk -rvvv
```

### Opción 2: Usando el script
```bash
./asterisk-docker.sh cli
```

### Opción 3: Comandos únicos sin entrar a CLI
```bash
# Ejecutar un solo comando y salir
docker compose exec asterisk asterisk -rx "core show version"
docker compose exec asterisk asterisk -rx "pjsip show endpoints"
docker compose exec asterisk asterisk -rx "core show channels"
```

---

## 📞 EJEMPLO DE SESIÓN COMPLETA

```bash
# 1. Ir al directorio del proyecto
cd /opt/vozipomni

# 2. Verificar que el contenedor esté ejecutándose
docker ps | grep asterisk

# 3. Si no está ejecutándose, iniciarlo
docker compose up -d asterisk

# 4. Esperar unos segundos
sleep 5

# 5. Acceder a la consola CLI
docker compose exec asterisk asterisk -rvvv

# Dentro de la consola verás:
# Asterisk 21.x.x, Copyright (C) 1999 - 2023 Sangoma Technologies Corporation
# *CLI>

# 6. Ejecutar comandos
*CLI> core show version
*CLI> pjsip show endpoints
*CLI> core show channels

# 7. Salir
*CLI> exit
```

---

## 🆘 SI NADA FUNCIONA

Si después de todos estos pasos aún no funciona:

1. **Reconstruir completamente el contenedor:**
   ```bash
   docker compose down
   docker compose build --no-cache asterisk
   docker compose up -d
   ```

2. **Ver logs completos:**
   ```bash
   docker compose logs asterisk > asterisk_logs.txt
   cat asterisk_logs.txt
   ```

3. **Verificar permisos:**
   ```bash
   docker compose exec asterisk ls -la /var/run/asterisk/
   docker compose exec asterisk ls -la /etc/asterisk/
   ```

4. **Verificar usuario:**
   ```bash
   docker compose exec asterisk whoami
   # Debe mostrar: asterisk
   ```

---

## ✅ CHECKLIST FINAL

- [ ] Archivo `asterisk.conf` corregido (alwaysfork=no, nofork=yes)
- [ ] Contenedor Asterisk ejecutándose: `docker ps | grep asterisk`
- [ ] Proceso Asterisk activo: `docker compose exec asterisk pgrep asterisk`
- [ ] Socket de control existe: `docker compose exec asterisk ls /var/run/asterisk/asterisk.ctl`
- [ ] Puedo acceder a CLI: `docker compose exec asterisk asterisk -r`
- [ ] Sin errores en logs: `docker compose logs asterisk`

---

## 🎯 RESUMEN DE COMANDOS CLAVE

```bash
# Estado del contenedor
docker compose ps asterisk

# Reiniciar Asterisk
docker compose restart asterisk

# Ver logs
docker compose logs -f asterisk

# Acceder a consola CLI
docker compose exec asterisk asterisk -rvvv

# Ejecutar comando único
docker compose exec asterisk asterisk -rx "COMANDO"

# Reconstruir contenedor
docker compose build --no-cache asterisk && docker compose up -d asterisk
```
