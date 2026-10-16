# Contribuir

Esta guía reúne las reglas prácticas para aportar código a VozipOmni: cómo trabajar con ramas, cómo escribir los mensajes de commit según el estilo que ya usa el repositorio, qué convenciones seguir en backend, frontend y telefonía, las reglas de seguridad que no se negocian, la lista de revisión de un pull request y cómo se despliega un cambio una vez fusionado. La organización del código está en [Estructura del código](./estructura-del-codigo.md) y la arquitectura en [Arquitectura](../general/arquitectura.md).

## Ramas

El repositorio tiene una sola rama de larga duración, `main` (`origin/main`). Es la que despliega `deploy.sh` por defecto (`BRANCH=main`) y la que dispara la CI en cada `push`.

- Trabaje en una rama corta a partir de `main`, por ejemplo `feature/reportes-exportacion` o `fix/kamailio-ack`.
- Abra un pull request hacia `main`; la CI corre en cada `pull_request` (ver [Pruebas y CI](./pruebas-y-ci.md)).
- Mantenga la rama al día con `git pull --rebase origin main` antes de pedir revisión.
- No haga `push --force` sobre `main`. Los servidores actualizan con `git pull` y un historial reescrito los deja en conflicto.

## Mensajes de commit

Los últimos commits (`git log --oneline -20`) siguen este estilo:

```text
Reportes: KPIs de contact center por pestanas y nuevas exportaciones
Notificaciones: contenedor global y sin falso 'Llamada fallida'
Grabaciones: vincular, reproducir y descargar
Audio del agente, ACK en Kamailio y locuciones en espanol
Kamailio: Record-Route y advertise para ACK/BYE; deploy.sh se relanza tras git pull
Seguridad: sin claves por defecto, TURN temporal y antifraude telefonico
WhatsApp: webhook en /api/webhooks/whatsapp/<APP_ID>/
```

Convención a seguir:

- Resumen en español, en una línea de hasta unos 72 caracteres.
- Prefijo con el área afectada seguido de dos puntos (`Kamailio:`, `Grabaciones:`, `WhatsApp:`, `Seguridad:`, `Reportes:`), y luego qué cambia, separando varios cambios con comas o punto y coma.
- Sin punto final. Los commits recientes evitan tildes y eñes en el resumen (`pestanas`, `espanol`); mantenerlo evita problemas de codificación en terminales de servidor.
- Si hace falta contexto (causa del error, cómo se probó), agréguelo en el cuerpo, separado por una línea en blanco.

Commits anteriores usan el formato `fix: ...` / `feat: ...`; para trabajo nuevo prefiera el estilo por área.

## Convenciones

Generales:

- Textos de interfaz, comentarios nuevos, mensajes de log y documentación en español.
- Cambios pequeños y enfocados: un PR por tema.
- No agregue archivos de respaldo (`*.backup`, `*.bak`) ni scripts de un solo uso a la raíz.

Backend:

- Declare `permission_classes` en cada vista con las clases de `backend/core/permissions.py`; no confíe en el menú del frontend.
- Registre rutas en el `urls.py` de la app o en `backend/apps/api/urls.py` con un `basename` único.
- Tareas de Celery con `name=` explícito; si son periódicas, use exactamente ese nombre en la programación.
- Lea configuración con `config(...)` de `python-decouple` en `settings.py` y úsela desde `django.conf.settings`.
- Migraciones con nombre descriptivo y reversibles. Detalle en [Backend](./backend.md).

Frontend:

- `useHttp` para páginas nuevas, `useToast` para mensajes, componentes de Nuxt UI v2.
- Rutas nuevas con su entrada y `roles` en `frontend/utils/navigation.ts`.
- No agregue otro `<UNotifications />`. Detalle en [Frontend](./frontend.md).

Telefonía:

- No edite a mano los archivos de `/var/lib/asterisk/dynamic`; cambie el generador en `backend/apps/telephony/`.
- Mantenga `${UNIQUEID}` en los nombres de `MixMonitor` y la regla de 6 dígitos de `kamailio.cfg` salvo que cambie ambos lados a la vez.
- Documente en el PR cómo probó la llamada. Detalle en [Telefonía interna](./telefonia-interna.md) y [Marcador](./marcador.md).

## Reglas de seguridad

Estas reglas vienen del trabajo ya hecho en el repositorio (por ejemplo el commit "Seguridad: sin claves por defecto, TURN temporal y antifraude telefonico") y de lo que valida la CI.

Sin contraseñas por defecto:

- En `settings.py` los secretos usan `default=''` (`ASTERISK_AMI_PASSWORD`, `TURN_SECRET`, `EMAIL_HOST_PASSWORD`) y el arranque falla con `DEBUG=False` si `SECRET_KEY` o `FIELD_ENCRYPTION_KEY` no están definidos. Mantenga ese patrón.
- En `docker-compose.prod.yml` las variables sensibles usan `${VAR:?mensaje}` para exigirlas. No agregue `${VAR:-valor}` con una clave.
- `deploy.sh` genera secretos aleatorios con `openssl rand`. Cualquier usuario o clave que cree un script debe seguir ese modelo.
- El `docker-compose.yml` de desarrollo todavía tiene claves por defecto; no copie ese patrón a otros archivos.

Dependencias con versión fija:

- Python: `==` en `backend/requirements/*.txt` y `dialer_engine/requirements.txt`, como ya están.
- Node: `frontend/package.json` usa rangos `^`. Para dependencias nuevas use versión exacta y, si el equipo lo acuerda, versione un `package-lock.json`.
- Imágenes Docker con etiqueta concreta (`postgres:14-alpine`, `prom/prometheus:v2.50.1`). Evite `latest` en servicios nuevos (`coturn/coturn:latest` es una excepción existente).
- Prefiera paquetes conocidos y mantenidos, y revise el nombre para descartar variantes sospechosas.

Sin secretos en el repositorio:

- `.env`, `.env.local` y `.env.production` están en `.gitignore`; `docker/nginx/ssl/` solo versiona su `README.md` y `.gitignore`. No fuerce su inclusión.
- Nunca suba `credentials.txt`, certificados, claves privadas, volcados de base de datos ni grabaciones.
- `docker/asterisk/entrypoint.sh` escribe la clave AMI en `docker/asterisk/configs/manager.conf` y la IP externa en `pjsip.conf` dentro del directorio montado. Revise `git diff docker/asterisk/configs/` antes de hacer commit desde una máquina donde corrió Asterisk.
- La CI ejecuta gitleaks sobre todo el historial: si se filtra un secreto, eliminarlo en un commit nuevo no basta. Rote la clave y avise al equipo.
- En issues, PR y documentación use marcadores como `<clave>` en lugar de valores reales, y no pegue la salida de `diagnostico-extension.sh`, que imprime secretos SIP.

Código:

- Endpoints sin autenticación (`AllowAny`) solo con justificación y throttle; indíquelo en el PR.
- Nada de `CORS_ALLOW_ALL=True` ni `DEBUG=True` en configuraciones de servidor.
- Valide y limite las entradas que terminan en el dialplan (números, prefijos, nombres de troncal): se escriben en archivos que ejecuta Asterisk.

## Lista de revisión del pull request

Antes de pedir revisión:

- [ ] La rama parte de `main` actualizado y el PR tiene un solo tema.
- [ ] Título al estilo del repositorio (`Area: que cambia`).
- [ ] La descripción explica qué cambia, por qué y cómo se probó.
- [ ] `ruff check .` y `bandit -r apps core config -q` sin hallazgos nuevos en `backend/`.
- [ ] `python manage.py check` y, si hay modelos, `makemigrations --check` sin cambios pendientes.
- [ ] Pruebas nuevas o actualizadas para la lógica tocada; `pytest` pasa en local.
- [ ] `npm run lint`, `npx vue-tsc --noEmit` y `npm run build` pasan en `frontend/`.
- [ ] Vistas nuevas con `permission_classes`; rutas nuevas en `utils/navigation.ts` con sus roles.
- [ ] Sin secretos, `.env`, certificados ni cambios locales de `manager.conf` o `pjsip.conf`.
- [ ] Dependencias nuevas con versión fija.
- [ ] Si toca telefonía: probadas llamada saliente, entrante a cola y, si aplica, marcador; indicado cómo.
- [ ] Si agrega variables de entorno: documentadas en `env.template` y en [Variables de entorno](../instalacion/variables-entorno.md), sin valores reales.
- [ ] Documentación de `docs/` actualizada si cambia un comportamiento visible o un endpoint ([API](../api/README.md)).
- [ ] La CI está en verde, o las fallas conocidas están explicadas en el PR (ver [Pruebas y CI](./pruebas-y-ci.md)).

## Después de fusionar: despliegue

El despliegue no es automático: la CI no publica nada. Una vez fusionado en `main`, en cada servidor:

```bash
sudo bash /opt/vozipomni/deploy.sh --update <IP_DEL_SERVIDOR>
# detrás de NAT
sudo bash /opt/vozipomni/deploy.sh --update <IP_PRIVADA> --nat <IP_PUBLICA>
```

El modo `--update` hace `git pull` de la rama, se relanza si `deploy.sh` cambió, reconstruye las imágenes, recrea los contenedores cuya imagen cambió y aplica las migraciones al arrancar el backend. No borra la base, las grabaciones ni el `.env`. No use `deploy.sh` sin `--update` para actualizar y nunca `--clean` en un servidor con datos. El detalle, la verificación posterior y cómo volver a una versión anterior están en [Actualización](../instalacion/actualizacion.md).

Después del despliegue:

- Revise `docker compose -f docker-compose.prod.yml ps` y los logs de `backend`, `celery_worker` y `asterisk`.
- Si hubo cambios de telefonía, haga una llamada de prueba y revise [Depuración VoIP](../operacion/depuracion-voip.md) si algo falla.
- Si hubo migraciones, tenga a mano el respaldo previo ([Respaldos](../operacion/respaldos.md)).
- Anote en `docs/CHANGELOG.md` los cambios visibles para operación.

## Ver también

- [Arquitectura](../general/arquitectura.md)
- [Glosario](../general/glosario.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [API](../api/README.md)
- [Entorno local](./entorno-local.md)
- [Estructura del código](./estructura-del-codigo.md)
- [Backend](./backend.md)
- [Frontend](./frontend.md)
- [Telefonía interna](./telefonia-interna.md)
- [Marcador](./marcador.md)
- [Pruebas y CI](./pruebas-y-ci.md)
