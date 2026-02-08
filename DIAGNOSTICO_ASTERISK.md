# 🔧 Guía de Diagnóstico Asterisk - VoziPOmni

## 📋 Índice
1. [Probar Conexión AMI desde VS Code](#1-probar-conexión-ami-desde-vs-code)
2. [Acceder al Servidor Asterisk por SSH](#2-acceder-al-servidor-asterisk-por-ssh)
3. [Verificar Estado de Asterisk](#3-verificar-estado-de-asterisk)
4. [Acceder a la Consola CLI de Asterisk](#4-acceder-a-la-consola-cli-de-asterisk)
5. [Verificar Configuración AMI](#5-verificar-configuración-ami)
6. [Solución de Problemas Comunes](#6-solución-de-problemas-comunes)

---

## 1. Probar Conexión AMI desde VS Code

Ejecuta el script de prueba que creé:

```powershell
# En la terminal de VS Code (PowerShell)
cd "c:\Users\PT\OneDrive - VOZIP COLOMBIA\Documentos\GitHub\vozipomni"

python test_asterisk_connection.py
```

El script te pedirá:
- **Host/IP del servidor**: La dirección IP o dominio del servidor Asterisk
- **Puerto AMI**: Por defecto 5038
- **Usuario AMI**: Por defecto 'admin'
- **Contraseña AMI**: La contraseña configurada en manager.conf

### Resultado Esperado ✅
```
====================================================================
  PRUEBA DE CONEXIÓN ASTERISK AMI
====================================================================

🔌 Intentando conectar a X.X.X.X:5038...
✅ Conexión TCP establecida

📋 Banner de Asterisk:
Asterisk Call Manager/X.X

🔐 Autenticando como 'admin'...
✅ AUTENTICACIÓN EXITOSA

📤 Ejecutando comandos de prueba...
   Response: Success
   CoreStartupDate: ...
   
====================================================================
  ✅ CONEXIÓN EXITOSA - Asterisk está funcionando
====================================================================
```

---

## 2. Acceder al Servidor Asterisk por SSH

Si tienes acceso SSH al servidor:

```powershell
# Desde PowerShell o usar PuTTY
ssh usuario@IP_DEL_SERVIDOR
```

O si usas clave privada:
```powershell
ssh -i ruta\a\clave.pem usuario@IP_DEL_SERVIDOR
```

---

## 3. Verificar Estado de Asterisk

Una vez conectado al servidor por SSH:

### 3.1 Verificar si Asterisk está ejecutándose
```bash
sudo systemctl status asterisk
# o
sudo service asterisk status
# o (para Docker)
docker ps | grep asterisk
```

**Salida esperada:**
```
● asterisk.service - Asterisk PBX
   Loaded: loaded
   Active: active (running)
```

### 3.2 Verificar versión de Asterisk
```bash
asterisk -V
# o
asterisk -rx "core show version"
```

**Salida esperada:**
```
Asterisk 18.x.x
```

### 3.3 Verificar procesos
```bash
ps aux | grep asterisk
```

---

## 4. Acceder a la Consola CLI de Asterisk

### 4.1 Método Principal (Consola Remota)
```bash
# Con privilegios sudo
sudo asterisk -rvvv

# Sin sudo (si tu usuario está en grupo asterisk)
asterisk -rvvv
```

**Flags:**
- `-r` = Conectar a consola remota
- `-vvv` = Verbosidad nivel 3 (muy detallado)

### 4.2 Si estás en Docker
```bash
# Ejecutar desde el host
docker exec -it nombre_contenedor_asterisk asterisk -rvvv

# o entrar al contenedor primero
docker exec -it nombre_contenedor_asterisk bash
asterisk -rvvv
```

### 4.3 Comandos Útiles en la Consola CLI

Una vez dentro de la consola Asterisk (`CLI>`):

#### Comandos Generales
```asterisk
core show version          # Mostrar versión
core show uptime           # Tiempo de actividad
core show channels         # Canales activos
core show calls            # Llamadas activas
core reload                # Recargar configuración general
```

#### Comandos AMI
```asterisk
manager show connected     # Conexiones AMI activas
manager show users         # Usuarios AMI configurados
manager reload             # Recargar configuración AMI
```

#### Comandos SIP/PJSIP
```asterisk
pjsip show endpoints       # Ver endpoints PJSIP
sip show peers             # Ver peers SIP (legacy)
pjsip show registrations   # Registros PJSIP
```

#### Comandos de Dialplan
```asterisk
dialplan show              # Mostrar dialplan completo
dialplan reload            # Recargar dialplan
```

#### Comandos de Debug
```asterisk
core set verbose 3         # Aumentar verbosidad
core set debug 3           # Activar debug
pjsip set logger on        # Debug PJSIP
```

#### Salir de la Consola
```asterisk
exit                       # Salir de la consola CLI
quit                       # Alternativa para salir
```

---

## 5. Verificar Configuración AMI

### 5.1 Desde el servidor, revisar manager.conf
```bash
sudo cat /etc/asterisk/manager.conf
```

**Configuración mínima requerida:**
```ini
[general]
enabled = yes
bindaddr = 0.0.0.0
port = 5038

[admin]
secret = tu_contraseña_segura
deny = 0.0.0.0/0.0.0.0
permit = 0.0.0.0/0.0.0.0
read = system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan
write = system,call,log,verbose,command,agent,user,config,originate,reporting,cdr
writetimeout = 5000
```

### 5.2 Verificar puerto AMI abierto
```bash
# Ver si Asterisk está escuchando en puerto 5038
sudo netstat -tlnp | grep 5038
# o
sudo ss -tlnp | grep 5038
```

**Salida esperada:**
```
tcp    0    0 0.0.0.0:5038    0.0.0.0:*    LISTEN    12345/asterisk
```

### 5.3 Verificar firewall
```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 5038/tcp

# CentOS/RHEL
sudo firewall-cmd --list-all
sudo firewall-cmd --permanent --add-port=5038/tcp
sudo firewall-cmd --reload
```

### 5.4 Probar conexión local al AMI
```bash
# Desde el mismo servidor
telnet localhost 5038
```

**Salida esperada:**
```
Asterisk Call Manager/X.X
```

---

## 6. Solución de Problemas Comunes

### ❌ Problema: "Connection refused"

**Causas posibles:**
1. Asterisk no está ejecutándose
   ```bash
   sudo systemctl start asterisk
   ```

2. AMI no está habilitado
   ```bash
   # Editar /etc/asterisk/manager.conf
   sudo nano /etc/asterisk/manager.conf
   # Asegurar: enabled = yes
   sudo asterisk -rx "manager reload"
   ```

3. Puerto incorrecto
   ```bash
   # Verificar puerto en manager.conf
   grep "port" /etc/asterisk/manager.conf
   ```

### ❌ Problema: "Authentication failed"

**Solución:**
```bash
# Verificar usuario y contraseña en manager.conf
sudo cat /etc/asterisk/manager.conf | grep -A 5 "\[admin\]"

# Recargar configuración
sudo asterisk -rx "manager reload"
```

### ❌ Problema: "Timeout"

**Causas posibles:**
1. Firewall bloqueando puerto
   ```bash
   sudo ufw allow from TU_IP to any port 5038
   ```

2. Asterisk vinculado solo a localhost
   ```bash
   # En manager.conf cambiar:
   # bindaddr = 127.0.0.1  →  bindaddr = 0.0.0.0
   sudo asterisk -rx "manager reload"
   ```

### ❌ Problema: "Permission denied" al ejecutar Asterisk

**Solución:**
```bash
# Agregar tu usuario al grupo asterisk
sudo usermod -a -G asterisk $USER

# Cerrar sesión y volver a entrar, o:
newgrp asterisk
```

### ❌ Problema: Asterisk no responde comandos

**Solución:**
```bash
# Reiniciar Asterisk
sudo systemctl restart asterisk

# O forzar recarga
sudo asterisk -rx "core restart now"
```

---

## 📝 Checklist de Verificación

Marca cada ítem conforme lo verificas:

- [ ] Asterisk está ejecutándose (`systemctl status asterisk`)
- [ ] AMI está habilitado en manager.conf (`enabled = yes`)
- [ ] Usuario AMI existe en manager.conf
- [ ] Puerto 5038 está abierto (`netstat -tlnp | grep 5038`)
- [ ] Firewall permite conexiones al puerto 5038
- [ ] Puedes conectarte localmente al AMI (`telnet localhost 5038`)
- [ ] Puedes acceder a la consola CLI (`asterisk -rvvv`)
- [ ] El script test_asterisk_connection.py se conecta exitosamente

---

## 🎯 Acceso Rápido a Consola Asterisk

### Opción 1: SSH + Consola CLI
```powershell
# Desde PowerShell en Windows
ssh usuario@servidor_asterisk
sudo asterisk -rvvv
```

### Opción 2: SSH Directo con Comando
```powershell
ssh usuario@servidor_asterisk 'sudo asterisk -rx "core show channels"'
```

### Opción 3: Usar script Python para comandos AMI
```python
# Usar el cliente AMI desde el proyecto Django
python manage.py shell

from apps.telephony.asterisk_ami import AsteriskAMI
ami = AsteriskAMI()
ami.connect()
# Ejecutar comandos...
ami.disconnect()
```

---

## 📞 Comandos Asterisk Más Útiles

### Monitoreo en Tiempo Real
```asterisk
core show channels verbose    # Ver todas las llamadas activas
pjsip show contacts           # Ver extensiones registradas
queue show                    # Ver estado de colas
```

### Depuración
```asterisk
pjsip set logger on           # Activar logs PJSIP
core set verbose 5            # Máxima verbosidad
core set debug 5              # Máximo debug
```

### Mantenimiento
```asterisk
module reload                 # Recargar todos los módulos
dialplan reload               # Recargar dialplan
core reload                   # Recarga completa
core restart now              # Reiniciar Asterisk
```

---

## 🆘 Soporte Adicional

Si ninguna de estas soluciones funciona:

1. **Revisa los logs de Asterisk:**
   ```bash
   sudo tail -f /var/log/asterisk/full
   sudo tail -f /var/log/asterisk/messages
   ```

2. **Verifica permisos:**
   ```bash
   ls -la /etc/asterisk/
   sudo chown -R asterisk:asterisk /etc/asterisk/
   ```

3. **Examina la configuración completa:**
   ```bash
   asterisk -rx "manager show settings"
   ```
