# Instalación en producción

Esta guía explica cómo instalar VozipOmni en un servidor Linux con `deploy.sh`, qué hace el script en cada fase, dónde quedan las credenciales y qué revisar después para dejar el contact center listo para la primera llamada. Antes de empezar revise los [Requisitos](requisitos.md).

## Resumen rápido

```bash
# Servidor con IP pública directa
curl -sL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh | sudo bash -s -- <IP_DEL_SERVIDOR>

# Servidor detrás de NAT (IP privada en la NIC, IP pública en el router)
curl -sL https://raw.githubusercontent.com/henry0295/vozipomni/main/deploy.sh | sudo bash -s -- <IP_PRIVADA> --nat <IP_PUBLICA>

# Con el repositorio ya clonado
sudo bash deploy.sh <IP_DEL_SERVIDOR>
```

Al terminar, abra `https://<IP_DEL_SERVIDOR>` y entre con el usuario `admin` y la contraseña que aparece en pantalla y en `/opt/vozipomni/credentials.txt`.

## Argumentos y variables

| Argumento | Descripción |
|---|---|
| `<IP>` | IP del servidor (la de la NIC). Obligatoria. Cualquier argumento con forma de IPv4 se toma como `VOZIPOMNI_IPV4`. |
| `--nat <IP>` / `-n <IP>` | IP pública real cuando el servidor está detrás de NAT. Se guarda como `NAT_IPV4`. |
| `--clean` / `-c` | Reinstalación desde cero: borra contenedores, volúmenes, imágenes, `.env`, `credentials.txt` y el directorio de instalación. Irreversible. |
| `--update` / `-u` | Actualiza una instalación existente sin borrar datos. Ver [Actualización](actualizacion.md). |
| `--help` / `-h` | Muestra la ayuda. |

| Variable de entorno | Por defecto | Uso |
|---|---|---|
| `VOZIPOMNI_IPV4` | – | Alternativa al argumento `<IP>` (`sudo VOZIPOMNI_IPV4=<IP> bash deploy.sh`). |
| `NAT_IPV4` | vacío | Alternativa a `--nat`. |
| `TZ` | `America/Bogota` | Zona horaria de los contenedores. |
| `INSTALL_DIR` | `/opt/vozipomni` | Directorio de instalación. |
| `BRANCH` | `main` | Rama de Git a desplegar. |

## Qué hace `deploy.sh`, en orden

1. Verifica prerrequisitos: que se ejecute como root y que la IP tenga formato válido.
2. Prepara el sistema: escribe `/etc/sysctl.d/10-vozipomni.conf` y `/etc/security/limits.d/99-vozipomni.conf`, pone SELinux en `permissive` si aplica y crea `/etc/docker/daemon.json` si no existe.
3. Instala Docker si falta (según la distribución), lo habilita, lo reinicia y detecta `docker compose` o `docker-compose`.
4. Solo con `--clean`: pide confirmación si la sesión es interactiva y elimina la instalación anterior por completo.
5. Clona el repositorio en `INSTALL_DIR` o, si ya existe, hace `git fetch`, `git stash` de cambios locales y `git pull`.
6. Genera la configuración:
   - Instalación nueva: crea contraseñas aleatorias para PostgreSQL, Redis, AMI, administrador y Grafana, además de `SECRET_KEY`, `FIELD_ENCRYPTION_KEY` y `TURN_SECRET`. Escribe `.env`, `backend/.env` y `credentials.txt` (permisos 600).
   - Con `.env` existente: reutiliza las credenciales, actualiza `VOZIPOMNI_IPV4`, `ALLOWED_HOSTS` y `CORS_ORIGINS` con la IP indicada y agrega `TURN_SECRET` si falta.
7. Configura el firewall (ufw, firewalld o iptables). Ver [Red y puertos](red-y-puertos.md).
8. Instala fail2ban (apt, dnf o yum) con una jaula `asterisk-ami` para el puerto 5038.
9. Configura HTTPS: si no hay certificados válidos en `docker/nginx/ssl/`, genera `vozipomni.crt` y `vozipomni.key` autofirmados por 365 días para la IP, copia `default.https.conf` sobre `default.prod.conf` y cambia `http://<IP>` por `https://<IP>` en `.env`. Ver [SSL y HTTPS](ssl-https.md).
10. Despliega los servicios por fases:
    - `down`, `build` de todas las imágenes y recreación de `docker/postgresql/init.sql` si falta.
    - Arranca PostgreSQL y Redis y espera sus healthchecks (180 s y 60 s).
    - Si reutilizó un `.env`, verifica que la contraseña de PostgreSQL coincida con el volumen y la sincroniza si es posible.
    - Arranca el backend y espera hasta 300 s (migraciones y `collectstatic`).
    - Ajusta permisos del volumen de Asterisk y levanta el resto con `up -d`.
11. Espera hasta 600 s a que `http://localhost:8000/api/health/` responda.
12. Prepara el entorno: crea `/app/logs`, agrega `FIELD_ENCRYPTION_KEY` si faltara y ejecuta `makemigrations`.
13. Post-despliegue: `migrate` y creación del superusuario `admin` con rol `admin` (si ya existe, solo corrige el rol).
14. Aplica ajustes de la versión 3.0.0: reinicia backend y Celery, vuelve a ejecutar `migrate`, cifra contraseñas SIP existentes (`encrypt_sip_passwords`) y comprueba `/api/docs/`.
15. Muestra el resultado: URL, usuario, contraseña y comandos útiles.

Si algo falla, el script muestra la línea del error, el estado de los contenedores y los últimos logs del backend. Puede corregir la causa y volver a ejecutarlo: reutiliza el `.env` existente.

## Credenciales

`/opt/vozipomni/credentials.txt` (permisos 600, solo root) contiene:

- URL web, admin de Django (`/admin`) y API (`/api`).
- Usuario `admin` y su contraseña.
- Usuario y contraseña de PostgreSQL, contraseña de Redis y credenciales del AMI.

El archivo muestra las URL con `http://`; como el paso 9 activa HTTPS, use `https://`. La contraseña de Grafana no está en ese archivo: está en `.env` como `GRAFANA_PASSWORD`. Guarde una copia de `credentials.txt` y `.env` en un lugar seguro y fuera del servidor; `--clean` los borra.

## Primer acceso

1. Abra `https://<IP_DEL_SERVIDOR>` (el puerto 80 redirige a HTTPS).
2. Acepte la advertencia del certificado autofirmado (Avanzado > Continuar). Cada navegador de agente debe hacerlo una vez.
3. Inicie sesión con `admin` y la contraseña de `credentials.txt`.
4. Cambie la contraseña del administrador. Desde la consola:

   ```bash
   cd /opt/vozipomni
   sudo docker compose -f docker-compose.prod.yml exec backend python manage.py changepassword admin
   ```

5. Otras URL: admin de Django en `/admin/` y documentación Swagger en `/api/docs/`.

## Verificación técnica

```bash
cd /opt/vozipomni
sudo docker compose -f docker-compose.prod.yml ps
sudo docker compose -f docker-compose.prod.yml logs --tail=50 backend
curl -s -H 'X-Forwarded-Proto: https' http://localhost:8000/api/health/
sudo docker compose -f docker-compose.prod.yml exec asterisk asterisk -rx 'pjsip show transports'
```

Todos los contenedores deben estar `running` y los que tienen healthcheck en `healthy`. El health del backend debe devolver `"status": "healthy"`. El encabezado `X-Forwarded-Proto` evita la redirección a HTTPS de Django.

## Checklist post-instalación

1. Troncal SIP: Telefonía > Troncales SIP (rol `admin`). Elija el tipo según si el servidor está detrás de NAT (5162) o no (5161). Si el proveedor autentica por IP sin registro, abra 5161/5162 udp solo para su IP (el firewall de `deploy.sh` no los abre). Ver [Troncales SIP](../administracion/troncales-sip.md).
2. Ruta saliente: Telefonía > Rutas Salientes, con patrón y troncal. Los números que marca el agente deben tener más de 6 dígitos; Kamailio trata los más cortos como extensiones internas. Ver [Rutas y dialplan](../administracion/rutas-y-dialplan.md).
3. Ruta entrante: Telefonía > Rutas Entrantes (DIDs) hacia una cola, IVR o extensión.
4. Seguridad: revise Telefonía > Seguridad y antifraude antes de abrir el tráfico saliente. Ver [Seguridad y antifraude](../administracion/seguridad-antifraude.md).
5. Agente: cree un usuario con rol `agent` y su agente en Operación > Agentes. La contraseña SIP se genera sola. Agréguelo a una cola. Ver [Agentes](../administracion/agentes.md) y [Colas](../administracion/colas.md).
6. Prueba del softphone: en otro navegador inicie sesión como el agente, acepte el certificado, permita el micrófono y confirme que el softphone aparece registrado.
7. Llamada saliente de prueba a un celular y llamada entrante al DID.
8. Revise que la llamada aparezca en Operación > Llamadas y su grabación en Calidad > Grabaciones.
9. Configure respaldos. Ver [Respaldos](../operacion/respaldos.md).

## Reinstalar desde cero

```bash
sudo bash deploy.sh --clean <IP_DEL_SERVIDOR>
```

Borra base de datos, grabaciones, configuración y credenciales. Haga un respaldo antes.

## Ver también

- [Requisitos](requisitos.md)
- [Actualización](actualizacion.md)
- [Variables de entorno](variables-entorno.md)
- [Red y puertos](red-y-puertos.md)
- [SSL y HTTPS](ssl-https.md)
- [Servicios Docker](../operacion/servicios-docker.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
- [Usuarios y roles](../administracion/usuarios-y-roles.md)
