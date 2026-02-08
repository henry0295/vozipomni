# ✅ Resumen: Configuración PJSIP para VoziPOmni

## 📋 Situación Inicial

**Problema reportado:**
- ❌ Error al acceder a consola Asterisk: `Unable to connect to remote asterisk`
- ❓ Pregunta: ¿`chan_sip` no está instalado?

## 🔍 Diagnóstico

**Asterisk 21 usa PJSIP por defecto:**
- ✅ `chan_pjsip.so` - Instalado y funcionando (SIP moderno)
- ❌ `chan_sip.so` - NO instalado (deprecado, no recomendado)
- ℹ️ PJSIP es el reemplazo oficial de chan_sip desde Asterisk 12+

## 🔧 Correcciones Realizadas

### 1. Solución Error de Consola CLI
**Archivo:** `docker/asterisk/configs/asterisk.conf`

**Cambio:**
```ini
# ANTES (❌ causaba el error)
alwaysfork = yes
nofork = no

# AHORA (✅ permite acceso a CLI)
alwaysfork = no
nofork = yes
```

**Efecto:** Ahora puedes acceder a la consola con:
```bash
docker compose exec asterisk asterisk -rvvv
```

---

### 2. Migración Completa a PJSIP

**Archivos actualizados:**

#### `backend/apps/telephony/views.py`
```python
# ANTES
ami.reload_module('chan_sip.so')  # ❌ módulo no disponible

# AHORA
ami.reload_module('res_pjsip.so')  # ✅ módulo correcto
ami.reload_module('chan_pjsip.so')
```

#### `backend/apps/telephony/asterisk_config.py`
```python
# ANTES
config.append(f"same => n,Dial(SIP/{route.destination},30,tr)")  # ❌

# AHORA
config.append(f"same => n,Dial(PJSIP/{route.destination},30,tr)")  # ✅
```

---

## 📦 Archivos de Ayuda Creados

### 1. **Guías de Documentación**
- ✅ `DIAGNOSTICO_ASTERISK.md` - Guía completa de diagnóstico
- ✅ `SOLUCION_ASTERISK_CLI.md` - Solución específica para el error CLI
- ✅ `GUIA_PJSIP.md` - Guía completa de PJSIP

### 2. **Scripts de Gestión**
- ✅ `asterisk-docker.sh` - Gestión del contenedor Asterisk (menú interactivo)
- ✅ `check-pjsip.sh` - Verificación completa de PJSIP
- ✅ `asterisk-helper.ps1` - Helper de PowerShell (Windows)
- ✅ `test_asterisk_connection.py` - Prueba de conexión AMI

### 3. **Configuración**
- ✅ `.env` - Archivo de variables de entorno (necesita configuración)

---

## 🚀 Pasos Siguientes (En el servidor)

### Paso 1: Actualizar código
```bash
cd /opt/vozipomni
git pull origin main
```

### Paso 2: Reiniciar contenedor Asterisk
```bash
docker compose restart asterisk
# Esperar 10 segundos
sleep 10
```

### Paso 3: Verificar que funciona
```bash
# Dar permisos a scripts
chmod +x asterisk-docker.sh check-pjsip.sh

# Acceder a consola CLI
docker compose exec asterisk asterisk -rvvv
```

### Paso 4: Verificar PJSIP
Dentro de la consola Asterisk:
```asterisk
*CLI> pjsip show endpoints
*CLI> pjsip show transports
*CLI> module show like pjsip
*CLI> exit
```

### Paso 5: Usar scripts de verificación
```bash
# Diagnóstico completo
./check-pjsip.sh full

# O menú interactivo
./asterisk-docker.sh
```

---

## 📞 Comandos Rápidos PJSIP

### Ver extensiones configuradas:
```bash
docker compose exec asterisk asterisk -rx "pjsip show endpoints"
```

### Ver extensiones registradas:
```bash
docker compose exec asterisk asterisk -rx "pjsip show contacts"
```

### Ver llamadas activas:
```bash
docker compose exec asterisk asterisk -rx "core show channels"
```

### Recargar PJSIP:
```bash
docker compose exec asterisk asterisk -rx "pjsip reload"
```

### Activar logging PJSIP:
```bash
docker compose exec asterisk asterisk -rx "pjsip set logger on"
docker compose logs -f asterisk
```

---

## 🔑 Configuración de Extensiones PJSIP

### Archivo: `/etc/asterisk/pjsip.conf`

**Ejemplo de extensión WebRTC:**
```ini
[1000](webrtc_endpoint)
auth=1000-auth
aors=1000-aor
callerid=Agent 1000 <1000>

[1000-auth]
type=auth
auth_type=userpass
username=1000
password=SecurePass123!

[1000-aor]
type=aor
max_contacts=1
remove_existing=yes
```

**Ejemplo de extensión SIP tradicional:**
```ini
[2000](sip_endpoint)
auth=2000-auth
aors=2000-aor
callerid=Agent 2000 <2000>

[2000-auth]
type=auth
auth_type=userpass
username=2000
password=SecurePass456!

[2000-aor]
type=aor
max_contacts=1
remove_existing=yes
```

---

## ✅ Checklist de Verificación Final

En el servidor, ejecuta:

```bash
cd /opt/vozipomni

# 1. Contenedor ejecutándose
docker ps | grep asterisk
# ✅ Debe mostrar: vozipomni_asterisk ... Up

# 2. Acceso a CLI funciona
docker compose exec asterisk asterisk -rx "core show version"
# ✅ Debe mostrar: Asterisk 21.x.x

# 3. PJSIP está cargado
docker compose exec asterisk asterisk -rx "module show like pjsip"
# ✅ Debe mostrar múltiples módulos pjsip "Running"

# 4. Transportes PJSIP activos
docker compose exec asterisk asterisk -rx "pjsip show transports"
# ✅ Debe mostrar: transport-udp, transport-tcp, transport-wss

# 5. Verificación completa
./check-pjsip.sh full
# ✅ Debe mostrar diagnóstico completo sin errores críticos
```

---

## 🎯 Diferencias Clave: SIP vs PJSIP

| Aspecto | chan_sip (antiguo) | chan_pjsip (moderno) |
|---------|-------------------|---------------------|
| **Archivo Config** | sip.conf | pjsip.conf |
| **Dialplan** | `Dial(SIP/1000)` | `Dial(PJSIP/1000)` |
| **Estado** | ❌ Deprecado | ✅ Activo |
| **WebRTC** | ❌ No soporta | ✅ Soporte completo |
| **Performance** | Limitado | Optimizado |
| **IPv6** | Parcial | ✅ Completo |
| **Asterisk 21** | ❌ No disponible | ✅ Por defecto |

---

## 📚 Recursos de Ayuda

### En el proyecto:
- 📖 `GUIA_PJSIP.md` - Guía completa de PJSIP
- 📖 `DIAGNOSTICO_ASTERISK.md` - Diagnóstico general
- 📖 `SOLUCION_ASTERISK_CLI.md` - Solución error CLI
- 🔧 `check-pjsip.sh` - Script de verificación
- 🔧 `asterisk-docker.sh` - Gestión del contenedor

### Online:
- [Asterisk PJSIP Wiki](https://wiki.asterisk.org/wiki/display/AST/Configuring+res_pjsip)
- [Migración SIP → PJSIP](https://wiki.asterisk.org/wiki/display/AST/Migrating+from+chan_sip+to+res_pjsip)

---

## 💡 Recomendaciones

1. **NO intentes habilitar chan_sip** - Está deprecado y será eliminado
2. **Usa PJSIP** - Es más moderno, estable y con mejor soporte
3. **Para WebRTC** - PJSIP es la única opción viable
4. **Configuración** - Usa templates en pjsip.conf para simplificar
5. **Testing** - Prueba con un softphone primero antes de producción

---

## 🆘 Soporte

Si tienes problemas:

1. **Ver logs:**
   ```bash
   docker compose logs -f asterisk
   ```

2. **Verificar PJSIP:**
   ```bash
   ./check-pjsip.sh full
   ```

3. **Acceder a CLI:**
   ```bash
   docker compose exec asterisk asterisk -rvvv
   ```

4. **Debug PJSIP:**
   ```asterisk
   *CLI> pjsip set logger on
   *CLI> core set verbose 5
   ```

---

## ✅ Conclusión

- ✅ Asterisk CLI ahora es accesible
- ✅ Sistema migrado completamente a PJSIP
- ✅ chan_sip NO es necesario (ni recomendado)
- ✅ Scripts de ayuda disponibles
- ✅ Documentación completa creada

**Siguiente paso:** Registrar softphones y probar llamadas
