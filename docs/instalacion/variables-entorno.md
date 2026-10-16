# Variables de entorno

Este documento lista las variables de entorno de VozipOmni en producción, agrupadas por área, con su obligatoriedad, valor por defecto y uso. Se construyó a partir de `docker-compose.prod.yml` (ancla `x-django-env` y cada servicio), `.env.example`, `env.template`, el `.env` que genera `deploy.sh` y `backend/config/settings.py`. No incluye valores reales: nunca copie secretos a documentación, tickets o repositorios.

## Cómo se cargan

| Archivo | Lo crea | Quién lo lee |
|---|---|---|
| `/opt/vozipomni/.env` | `deploy.sh` (permisos 600) | Docker Compose, para sustituir `${VAR}` en `docker-compose.prod.yml`. |
| `/opt/vozipomni/backend/.env` | `deploy.sh` | Se copia dentro de la imagen del backend (`COPY . .`, no hay `.dockerignore`) y python-decouple lo usa como respaldo. |

Reglas prácticas:

- Compose no pasa el `.env` completo a los contenedores: cada servicio recibe solo las variables listadas en su bloque `environment`. Una variable que solo está en el `.env` raíz y no aparece en `docker-compose.prod.yml` no llega a Django.
- python-decouple da prioridad al entorno del proceso sobre `backend/.env`. Las variables que define compose ganan; las demás se pueden poner en `backend/.env`, pero requieren reconstruir la imagen (`build backend daphne celery_worker celery_beat`).
- `backend/.env` contiene secretos y queda dentro de la imagen del backend. No publique esa imagen en un registro.
- Después de cambiar el `.env` raíz, aplique con `docker compose -f docker-compose.prod.yml up -d` (recrea los contenedores afectados).
- "Obligatoria" significa que compose falla con el mensaje `... requerido en .env` si falta (sintaxis `${VAR:?}`) o que Django no arranca sin ella.

## Servidor y red

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `VOZIPOMNI_IPV4` | Sí | – | IP del servidor (la de la NIC). La usan Django (se agrega a `ALLOWED_HOSTS`, `FRONTEND_URL` por defecto), Asterisk, Kamailio, RTPEngine, coturn, nginx, marcador y `websocket_server`. |
| `NAT_IPV4` | No | vacío | IP pública cuando el servidor está detrás de NAT. Asterisk la usa en `trunk-nat-transport`, RTPEngine en `interface=<privada>!<pública>` y coturn en `--external-ip`. |
| `TZ` | No | `America/Bogota` | Zona horaria de los contenedores. |
| `KAMAILIO_TRUST_LAN` | No | `0` | `1` hace que Kamailio confíe en orígenes RFC1918 (teléfonos SIP en la LAN). Ver [Red y puertos](red-y-puertos.md). |
| `KAMAILIO_HOST` | No | `127.0.0.1` | Host de Kamailio en el `contact=` de `pjsip_agents.conf`. En código el valor por defecto es `kamailio`, pero compose lo fija en `127.0.0.1`. |

## Django (backend, daphne, celery)

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `SECRET_KEY` | Sí | – | Clave de Django. Con `DEBUG=False` Django se niega a arrancar si tiene el valor inseguro por defecto. `websocket_server` también la usa. |
| `DEBUG` | – | `False` | Compose la fija en `"False"`. |
| `ALLOWED_HOSTS` | Sí | – (en código `localhost,127.0.0.1`) | Hosts aceptados, separados por coma. `deploy.sh` escribe `<IP>,localhost,127.0.0.1`. Agregue su dominio si usa uno. |
| `CORS_ORIGINS` | Sí | – | Orígenes permitidos, separados por coma (`https://<IP>`, `https://<dominio>`). |
| `CORS_ALLOW_ALL` | No | `False` | Permite cualquier origen. No está en compose; no la active en producción. |
| `FIELD_ENCRYPTION_KEY` | Sí | – | Clave Fernet para campos cifrados (contraseñas SIP). Sin ella Django no arranca con `DEBUG=False`. No la cambie en una instalación con datos: lo cifrado con la clave anterior deja de poder leerse. |
| `SECURE_SSL_REDIRECT` | No | `True` | Redirección a HTTPS de Django. Solo en `backend/.env`. |
| `SECURE_HSTS_SECONDS` | No | `31536000` | Duración de HSTS en Django. Solo en `backend/.env`. |
| `LOG_LEVEL` | No | `INFO` | Nivel de log. Solo en `backend/.env`. |
| `LOG_FILE` | No | `/app/logs/vozipomni.log` | Archivo de log (montado en `./logs`). Solo en `backend/.env`. |
| `ENVIRONMENT` | No | `development` | Campo `environment` de los logs JSON. Solo en `backend/.env`. |
| `FRONTEND_URL` | No | `https://<VOZIPOMNI_IPV4>` | URL pública usada en enlaces de correo (recuperar contraseña). |
| `PUBLIC_BASE_URL` | No | vacío | URL HTTPS pública con certificado válido para webhooks de Meta. También se usa para el host TURN si `TURN_HOST` está vacío. |
| `GUNICORN_WORKERS` | No | `4` | Workers de Gunicorn del servicio `backend`. |
| `GUNICORN_TIMEOUT` | No | `120` | Timeout de Gunicorn en segundos. |

## Base de datos

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `POSTGRES_DB` | No | `vozipomni` | Nombre de la base. |
| `POSTGRES_USER` | No | `vozipomni_user` | Usuario de la base. |
| `POSTGRES_PASSWORD` | Sí | – | Contraseña. Si cambia en `.env` y no en PostgreSQL, `deploy.sh` intenta sincronizarla; también existe `fix-db-password.sh`. |
| `DATABASE_URL` | – | la arma compose | `postgresql://<usuario>:<clave>@postgres:5432/<base>`. Tiene prioridad en `settings.py`. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | – | los arma compose | Respaldo si no hay `DATABASE_URL`. En código: `vozipomni`, `vozipomni_user`, `POSTGRES_PASSWORD`, `postgres`, `5432`. |

## Redis y Celery

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `REDIS_PASSWORD` | Sí | – | Contraseña de Redis (`--requirepass`). La usan Django, Kamailio, RTPEngine, marcador y `websocket_server`. |
| `REDIS_URL` | – | la arma compose | `redis://:<clave>@redis:6379/0`. Broker de Celery y capa de Channels. En código: `redis://localhost:6379/0`. |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | – | las arma compose | `settings.py` fija `CELERY_BROKER_URL = REDIS_URL` y `CELERY_RESULT_BACKEND = 'django-db'`. |
| `CELERY_CONCURRENCY` | No | `4` | Procesos del worker. |
| `CELERY_LOG_LEVEL` | No | `info` | Nivel de log de worker y beat. |

## Asterisk y AMI

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `ASTERISK_AMI_USER` | Sí | `admin` (lo escribe `deploy.sh`) | Usuario AMI. `manager.conf` define la sección `[admin]`; no cambie este valor. |
| `ASTERISK_AMI_PASSWORD` | Sí | – | Contraseña AMI. El entrypoint de Asterisk la escribe en `manager.conf`. Sin ella el listener de eventos no arranca. |
| `ASTERISK_HOST` | – | `<VOZIPOMNI_IPV4>` (compose) | Host del AMI para backend y marcador. En código: `asterisk`. |
| `ASTERISK_AMI_PORT` | – | `5038` | Puerto AMI. |
| `ASTERISK_CONFIG_DIR` | – | `/var/lib/asterisk/dynamic` | Directorio de configuración generada. |
| `ASTERISK_PUBLIC_IP` | – | `<VOZIPOMNI_IPV4>` (compose) | Definida en compose; no se encontró lectura en el código Python. |
| `ASTERISK_AMI_PERMIT_NETWORK` | No | `172.20.0.0/255.255.255.0` | Red extra que el AMI acepta (además de `127.0.0.1`). |
| `ASTERISK_AMI_PERMIT_IP` | No | `<VOZIPOMNI_IPV4>` | IP extra que el AMI acepta. |
| `PJSIP_CONFIG_PATH` | No | `<ASTERISK_CONFIG_DIR>/pjsip_wizard.conf` | Archivo de troncales. Solo en `backend/.env`. |

## Softphone WebRTC y TURN

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `TURN_SECRET` | Sí (coturn) | – | Secreto compartido entre backend y coturn para firmar credenciales temporales. `deploy.sh` lo genera. Si el backend no lo tiene, solo entrega STUN. |
| `TURN_HOST` | No | vacío | Host TURN anunciado. Vacío: host de `PUBLIC_BASE_URL` o, si no hay, el host con el que se abrió la web. |
| `TURN_PORT` | No | `3478` | Puerto de coturn y de las URL `turn:`. |
| `TURN_REALM` | No | `vozipomni` | Realm de coturn. |
| `TURN_CREDENTIAL_TTL` | No | `43200` (12 h) | Vigencia de la credencial TURN. Solo en `backend/.env`. |
| `SIP_WS_TICKET_TTL` | No | `86400` (24 h) | Vigencia del ticket para abrir `/sip/ws`. Solo en `backend/.env`. |

## Correo

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `EMAIL_HOST` | No | vacío | Servidor SMTP. Vacío: los correos se escriben en el log (backend de consola). |
| `EMAIL_PORT` | No | `587` | Puerto SMTP. |
| `EMAIL_USE_TLS` | No | `True` | STARTTLS. |
| `EMAIL_USE_SSL` | No | `False` | SSL implícito. Solo en `backend/.env`. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | No | vacío | Credenciales SMTP. |
| `DEFAULT_FROM_EMAIL` | No | vacío en compose | Remitente. Compose la pasa vacía si no está en `.env`, lo que anula el valor por defecto del código; defínala si configura SMTP. |

`EMAIL_BACKEND`, presente en `env.template`, no se lee: `settings.py` elige SMTP o consola según `EMAIL_HOST`.

## Omnicanal

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `WHATSAPP_GRAPH_API_VERSION` | No | `v21.0` | Versión de la Graph API de Meta. |
| `PUBLIC_BASE_URL` | Para Meta | vacío | Ver sección Django. |

## Frontend

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `NUXT_PUBLIC_API_BASE` | No | `/api` | Base de la API (relativa, detrás de nginx). |
| `NUXT_PUBLIC_WS_BASE` | No | `/ws` | Base de los WebSockets de Channels. |
| `NUXT_PUBLIC_APP_NAME` | No | `VozipOmni` | Nombre mostrado. |

## Monitoreo

| Variable | Obligatoria | Por defecto | Descripción |
|---|---|---|---|
| `GRAFANA_PASSWORD` | Sí | – | Contraseña del administrador de Grafana. `deploy.sh` la genera. |
| `GRAFANA_USER` | No | `admin` | Usuario administrador de Grafana. |

## Otros servicios

| Variable | Servicio | Por defecto | Descripción |
|---|---|---|---|
| `WS_PORT` | `websocket_server` | `8765` | Puerto del servidor WebSocket auxiliar. |
| `BACKEND_URL` | `dialer_engine` | `http://backend:8000` | API usada para consultar la lista DNC. No se define en compose. |
| `DIALER_API_TOKEN` | `dialer_engine` | vacío | Token Bearer para esa consulta. No se define en compose. |
| `WHISPER_MODEL`, `WHISPER_LANGUAGE` | `celery_worker` | `base`, autodetección | Transcripción local, si instala Whisper manualmente. |

`NGINX_HTTP_PORT` y `NGINX_HTTPS_PORT` aparecen en el `.env` generado, pero nginx escucha 80 y 443 fijos en su configuración y compose no los usa.

## Grabaciones y marcador

Estas variables se leen con python-decouple en `backend/config/recording_config.py` y `backend/config/dialer_config.py`. No están en compose, así que para cambiarlas hay que usar `backend/.env` y reconstruir.

| Variable | Por defecto | Descripción |
|---|---|---|
| `RECORDING_ARCHIVE_DAYS` | `90` | Días antes de archivar grabaciones (tarea de retención). |
| `RECORDING_DELETE_DAYS` | `180` | Días antes de eliminar el archivo. |
| `RECORDING_DELETE_LOW_PRIORITY` | `30` | Días para grabaciones de baja prioridad. |
| `RECORDING_BASE_DIR`, `RECORDING_FORMAT`, `RECORDING_QUALITY`, `RECORDING_COMPRESSION` | `/app/recordings`, `wav`, `64`, `True` | Almacenamiento. |
| `TRANSCRIPTION_SERVICE`, `TRANSCRIPTION_LANGUAGE`, `TRANSCRIPTION_AUTO`, `TRANSCRIPTION_ONLY_SUCCESS` | `none`, `es-CO`, `False`, `True` | Transcripción. |
| `DIALER_PREDICTIVE_RATIO`, `DIALER_ABANDON_TARGET`, `DIALER_MAX_RATIO`, `DIALER_MIN_RATIO`, `DIALER_RATIO_STEP`, `DIALER_PROCESSING_INTERVAL` | `1.5`, `0.03`, `3.0`, `1.0`, `0.1`, `10` | Parámetros del predictivo en `dialer_config.py`. |

No se encontró código que importe `dialer_config.py`, por lo que no hay evidencia de que las variables `DIALER_*` tengan efecto. En instalaciones antiguas `deploy.sh` agrega al `.env` raíz un bloque "Mejoras v3.0.0" con algunas de estas variables y con `DIALER_MAX_CONCURRENT_CALLS`, `RECORDING_FILE_FORMAT` y `RECORDING_AUDIO_QUALITY`, que ningún código lee.

## Ver también

- [Instalación](instalacion.md)
- [Actualización](actualizacion.md)
- [Red y puertos](red-y-puertos.md)
- [SSL y HTTPS](ssl-https.md)
- [Servicios Docker](../operacion/servicios-docker.md)
- [Omnicanal](../administracion/omnicanal.md)
- [Entorno local](../desarrollo/entorno-local.md)
