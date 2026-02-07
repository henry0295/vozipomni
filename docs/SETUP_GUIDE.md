# Instalación y Configuración de Funcionalidades Core

## 🚀 Guía Rápida de Instalación

### 1. Actualizar Dependencias

#### Backend
```bash
cd backend
pip install -r requirements.txt
```

Verificar que `requirements.txt` incluya:
- `panoramisk==1.4` (Asterisk AMI)
- `channels==4.0.0` (WebSocket)
- `channels-redis==4.1.0` (WebSocket backend)

#### Frontend
```bash
cd frontend
npm install
```

Asegurarse de tener:
```json
{
  "dependencies": {
    "jssip": "^3.10.1",
    "lucide-react": "^0.300.0"
  }
}
```

### 2. Configurar Variables de Entorno

Editar `backend/.env`:

```env
# Django Core
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=192.168.1.100,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://192.168.1.100,https://192.168.1.100

# Base de Datos
DB_NAME=vozipomni
DB_USER=vozipomni
DB_PASSWORD=your-db-password
DB_HOST=postgres
DB_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Asterisk AMI
ASTERISK_HOST=asterisk
ASTERISK_AMI_PORT=5038
ASTERISK_AMI_USER=admin
ASTERISK_AMI_PASSWORD=VoziPOmni2026!
ASTERISK_PUBLIC_IP=192.168.1.100
ASTERISK_AMI_ENABLE=True

# Celery
CELERY_BROKER_URL=redis://:your-redis-password@redis:6379/0
CELERY_RESULT_BACKEND=redis://:your-redis-password@redis:6379/0
```

### 3. Actualizar Settings de Django

Agregar a `backend/config/settings.py`:

```python
from decouple import config

# Asterisk Configuration
ASTERISK_HOST = config('ASTERISK_HOST', default='asterisk')
ASTERISK_AMI_PORT = config('ASTERISK_AMI_PORT', default=5038, cast=int)
ASTERISK_AMI_USER = config('ASTERISK_AMI_USER', default='admin')
ASTERISK_AMI_PASSWORD = config('ASTERISK_AMI_PASSWORD')
ASTERISK_PUBLIC_IP = config('ASTERISK_PUBLIC_IP')
ASTERISK_AMI_ENABLE = config('ASTERISK_AMI_ENABLE', default=True, cast=bool)
```

### 4. Configurar WebSocket Routing

Actualizar `backend/apps/api/routing.py`:

```python
from django.urls import re_path
from apps.api import consumers_enhanced

websocket_urlpatterns = [
    # Dashboard en tiempo real
    re_path(r'ws/dashboard/$', consumers_enhanced.RealtimeDashboardConsumer.as_asgi()),
    
    # Eventos de Asterisk
    re_path(r'ws/asterisk/$', consumers_enhanced.AsteriskEventConsumer.as_asgi()),
]
```

### 5. Iniciar AMI Service

#### Opción A: Auto-start con AppConfig

Crear/editar `backend/apps/telephony/apps.py`:

```python
from django.apps import AppConfig
from django.conf import settings
import asyncio

class TelephonyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.telephony'
    
    def ready(self):
        """Iniciar servicios al arrancar Django"""
        if getattr(settings, 'ASTERISK_AMI_ENABLE', False):
            # Solo en proceso principal (no en reloader)
            import os
            if os.environ.get('RUN_MAIN') != 'true':
                return
                
            from .asterisk_ami import start_ami_service
            
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(start_ami_service())
            except RuntimeError:
                # Si no hay loop, crear uno nuevo
                asyncio.run(start_ami_service())
```

#### Opción B: Management Command

Crear `backend/apps/telephony/management/commands/start_ami.py`:

```python
from django.core.management.base import BaseCommand
from apps.telephony.asterisk_ami import start_ami_service
import asyncio

class Command(BaseCommand):
    help = 'Start Asterisk AMI service'

    def handle(self, *args, **options):
        self.stdout.write('Starting Asterisk AMI service...')
        asyncio.run(start_ami_service())
```

Ejecutar:
```bash
python manage.py start_ami
```

### 6. Actualizar Docker Compose

Asegurarse de que `docker-compose.yml` incluya:

```yaml
services:
  # ... otros servicios ...
  
  backend:
    environment:
      - ASTERISK_HOST=asterisk
      - ASTERISK_AMI_PORT=5038
      - ASTERISK_AMI_USER=admin
      - ASTERISK_AMI_PASSWORD=VoziPOmni2026!
      - ASTERISK_PUBLIC_IP=${VOZIPOMNI_IPV4}
      - ASTERISK_AMI_ENABLE=True
    depends_on:
      - postgres
      - redis
      - asterisk
```

### 7. Verificar Asterisk WebRTC

Verificar `docker/asterisk/configs/pjsip.conf`:

```ini
[transport-wss]
type=transport
protocol=wss
bind=0.0.0.0:8089
external_media_address=${ASTERISK_PUBLIC_IP}
external_signaling_address=${ASTERISK_PUBLIC_IP}

[agent1000]
type=endpoint
context=from-internal
disallow=all
allow=ulaw,alaw,opus
webrtc=yes
auth=agent1000
aors=agent1000
dtls_auto_generate_cert=yes
media_encryption=dtls

[agent1000]
type=auth
auth_type=userpass
password=VoziPOmni2026!
username=agent1000

[agent1000]
type=aor
max_contacts=5
remove_existing=yes
```

### 8. Integrar Softphone en Frontend

Editar `frontend/src/components/AgentConsole/AgentConsole.jsx`:

```jsx
import React, { useState, useEffect } from 'react';
import Softphone from '../WebRTC/Softphone';
import api from '../../services/api';

const AgentConsole = () => {
  const [agent, setAgent] = useState(null);

  useEffect(() => {
    // Obtener datos del agente
    api.get('/agents/me/')
      .then(res => setAgent(res.data))
      .catch(err => console.error(err));
  }, []);

  if (!agent) return <div>Cargando...</div>;

  const wsServer = `wss://${window.location.hostname}:8089/ws`;

  return (
    <div className="agent-console">
      <h1>Consola de Agente</h1>
      
      <div className="grid grid-cols-3 gap-4">
        {/* Softphone */}
        <div className="col-span-1">
          <Softphone
            agentExtension={agent.sip_extension}
            sipPassword={agent.sip_password}
            wsServer={wsServer}
          />
        </div>
        
        {/* Otras secciones de la consola */}
        <div className="col-span-2">
          {/* Información del contacto, script, etc */}
        </div>
      </div>
    </div>
  );
};

export default AgentConsole;
```

### 9. Integrar Dashboard en Frontend

Editar `frontend/src/App.jsx`:

```jsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import RealtimeDashboard from './components/Dashboard/RealtimeDashboard';
import Login from './components/Common/Login';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={
          <RealtimeDashboard wsUrl={`wss://${window.location.host}/ws/dashboard/`} />
        } />
        {/* Otras rutas */}
      </Routes>
    </Router>
  );
}

export default App;
```

### 10. Levantar el Sistema

```bash
# Detener servicios actuales
docker-compose down

# Reconstruir imágenes
docker-compose build

# Iniciar todo
docker-compose up -d

# Ver logs
docker-compose logs -f backend
docker-compose logs -f asterisk

# Verificar AMI connection
docker-compose exec backend python manage.py shell
>>> from apps.telephony.asterisk_ami import asterisk_ami
>>> import asyncio
>>> asyncio.run(asterisk_ami.connect())
>>> print(asterisk_ami.connected)
True
```

## ✅ Verificación Post-Instalación

### 1. Verificar Asterisk AMI

```bash
# Desde el host
docker-compose exec asterisk asterisk -rx "manager show connected"

# Debería mostrar la conexión desde el backend
```

### 2. Verificar WebSocket

```javascript
// En la consola del navegador (Chrome DevTools)
const ws = new WebSocket('wss://192.168.1.100/ws/dashboard/');
ws.onopen = () => console.log('✓ WebSocket connected');
ws.onmessage = (e) => console.log('Message:', JSON.parse(e.data));
```

### 3. Probar Softphone

1. Login como agente
2. Ir a consola de agente
3. Verificar que diga "Conectado" en el softphone
4. Intentar marcar extensión de prueba (ej: `100` para IVR)

### 4. Verificar Dashboard

1. Login como supervisor/admin
2. Ir a `/dashboard`
3. Verificar que muestre datos en tiempo real
4. Hacer una llamada de prueba y ver que se actualice

## 🐛 Troubleshooting

### AMI no conecta

**Problema**: `Failed to start AMI service`

**Solución**:
```bash
# Verificar credenciales
docker-compose exec asterisk cat /etc/asterisk/manager.conf

# Verificar que el servicio esté escuchando
docker-compose exec asterisk netstat -tlnp | grep 5038

# Verificar logs de Asterisk
docker-compose exec asterisk asterisk -rvvv
```

### WebRTC no registra

**Problema**: Softphone dice "Desconectado"

**Solución**:
```bash
# Verificar transport WSS
docker-compose exec asterisk asterisk -rx "pjsip show transports"

# Verificar endpoint
docker-compose exec asterisk asterisk -rx "pjsip show endpoint agent1000"

# Ver logs PJSIP
docker-compose exec asterisk asterisk -rx "pjsip set logger on"

# Verificar firewall (puerto 8089)
sudo ufw allow 8089/tcp
```

### WebSocket no conecta

**Problema**: `WebSocket connection failed`

**Solución**:
```bash
# Verificar Redis (Channels backend)
docker-compose exec redis redis-cli ping

# Verificar routing de Channels
docker-compose exec backend python manage.py shell
>>> from django.core.asgi import get_asgi_application
>>> get_asgi_application()

# Verificar logs de Daphne/ASGI
docker-compose logs -f backend | grep -i websocket
```

### Audio no se escucha (WebRTC)

**Problema**: Llamada conecta pero no hay audio

**Solución**:
```bash
# Verificar puertos RTP (10000-20000 UDP)
sudo ufw allow 10000:20000/udp

# Verificar NAT settings en pjsip.conf
docker-compose exec asterisk asterisk -rx "pjsip show endpoints"

# Verificar external_media_address
grep external_media_address docker/asterisk/configs/pjsip.conf
```

## 📚 Referencias

- [Asterisk AMI Events](https://wiki.asterisk.org/wiki/display/AST/Asterisk+13+AMI+Events)
- [JsSIP Documentation](https://jssip.net/documentation/)
- [Django Channels Tutorial](https://channels.readthedocs.io/en/stable/tutorial/)
- [WebRTC in Asterisk](https://wiki.asterisk.org/wiki/display/AST/WebRTC)
