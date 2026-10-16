# Entorno de desarrollo local

Esta guía explica cómo levantar VozipCX en una máquina de desarrollo: con el `docker-compose.yml` de desarrollo, o ejecutando el backend (Django) y el frontend (Nuxt) directamente sin Docker. También cubre las variables mínimas, los certificados autofirmados para probar el softphone, cómo crear el primer administrador y qué partes de la telefonía no funcionan igual que en producción. La descripción de los servicios y del flujo de señalización está en [Arquitectura](../general/arquitectura.md); aquí solo se trata lo que cambia en local.

## Opciones

| Opción | Cuándo usarla | Qué queda fuera |
|---|---|---|
| `docker compose up -d` con `docker-compose.yml` | Probar el sistema completo (API, WebSockets, Celery, Asterisk, Kamailio, nginx) | El audio WebRTC puede fallar por la red bridge (ver [Limitaciones](#limitaciones)) |
| Backend y frontend sin Docker | Trabajo diario en API, modelos, páginas y componentes | Asterisk, Kamailio, RTPEngine y el marcador; hace falta PostgreSQL y Redis |
| Mixto | Datos y telefonía en Docker, Django o Nuxt en el host con recarga en caliente | Hay que apuntar las variables a los puertos publicados |

## Requisitos

- Git, Docker con Compose v2 (`docker compose`).
- Python 3.11 (es la versión de `backend/Dockerfile` y de `.github/workflows/ci.yml`).
- Node.js 20 (imagen `node:20-alpine` de `frontend/Dockerfile` y CI).
- OpenSSL, para `generate-dev-ssl.ps1` o `generate-dev-ssl.sh`.
- En Windows, Git Bash o WSL ayudan con los scripts `.sh`; `generate-dev-ssl.ps1` es la alternativa nativa.

## Opción 1: docker-compose.yml (desarrollo)

`docker-compose.yml` es el compose de desarrollo. A diferencia de `docker-compose.prod.yml`, usa una red bridge (`vozipomni_network`) con puertos publicados en el host, y monta el código del backend como volumen (`./backend:/app`), así que los cambios en Python se ven al reiniciar el contenedor.

```powershell
# Desde la raíz del repositorio
Copy-Item env.template .env      # luego edite .env
docker compose up -d
docker compose logs -f backend
```

Servicios y puertos publicados (según `docker-compose.yml`):

| Servicio | Puertos en el host | Notas |
|---|---|---|
| `postgres` | 5432 | Enlazado a `${VOZIPOMNI_IPV4:-0.0.0.0}` |
| `redis` | 6379 | Con `--requirepass ${REDIS_PASSWORD}` |
| `backend` | 8000 | `migrate`, `collectstatic` y luego `daphne -b 0.0.0.0 -p 8000 config.asgi:application` (HTTP y WebSocket en el mismo puerto) |
| `celery_worker` | – | `celery -A config worker`; arranca el listener AMI al quedar listo |
| `celery_beat` | – | `--scheduler django_celery_beat.schedulers:DatabaseScheduler` |
| `asterisk` | 5080, 5161, 5162, 5038, 8088, 8089, 10000-10300/udp | En bridge, no en host |
| `kamailio` | 5060/udp, 5061/tcp, 8080/tcp | |
| `rtpengine` | 22222/udp, 23000-23300/udp | |
| `nginx` | `${NGINX_HTTP_PORT:-80}`, `${NGINX_HTTPS_PORT:-443}` | Usa `docker/nginx/default.conf` |
| `frontend` | 3000 | Build de producción de Nuxt |
| `frontend_dev` | 3001 | Solo con `--profile dev`; `npm run dev` con `./frontend` montado |
| `coturn` | host | Solo con `--profile turn` |
| `pg_backup` | – | Solo con `--profile backup` |

Frontend con recarga en caliente dentro de Docker:

```powershell
docker compose --profile dev up -d frontend_dev
# http://localhost:3001
```

Comandos habituales:

```powershell
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py shell
docker compose restart celery_worker celery_beat
docker compose logs -f celery_worker
```

El compose de desarrollo no define `daphne` ni `dialer_engine` como servicios aparte: el backend ya sirve WebSockets con Daphne, y el marcador solo existe en `docker-compose.prod.yml`. Para probar el marcador vea [Marcador](./marcador.md).

### Contraseñas por defecto del compose de desarrollo

`docker-compose.yml` trae valores por defecto para `SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` y `ASTERISK_AMI_PASSWORD` si no están en `.env`. Son valores débiles y conocidos: defínalos siempre en su `.env` local y no reutilice ese archivo fuera de su máquina. El mismo compose pasa `NUXT_PUBLIC_TURN_*` al frontend con una clave por defecto, pero `frontend/nuxt.config.ts` ya no lee esas variables (ver [Frontend](./frontend.md)).

## Opción 2: sin Docker

Necesita PostgreSQL 14 y Redis 7 accesibles. Lo más simple es levantar solo esos dos con el compose:

```powershell
docker compose up -d postgres redis
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # en Linux/macOS: source .venv/bin/activate
pip install -r requirements/dev.txt
```

`requirements/dev.txt` incluye `base.txt` más pytest, pytest-django, pytest-cov, pytest-xdist, factory-boy, Faker, ipython y django-debug-toolbar, todos con versión fija. `requirements.txt` solo apunta a `requirements/base.txt`; la imagen Docker instala `requirements/prod.txt`.

`backend/config/settings.py` lee la configuración con `python-decouple` (`config(...)`), que toma variables de entorno o de un archivo `.env` (lo busca desde `backend/config/` hacia arriba). Variables mínimas para desarrollo:

| Variable | Valor sugerido en local | Por qué |
|---|---|---|
| `DEBUG` | `True` | Con `False` exige `SECRET_KEY` y `FIELD_ENCRYPTION_KEY` reales y activa HTTPS forzado |
| `SECRET_KEY` | una clave generada | Con `DEBUG=False` el valor por defecto aborta el arranque |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | `localhost`, `5432`, y los de su `.env` | `DATABASE_URL` tiene prioridad si existe |
| `REDIS_URL` | `redis://:<clave>@localhost:6379/0` | Broker de Celery y capa de Channels |
| `ASTERISK_HOST`, `ASTERISK_AMI_USER`, `ASTERISK_AMI_PASSWORD` | Solo si hay Asterisk | Sin clave AMI el listener no arranca y las recargas fallan |
| `ASTERISK_CONFIG_DIR` | una carpeta local | Por defecto `/var/lib/asterisk/dynamic`; fuera de Docker la escritura falla y se registra una advertencia |

Con `DEBUG=True` y sin `FIELD_ENCRYPTION_KEY`, `settings.py` genera una clave temporal en cada arranque: los campos cifrados (contraseñas SIP) guardados en una sesión no se podrán leer en la siguiente. Si va a crear troncales o extensiones, fije una clave propia en su `.env`. La lista completa está en [Variables de entorno](../instalacion/variables-entorno.md).

Arranque:

```powershell
python manage.py migrate
python manage.py createsuperuser
# HTTP + WebSocket (Channels) en el mismo puerto:
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

`python manage.py runserver` sirve la API, pero `daphne` no está en `INSTALLED_APPS`, así que `runserver` no atiende los WebSockets de `/ws/`. Use Daphne si trabaja con el tablero, la consola del agente o la mensajería.

Celery, en otras dos terminales:

```powershell
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

En Windows, Celery 5 no tiene soporte oficial para el pool por defecto; agregue `--pool=solo` al worker si las tareas no se ejecutan.

La documentación interactiva de la API queda en `http://localhost:8000/api/docs/` (drf-spectacular) y el esquema en `/api/schema/`.

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev          # http://localhost:3000
```

`frontend/.env.example` apunta a `NUXT_PUBLIC_API_BASE=http://localhost:8000/api` y `NUXT_PUBLIC_WS_BASE=ws://localhost:8000/ws`, que son los únicos valores que lee `runtimeConfig`. Con `DEBUG=True` y sin `CORS_ORIGINS`, el backend ya permite `http://localhost:3000` y `http://127.0.0.1:3000`.

Scripts de `frontend/package.json`: `dev`, `build`, `generate`, `preview`, `lint` y `lint:fix`. No hay script de pruebas; ver [Pruebas y CI](./pruebas-y-ci.md).

## Certificados autofirmados

Los navegadores solo permiten el micrófono (`getUserMedia`) en contextos seguros: HTTPS o `localhost`. En cuanto se entra por la IP de la máquina, hace falta HTTPS. Los scripts de la raíz generan un certificado autofirmado con SAN para esa IP:

```powershell
.\generate-dev-ssl.ps1 -IP 192.168.1.100
```

`.gitignore` excluye `*.ps1`, así que `generate-dev-ssl.ps1` puede no venir en un clon nuevo; en ese caso use `generate-dev-ssl.sh` desde Git Bash o WSL.

```bash
./generate-dev-ssl.sh 192.168.1.100
```

Ambos escriben `docker/nginx/ssl/vozipomni.crt` y `docker/nginx/ssl/vozipomni.key` (RSA 2048, 3650 días, SAN con la IP, `localhost` y `vozipomni`). Si no se pasa la IP, leen `VOZIPOMNI_IPV4` del `.env` y, si no existe, usan `localhost`.

Sin esos dos archivos, `docker/nginx/entrypoint.sh` elimina el bloque `server` HTTPS de `default.conf` y nginx arranca solo en HTTP (lo avisa en el log con "WebRTC NO funcionará"). Por eso, después de generarlos, hay que reiniciar nginx:

```powershell
docker compose restart nginx
# Abrir https://<IP> y aceptar la advertencia del certificado
```

Los archivos de `docker/nginx/ssl/` no deben subirse al repositorio. El manejo de certificados en servidores está en [Certificados SSL y HTTPS](../instalacion/ssl-https.md).

## Crear un administrador

El gestor de usuarios (`VozipOmniUserManager` en `backend/apps/users/models.py`) asigna siempre `role='admin'` a los superusuarios, así que basta con:

```powershell
# Con Docker
docker compose exec backend python manage.py createsuperuser
# Sin Docker
python manage.py createsuperuser
```

Use una contraseña propia; no hay usuarios ni claves por defecto en el código. En servidores, `deploy.sh` crea el usuario `admin` con una contraseña aleatoria y la deja en `credentials.txt`. Los demás usuarios (supervisores, analistas, agentes) se crean desde `/users` o `/api/users/`.

## Limitaciones

- WebRTC exige HTTPS fuera de `localhost`. Además, el softphone (`frontend/components/AgentSoftphone.vue`) arma la URL del WebSocket SIP con el origen de la página más `/sip/ws`. Con `npm run dev` en el puerto 3000 esa ruta no llega a Kamailio: para probar llamadas entre por nginx (`https://<IP>`).
- `docker/nginx/default.conf`, que usa el compose de desarrollo, reenvía `/sip/ws` a Kamailio sin `auth_request`. El ticket firmado solo se valida con `default.https.conf` y `default.prod.conf`. No exponga un entorno de desarrollo a Internet.
- En producción Asterisk, Kamailio, RTPEngine y coturn usan `network_mode: host`. En el compose de desarrollo Asterisk, Kamailio y RTPEngine están en bridge con puertos mapeados: las IP que anuncian en SDP y Via son las del contenedor, y el audio puede no llegar (sin audio o en un solo sentido). Para pruebas reales de voz use un servidor Linux con `docker-compose.prod.yml`.
- En Docker Desktop (Windows y macOS) `network_mode: host` no equivale al de Linux, por lo que `coturn` (`--profile turn`) no queda expuesto como en un servidor.
- `kamailio.cfg` decide por longitud del número (más de 6 dígitos va a Asterisk). Las extensiones de prueba deben tener 6 dígitos o menos. Ver [Telefonía interna](./telefonia-interna.md).
- Sin Asterisk, las señales que regeneran la configuración (`apps/telephony/signals.py`) registran errores de escritura o de AMI, pero no impiden guardar los modelos.

## Problemas frecuentes

| Síntoma | Causa probable | Qué revisar |
|---|---|---|
| `RuntimeError: SECRET_KEY is set to the insecure default value` | `DEBUG` no está en `True` | Variable `DEBUG` en `.env` |
| `RuntimeError: FIELD_ENCRYPTION_KEY is required` | `DEBUG=False` sin clave | Defina `FIELD_ENCRYPTION_KEY` o use `DEBUG=True` |
| El frontend recibe errores CORS | Origen no permitido | `CORS_ORIGINS` o el puerto real del frontend |
| El tablero no actualiza en vivo | Backend levantado con `runserver` | Use `daphne` |
| Tareas de Celery nunca corren en Windows | Pool de procesos | `--pool=solo` |
| Softphone "disconnected" | Entrada por `localhost:3000` o sin HTTPS | Entrar por nginx con certificado |

Para capturar tráfico SIP y RTP vea [Depuración VoIP](../operacion/depuracion-voip.md).

## Ver también

- [Arquitectura](../general/arquitectura.md)
- [Glosario](../general/glosario.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [API](../api/README.md)
- [Estructura del código](./estructura-del-codigo.md)
- [Backend](./backend.md)
- [Frontend](./frontend.md)
- [Telefonía interna](./telefonia-interna.md)
- [Marcador](./marcador.md)
- [Pruebas y CI](./pruebas-y-ci.md)
- [Contribuir](./contribuir.md)
