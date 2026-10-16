# Certificados SSL y HTTPS

Este documento explica cómo VozipOmni maneja los certificados TLS: dónde están, cómo los genera la instalación, cómo decide nginx entre HTTP y HTTPS y cómo reemplazar el certificado autofirmado por uno de confianza (Let's Encrypt o de una CA propia). Se basa en `deploy.sh`, `docker/nginx/Dockerfile.prod`, `docker/nginx/nginx-ssl-switch.sh`, `docker/nginx/default.https.conf` y `generate-dev-ssl.sh`.

## Por qué HTTPS es obligatorio

- El navegador solo entrega el micrófono (`getUserMedia`) en un contexto seguro: HTTPS o `localhost`. Sin HTTPS el softphone WebRTC no funciona.
- El softphone abre `wss://<servidor>/sip/ws`, que nginx termina con el mismo certificado.
- Con `DEBUG=False`, Django redirige a HTTPS (`SECURE_SSL_REDIRECT`) y marca las cookies de sesión y CSRF como seguras.
- Los webhooks de Meta (WhatsApp, Messenger, Instagram) exigen HTTPS con certificado válido en un dominio público (`PUBLIC_BASE_URL`).

## Dónde están los certificados

| En el servidor | En el contenedor nginx |
|---|---|
| `/opt/vozipomni/docker/nginx/ssl/vozipomni.crt` | `/etc/nginx/ssl/vozipomni.crt` |
| `/opt/vozipomni/docker/nginx/ssl/vozipomni.key` | `/etc/nginx/ssl/vozipomni.key` |

El directorio se monta sin `:ro` en `docker-compose.prod.yml`. Los nombres de archivo son fijos: `default.https.conf` los referencia así. La configuración HTTPS tiene un solo bloque `server` con `server_name _`, por lo que responde a cualquier nombre o IP.

Asterisk (`/etc/asterisk/keys/`) y Kamailio generan sus propios certificados autofirmados para uso interno. No hace falta reemplazarlos: nginx se conecta a Asterisk por `127.0.0.1:8089` con `proxy_ssl_verify off` y a Kamailio por WebSocket plano en `127.0.0.1:8080`.

## Cómo se crean en la instalación

`deploy.sh` (función `setup_https_automatic`) hace lo siguiente en cada instalación que no sea `--update`:

1. Si ya existen `vozipomni.crt` y `vozipomni.key` y el certificado vence en más de 24 horas (`openssl x509 -checkend 86400`), los reutiliza. Un certificado real válido no se sobrescribe.
2. Si no, genera uno autofirmado RSA 2048 por 365 días con `CN=<IP>` y `subjectAltName=IP:<IP>,DNS:localhost,DNS:vozipomni.local`.
3. Copia `default.https.conf` sobre `default.prod.conf` y cambia `http://<IP>` por `https://<IP>` (y `ws://` por `wss://`) en `.env`.

El mensaje final del script sugiere `quick-https.sh`, pero ese archivo no existe en el repositorio. No hace falta: HTTPS ya queda activo con el paso anterior.

## Cómo elige nginx entre HTTP y HTTPS

La imagen (`Dockerfile.prod`) copia `default.prod.conf` (solo HTTP) como configuración activa y `default.https.conf` como `default.https.conf.bak`. Al arrancar, el script `/docker-entrypoint.d/01-ssl-switch.sh`:

- Si encuentra los dos archivos, copia la configuración HTTPS y la activa: el puerto 80 redirige a HTTPS (salvo `/health`) y el 443 sirve la aplicación.
- Si faltan y `ALLOW_SELF_SIGNED_SSL` no vale `true`, termina con error ("faltan certificados confiables"). Compose no define esa variable, así que en producción nginx necesita los certificados para arrancar.
- Con `ALLOW_SELF_SIGNED_SSL=true` genera uno autofirmado por 3650 días. Úselo solo para pruebas.

El script siempre imprime "El certificado es autofirmado", aunque haya instalado uno real; es solo un mensaje.

Parámetros TLS de `default.https.conf`: TLS 1.2 y 1.3, cifrados ECDHE con AES-GCM, sesión de 1 día, sin session tickets, HSTS de 2 años con `includeSubDomains` y `preload`, y cabeceras CSP, `X-Frame-Options`, `X-Content-Type-Options` y `Referrer-Policy`.

## Certificado autofirmado con IP

Es la configuración por defecto. Cada navegador debe aceptar la advertencia una vez al entrar a `https://<IP_DEL_SERVIDOR>`; esa excepción cubre también el WebSocket SIP porque usa el mismo origen.

Para regenerarlo (por ejemplo si cambió la IP), desde el directorio de instalación:

```bash
cd /opt/vozipomni
sudo bash generate-dev-ssl.sh <IP_DEL_SERVIDOR>
sudo docker compose -f docker-compose.prod.yml restart nginx
```

`generate-dev-ssl.sh` crea un certificado por 3650 días con SAN `IP:<IP>`, `DNS:localhost` y `DNS:vozipomni`. Si no recibe la IP la toma de `VOZIPOMNI_IPV4` en `.env`. Para desarrollo en Windows existe `generate-dev-ssl.ps1`.

## Instalar un certificado de Let's Encrypt

Requisitos: un dominio con registro DNS `A` apuntando a la IP pública del servidor y el puerto 80 accesible desde Internet.

El bloque HTTP de `default.https.conf` redirige todo a HTTPS y no tiene una ruta para `/.well-known/acme-challenge/`, así que el método webroot no funciona sin editar la configuración. El camino más simple es el modo `standalone` de certbot, deteniendo nginx unos segundos.

1. Instale certbot (`sudo apt install certbot` en Debian/Ubuntu; en RHEL y derivados está en EPEL).
2. Emita el certificado:

   ```bash
   cd /opt/vozipomni
   sudo docker compose -f docker-compose.prod.yml stop nginx
   sudo certbot certonly --standalone -d <DOMINIO>
   ```

3. Copie los archivos con los nombres que espera nginx y vuelva a arrancarlo:

   ```bash
   sudo cp /etc/letsencrypt/live/<DOMINIO>/fullchain.pem docker/nginx/ssl/vozipomni.crt
   sudo cp /etc/letsencrypt/live/<DOMINIO>/privkey.pem  docker/nginx/ssl/vozipomni.key
   sudo chmod 644 docker/nginx/ssl/vozipomni.crt
   sudo chmod 600 docker/nginx/ssl/vozipomni.key
   sudo docker compose -f docker-compose.prod.yml start nginx
   ```

4. Actualice `/opt/vozipomni/.env` para el dominio y recree los servicios:

   ```text
   ALLOWED_HOSTS=<DOMINIO>,<IP_DEL_SERVIDOR>,localhost,127.0.0.1
   CORS_ORIGINS=https://<DOMINIO>,https://<IP_DEL_SERVIDOR>
   FRONTEND_URL=https://<DOMINIO>
   PUBLIC_BASE_URL=https://<DOMINIO>
   TURN_HOST=<DOMINIO>
   ```

   ```bash
   sudo docker compose -f docker-compose.prod.yml up -d
   ```

   `TURN_HOST` es opcional; si queda vacío se usa el host de `PUBLIC_BASE_URL`.

5. Renovación automática. Cree estos ganchos para que certbot detenga nginx, renueve y copie los archivos:

   ```bash
   # /etc/letsencrypt/renewal-hooks/pre/vozipomni.sh
   #!/bin/sh
   docker compose -f /opt/vozipomni/docker-compose.prod.yml stop nginx

   # /etc/letsencrypt/renewal-hooks/deploy/vozipomni.sh
   #!/bin/sh
   cp "$RENEWED_LINEAGE/fullchain.pem" /opt/vozipomni/docker/nginx/ssl/vozipomni.crt
   cp "$RENEWED_LINEAGE/privkey.pem"   /opt/vozipomni/docker/nginx/ssl/vozipomni.key
   chmod 600 /opt/vozipomni/docker/nginx/ssl/vozipomni.key

   # /etc/letsencrypt/renewal-hooks/post/vozipomni.sh
   #!/bin/sh
   docker compose -f /opt/vozipomni/docker-compose.prod.yml start nginx
   ```

   Dé permisos de ejecución (`chmod +x`) y pruebe con `sudo certbot renew --dry-run`. Compruebe que exista el temporizador de renovación con `systemctl list-timers | grep certbot`.

## Instalar un certificado propio

1. Arme `vozipomni.crt` con el certificado del servidor primero y luego los intermedios de la CA:

   ```bash
   cat servidor.crt intermedio.crt > vozipomni.crt
   ```

2. Use la clave privada sin contraseña como `vozipomni.key` (nginx no puede pedir la frase al arrancar).
3. Compruebe que certificado y clave corresponden (claves RSA):

   ```bash
   openssl x509 -noout -modulus -in vozipomni.crt | openssl md5
   openssl rsa  -noout -modulus -in vozipomni.key | openssl md5
   ```

4. Cópielos a `/opt/vozipomni/docker/nginx/ssl/`, ajuste permisos (644 y 600) y reinicie nginx con `sudo docker compose -f docker-compose.prod.yml restart nginx`.
5. Actualice `.env` como en el paso 4 de Let's Encrypt.

## Verificación

```bash
cd /opt/vozipomni
sudo docker compose -f docker-compose.prod.yml logs nginx | grep SSL-switch
openssl s_client -connect <DOMINIO>:443 -servername <DOMINIO> </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
curl -I https://<DOMINIO>/
```

En el navegador, abra la consola del agente y confirme que el softphone queda registrado.

## Precauciones

- HSTS: la configuración envía `Strict-Transport-Security` con `includeSubDomains` y `preload`. Al usar un dominio, instale el certificado válido antes de que los usuarios entren: con HSTS activo el navegador no permite saltar la advertencia de un certificado inválido, y la política afecta también a los subdominios. Los navegadores no aplican HSTS a direcciones IP.
- Si vuelve a ejecutar `deploy.sh` sin `--update`, reescribe `ALLOWED_HOSTS` y `CORS_ORIGINS` solo con la IP. Agregue de nuevo el dominio después.
- Los certificados de `docker/nginx/ssl/` no están en Git, pero tampoco en `.gitignore`: no los agregue a un commit.
- Incluya `docker/nginx/ssl/` en sus respaldos.

## Ver también

- [Instalación](instalacion.md)
- [Red y puertos](red-y-puertos.md)
- [Variables de entorno](variables-entorno.md)
- [Requisitos](requisitos.md)
- [Omnicanal](../administracion/omnicanal.md)
- [Respaldos](../operacion/respaldos.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
