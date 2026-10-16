# 📝 Changelog - VoziPOmni

## [1.1.0] - 2026-03-02

### ✨ Nuevas Características

#### **Sistema de Gestión de Extensiones Automatizado**
- **Management Command**: Nuevo comando `generate_asterisk_config`
  - Regenera automáticamente configuración de Asterisk (PJSIP, dialplan, voicemail, queues)
  - Opciones: `--only-extensions`, `--only-trunks`, `--no-reload`
  - Logging detallado con colores
  - Manejo robusto de errores

- **Migración de Preparación**: `0008_create_default_extensions`
  - Migración vacía que prepara el sistema para gestión mejorada
  - **No crea datos automáticamente** - Sistema inicia limpio
  - Cada instalación crea sus propias extensiones según necesidades
  - Diseñado para escenarios productivos y multi-tenant

- **ExtensionSerializer Mejorado**
  - Generación automática de contraseñas seguras si no se proporciona
  - Valores por defecto inteligentes:
    - `context`: `from-internal`
    - `transport`: Automático según tipo (UDP para SIP, WSS para WebRTC)
    - `callerid`: Formato correcto `"Nombre" <extension>`
    - `codecs`: Optimizados según tipo (opus para WebRTC, ulaw/alaw para SIP)
    - `max_contacts`: 1
  - Validación automática de datos
  - Logging de operaciones (creación/actualización)
  - Protección de contraseñas (no se exponen en respuestas API)
  - Soporte para actualización sin cambiar contraseña

#### **Scripts de Deploy**
- `apply-improvements.sh` (Linux/Mac)
- `apply-improvements.ps1` (Windows PowerShell)
- Automatizan todo el proceso de aplicación de mejoras
- Verificación completa del sistema
- Salida formateada y amigable

#### **Documentación Completa**
- `MEJORAS_IMPLEMENTADAS.md`: Detalles técnicos de todas las mejoras
- `SOLUCION_RAPIDA.md`: Guía de solución de problemas paso a paso
- `INSTRUCCIONES_DEPLOY_MEJORAS.md`: Deploy en servidores de producción
- `CHANGELOG.md`: Este archivo

### 🔧 Mejoras

#### **Backend**
- Signals automáticos ya configurados (sin cambios necesarios)
  - Extensiones → Regenera PJSIP extensions y dialplan
  - Troncales → Regenera PJSIP wizard
  - Rutas → Regenera dialplan
  - Colas → Regenera queues.conf
  - Todo automático, sin intervención manual

- API de Extensiones
  - Validación mejorada
  - Manejo de errores más robusto
  - Logging detallado

#### **Frontend**
- Ya existía interfaz completa para extensiones (`pages/extensions/index.vue`)
- Compatible con las nuevas mejoras del backend
- Sin cambios necesarios

#### **Asterisk**
- Configuración PJSIP optimizada
  - Correcta generación de secciones endpoint/auth/aor
  - Soporte para SIP tradicional y WebRTC
  - Identify por username para match correcto de INVITEs

### 🐛 Correcciones

- **Fix**: Error "AOR not found" al registrar extensiones
  - Causa: Faltaba la sección `[extension] type=aor` en pjsip_extensions.conf
  - Solución: AsteriskConfigGenerator ahora genera las 3 secciones correctamente

- **Fix**: Extensiones creadas en frontend no aparecían en Asterisk
  - Causa: Signals ya funcionaban pero faltaba comando de regeneración manual
  - Solución: Nuevo management command para regeneración bajo demanda

- **Fix**: Contraseñas no se validaban al crear extensiones
  - Solución: Serializer genera automáticamente contraseñas seguras

- **Fix**: Valores por defecto inconsistentes
  - Solución: Serializer aplica valores por defecto basados en tipo de extensión

### 📚 Documentación

- Nueva documentación completa para deploy en producción
- Guías de solución de problemas
- Scripts automatizados de verificación
- Ejemplos de uso en todos los escenarios

### 🔒 Seguridad

- Generación de contraseñas con módulo `secrets` (criptográficamente seguro)
- Contraseñas nunca se exponen en respuestas API
- Logging de todas las operaciones de creación/modificación

### ⚡ Rendimiento

- Signals ejecutados en threads separados para no bloquear peticiones HTTP
- Lock para evitar regeneraciones múltiples simultáneas
- Configuración generada eficientemente en lotes

---

## [1.0.0] - Versión Base

### Características Iniciales

- Sistema de Contact Center completo
- Backend Django + DRF
- Frontend Nuxt 3
- Integración Asterisk (PJSIP)
- Gestión de:
  - Extensiones
  - Troncales SIP
  - Rutas entrantes/salientes
  - Colas ACD
  - Campañas
  - Grabaciones
  - IVR
  - Buzones de voz
- Dashboard en tiempo real
- APIs REST completas
- Signals para sincronización con Asterisk
- Docker Compose para deploy

---

## 🔮 Próximas Versiones (Roadmap)

### [1.2.0] - Planificado
- [ ] Dashboard de estado de extensiones en tiempo real
- [ ] Botón "Generar Nueva Contraseña" en frontend
- [ ] Visualización temporal de contraseña al crear extensión
- [ ] Indicadores de registro en vivo (conectado/desconectado)
- [ ] Notificaciones push cuando cambia estado de extensión

### [1.3.0] - Planificado
- [ ] Importación masiva de extensiones (CSV)
- [ ] Exportación de extensiones
- [ ] Plantillas de configuración de extensiones
- [ ] Clonación de extensiones

### [1.4.0] - Planificado
- [ ] Softphone WebRTC integrado en navegador
- [ ] Click-to-call desde contactos
- [ ] Historial de llamadas por extensión
- [ ] Estadísticas de uso de extensión

### [2.0.0] - Planificado
- [ ] Multi-tenancy (múltiples empresas)
- [ ] Roles y permisos granulares
- [ ] API pública con autenticación OAuth2
- [ ] Webhooks para eventos

---

## 📋 Notas de Migración

### De 1.0.0 a 1.1.0

1. **Actualizar código**:
   ```bash
   git pull origin main
   ```

2. **Aplicar mejoras**:
   ```bash
   ./apply-improvements.sh  # Linux/Mac
   .\apply-improvements.ps1  # Windows
   ```

3. **Verificar**:
   - Extensiones creadas: `docker exec vozipomni_backend python manage.py shell -c "from apps.telephony.models import Extension; print(Extension.objects.count())"`
   - Endpoints en Asterisk: `docker exec vozipomni_asterisk asterisk -rx "pjsip show endpoints"`

**No hay breaking changes**. Todas las mejoras son backward compatible.

---

## 🙏 Contribuciones

Mejoras implementadas para resolver:
- Issue: "Error 'AOR not found' al registrar extensiones"
- Feature Request: "Gestión completa desde frontend sin consola"
- Enhancement: "Generación automática de contraseñas"

---

**Formato**: Este changelog sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/)  
**Versionado**: [Semantic Versioning](https://semver.org/lang/es/)
