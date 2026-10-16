# Actualización

Esta guía describe cómo actualizar una instalación existente de VozipOmni con `deploy.sh --update`, qué hace el script paso a paso, cómo verificar el resultado y cómo volver a una versión anterior si algo sale mal. El modo update no borra la base de datos, las grabaciones ni el `.env`.

## Comando

```bash
# Desde el servidor, con la instalación en /opt/vozipomni
sudo bash /opt/vozipomni/deploy.sh --update <IP_DEL_SERVIDOR>

# Servidor detrás de NAT
sudo bash /opt/vozipomni/deploy.sh --update <IP_PRIVADA> --nat <IP_PUBLICA>

# Equivalente remoto
curl -sL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh | sudo bash -s -- --update <IP_DEL_SERVIDOR>
```

La IP es obligatoria también en modo update. Use la misma IP (y la misma IP de NAT) de la instalación, salvo que el servidor haya cambiado de dirección. Las variables `INSTALL_DIR` y `BRANCH` funcionan igual que en la [Instalación](instalacion.md).

## Antes de actualizar

1. Planee una ventana de mantenimiento. Al recrear los contenedores de Asterisk, Kamailio o RTPEngine se cortan las llamadas en curso, y los agentes se vuelven a registrar (Kamailio guarda los registros en memoria).
2. Anote el commit actual para poder volver atrás:

   ```bash
   sudo git -C /opt/vozipomni log --oneline -1
   ```

3. Haga un respaldo de la base de datos y de la configuración (ver [Respaldos](../operacion/respaldos.md)). Como mínimo:

   ```bash
   cd /opt/vozipomni
   sudo docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U vozipomni_user vozipomni > /root/vozipomni_$(date +%F).sql
   sudo cp .env credentials.txt /root/
   ```

4. Revise si modificó archivos versionados (por ejemplo en `docker/asterisk/configs/`) con `sudo git -C /opt/vozipomni status`. El update los guarda con `git stash` y los reemplaza por la versión del repositorio.
5. Verifique espacio en disco: se reconstruyen varias imágenes.

## Qué hace `--update`, paso a paso

1. Verifica root y el formato de la IP.
2. Comprueba que exista `INSTALL_DIR/.git`; si no, aborta y pide una instalación normal.
3. Detecta `docker compose` o `docker-compose`.
4. Migra secretos sin tocar los existentes:
   - Genera `GRAFANA_PASSWORD` y `TURN_SECRET` si faltan o están vacíos.
   - Exige `SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `ASTERISK_AMI_PASSWORD` y `FIELD_ENCRYPTION_KEY`. Si alguno falta, aborta: esos no se generan durante un update.
5. Abre los puertos TURN (3478 tcp/udp y 49152-49200/udp) si ufw está activo o firewalld está corriendo.
6. Guarda `VOZIPOMNI_IPV4` en `.env` y, solo si pasó `--nat`, también `NAT_IPV4`.
7. Actualiza el código: `git fetch origin`, `git checkout <BRANCH>`, `git stash` y `git pull origin <BRANCH>`.
8. Si el `git pull` trajo una versión distinta de `deploy.sh`, se relanza a sí mismo con los mismos argumentos (variable `VOZIPOMNI_DEPLOY_REEXEC=1` para no repetirlo) y así ejecuta los pasos nuevos.
9. Reconstruye las imágenes `backend`, `daphne`, `frontend`, `celery_worker`, `celery_beat`, `websocket_server`, `dialer_engine`, `nginx`, `asterisk`, `kamailio` y `rtpengine`.
10. `up -d --remove-orphans`: recrea solo los contenedores cuya imagen o configuración cambió.
11. Sincroniza la contraseña de PostgreSQL con la del `.env` si no coinciden (sin perder datos cuando es posible).
12. Espera hasta 180 s a que el backend esté `healthy`. Si no lo logra, el script termina con error.
13. `python manage.py migrate --noinput` (el backend también lo ejecuta al arrancar).
14. Verifica el usuario `admin`: corrige su rol si hace falta. Si el usuario no existe, lo crea con contraseña `admin`; en ese caso cámbiela de inmediato.
15. Espera a Asterisk (60 s) y ejecuta `dialplan reload` (3 intentos) o, si falla, `core reload`. No aborta si Asterisk no responde.
16. Corrige troncales con `dtmf_mode=rfc2833` a `rfc4733`.
17. Regenera y recarga la configuración PJSIP (`PJSIPConfigGenerator().save_and_reload()`). Un fallo aquí solo genera una advertencia.
18. `collectstatic --noinput --clear` y muestra el estado de los servicios.

### Lo que el update no hace

- No borra volúmenes ni datos.
- No regenera certificados SSL ni cambia la configuración de nginx.
- No cambia `ALLOWED_HOSTS` ni `CORS_ORIGINS` (la IP del servidor se agrega sola a `ALLOWED_HOSTS` en `settings.py`).
- No reconfigura firewall ni fail2ban más allá de los puertos TURN.
- No reconstruye las imágenes de registro (`postgres`, `redis`, `coturn`, `prometheus`, `grafana`).

## Verificación

```bash
cd /opt/vozipomni
sudo git log --oneline -1
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs --tail=100 backend celery_worker
curl -s -H 'X-Forwarded-Proto: https' http://localhost:8000/api/health/
sudo docker compose -f docker-compose.prod.yml exec asterisk asterisk -rx 'pjsip show registrations'
sudo docker compose -f docker-compose.prod.yml exec asterisk asterisk -rx 'pjsip show endpoints'
```

Después, desde la web:

1. Inicie sesión como administrador y revise el dashboard.
2. Inicie sesión como agente y confirme que el softphone se registra (puede tardar unos segundos tras el reinicio de Kamailio).
3. Haga una llamada saliente y una entrante de prueba.
4. Confirme que la llamada aparece en Operación > Llamadas.

Si las troncales no aparecen registradas, recargue PJSIP manualmente:

```bash
sudo docker compose -f docker-compose.prod.yml exec backend python manage.py shell -c \
  "from apps.telephony.pjsip_config_generator import PJSIPConfigGenerator; PJSIPConfigGenerator().save_and_reload()"
```

## Volver a una versión anterior

`deploy.sh --update` siempre vuelve a la punta de la rama (`git checkout <BRANCH>` + `git pull`), así que no sirve para bajar de versión. El retroceso se hace a mano:

1. Si la versión nueva aplicó migraciones que la anterior no conoce, revierta primero esas migraciones (mientras el código nuevo sigue desplegado, porque es el que tiene los archivos de migración) o prepárese para restaurar el respaldo de la base de datos:

   ```bash
   sudo docker compose -f docker-compose.prod.yml exec backend python manage.py showmigrations <app>
   sudo docker compose -f docker-compose.prod.yml exec backend python manage.py migrate <app> <migracion_anterior>
   ```

2. Cambie el código al commit anotado:

   ```bash
   cd /opt/vozipomni
   sudo git checkout <COMMIT_ANTERIOR>
   ```

3. Reconstruya y reinicie:

   ```bash
   sudo docker compose -f docker-compose.prod.yml build backend daphne frontend celery_worker celery_beat websocket_server dialer_engine nginx asterisk kamailio rtpengine
   sudo docker compose -f docker-compose.prod.yml up -d --remove-orphans
   sudo docker compose -f docker-compose.prod.yml exec asterisk asterisk -rx 'core reload'
   ```

4. Si no pudo revertir las migraciones, restaure la base de datos desde el respaldo (ver [Respaldos](../operacion/respaldos.md)).
5. El repositorio queda en "detached HEAD". Cuando la corrección esté publicada, vuelva con `sudo git checkout main` y ejecute de nuevo `deploy.sh --update`.

## Precauciones

- `git stash` guarda los cambios locales a archivos versionados; no se pierden, pero dejan de aplicarse. Recupérelos con `git stash list` y `git stash pop` revisando conflictos. Es mejor no editar archivos del repositorio en producción. Es normal que el stash contenga el cambio a `docker/nginx/default.prod.conf` que hace la instalación al activar HTTPS; no hace falta recuperarlo, porque la imagen de nginx activa HTTPS sola cuando encuentra los certificados.
- Los archivos no versionados (`.env`, `backend/.env`, `credentials.txt`, certificados en `docker/nginx/ssl/`) no se tocan.
- No ejecute `deploy.sh` sin `--update` para actualizar: ese modo vuelve a escribir `ALLOWED_HOSTS` y `CORS_ORIGINS` con la IP y, si se usa `--clean`, borra todo.
- Si cambió la IP del servidor, además de pasar la nueva IP revise `ALLOWED_HOSTS`, `CORS_ORIGINS`, `FRONTEND_URL` y los certificados.
- Tras varias actualizaciones, libere espacio con `docker image prune` (elimina imágenes sin usar; revise antes qué borra).

## Ver también

- [Instalación](instalacion.md)
- [Variables de entorno](variables-entorno.md)
- [Respaldos](../operacion/respaldos.md)
- [Mantenimiento](../operacion/mantenimiento.md)
- [Servicios Docker](../operacion/servicios-docker.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
