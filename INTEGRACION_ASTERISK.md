# Integración Completa con Asterisk - VoziPOmni

## ✅ Funcionalidades Implementadas

### 1. Gestión de Extensiones (Frontend)
- ✅ **Crear extensiones** (SIP, IAX2, PJSIP)
- ✅ **Editar extensiones** (modal reutilizable)
- ✅ **Eliminar extensiones** con confirmación
- ✅ **Listado paginado** con búsqueda y filtros
- ✅ **Validación** de campos obligatorios
- ✅ **Disable campo extensión** al editar (evitar duplicados)

### 2. Generación Automática de Configuración de Asterisk (Backend)

Archivo: `backend/apps/telephony/asterisk_config.py`

#### Archivos Generados Automáticamente:

**sip.conf** - Extensiones SIP
```ini
[1001]
type=friend
secret=********
context=from-internal
callerid="Juan Pérez" <1001>
host=dynamic
qualify=yes
nat=force_rport,comedia
mailbox=1001@default
```

**pjsip.conf** - Extensiones PJSIP (SIP moderno)
```ini
[1002]
type=endpoint
context=from-internal
auth=1002
aors=1002
callerid="María López" <1002>
```

**extensions.conf** - Dialplan completo
```conf
[from-internal]
; Llamadas entre extensiones
exten => 1001,1,NoOp(Llamada a Juan Pérez)
same => n,Dial(SIP/1001,30,tr)
same => n,Hangup()

[from-external]
; Rutas entrantes (DIDs)
exten => +573001234567,1,NoOp(DID: Línea principal)
same => n,Dial(SIP/1001,30,tr)
same => n,Hangup()

; Rutas salientes
exten => _9XXXXXXXXXX,1,NoOp(Saliente: Llamadas nacionales)
same => n,Dial(SIP/${EXTEN:1}@trunk_voip,60,tr)
same => n,Hangup()
```

**voicemail.conf** - Buzones de voz
```ini
[default]
1001 => 1234,Juan Pérez,juan@email.com
```

**musiconhold.conf** - Música en espera
```ini
[default]
mode=files
directory=/var/lib/asterisk/moh
```

### 3. Recarga Automática de Asterisk (AMI)

#### Cliente AMI Mejorado
Archivo: `backend/apps/telephony/asterisk_ami.py`

**Métodos Sincrónicos Implementados:**
- `connect()` - Conectar al AMI
- `disconnect()` - Desconectar
- `reload_module(module_name)` - Recargar módulo específico
- `reload_dialplan()` - Recargar dialplan (extensions.conf)
- `sip_show_peers()` - Listar peers SIP
- `pjsip_show_endpoints()` - Listar endpoints PJSIP

**Flujo Automático:**
```
Usuario crea/edita extensión
      ↓
Django ViewSet guarda en DB
      ↓
perform_create/update/destroy ejecuta _reload_asterisk_config()
      ↓
AsteriskConfigGenerator genera archivos .conf
      ↓
AsteriskAMI recarga módulos correspondientes
      ↓
Asterisk aplica nueva configuración SIN REINICIAR
```

### 4. Vistas Actualizadas con Auto-Reload

#### ExtensionViewSet
- `perform_create()` → Regenera sip.conf/pjsip.conf + recarga chan_sip/chan_pjsip
- `perform_update()` → Regenera configuración + recarga
- `perform_destroy()` → Elimina y recarga
- `reload_config()` → Endpoint manual GET /api/telephony/extensions/{id}/reload_config/

#### InboundRouteViewSet
- Auto-recarga dialplan al crear/editar/eliminar DIDs

#### OutboundRouteViewSet
- Auto-recarga dialplan al crear/editar/eliminar rutas salientes

#### VoicemailViewSet
- Auto-recarga módulo app_voicemail.so

#### MusicOnHoldViewSet
- Auto-recarga módulo res_musiconhold.so

## 📋 Configuración Requerida

### 1. Variables de Entorno (`.env`)

```bash
# Asterisk AMI Configuration
ASTERISK_HOST=asterisk
ASTERISK_AMI_PORT=5038
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=VoziPOmni2026!
```

### 2. Asterisk manager.conf

```ini
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

[admin]
secret = VoziPOmni2026!
read = all
write = all
```

### 3. Permisos de Archivos

El contenedor backend debe tener permisos para escribir en `/etc/asterisk/`:

```bash
docker compose exec asterisk chmod 777 /etc/asterisk
```

O mejor, montar volumen con permisos:

```yaml
# docker-compose.yml
services:
  asterisk:
    volumes:
      - asterisk_config:/etc/asterisk
      
  backend:
    volumes:
      - asterisk_config:/etc/asterisk

volumes:
  asterisk_config:
```

## 🚀 Uso

### Crear Extensión desde Frontend

1. Ir a **Telefonía → Extensiones**
2. Clic en **+ Nueva Extensión**
3. Llenar formulario:
   - Extensión: `1001`
   - Nombre: `Juan Pérez`
   - Tipo: `SIP`
   - Contraseña: `secreto123`
   - Contexto: `from-internal`
   - Caller ID: `"Juan Pérez" <1001>`
   - Email: `juan@email.com`
   - Buzón habilitado: ☑
4. Clic en **Crear Extensión**

**Resultado:**
- ✅ Extensión guardada en PostgreSQL
- ✅ Archivo `sip.conf` regenerado automáticamente
- ✅ Asterisk recarga `chan_sip.so` vía AMI
- ✅ Extensión lista para registrarse en Asterisk

### Editar Extensión

1. Clic en botón **✏️ Editar**
2. Modal abre con datos prellenados
3. Campo "Extensión" deshabilitado (no se puede cambiar número)
4. Modificar datos necesarios
5. Contraseña opcional (dejar vacío para mantener)
6. Clic en **Actualizar Extensión**

**Resultado:**
- ✅ Extensión actualizada en DB
- ✅ Configuración regenerada
- ✅ Asterisk recargado

### Eliminar Extensión

1. Clic en botón **🗑️ Eliminar**
2. Confirmar en diálogo
3. **Resultado:**
   - ✅ Extensión eliminada de DB y Asterisk

## 🔧 Troubleshooting

### Error: "No se puede conectar a Asterisk AMI"

**Solución:**
```bash
# Verificar que Asterisk esté corriendo
docker compose ps

# Ver logs de Asterisk
docker compose logs asterisk

# Verificar configuración AMI
docker compose exec asterisk asterisk -rx "manager show users"
```

### Error: "Permission denied writing to /etc/asterisk"

**Solución:**
```bash
# Opción 1: Cambiar permisos (no recomendado en producción)
docker compose exec asterisk chmod 777 /etc/asterisk

# Opción 2: Usar volumen compartido (RECOMENDADO)
# Ver docker-compose.yml arriba
```

### Configuración no se aplica en Asterisk

**Verificar:**
```bash
# Ver peers SIP activos
docker compose exec asterisk asterisk -rx "sip show peers"

# Ver endpoints PJSIP
docker compose exec asterisk asterisk -rx "pjsip show endpoints"

# Ver dialplan
docker compose exec asterisk asterisk -rx "dialplan show"

# Recargar manualmente si es necesario
docker compose exec asterisk asterisk -rx "module reload chan_sip.so"
docker compose exec asterisk asterisk -rx "dialplan reload"
```

## 📊 Estructura de Archivos

```
backend/apps/telephony/
├── asterisk_config.py      # ✅ Generador de archivos .conf
├── asterisk_ami.py          # ✅ Cliente AMI sync + async
├── views.py                 # ✅ ViewSets con auto-reload
├── models.py                # Modelos de datos
├── serializers.py           # Serializers DRF
└── urls.py                  # Rutas API

frontend/src/components/Telephony/
├── Extensions.jsx           # ✅ CRUD completo con editar/borrar
├── InboundRoutes.jsx        # ✅ Manejo de respuestas paginadas
├── OutboundRoutes.jsx       # ✅ Manejo de respuestas paginadas
├── Voicemail.jsx            # ✅ Manejo de respuestas paginadas
├── MusicOnHold.jsx          # ✅ Manejo de respuestas paginadas
└── TimeConditions.jsx       # ✅ Manejo de respuestas paginadas
```

## ✨ Próximas Mejoras Sugeridas

1. **Estado en Tiempo Real**
   - Mostrar si extensión está registrada (online/offline)
   - Usar eventos AMI para actualizar estado en vivo

2. **Validaciones Avanzadas**
   - Verificar extensión disponible antes de crear
   - Validar formato de contraseñas seguras
   - Validar Caller ID format

3. **Importación Masiva**
   - CSV import de extensiones
   - Template Excel para bulk creation

4. **Provisionamiento Auto**
   - Generar configuraciones para teléfonos IP
   - Auto-provisioning vía TFTP/HTTP

5. **Auditoría**
   - Log de cambios en configuración
   - Historial de quién modificó qué

## 📝 Notas Finales

- **Seguridad**: La contraseña AMI debe ser fuerte y guardarse en `.env`
- **CORS**: Ya configurado con `CORS_ORIGIN_ALLOW_ALL=True` (cambiar en producción)
- **Paginación**: API devuelve máximo 50 registros por página
- **Autenticación**: JWT requerido para todos los endpoints
- **Timezone**: UTC configurado en Django

---

**Última actualización:** 7 de febrero de 2026  
**Versión:** 1.0.0  
**Autor:** VoziPOmni Development Team
