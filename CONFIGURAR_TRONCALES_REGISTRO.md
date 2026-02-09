# 📞 Configuración de Troncales SIP con Registro en PJSIP

## ✅ Nueva Funcionalidad Implementada

Ahora la tabla de Troncales SIP muestra una columna **"Registro"** que consulta en tiempo real el estado de registro de cada troncal en Asterisk.

### Estados Posibles:

| Estado | Significado | Color |
|--------|-------------|-------|
| **Registrado** ✅ | La troncal está registrada correctamente | Verde |
| **No Registrado** ⚠️ | La troncal no está registrada | Naranja |
| **Fallo** ❌ | El registro falló (credenciales incorrectas, etc.) | Rojo |
| **Sin Configurar** ℹ️ | No hay configuración de registro en Asterisk | Azul |
| **Asterisk Desconectado** ❌ | No se puede conectar a Asterisk | Rojo |

---

## 🔧 Configurar Troncal con Registro en PJSIP

Para que una troncal muestre **"Registrado"**, necesitas configurarla correctamente en `/etc/asterisk/pjsip.conf`.

### Ejemplo Completo de Troncal con Registro

Supongamos que creaste una troncal en el frontend con estos datos:
- **Nombre:** prueba
- **Host:** prueba.sip.com
- **Puerto:** 5060
- **Usuario:** prueba
- **Contraseña:** MiPassword123

Agrega esto al final de `pjsip.conf`:

```ini
; ========================================
; Troncal: prueba
; ========================================

; 1. ENDPOINT - Configuración del endpoint
[prueba]
type=endpoint
context=from-external
transport=transport-udp
disallow=all
allow=ulaw
allow=alaw
allow=g729
direct_media=no
from_user=prueba
from_domain=prueba.sip.com
outbound_auth=prueba-auth
aors=prueba-aor

; 2. AUTH - Autenticación saliente
[prueba-auth]
type=auth
auth_type=userpass
username=prueba
password=MiPassword123

; 3. AOR - Address of Record
[prueba-aor]
type=aor
contact=sip:prueba.sip.com:5060
qualify_frequency=60

; 4. IDENTIFY - Identificar llamadas entrantes del proveedor
[prueba-identify]
type=identify
endpoint=prueba
match=IP_DEL_PROVEEDOR

; 5. REGISTRATION - Registro con el proveedor (IMPORTANTE)
[prueba-reg]
type=registration
transport=transport-udp
outbound_auth=prueba-auth
server_uri=sip:prueba.sip.com:5060
client_uri=sip:prueba@prueba.sip.com
retry_interval=60
forbidden_retry_interval=600
expiration=3600
```

---

## 📋 Pasos para Aplicar la Configuración

### 1. Editar pjsip.conf

```bash
# Entrar al servidor
ssh usuario@servidor

# Ir al proyecto
cd /opt/vozipomni

# Editar configuración
docker compose exec asterisk nano /etc/asterisk/pjsip.conf

# Pegar la configuración al final del archivo
# Guardar: Ctrl+O, Enter, Ctrl+X
```

### 2. Recargar PJSIP

```bash
# Recargar configuración PJSIP
docker compose exec asterisk asterisk -rx "pjsip reload"

# Verificar que el registro se creó
docker compose exec asterisk asterisk -rx "pjsip show registrations"
```

**Salida esperada:**
```
 <Registration/ServerURI..............................>  <Auth..........>  <Status.......>
==========================================================================================
 prueba-reg/sip:prueba.sip.com:5060                      prueba-auth       Registered
```

### 3. Verificar en el Frontend

1. Abre la interfaz web
2. Ve a **Configuración → Troncales SIP**
3. La columna **"Registro"** debería mostrar: **"Registrado" ✅**

---

## 🔍 Verificar Estado de Registro

### Desde la CLI de Asterisk:

```bash
docker compose exec asterisk asterisk -rvvv
```

Comandos útiles:
```asterisk
*CLI> pjsip show registrations
*CLI> pjsip show registration prueba-reg
*CLI> pjsip show endpoints
*CLI> pjsip set logger on    # Ver debug en tiempo real
```

### Desde el servidor (sin entrar a CLI):

```bash
# Ver todos los registros
docker compose exec asterisk asterisk -rx "pjsip show registrations"

# Ver registro específico
docker compose exec asterisk asterisk -rx "pjsip show registration prueba-reg"

# Ver logs en tiempo real
docker compose logs -f asterisk | grep -i registration
```

---

## 🛠️ Solución de Problemas

### ❌ Estado: "No Registrado"

**Posibles causas:**

1. **Credenciales incorrectas**
   ```bash
   # Verificar en pjsip.conf que username y password sean correctos
   docker compose exec asterisk grep -A5 "prueba-auth" /etc/asterisk/pjsip.conf
   ```

2. **Host/Puerto incorrecto**
   ```bash
   # Verificar conectividad
   docker compose exec asterisk ping -c 3 prueba.sip.com
   docker compose exec asterisk nc -zv prueba.sip.com 5060
   ```

3. **Firewall bloqueando**
   ```bash
   # Verificar que el puerto 5060 UDP esté abierto
   sudo ufw status
   sudo ufw allow 5060/udp
   ```

### ❌ Estado: "Fallo"

**Revisar logs de Asterisk:**

```bash
# Ver errores recientes
docker compose logs asterisk | grep -i "registration\|prueba" | tail -20

# Activar debug PJSIP
docker compose exec asterisk asterisk -rx "pjsip set logger on"
docker compose logs -f asterisk
```

**Errores comunes:**

- **"401 Unauthorized"** → Credenciales incorrectas
- **"403 Forbidden"** → IP no autorizada por el proveedor
- **"408 Request Timeout"** → Problema de red/firewall
- **"503 Service Unavailable"** → Servidor del proveedor caído

### ❌ Estado: "Sin Configurar"

La troncal existe en la base de datos pero no tiene configuración de registro en `pjsip.conf`.

**Solución:**
1. Agregar la configuración como se muestra arriba
2. Recargar PJSIP: `docker compose exec asterisk asterisk -rx "pjsip reload"`

### ❌ Estado: "Asterisk Desconectado"

El backend no puede conectarse al AMI de Asterisk.

**Verificar:**

```bash
# Asterisk ejecutándose?
docker ps | grep asterisk

# AMI configurado?
docker compose exec asterisk asterisk -rx "manager show connected"

# Puerto AMI abierto?
docker compose exec asterisk netstat -tlnp | grep 5038
```

---

## 📝 Plantilla de Configuración PJSIP

Para facilitar, puedes usar esta plantilla reemplazando las variables:

```ini
; ========================================
; Troncal: {NOMBRE_TRONCAL}
; ========================================

[{NOMBRE_TRONCAL}]
type=endpoint
context=from-external
transport=transport-udp
disallow=all
allow=ulaw
allow=alaw
allow=g729
direct_media=no
from_user={USUARIO}
from_domain={HOST}
outbound_auth={NOMBRE_TRONCAL}-auth
aors={NOMBRE_TRONCAL}-aor

[{NOMBRE_TRONCAL}-auth]
type=auth
auth_type=userpass
username={USUARIO}
password={PASSWORD}

[{NOMBRE_TRONCAL}-aor]
type=aor
contact=sip:{HOST}:{PUERTO}
qualify_frequency=60

[{NOMBRE_TRONCAL}-identify]
type=identify
endpoint={NOMBRE_TRONCAL}
match={IP_PROVEEDOR}

[{NOMBRE_TRONCAL}-reg]
type=registration
transport=transport-udp
outbound_auth={NOMBRE_TRONCAL}-auth
server_uri=sip:{HOST}:{PUERTO}
client_uri=sip:{USUARIO}@{HOST}
retry_interval=60
forbidden_retry_interval=600
expiration=3600
```

**Variables a reemplazar:**
- `{NOMBRE_TRONCAL}` → Nombre de la troncal (mismo que pusiste en el frontend)
- `{HOST}` → Host del proveedor SIP
- `{PUERTO}` → Puerto (generalmente 5060)
- `{USUARIO}` → Usuario SIP
- `{PASSWORD}` → Contraseña SIP
- `{IP_PROVEEDOR}` → IP del servidor del proveedor (para identificar llamadas entrantes)

---

## 🎯 Ejemplo Real: Troncal con Proveedor

Supongamos que tienes una troncal con este proveedor:
- **Proveedor:** VoIP Provider SA
- **Host:** sip.voipprovider.com
- **Puerto:** 5060
- **Usuario:** 123456
- **Password:** abc123xyz
- **IP del Proveedor:** 200.10.20.30

**Configuración en el Frontend:**

1. Ve a **Configuración → Troncales SIP**
2. Click en **"+ Nueva Troncal"**
3. Llena el formulario:
   - Nombre: `voipprovider`
   - Host: `sip.voipprovider.com`
   - Puerto: `5060`
   - Usuario: `123456`
   - Contraseña: `abc123xyz`
4. Guarda

**Configuración en pjsip.conf:**

```bash
docker compose exec asterisk nano /etc/asterisk/pjsip.conf
```

Agregar al final:

```ini
; Troncal VoIP Provider
[voipprovider]
type=endpoint
context=from-external
transport=transport-udp
disallow=all
allow=ulaw
allow=alaw
direct_media=no
from_user=123456
from_domain=sip.voipprovider.com
outbound_auth=voipprovider-auth
aors=voipprovider-aor

[voipprovider-auth]
type=auth
auth_type=userpass
username=123456
password=abc123xyz

[voipprovider-aor]
type=aor
contact=sip:sip.voipprovider.com:5060
qualify_frequency=60

[voipprovider-identify]
type=identify
endpoint=voipprovider
match=200.10.20.30

[voipprovider-reg]
type=registration
transport=transport-udp
outbound_auth=voipprovider-auth
server_uri=sip:sip.voipprovider.com:5060
client_uri=sip:123456@sip.voipprovider.com
retry_interval=60
expiration=3600
```

Recargar:
```bash
docker compose exec asterisk asterisk -rx "pjsip reload"
docker compose exec asterisk asterisk -rx "pjsip show registrations"
```

---

## ✅ Checklist Final

Verifica que todo esté correcto:

- [ ] Troncal creada en el frontend
- [ ] Configuración agregada a `pjsip.conf`
- [ ] Sección `[nombre-reg]` existe con `type=registration`
- [ ] PJSIP recargado: `pjsip reload`
- [ ] Estado de registro verificado: `pjsip show registrations`
- [ ] En el frontend aparece **"Registrado" ✅** en la columna "Registro"
- [ ] Puertos 5060 UDP y RTP (10000-10100 UDP) abiertos en firewall

---

## 🆘 Ayuda Adicional

Si tienes problemas:

1. **Ver logs completos:**
   ```bash
   docker compose logs asterisk > asterisk_debug.log
   ```

2. **Activar debug PJSIP:**
   ```bash
   docker compose exec asterisk asterisk -rx "pjsip set logger on"
   docker compose exec asterisk asterisk -rx "core set verbose 5"
   ```

3. **Verificar script de diagnóstico:**
   ```bash
   ./check-pjsip.sh full
   ```

4. **Consultar estado desde código:**
   El backend consulta automáticamente el estado mediante AMI cada vez que cargas la tabla de troncales.

---

**Fecha de creación:** $(date)
**Versión Asterisk:** 21 LTS
**Protocolo:** PJSIP
