# Nuevas Funcionalidades Implementadas

## 🎯 Resumen

Se han implementado 3 funcionalidades críticas para VoziPOmni:

1. ✅ **Integración Asterisk AMI** - Comunicación en tiempo real con Asterisk
2. ✅ **WebRTC Softphone** - Softphone funcional en React con JsSIP
3. ✅ **Dashboard en Tiempo Real** - Monitoreo en vivo con WebSocket

---

## 📞 1. Integración Asterisk AMI

### Archivos Creados

- `backend/apps/telephony/asterisk_ami.py` - Cliente AMI principal
- `backend/apps/telephony/services.py` - Servicios de alto nivel
- `backend/apps/api/consumers_enhanced.py` - WebSocket consumers mejorados

### Características

#### Cliente AMI (`AsteriskAMI`)
```python
from apps.telephony.asterisk_ami import asterisk_ami

# Originar llamada
await asterisk_ami.originate_call(
    channel="PJSIP/1000",
    extension="573001234567",
    caller_id="Contact Center"
)

# Colgar llamada
await asterisk_ami.hangup(channel="PJSIP/1000-00000001")

# Gestión de colas
await asterisk_ami.add_queue_member(
    queue="ventas",
    interface="PJSIP/1000",
    member_name="Juan Pérez"
)

# Pausar agente
await asterisk_ami.pause_queue_member(
    queue="ventas",
    interface="PJSIP/1000",
    paused=True
)

# Grabar llamada
await asterisk_ami.monitor_start(
    channel="PJSIP/1000-00000001",
    filename="/var/spool/asterisk/monitor/call-123"
)
```

#### Eventos Soportados

**Eventos de Llamadas:**
- `Newchannel` → Nuevo canal creado
- `Newstate` → Cambio de estado
- `Hangup` → Llamada colgada
- `Bridge` → Dos canales conectados

**Eventos de Agentes:**
- `AgentConnect` → Agente conectado a llamada
- `AgentComplete` → Llamada completada

**Eventos de Colas:**
- `QueueMemberAdded` → Agente agregado a cola
- `QueueMemberStatus` → Estado de agente
- `QueueCallerJoin` → Llamada ingresa a cola
- `QueueCallerLeave` → Llamada sale de cola
- `QueueCallerAbandon` → Llamada abandonada

#### Servicios Wrapper (`CallService`, `QueueService`)

```python
from apps.telephony.services import CallService, QueueService

# Originar llamada (síncrono)
result = CallService.originate_call(
    agent_extension="1000",
    destination="573001234567",
    campaign_id=5
)

# Agregar agente a cola
result = QueueService.add_agent_to_queue(
    queue_name="ventas",
    agent_extension="1000",
    agent_name="Juan Pérez"
)

# Pausar agente
result = QueueService.pause_agent(
    queue_name="ventas",
    agent_extension="1000",
    paused=True,
    reason="Descanso"
)
```

### Configuración Necesaria

#### 1. Variables de Entorno (`.env`)

```env
# Asterisk AMI
ASTERISK_HOST=asterisk
ASTERISK_AMI_PORT=5038
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=VoziPOmni2026!
ASTERISK_PUBLIC_IP=192.168.1.100
```

#### 2. Actualizar `settings.py`

```python
# Asterisk Configuration
ASTERISK_HOST = env('ASTERISK_HOST', default='asterisk')
ASTERISK_AMI_PORT = env.int('ASTERISK_AMI_PORT', default=5038)
ASTERISK_AMI_USER = env('ASTERISK_AMI_USER', default='admin')
ASTERISK_AMI_PASSWORD = env('ASTERISK_AMI_PASSWORD')
ASTERISK_PUBLIC_IP = env('ASTERISK_PUBLIC_IP')
```

#### 3. Iniciar AMI al arrancar Django

En `apps.py` de telephony:

```python
from django.apps import AppConfig
from django.conf import settings

class TelephonyConfig(AppConfig):
    name = 'apps.telephony'

    def ready(self):
        if settings.ASTERISK_AMI_ENABLE:
            from .asterisk_ami import start_ami_service
            import asyncio
            asyncio.create_task(start_ami_service())
```

---

## 📱 2. WebRTC Softphone

### Archivo Creado

- `frontend/src/components/WebRTC/Softphone.jsx`

### Características

- ✅ Registro SIP automático
- ✅ Llamadas salientes (outbound)
- ✅ Llamadas entrantes (inbound)
- ✅ Dial pad con DTMF
- ✅ Mute/Unmute
- ✅ Control de volumen
- ✅ Timer de duración
- ✅ Indicador de conexión
- ✅ Manejo de llamadas perdidas

### Uso

```jsx
import Softphone from './components/WebRTC/Softphone';

function AgentConsole() {
  return (
    <Softphone
      agentExtension="1000"
      sipPassword="secret123"
      wsServer="wss://192.168.1.100:8089/ws"
    />
  );
}
```

### Dependencias

```bash
cd frontend
npm install jssip lucide-react
```

### Configuración Asterisk

Verificar que en `pjsip.conf` esté habilitado WebRTC:

```ini
[transport-wss]
type=transport
protocol=wss
bind=0.0.0.0:8089
```

---

## 📊 3. Dashboard en Tiempo Real

### Archivo Creado

- `frontend/src/components/Dashboard/RealtimeDashboard.jsx`

### Características

#### Estadísticas en Vivo
- Llamadas hoy (total, contestadas, abandonadas)
- Nivel de servicio (< 20s)
- Agentes por estado (listos, en llamada, ACW, pausados)
- Tiempo promedio de conversación

#### Monitoreo de Agentes
- Lista de agentes con estado en tiempo real
- Llamadas del día por agente
- Tiempo promedio por agente
- Indicador visual de estado

#### Llamadas Activas
- Lista de llamadas en curso
- Caller ID y agente asignado
- Duración en tiempo real

#### Colas ACD
- Estado de todas las colas
- Llamadas en espera
- Llamadas contestadas/abandonadas
- Tiempo promedio de espera

#### Log de Eventos
- Stream en vivo de eventos de Asterisk
- Últimos 20 eventos
- Timestamp de cada evento

### Uso

```jsx
import RealtimeDashboard from './components/Dashboard/RealtimeDashboard';

function DashboardPage() {
  const wsUrl = `wss://${window.location.host}/ws/dashboard/`;
  
  return <RealtimeDashboard wsUrl={wsUrl} />;
}
```

### WebSocket Backend

El dashboard se conecta a `consumers_enhanced.py`:

```python
# routing.py
from django.urls import re_path
from apps.api import consumers_enhanced

websocket_urlpatterns = [
    re_path(r'ws/dashboard/$', consumers_enhanced.RealtimeDashboardConsumer.as_asgi()),
    re_path(r'ws/asterisk/$', consumers_enhanced.AsteriskEventConsumer.as_asgi()),
]
```

---

## 🚀 Cómo Usar las Nuevas Funcionalidades

### Paso 1: Instalar Dependencias Backend

```bash
cd backend
pip install panoramisk==1.4
```

### Paso 2: Instalar Dependencias Frontend

```bash
cd frontend
npm install jssip lucide-react
```

### Paso 3: Configurar Variables de Entorno

Editar `backend/.env`:

```env
# Asterisk AMI
ASTERISK_HOST=asterisk
ASTERISK_AMI_PORT=5038
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=VoziPOmni2026!
ASTERISK_PUBLIC_IP=192.168.1.100

# WebSocket
ASTERISK_AMI_ENABLE=True
```

### Paso 4: Actualizar Configuración Django

Agregar al `settings.py`:

```python
# Asterisk
ASTERISK_HOST = env('ASTERISK_HOST', default='asterisk')
ASTERISK_AMI_PORT = env.int('ASTERISK_AMI_PORT', default=5038)
ASTERISK_AMI_USER = env('ASTERISK_AMI_USER', default='admin')
ASTERISK_AMI_PASSWORD = env('ASTERISK_AMI_PASSWORD')
ASTERISK_PUBLIC_IP = env('ASTERISK_PUBLIC_IP')
ASTERISK_AMI_ENABLE = env.bool('ASTERISK_AMI_ENABLE', default=True)
```

### Paso 5: Actualizar Routing WebSocket

En `backend/apps/api/routing.py`:

```python
from django.urls import re_path
from . import consumers_enhanced

websocket_urlpatterns = [
    re_path(r'ws/dashboard/$', consumers_enhanced.RealtimeDashboardConsumer.as_asgi()),
    re_path(r'ws/asterisk/$', consumers_enhanced.AsteriskEventConsumer.as_asgi()),
]
```

### Paso 6: Iniciar Servicios

```bash
# Levantar Docker Compose
docker-compose up -d

# Verificar logs de AMI
docker-compose logs -f backend | grep AMI
```

### Paso 7: Usar Softphone

1. Login como agente
2. El softphone se registrará automáticamente
3. Marcar número o recibir llamadas

### Paso 8: Ver Dashboard

1. Login como supervisor/admin
2. Ir a `/dashboard`
3. Ver estadísticas en tiempo real

---

## 🧪 Testing

### Probar Conexión AMI

```python
# Django shell
python manage.py shell

from apps.telephony.asterisk_ami import asterisk_ami
import asyncio

# Conectar
asyncio.run(asterisk_ami.connect())

# Verificar
print(asterisk_ami.connected)  # True

# Originar llamada de prueba
asyncio.run(asterisk_ami.originate_call(
    channel="PJSIP/1000",
    extension="100",  # IVR o extensión de prueba
))
```

### Probar WebSocket

```javascript
// Console del navegador
const ws = new WebSocket('wss://localhost/ws/dashboard/');

ws.onopen = () => console.log('Connected!');
ws.onmessage = (e) => console.log('Message:', JSON.parse(e.data));
```

---

## 📝 Próximos Pasos

1. ✅ **Testing Completo**: Probar todas las funcionalidades
2. ⏳ **Marcadores Automáticos**: Implementar predictivo, progresivo
3. ⏳ **Reportería Avanzada**: Gráficos con Chart.js
4. ⏳ **Grabaciones**: Player de audio, búsqueda
5. ⏳ **IVR Builder**: Constructor visual drag-and-drop

---

## 🐛 Troubleshooting

### AMI no conecta

```bash
# Verificar que Asterisk esté corriendo
docker-compose exec asterisk asterisk -rx "manager show connected"

# Verificar credenciales en manager.conf
docker-compose exec asterisk cat /etc/asterisk/manager.conf
```

### WebRTC no registra

```bash
# Verificar transport WebSocket
docker-compose exec asterisk asterisk -rx "pjsip show transports"

# Ver logs de PJSIP
docker-compose exec asterisk asterisk -rx "pjsip set logger on"
```

### WebSocket no conecta

```bash
# Verificar routing
docker-compose logs backend | grep WebSocket

# Verificar Channels layer (Redis)
docker-compose exec backend python manage.py shell
>>> from channels.layers import get_channel_layer
>>> channel_layer = get_channel_layer()
>>> channel_layer
```

---

## 📚 Referencias

- [Panoramisk Docs](https://panoramisk.readthedocs.io/)
- [JsSIP Documentation](https://jssip.net/documentation/)
- [Django Channels](https://channels.readthedocs.io/)
- [Asterisk AMI](https://wiki.asterisk.org/wiki/display/AST/Asterisk+Manager+Interface+%28AMI%29)
