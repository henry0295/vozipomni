# 📞 Guía PJSIP para VoziPOmni

## ✅ Estado Actual

**PJSIP está instalado y funcionando:**
- ✅ `chan_pjsip.so` - Running
- ✅ Configuración en: `/etc/asterisk/pjsip.conf`
- ✅ Dialplan configurado con: `Dial(PJSIP/${EXTEN})`

**SIP Legacy NO está disponible:**
- ❌ `chan_sip.so` - No instalado (deprecado en Asterisk 21)

---

## 📋 Comandos PJSIP en Asterisk CLI

### Ver Endpoints (Extensiones)
```asterisk
pjsip show endpoints         # Listar todos los endpoints
pjsip show endpoint 1000     # Ver detalles de un endpoint específico
pjsip show contacts          # Ver extensiones registradas
```

### Ver Configuración
```asterisk
pjsip show auths            # Ver autenticaciones configuradas
pjsip show aors             # Ver Address of Records (AORs)
pjsip show transports       # Ver transportes (UDP, TCP, WSS)
```

### Diagnóstico
```asterisk
pjsip show registrations    # Ver registros SIP
pjsip show channels         # Ver canales PJSIP activos
pjsip show channel <id>     # Detalles de un canal específico
pjsip set logger on         # Activar logging PJSIP
pjsip set logger off        # Desactivar logging PJSIP
```

### Recargar Configuración
```asterisk
module reload res_pjsip.so              # Recargar módulo PJSIP
pjsip reload                            # Recargar configuración PJSIP
dialplan reload                         # Recargar dialplan
```

---

## 🔧 Probar Configuración Actual

### 1. Desde PowerShell/Linux (en servidor):
```bash
cd /opt/vozipomni
docker compose exec asterisk asterisk -rx "pjsip show endpoints"
```

### 2. Dentro de la consola CLI:
```bash
docker compose exec asterisk asterisk -rvvv
```

Luego ejecutar:
```asterisk
*CLI> pjsip show endpoints
*CLI> pjsip show contacts
*CLI> pjsip show transports
```

---

## 📝 Estructura de Configuración PJSIP

En `/etc/asterisk/pjsip.conf` cada extensión necesita **3 secciones**:

### Ejemplo: Extensión 1000

```ini
; 1. ENDPOINT - Configuración del dispositivo
[1000](webrtc_endpoint)
auth=1000-auth
aors=1000-aor
callerid=Agent 1000 <1000>

; 2. AUTH - Autenticación
[1000-auth]
type=auth
auth_type=userpass
username=1000
password=SecurePassword123

; 3. AOR - Address of Record (registro)
[1000-aor]
type=aor
max_contacts=1
remove_existing=yes
```

---

## 🎯 Agregar Nueva Extensión PJSIP

### Para Agente WebRTC (softphone en navegador):

Agregar al final de `pjsip.conf`:

```ini
[1001](webrtc_endpoint)
auth=1001-auth
aors=1001-aor
callerid=Agent 1001 <1001>

[1001-auth]
type=auth
auth_type=userpass
username=1001
password=Agent1001Pass!

[1001-aor]
type=aor
max_contacts=1
remove_existing=yes
```

### Para Agente SIP Tradicional (teléfono IP):

```ini
[2001](sip_endpoint)
auth=2001-auth
aors=2001-aor
callerid=Agent 2001 <2001>

[2001-auth]
type=auth
auth_type=userpass
username=2001
password=Agent2001Pass!

[2001-aor]
type=aor
max_contacts=1
remove_existing=yes
```

Después de agregar:
```bash
docker compose exec asterisk asterisk -rx "pjsip reload"
```

---

## 🔍 Verificar Extensiones Registradas

### Comando CLI:
```asterisk
*CLI> pjsip show contacts

Contact:  <Aor/ContactUri..............................> <Hash....> <Status> <RTT(ms)..>
=========================================================================================
Contact:  1000/sip:1000@192.168.1.100:5060               abc123456  Avail         12.345

Objects found: 1
```

**Estados posibles:**
- `Avail` - Disponible (registrado correctamente)
- `Unavail` - No disponible (no registrado)
- `Unknown` - Estado desconocido

---

## 🛠️ Script de Verificación PJSIP

He creado un archivo: `check-pjsip.sh`

Ver más abajo para el contenido del script.

---

## 📞 Hacer una Llamada de Prueba

### Desde la CLI de Asterisk:

```asterisk
*CLI> channel originate PJSIP/1000 application Playback demo-congrats
```

Esto:
1. Llama a la extensión 1000
2. Cuando conteste, reproduce un audio de prueba

### Llamada entre extensiones:

Si tienes extensión 1000 y 1001 registradas:
1. Desde el teléfono en 1000, marcar: **1001**
2. Debe sonar en 1001

---

## ⚙️ Diferencias SIP vs PJSIP

| Característica | chan_sip (antiguo) | chan_pjsip (nuevo) |
|----------------|-------------------|-------------------|
| Archivo Config | sip.conf | pjsip.conf |
| Dialplan | Dial(SIP/1000) | Dial(PJSIP/1000) |
| WebRTC | No soportado | ✅ Soportado |
| IPv6 | Limitado | ✅ Completo |
| Estado | Deprecado | ✅ Activo |
| Performance | Básico | ✅ Mejorado |

---

## 🔄 Si NECESITAS chan_sip (No Recomendado)

Si absolutamente necesitas habilitar el SIP legacy:

### 1. Modificar Dockerfile:

```dockerfile
# En docker/asterisk/Dockerfile, agregar en menuselect:
menuselect/menuselect \
    --enable chan_sip \
    ...
```

### 2. Reconstruir imagen:

```bash
cd /opt/vozipomni
docker compose build --no-cache asterisk
docker compose up -d asterisk
```

### 3. Verificar:

```asterisk
*CLI> module show like chan_sip
```

**⚠️ ADVERTENCIA:** chan_sip está oficialmente deprecado y será eliminado en futuras versiones de Asterisk.

---

## 📊 Comandos de Monitoreo PJSIP

### Ver llamadas activas:
```asterisk
core show channels
pjsip show channels
```

### Ver estadísticas:
```asterisk
pjsip show version
pjsip show settings
```

### Debug completo:
```asterisk
core set verbose 5
core set debug 5
pjsip set logger on
```

Para desactivar:
```asterisk
core set verbose 0
core set debug 0
pjsip set logger off
```

---

## 🧪 Pruebas de Conectividad

### 1. Verificar que el puerto está abierto:

```bash
# Desde el servidor
netstat -tulpn | grep 5060

# Debería mostrar:
# udp 0 0 0.0.0.0:5060 0.0.0.0:* LISTEN
```

### 2. Verificar transportes PJSIP:

```asterisk
*CLI> pjsip show transports

Transport:  <TransportId........>  <Type>  <cos>  <tos>  <BindAddress..................>
==========================================================================================
Transport:  transport-udp             udp      3      0  0.0.0.0:5060
Transport:  transport-tcp             tcp      3      0  0.0.0.0:5060
Transport:  transport-wss             wss      3      0  0.0.0.0:8089

Objects found: 3
```

### 3. Prueba de registro desde softphone:

**Configuración del softphone:**
- **Server/Domain:** IP_DEL_SERVIDOR
- **Port:** 5060
- **Username:** 1000 (o el que hayas configurado)
- **Password:** (la contraseña en pjsip.conf)
- **Transport:** UDP (para SIP tradicional) o WSS (para WebRTC)

---

## 🎯 Resumen de Comandos Rápidos

```bash
# Ver todas las extensiones PJSIP
docker compose exec asterisk asterisk -rx "pjsip show endpoints"

# Ver extensiones registradas
docker compose exec asterisk asterisk -rx "pjsip show contacts"

# Ver transportes
docker compose exec asterisk asterisk -rx "pjsip show transports"

# Recargar PJSIP
docker compose exec asterisk asterisk -rx "pjsip reload"

# Ver llamadas activas
docker compose exec asterisk asterisk -rx "core show channels"

# Activar debug PJSIP
docker compose exec asterisk asterisk -rx "pjsip set logger on"
```

---

## 🆘 Solución de Problemas PJSIP

### Problema: "No endpoints found"

**Causa:** Configuración vacía o incorrecta

**Solución:**
```bash
# Verificar archivo pjsip.conf
docker compose exec asterisk cat /etc/asterisk/pjsip.conf

# Verificar errores de sintaxis
docker compose exec asterisk asterisk -rx "pjsip reload"
```

### Problema: Extensión no se registra

**Verificar:**
1. Credenciales correctas en pjsip.conf
2. Puerto 5060 UDP abierto en firewall
3. IP del servidor correcta
4. Logs de Asterisk:
   ```bash
   docker compose logs -f asterisk
   ```

### Problema: No hay audio en llamadas

**Verificar:**
1. Puertos RTP abiertos (10000-10100 UDP)
2. Codecs compatibles:
   ```asterisk
   *CLI> pjsip show endpoint 1000
   # Ver sección "Codecs"
   ```
3. NAT configurado correctamente:
   ```ini
   rtp_symmetric=yes
   force_rport=yes
   rewrite_contact=yes
   ```

---

## 📚 Recursos Adicionales

- **Wiki Asterisk PJSIP:** https://wiki.asterisk.org/wiki/display/AST/Configuring+res_pjsip
- **Migración SIP a PJSIP:** https://wiki.asterisk.org/wiki/display/AST/Migrating+from+chan_sip+to+res_pjsip
- **PJSIP Configuration Wizard:** https://wiki.asterisk.org/wiki/display/AST/PJSIP+Configuration+Wizard

---

## ✅ Checklist de Verificación PJSIP

- [ ] Módulo chan_pjsip cargado: `module show like pjsip`
- [ ] Archivo pjsip.conf configurado correctamente
- [ ] Transportes funcionando: `pjsip show transports`
- [ ] Al menos un endpoint configurado: `pjsip show endpoints`
- [ ] Puerto 5060 UDP abierto en firewall
- [ ] Puertos RTP (10000-10100 UDP) abiertos
- [ ] Dialplan usando PJSIP: `Dial(PJSIP/${EXTEN})`
- [ ] Extensión de prueba registrada: `pjsip show contacts`
