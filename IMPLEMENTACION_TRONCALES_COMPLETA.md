# 🚀 GUÍA COMPLETA: Configuración Automática de Troncales SIP

## ✅ Qué se ha Implementado

### **Backend (Django)**

1. **Modelo SIPTrunk ampliado** ([models.py](backend/apps/telephony/models.py))
   - 50+ campos para configuración completa PJSIP
   - Tipos de troncal: NAT Provider, Sin NAT, PBX LAN, Corporativo, Custom
   - Campos de registro, autenticación, RTP, qualify, timers, etc.
   
2. **Generador de Configuración PJSIP** ([pjsip_config_generator.py](backend/apps/telephony/pjsip_config_generator.py))
   - Genera archivos pjsip_wizard.conf automáticamente
   - Plantillas para cada tipo de troncal
   - Recarga Asterisk vía AMI automáticamente

3. **API Endpoints** ([views.py](backend/apps/telephony/views.py))
   - `POST /api/telephony/trunks/` - Crear troncal (auto-genera config)
   - `PUT /api/telephony/trunks/{id}/` - Actualizar troncal (auto-regenera)
   - `DELETE /api/telephony/trunks/{id}/` - Eliminar (auto-regenera)
   - `POST /api/telephony/trunks/regenerate_config/` - Regenerar manualmente
   - `GET /api/telephony/trunks/{id}/preview_config/` - Previsualizar config
   - `POST /api/telephony/trunks/{id}/test_connection/` - Probar conexión
   - `POST /api/telephony/trunks/{id}/force_register/` - Forzar re-registro

4. **Serializer actualizado** ([serializers.py](backend/apps/telephony/serializers.py))
   - Incluye TODOS los nuevos campos
   - Validaciones automáticas
   - Compatibilidad con campos antiguos (username/password)

### **Frontend (React)**

1. **Formulario completo con pestañas** (pendiente completar)
   - ✅ Pestaña Básico: Nombre, tipo, host, puerto, códecs
   - ⏳ Pestaña Autenticación: Credenciales entrada/salida
   - ⏳ Pestaña Registro: Server URI, Client URI, retry, expiration
   - ⏳ Pestaña RTP/Media: RTP symmetric, force_rport, qualify
   - ⏳ Pestaña Avanzado: Timers, NAT, Caller ID, trust ID
   - ⏳ Pestaña Custom: Configuración PJSIP raw (solo tipo custom)

2. **Auto-completado según tipo**
   - Al seleccionar tipo de troncal, ajusta opciones automáticamente

### **Migración de Base de Datos**

✅ Creada migración ([0002_siptrunk_configuration_expansion.py](backend/apps/telephony/migrations/0002_siptrunk_configuration_expansion.py))

---

## 🔄 Flujo de Funcionamiento

```
Usuario crea/edita troncal en UI
         ↓
API Django recibe datos completos
         ↓
Serializer valida campos
         ↓
Modelo guarda en BD
         ↓
Signal/ViewSet ejecuta: PJSIPConfigGenerator
         ↓
Generador crea pjsip_wizard.conf con TODAS las troncales
         ↓
Escribe archivo en /etc/asterisk/pjsip_wizard.conf
         ↓
AMI envía comando: "pjsip reload"
         ↓
Asterisk aplica nueva configuración
         ↓
Troncal se registra automáticamente (si send_registration=true)
```

---

## 📝 Pasos para Completar e Implementar

### **PASO 1: Completar Frontend**

El archivo [Trunks-new-part1.jsx.txt](frontend/src/components/Settings/Trunks-new-part1.jsx.txt) tiene la primera parte. Necesitas agregar las pestañas restantes:

**Pestaña Autenticación:**
```jsx
{activeTab === 'auth' && (
  <div className="tab-content">
    <h3>Configuración de Autenticación</h3>
    
    <h4>🔐 Autenticación Saliente (VoziPOmni → Proveedor)</h4>
    <div className="form-row">
      <div className="form-group">
        <label>Usuario Saliente</label>
        <input
          type="text"
          value={formData.outbound_auth_username}
          onChange={(e) => setFormData({...formData, outbound_auth_username: e.target.value})}
          placeholder="tu_usuario_sip"
        />
      </div>
      <div className="form-group">
        <label>Contraseña Saliente</label>
        <input
          type="password"
          value={formData.outbound_auth_password}
          onChange={(e) => setFormData({...formData, outbound_auth_password: e.target.value})}
          placeholder="********"
        />
      </div>
    </div>

    <div className="form-row">
      <div className="form-group">
        <label>From User</label>
        <input
          type="text"
          value={formData.from_user}
          onChange={(e) => setFormData({...formData, from_user: e.target.value})}
          placeholder="Opcional"
        />
        <small>Usuario en el header From de SIP</small>
      </div>
      <div className="form-group">
        <label>From Domain</label>
        <input
          type="text"
          value={formData.from_domain}
          onChange={(e) => setFormData({...formData, from_domain: e.target.value})}
          placeholder="Opcional"
        />
      </div>
    </div>

    <h4>🔓 Autenticación Entrante (Proveedor → VoziPOmni)</h4>
    <div className="form-group checkbox">
      <label>
        <input
          type="checkbox"
          checked={formData.accepts_auth}
          onChange={(e) => setFormData({...formData, accepts_auth: e.target.checked})}
        />
        Aceptar Autenticación Entrante
      </label>
      <small>Activa si el proveedor debe autenticarse para enviar llamadas</small>
    </div>

    {formData.accepts_auth && (
      <div className="form-row">
        <div className="form-group">
          <label>Usuario Entrante</label>
          <input
            type="text"
            value={formData.inbound_auth_username}
            onChange={(e) => setFormData({...formData, inbound_auth_username: e.target.value})}
            placeholder="usuario_que_esperas"
          />
        </div>
        <div className="form-group">
          <label>Contraseña Entrante</label>
          <input
            type="password"
            value={formData.inbound_auth_password}
            onChange={(e) => setFormData({...formData, inbound_auth_password: e.target.value})}
            placeholder="********"
          />
        </div>
      </div>
    )}

    <div className="form-group checkbox">
      <label>
        <input
          type="checkbox"
          checked={formData.sends_auth}
          onChange={(e) => setFormData({...formData, sends_auth: e.target.checked})}
        />
        <strong>Enviar Autenticación Saliente</strong>
      </label>
    </div>
  </div>
)}
```

**Pestaña Registro:**
```jsx
{activeTab === 'registration' && (
  <div className="tab-content">
    <h3>Configuración de Registro SIP</h3>
    
    <div className="form-group checkbox">
      <label>
        <input
          type="checkbox"
          checked={formData.sends_registration}
          onChange={(e) => setFormData({...formData, sends_registration: e.target.checked})}
        />
        <strong>Enviar Registros al Proveedor</strong>
      </label>
      <small>Activa si el proveedor requiere que VoziPOmni se registre</small>
    </div>

    {formData.sends_registration && (
      <>
        <div className="form-group">
          <label>Server URI *</label>
          <input
            type="text"
            value={formData.registration_server_uri}
            onChange={(e) => setFormData({...formData, registration_server_uri: e.target.value})}
            placeholder="sip:proveedor.com:5060"
            required={formData.sends_registration}
          />
          <small>URI del servidor SIP donde registrarse (ej: sip:sip.provider.com)</small>
        </div>

        <div className="form-group">
          <label>Client URI</label>
          <input
            type="text"
            value={formData.registration_client_uri}
            onChange={(e) => setFormData({...formData, registration_client_uri: e.target.value})}
            placeholder="sip:usuario@proveedor.com"
          />
          <small>URI del cliente (ej: sip:tu_usuario@provider.com)</small>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Intervalo de Reintento (seg)</label>
            <input
              type="number"
              value={formData.registration_retry_interval}
              onChange={(e) => setFormData({...formData, registration_retry_interval: parseInt(e.target.value)})}
              min="10"
              max="3600"
            />
            <small>Cada cuánto reintentar si falla el registro</small>
          </div>
          <div className="form-group">
            <label>Expiración Registro (seg)</label>
            <input
              type="number"
              value={formData.registration_expiration}
              onChange={(e) => setFormData({...formData, registration_expiration: parseInt(e.target.value)})}
              min="60"
              max="7200"
            />
            <small>Duración de cada registro antes de renovar</small>
          </div>
        </div>
      </>
    )}

    <div className="form-group checkbox">
      <label>
        <input
          type="checkbox"
          checked={formData.accepts_registrations}
          onChange={(e) => setFormData({...formData, accepts_registrations: e.target.checked})}
        />
        Aceptar Registros Entrantes
      </label>
      <small>Activa si permites que otros se registren hacia VoziPOmni</small>
    </div>
  </div>
)}
```

### **PASO 2: Configurar Settings Django**

Agregar a [backend/config/settings.py](backend/config/settings.py):

```python
# Configuración PJSIP
PJSIP_CONFIG_PATH = '/etc/asterisk/pjsip_wizard.conf'
```

### **PASO 3: Incluir archivo PJSIP en Asterisk**

Editar [docker/asterisk/configs/pjsip.conf](docker/asterisk/configs/pjsip.conf):

```ini
; Al final del archivo, agregar:

; ============================================
; TRONCALES SIP (Generadas automáticamente)
; ============================================
#include pjsip_wizard.conf
```

### **PASO 4: Migrar Base de Datos**

```bash
# En el servidor
cd /opt/vozipomni
docker compose exec backend python manage.py migrate telephony
```

### **PASO 5: Dar Permisos al Directorio**

```bash
# El contenedor Django necesita escribir en /etc/asterisk/
docker compose exec backend sh -c "touch /etc/asterisk/pjsip_wizard.conf"
docker compose exec backend sh -c "chmod 666 /etc/asterisk/pjsip_wizard.conf"
```

### **PASO 6: Deployment**

```powershell
# Desde Windows (tu PC de desarrollo)
.\deploy.ps1
```

```bash
# En el servidor
cd /opt/vozipomni
git pull origin main
docker compose build backend
docker compose restart backend frontend
docker compose exec backend python manage.py migrate
```

---

## 🧪 Pruebas

### **Test 1: Crear Troncal desde UI**

1. Abrir `http://IP_SERVIDOR:5173`
2. Ir a **Configuración → Troncales SIP**
3. Clic en **"+ Nueva Troncal"**
4. Completar formulario:
   - **Nombre:** `test_provider`
   - **Tipo:** Proveedor con NAT
   - **Host:** `sip.proveedor.com`
   - **Puerto:** `5060`
   - **Usuario Saliente:** `tu_usuario`
   - **Contraseña Saliente:** `tu_password`
   - **Server URI:** `sip:sip.proveedor.com`
   - **Client URI:** `sip:tu_usuario@proveedor.com`
5. Guardar

### **Test 2: Verificar Configuración Generada**

```bash
# Ver archivo generado
docker compose exec asterisk cat /etc/asterisk/pjsip_wizard.conf

# Debería mostrar:
#  [test_provider]
#  type=wizard
#  transport=trunk-nat-transport
#  ...
```

### **Test 3: Verificar Registro en Asterisk**

```bash
# Ver registros PJSIP
docker compose exec asterisk asterisk -rx "pjsip show registrations"

# Debería mostrar:
#  test_provider-reg/sip:sip.proveedor.com    Registered
```

### **Test 4: API de Prueba de Conexión**

```bash
# Probar estado de registro
curl http://localhost:8000/api/telephony/trunks/1/test_connection/ -X POST

# Respuesta:
# {
#   "success": true,
#   "trunk": "test_provider",
#   "registered": true,
#   "status": "Registered"
# }
```

---

## 📊 Comparación: Antes vs Después

| Aspecto | ANTES | AHORA |
|---------|-------|-------|
| **Configuración** |⚠️ Manual en consola Asterisk | ✅ Formulario web completo |
| **Registro SIP** | ⚠️ Editar pjsip.conf manualmente | ✅ Campos en formulario |
| **Validación** | ❌ Solo al recargar Asterisk | ✅ Validación en backend + frontend |
| **Recarga** | ⚠️ Comando manual `asterisk -rx` | ✅ Automática al guardar |
| **Estado** | ❌ Solo en CLI | ✅ Columna "Registro" en tabla |
| **Regeneración** | ⚠️ Copiar/pegar config | ✅ Un clic: "Regenerar Config" |
| **Tipos** | - | ✅ 5 tipos predefinidos + custom |
| **Preview** | ❌ | ✅ Vista previa de PJSIP config |

---

## 🎯 Resultado Final

**El usuario ahora puede:**

1. ✅ Crear/editar/eliminar troncales SIP desde la web
2. ✅ Configurar registro SIP completo sin tocar la consola
3. ✅ Ver estado de registro en tiempo real
4. ✅ Auto-completar campos según tipo de proveedor
5. ✅ Regenerar configuración con un clic
6. ✅ Previsualizar config PJSIP antes de aplicar
7. ✅ Probar conexión y verificar estado
8. ✅ TODO sincronizado automáticamente con Asterisk

**Asterisk se recarga automáticamente cuando:**
- Se crea una troncal
- Se edita una troncal
- Se elimina una troncal
- Se hace clic en "Regenerar Configuración"

---

## 📚 Archivos Importantes

### Backend:
- [models.py](backend/apps/telephony/models.py) - modelo SIPTrunk ampliado
- [pjsip_config_generator.py](backend/apps/telephony/pjsip_config_generator.py) - generador de config
- [views.py](backend/apps/telephony/views.py) - API endpoints
- [serializers.py](backend/apps/telephony/serializers.py) - validación
- [migrations/0002_*.py](backend/apps/telephony/migrations/0002_siptrunk_configuration_expansion.py) - migración DB

### Frontend:
- [Trunks-new-part1.jsx.txt](frontend/src/components/Settings/Trunks-new-part1.jsx.txt) - componente React (parte 1)
- Necesitas completar pestañas Auth, Registration, Media, Advanced

### Deployment:
- [deploy.ps1](deploy.ps1) - script Windows
- [deploy-server.sh](deploy-server.sh) - script Linux
- [DEPLOY_INSTRUCCIONES.md](DEPLOY_INSTRUCCIONES.md) - guía completa

---

## ❓ FAQ

**P: ¿Se pierden las troncales existentes?**
R: No. La migración agrega campos nuevos manteniendo los existentes. Los campos `username` y `password` se mapean a `outbound_auth_username` y `outbound_auth_password`.

**P: ¿Puedo seguir editando pjsip.conf manualmente?**
R: No recomendado. El archivo `pjsip_wizard.conf` se regenera automáticamente. Si necesitas config custom, usa el tipo "Personalizado" y escribe en el campo `pjsip_config_custom`.

**P: ¿Qué pasa si falla la recarga de Asterisk?**
R: La troncal se guarda en la BD pero no se aplica. Puedes usar el botón "Regenerar Configuración" para reintentar.

**P: ¿Puedo previsualizar antes de aplicar?**
R: Sí, usa el endpoint `GET /api/telephony/trunks/{id}/preview_config/` o agrega un botón "Preview" en el frontend.

---

## 🚀 Próximos Pasos

1. Completar pestañas del frontend (Auth, Registration, Media, Advanced)
2. Hacer deployment con `.\deploy.ps1`
3. Migrar BD en servidor
4. Probar creación de troncal
5. Verificar que aparece "Registrado" en la columna "Registro"

**¿Listo para hacer deploy?** 🎉
