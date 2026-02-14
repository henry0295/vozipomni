# 🚀 Quick Start - Nuevas Funcionalidades

## ¿Qué hay de nuevo en VozipOmni v2.1?

### ✨ WebRTC Support
Agentes ahora pueden usar **WebPhone en el navegador** sin instalar nada.

**Ventajas:**
- ✅ Trabajo remoto total
- ✅ No instalar softphones
- ✅ Audio de alta calidad
- ✅ Seguro y encriptado

### 📞 Campañas Sin Wombat Dialer

**Pregunta:** ¿Puedo usar Asterisk para campañas sin Wombat Dialer?
**Respuesta:** **SÍ, completamente.**

| Tipo Campaña | ✅ Soportado | Descripción |
|--------------|--------------|-------------|
| **Manual** | ✅ | Click-to-call por agente |
| **Progresiva** | ✅ | 1 llamada por agente disponible |
| **Predictiva** | ✅ | Algoritmo inteligente, múltiples llamadas |
| **Call Blasting** | ✅ | Mensajes masivos sin agentes |

### 🔧 Componentes Nuevos

```
1. Kamailio       → Proxy SIP para WebRTC
2. RTPEngine      → Bridge de medios WebRTC ↔ VoIP
3. WebSocket      → Server para tareas asíncronas
4. Dialer Engine  → Motor de discado propio
5. WebPhone UI    → Componente Vue con JSSIP
```

---

## 🏃 Inicio Rápido

### 1. Instalar Frontend

```bash
cd frontend
npm install
```

### 2. Construir Servicios

```bash
docker-compose -f docker-compose.prod.yml build
```

### 3. Levantar Todo

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Verificar

```bash
# WebSocket Server
curl http://localhost:8765/health

# Ver logs del Dialer
docker-compose -f docker-compose.prod.yml logs -f dialer_engine

# Ver logs de Kamailio
docker-compose -f docker-compose.prod.yml logs -f kamailio
```

---

## 📞 Usar el WebPhone

1. **Login** en la aplicación web
2. El **WebPhone** aparece automáticamente en el dashboard
3. Se registra automáticamente con tus credenciales
4. **¡Listo para llamar!**

### Controles del WebPhone:

- ✅ Llamar / Colgar
- ✅ Mute / Unmute
- ✅ Hold / Resume
- ✅ Transferir
- ✅ DTMF (tonos)

---

## 🎯 Crear Campañas

### Campaña Manual

```python
# Desde Django Admin
Tipo: Manual
Agentes: Seleccionar agentes
Contactos: Cargar lista

# Los agentes ven los contactos y hacen click para llamar
```

### Campaña Progresiva

```python
# Desde Django Admin
Tipo: Progresiva
Ratio: 1:1 (automático)
Cola: Seleccionar cola
Troncal: Seleccionar troncal saliente

# El sistema llama automáticamente cuando hay agentes libres
```

### Campaña Predictiva

```python
# Desde Django Admin
Tipo: Predictiva
Ratio Inicial: 1.5
Objetivo Abandono: 3%
Cola: Seleccionar cola

# El algoritmo ajusta el ratio automáticamente
```

### Call Blasting

```python
# Desde Django Admin
Tipo: Call Blasting
Concurrencia: 50 llamadas simultáneas
Delay: 5 segundos entre lotes
Audio: Seleccionar mensaje grabado

# Sistema llama masivamente y reproduce el audio
```

---

## 📊 Arquitectura Simplificada

```
┌─────────────┐
│  BROWSER    │ ←→ WebPhone (JSSIP)
└──────┬──────┘
       │ WSS
┌──────▼──────┐
│  KAMAILIO   │ ←→ Proxy SIP WebRTC
└──────┬──────┘
       │ SIP UDP
┌──────▼──────┐
│  ASTERISK   │ ←→ PBX + Dialplan + Queues
└──────┬──────┘
       │ AMI
┌──────▼──────┐
│DIALER ENGINE│ ←→ Campañas (Prog/Pred/Blast)
└─────────────┘
```

---

## 🔧 Troubleshooting

### WebPhone no conecta

```bash
# Verificar Kamailio
docker-compose -f docker-compose.prod.yml logs kamailio

# Verificar puertos
netstat -an | grep 8080  # WebSocket
netstat -an | grep 5060  # SIP
```

### Campañas no inician

```bash
# Verificar Dialer Engine
docker-compose -f docker-compose.prod.yml logs dialer_engine

# Verificar Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli
> AUTH vozipomni_redis_2026
> KEYS campaign:*
```

### Audio cortado en WebRTC

```bash
# Verificar RTPEngine
docker-compose -f docker-compose.prod.yml logs rtpengine

# Verificar puertos RTP
netstat -an | grep "2300"  # Rango 23000-23100
```

---

## 📚 Documentación Completa

Ver [MEJORAS_OMNILEADS.md](MEJORAS_OMNILEADS.md) para documentación detallada de:

- Arquitectura completa
- Configuración avanzada
- Algoritmos de discado predictivo
- Integración con Asterisk
- API del WebSocket Server
- Personalización del WebPhone

---

## ✅ Estado del Proyecto

| Componente | Estado | Producción |
|------------|--------|------------|
| WebRTC (Kamailio + RTPEngine) | ✅ | ✅ |
| WebSocket Server | ✅ | ✅ |
| Dialer Engine | ✅ | ✅ |
| WebPhone Frontend | ✅ | ✅ |
| Redis Config Asterisk | ✅ | ✅ |
| Campaña Manual | ✅ | ✅ |
| Campaña Progresiva | ✅ | ✅ |
| Campaña Predictiva | ✅ | ✅ |
| Call Blasting | ✅ | ✅ |

**🎉 Todo listo para producción**

---

**Versión:** 2.1.0  
**Fecha:** 14 de febrero de 2026  
**Próxima actualización:** PSTN Emulator + Advanced Analytics
