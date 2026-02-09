# 🔍 Por Qué Aparece "Sin Configurar" en la Columna de Registro

## Problema Actual

Al ver la tabla de Troncales SIP, la columna **"Registro"** muestra el badge **"Sin Configurar"** en color azul/info.

---

## ✅ Esto NO es un error - Es el comportamiento correcto

El estado **"Sin Configurar"** significa que:

> La troncal existe en la base de datos de VoziPOmni, pero **no tiene configurado el componente de REGISTRO** en Asterisk PJSIP.

---

## 📖 Conceptos: Troncal vs Registro

### 1. **Troncal SIP (Endpoint)**
- Permite **recibir y realizar** llamadas
- Se configura con: endpoint, auth, aor
- Puede funcionar **sin registro**
- Útil para proveedores que usan IP estática

### 2. **Registro SIP (Registration)**
- Permite **registrarse** en un servidor SIP remoto
- Envía credenciales al proveedor
- Mantiene sesión activa
- Necesario para la mayoría de proveedores VoIP

---

## 🏗️ Arquitectura de una Troncal PJSIP Completa

```ini
# /etc/asterisk/pjsip.conf

# ========== 1. ENDPOINT (obligatorio) ==========
[mi_troncal]
type=endpoint
context=from-trunk
transport=transport-udp
aors=mi_troncal-aor
outbound_auth=mi_troncal-auth
allow=ulaw,alaw,g729
direct_media=no

# ========== 2. AOR (Address of Record) ==========
[mi_troncal-aor]
type=aor
contact=sip:proveedor.com:5060
max_contacts=1
qualify_frequency=60

# ========== 3. AUTH (Autenticación) ==========
[mi_troncal-auth]
type=auth
auth_type=userpass
username=mi_usuario
password=mi_contraseña

# ========== 4. REGISTRATION (OPCIONAL) ==========
# ⚠️ ESTE ES EL COMPONENTE QUE FALTA
[mi_troncal-reg]
type=registration
transport=transport-udp
outbound_auth=mi_troncal-auth
server_uri=sip:proveedor.com
client_uri=sip:mi_usuario@proveedor.com
retry_interval=60
expiration=3600
```

---

## 🔍 Cómo Funciona la Detección de Registro

### Flujo del Código:

```
1. Frontend solicita: GET /api/telephony/trunks/
                             ↓
2. SIPTrunkSerializer ejecuta: get_registration_detail()
                             ↓
3. asterisk_ami.py ejecuta: pjsip_show_registrations()
                             ↓
4. Asterisk AMI comando: PJSIPShowRegistrations
                             ↓
5. Asterisk retorna: Lista de objetos [registration]
                             ↓
6. asterisk_ami.py busca: "prueba" o "prueba-reg"
                             ↓
7. Si NO encuentra → return 'Not Configured'
                             ↓
8. Serializer mapea: 'Not Configured' → {'text': 'Sin Configurar', 'class': 'info'}
                             ↓
9. Frontend muestra: Badge azul "Sin Configurar"
```

### Código en `asterisk_ami.py` líneas 174-198:

```python
def get_trunk_registration_status(self, trunk_name):
    """Obtener estado de registro de una troncal específica"""
    try:
        registrations = self.pjsip_show_registrations()
        
        # Buscar por nombre de troncal o nombre con sufijo -reg
        trunk_key = trunk_name                    # Busca "prueba"
        if trunk_key not in registrations:
            trunk_key = f"{trunk_name}-reg"      # Busca "prueba-reg"
        
        if trunk_key in registrations:
            # Encontró el registro → verificar estado
            status = registrations[trunk_key].get('status', 'Unknown')
            # ... procesar estado ...
        
        # No encontró ningún registro
        return 'Not Configured'  # ← Por eso aparece "Sin Configurar"
```

---

## ✅ Posibles Estados de Registro

| Estado AMI | Texto en UI | Clase CSS | Significado |
|------------|-------------|-----------|-------------|
| `Registered` | Registrado | success (verde) | ✅ Conectado al proveedor |
| `Unregistered` | No Registrado | warning (amarillo) | ⚠️ Sin conexión activa |
| `Failed` / `Rejected` | Fallo | error (rojo) | ❌ Error de autenticación |
| `Not Configured` | **Sin Configurar** | **info (azul)** | ℹ️ **No hay objeto [registration]** |
| `Disconnected` | Asterisk Desconectado | error (rojo) | ❌ AMI no conectado |
| `Unknown` | Desconocido | warning (amarillo) | ⚠️ Estado no reconocido |

---

## 🛠️ Soluciones

### Opción 1: Configurar el Registro en Asterisk (Recomendado)

Si tu proveedor SIP requiere registro, debes configurar el objeto `[registration]`:

#### Paso 1: Conectar al servidor

```bash
ssh usuario@IP_SERVIDOR
cd /opt/vozipomni
```

#### Paso 2: Editar configuración PJSIP

```bash
# Editar archivo de configuración
docker compose exec asterisk sh -c "vi /etc/asterisk/pjsip.conf"

# O editar localmente en el host
sudo nano docker/asterisk/configs/pjsip.conf
```

#### Paso 3: Agregar configuración de registro

```ini
# Al final del archivo, agregar:

[prueba-reg]
type=registration
transport=transport-udp
outbound_auth=prueba-auth
server_uri=sip:prueba.sip.com         ← Servidor del proveedor
client_uri=sip:prueba@prueba.sip.com  ← Tu usuario@proveedor
contact_user=prueba
retry_interval=60
forbidden_retry_interval=300
expiration=3600
max_retries=10
auth_rejection_permanent=yes
```

#### Paso 4: Recargar Asterisk

```bash
docker compose exec asterisk asterisk -rx "pjsip reload"
```

#### Paso 5: Verificar registro

```bash
# Ver todos los registros
docker compose exec asterisk asterisk -rx "pjsip show registrations"

# Salida esperada:
#  <Registration/ServerURI..............................>  <State.......>
#  ==========================================================================================
#  prueba-reg/sip:prueba.sip.com                          Registered
```

#### Paso 6: Verificar en la UI

1. Abrir navegador → VoziPOmni → Configuración → Troncales SIP
2. Hacer clic en **Recargar** o refrescar página
3. La columna **"Registro"** ahora debería mostrar: **"Registrado"** (verde)

---

### Opción 2: Aceptar que la Troncal NO Requiere Registro

Algunos proveedores SIP **no requieren registro** porque:
- Usan autenticación por IP (whitelist)
- Aceptan llamadas directas de IPs específicas
- Configuración punto a punto (peer-to-peer)

#### En este caso, "Sin Configurar" es correcto:

**Mensaje actual:**
```
🔵 Sin Configurar
```

**Posible mejora (opcional):**

Si quieres un mensaje más descriptivo, podemos cambiar el texto a:
```
ℹ️ Peer (sin registro)
```

---

### Opción 3: Modificar el Código para Otro Mensaje

Si prefieres un mensaje diferente cuando no hay registro configurado:

#### Modificar `backend/apps/telephony/serializers.py`:

```python
def get_registration_detail(self, obj):
    """Obtener detalle legible del estado de registro"""
    status = self.get_registration_status(obj)
    
    status_map = {
        'Registered': {'text': 'Registrado', 'class': 'success'},
        'Unregistered': {'text': 'No Registrado', 'class': 'warning'},
        'Failed': {'text': 'Fallo', 'class': 'error'},
        'Not Configured': {'text': 'Peer (sin registro)', 'class': 'info'},  # ← Cambiar aquí
        # ... resto igual
    }
```

---

## 🧪 Verificar Estado de Registro Manualmente

### En el Servidor Linux:

```bash
# Conectar a Asterisk CLI
docker compose exec asterisk asterisk -rvvv

# En la consola de Asterisk:
pjsip show registrations

# Ver detalles de un registro específico:
pjsip show registration prueba-reg

# Ver endpoints:
pjsip show endpoints

# Ver estado completo:
pjsip show endpoint prueba
```

### Desde la API (en desarrollo):

```bash
# Llamar directamente a la API
curl http://localhost:8000/api/telephony/trunks/ | jq '.[0].registration_detail'

# Salida esperada:
{
  "text": "Sin Configurar",
  "class": "info"
}
```

---

## 📊 Diagrama de Decisión

```
┌─────────────────────────────────────────┐
│ ¿La troncal necesita REGISTRARSE en el  │
│ servidor del proveedor SIP?             │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
      SÍ              NO
       │               │
       │               └──► "Sin Configurar" es OK
       │                   La troncal funciona como PEER
       │
       └──► Configurar objeto [registration]
            en /etc/asterisk/pjsip.conf
```

---

## ❓ FAQ

### 1. ¿Mi troncal no funciona porque dice "Sin Configurar"?

**No necesariamente.** Depende de tu proveedor:
- Si el proveedor **requiere registro** → Debes configurar `[registration]`
- Si el proveedor **autentica por IP** → No necesitas registro, la troncal funciona igual

### 2. ¿Cómo sé si mi proveedor requiere registro?

Revisa la documentación de tu proveedor VoIP. Palabras clave:
- **"Username/Password authentication"** → SÍ requiere registro
- **"IP authentication"** o **"Whitelist"** → NO requiere registro

### 3. ¿Puedo ocultar la columna "Registro" si no la uso?

Sí, puedes comentar la columna en [frontend/src/components/Settings/Trunks.jsx](frontend/src/components/Settings/Trunks.jsx#L137):

```jsx
{/* <th>Registro</th> */}

// Y en el cuerpo de la tabla:
{/* <td>
  <span className={`status-badge ...`}>
    {trunk.registration_detail?.text || 'Verificando...'}
  </span>
</td> */}
```

---

## ✅ Resumen

**Estado Actual:** "Sin Configurar" (azul)

**Significado:** La troncal existe pero no tiene configurado el objeto `[registration]` en Asterisk PJSIP

**Acción Requerida:**

1. ✅ **Si tu proveedor requiere registro** → Configurar `[nombre-reg]` en pjsip.conf
2. ✅ **Si es autenticación por IP** → Dejar como está, es correcto
3. ✅ **Si prefieres otro texto** → Modificar el mapeo en serializers.py

---

## 📞 Próximos Pasos

1. Verificar con tu proveedor SIP si requiere registro
2. Si sí, seguir "Opción 1: Configurar el Registro"
3. Si no, considerar cambiar el mensaje a algo más claro
4. Hacer deploy de los cambios al servidor

**¿Necesitas ayuda configurando el registro en Asterisk?** 🚀
