# Troncales SIP

Este manual explica cómo conectar VozipCX con un proveedor de telefonía, una PBX o un enlace corporativo mediante troncales SIP: qué tipo de troncal elegir, qué hace cada campo del formulario, cómo se genera la configuración PJSIP Wizard en Asterisk y cómo revisar el estado de registro. Se basa en `frontend/pages/trunks/index.vue`, el modelo `SIPTrunk` de `backend/apps/telephony/models.py`, `backend/apps/telephony/pjsip_config_generator.py`, el `SIPTrunkSerializer` de `backend/apps/telephony/serializers.py`, el `SIPTrunkViewSet` de `backend/apps/telephony/views.py` y los transportes de `docker/asterisk/configs/pjsip.conf`.

Una **troncal** es la conexión SIP por la que salen las llamadas hacia la red pública (rutas salientes) y por la que entran las llamadas a los DIDs (rutas entrantes). Cada troncal activa se escribe como un bloque `type=wizard` en `/var/lib/asterisk/dynamic/pjsip_wizard.conf`. El **nombre** de la troncal es el nombre del endpoint PJSIP, el mismo que aparece en `Dial(PJSIP/<número>@<troncal>)`.

## Acceso

- **Telefonía → Troncales SIP** (ruta `/trunks`). Visible solo para Administrador.
- En la API, `/api/trunks/` y `/api/telephony/trunks/` (mismo viewset, permiso `IsAdminUserCustom`).

La pantalla muestra cuatro tarjetas (**Total Troncales**, **Registrados**, **No Registrados**, **Error / Inactivos**) y la tabla **Lista de Troncales** con las columnas **Nombre / Descripción**, **Host**, **Tipo**, **Estado Asterisk**, **Activo**, **Canales** y **Acciones**.

## Tipos de troncal

El tipo define el transporte (puerto local de Asterisk) y precarga las casillas de autenticación y NAT.

| Tipo (valor) | Transporte y puerto | Uso | Valores que precarga |
|---|---|---|---|
| Proveedor con NAT (`nat_provider`) | `trunk-nat-transport`, UDP 5162 | Recomendado cuando el servidor tiene IP privada (192.168.x.x, 10.x.x.x) y sale a Internet por NAT. | Enviar autenticación y registro; RTP simétrico, forzar RPORT y reescribir Contact; contexto `from-pstn`. |
| Proveedor sin NAT (`no_nat_provider`) | `trunk-transport`, UDP 5161 | Solo si el servidor tiene IP pública directa (VPS). | Los mismos valores que el tipo con NAT. |
| PBX en LAN (`pbx_lan`) | `trunk-transport`, UDP 5161 | PBX IP en la misma red. Autenticación en ambos sentidos, sin registro. | Enviar y aceptar autenticación; sin opciones de NAT; contexto `from-pbx`. |
| Troncal Corporativa (`corporate`) | `trunk-transport`, UDP 5161 | Enlace dedicado o backbone privado, por IP. | Sin autenticación ni registro; sin NAT. El generador fuerza `sends_auth=no` y `sends_registrations=no`. |
| Personalizado (`custom`) | El que indiques | Configuración PJSIP Wizard escrita a mano. | Ninguno. |

El transporte `trunk-nat-transport` recibe `external_media_address` y `external_signaling_address` con la IP pública real al arrancar el contenedor (`entrypoint.sh`). Si el servidor tiene IP privada y eliges un tipo sin NAT, la llamada conecta pero el audio no llega: Asterisk anuncia la IP privada en el SDP.

## Crear una troncal

1. Entra a **Telefonía → Troncales SIP** y haz clic en **Nuevo Troncal**.
2. Pestaña **Información Básica**: elige **Tipo de Troncal** y completa **Nombre del Troncal**, **Host / IP / FQDN**, **Puerto**, **Máx. Canales Simultáneos** e **Idioma**.
3. Pestaña **Autenticación**: marca **Enviar autenticación** y **Enviar registro (REGISTER)** según el proveedor, y completa usuario, contraseña y URIs de registro.
4. Pestaña **Media y Códecs**: revisa códecs, **Modo DTMF**, opciones de NAT y **Caller ID**.
5. Pestaña **Avanzado**: revisa **Contexto**, **Session Timers**, **Monitoreo (Qualify)** e **Identidad SIP**.
6. Haz clic en **Crear Troncal**. El pie del formulario recuerda el puerto que se usará (UDP 5162 o 5161).

Al guardar, crear, editar o eliminar, el backend regenera `pjsip_wizard.conf` y recarga por AMI `res_pjsip_config_wizard.so`, `res_pjsip.so`, ejecuta `pjsip reload` y recarga `res_pjsip_outbound_registration.so` para que el registro se intente de inmediato. Si la recarga falla, la troncal queda guardada y el error solo se registra en el log.

Validaciones del backend (`SIPTrunkSerializer.validate`):

- Tipo Personalizado sin configuración: "Debes proporcionar configuración PJSIP personalizada...".
- **Enviar registro** sin **Server URI**: "Debes proporcionar Server URI para habilitar registro".
- **Enviar autenticación** sin usuario, o **Aceptar autenticación** sin usuario entrante: se rechaza con el mensaje del campo.

## Campos

| Campo (pantalla) | Campo del modelo | Efecto en PJSIP |
|---|---|---|
| Nombre del Troncal | `name` | Nombre de la sección `[nombre]` y del endpoint. Único. Usa letras, números, `_` o `-`, sin espacios. |
| Host / IP / FQDN, Puerto | `host`, `port` | `remote_hosts=host` (o `host:puerto` si el puerto no es 5060). |
| Protocolo | `protocol` | Se guarda, pero el generador no lo usa: los transportes de troncal son UDP. |
| Máx. Canales Simultáneos | `max_channels` | No va a PJSIP. Lo aplica la política antifraude en cada ruta saliente y en el marcador. |
| Idioma | `language` | `endpoint/language` (locuciones). |
| Usuario / Contraseña (saliente) | `outbound_auth_username`, `outbound_auth_password` | `outbound_auth/username` y `outbound_auth/password`. |
| From User / From Domain | `from_user`, `from_domain` | `endpoint/from_user` y `endpoint/from_domain`. Si From User queda vacío, se usa el usuario saliente. |
| Server URI / Client URI | `registration_server_uri`, `registration_client_uri` | `registration/server_uri` y `registration/client_uri`. |
| Intervalo de reintento / Expiración registro | `registration_retry_interval`, `registration_expiration` | `registration/retry_interval` (60) y `registration/expiration` (3600). |
| Aceptar autenticación / Usuario y Contraseña Entrante | `accepts_auth`, `inbound_auth_*` | `inbound_auth/*`: el proveedor o la PBX debe autenticarse ante VozipCX. |
| Aceptar registros | `accepts_registrations` | `accepts_registrations=yes`: el extremo remoto se registra en VozipCX. |
| Códecs | `codec` | `endpoint/allow=!all,<lista>`, en orden de preferencia. El formulario propone `ulaw,alaw`. |
| Modo DTMF | `dtmf_mode` | `endpoint/dtmf_mode`. `rfc2833` se convierte a `rfc4733`, porque PJSIP no acepta el nombre antiguo. |
| RTP Simétrico, Forzar RPORT, Reescribir Contact | `rtp_symmetric`, `force_rport`, `rewrite_contact` | Opciones de NAT del endpoint. En PBX en LAN y Corporativa se escriben siempre en `no`. |
| Media Directa | `direct_media` | `endpoint/direct_media`. Déjalo en `no` para que Asterisk grabe y procese el audio. |
| Caller ID (número) / Nombre Caller ID | `caller_id`, `caller_id_name` | `endpoint/callerid="Nombre" <número>`. Además activa `trust_id_outbound`, `send_pai` y `send_rpid`. |
| Contexto / Contexto Personalizado | `context`, `custom_context` | `endpoint/context`: dónde entran al dialplan las llamadas que llegan por la troncal. |
| Session Timers, Min SE, Session Expires | `timers`, `timers_min_se`, `timers_sess_expires` | `endpoint/timers*` (90 y 1800 s por defecto). |
| Habilitar Qualify, Frecuencia, Timeout | `qualify_*` | `aor/qualify_frequency` (y `qualify_timeout` en el tipo con NAT). Envía OPTIONS para medir disponibilidad. |
| Trust ID Inbound/Outbound, Enviar PAI, Enviar RPID | `trust_id_*`, `send_pai`, `send_rpid` | Identidad SIP del endpoint. |
| Configuración PJSIP Wizard Personalizada | `pjsip_config_custom` | Solo tipo Personalizado. Se copia tal cual al archivo. |

El modelo tiene además `local_net`, `external_media_address` y `external_signaling_address`, pero el formulario no los muestra y el generador no los usa: las direcciones externas se toman del transporte.

### Contextos de entrada

- `from-pstn`: llamadas del proveedor. Busca el DID en las rutas entrantes; si no hay ruta, envía la llamada al IVR 9000 de `extensions.conf`.
- `from-pbx`: llamadas desde una PBX en LAN. Permite marcar extensiones `_1XXX` directamente; el resto va al IVR 9000.
- `from-trunk`: redirige a `from-pstn`.

## Estado y acciones

La columna **Estado Asterisk** se consulta por AMI al cargar la página y cada 30 segundos (botón de flechas para forzarlo).

| Estado | Significado |
|---|---|
| Registrado | El registro saliente está `Registered`. |
| No Registrado / Conectando... / Rechazado | Registro `Unregistered`, `Attempting` o `Rejected`/`Failed`. |
| Disponible / Inalcanzable / Sin Contacto | Troncal sin registro: el endpoint tiene contacto disponible, contacto que no responde al qualify o ningún contacto. |
| EP sin Registro | Existe el endpoint pero no el registro. |
| No Encontrado / No Configurado | Asterisk no tiene el endpoint. El sistema intenta regenerar la configuración (como máximo cada 120 s) y muestra el botón **Regenerar configuración PJSIP**. |
| Desconectado | No hay conexión AMI con Asterisk. |

Acciones de cada fila:

- **Editar** (lápiz). Las contraseñas aparecen vacías: déjalas así para conservarlas.
- **Probar conexión** (señal). Consulta el registro o, si la troncal no se registra, si el endpoint tiene contactos.
- **Ver configuración PJSIP** (código). Muestra el bloque que se escribirá para esa troncal, contraseñas incluidas; no compartas capturas de esta ventana.
- **Eliminar** (papelera). Pide confirmación y regenera el archivo. Las rutas salientes de esa troncal se borran con ella (`on_delete=CASCADE`).

La API expone también `POST /api/telephony/trunks/{id}/force_register/` y `POST /api/telephony/trunks/force_register_all/`, que no tienen botón en la pantalla revisada.

Según el código revisado, el interruptor **Activo** llama a `/trunks/{id}/toggle_status/`, acción que no existe en el backend. Para desactivar una troncal usa `PATCH /api/trunks/{id}/` con `{"is_active": false}`. El administrador de Django no es una buena alternativa aquí: su formulario de troncal declara `username` y `password`, que son propiedades y no campos del modelo. Las troncales inactivas no se escriben en `pjsip_wizard.conf`.

## Ejemplo: proveedor con registro

Proveedor `sip.proveedor.example`, usuario `<USUARIO_SIP>`, servidor detrás de NAT:

- Tipo: Proveedor con NAT. Nombre: `proveedor_principal`. Host: `sip.proveedor.example`. Puerto: 5060. Canales: 30.
- Autenticación: Enviar autenticación y Enviar registro. Usuario `<USUARIO_SIP>`, Contraseña `<CLAVE_SIP>`.
- Server URI `sip:sip.proveedor.example`. Client URI `sip:<USUARIO_SIP>@sip.proveedor.example`.
- Códecs `ulaw,alaw`, DTMF RFC4733, Caller ID `6012345678`.

Configuración generada (extracto):

```ini
[proveedor_principal]
type=wizard
transport=trunk-nat-transport
accepts_registrations=no
accepts_auth=no
sends_registrations=yes
sends_auth=yes
endpoint/rtp_symmetric=yes
endpoint/force_rport=yes
endpoint/rewrite_contact=yes
endpoint/direct_media=no
aor/qualify_frequency=60
endpoint/allow=!all,ulaw,alaw
endpoint/dtmf_mode=rfc4733
endpoint/context=from-pstn
remote_hosts=sip.proveedor.example
outbound_auth/username=<USUARIO_SIP>
outbound_auth/password=<CLAVE_SIP>
endpoint/from_user=<USUARIO_SIP>
endpoint/callerid="6012345678" <6012345678>
endpoint/trust_id_outbound=yes
endpoint/send_pai=yes
endpoint/send_rpid=yes
registration/server_uri=sip:sip.proveedor.example
registration/client_uri=sip:<USUARIO_SIP>@sip.proveedor.example
registration/retry_interval=60
registration/expiration=3600
```

Después crea al menos una ruta saliente que use esta troncal (ver [Rutas y dialplan](./rutas-y-dialplan.md)); sin ruta, las llamadas externas se rechazan.

## Buenas prácticas

- Elige **Proveedor con NAT** si el servidor no tiene IP pública propia en su interfaz. Es el caso más común en la nube y en oficinas.
- Abre en el firewall los puertos 5161/5162 UDP y el rango RTP de Asterisk (10000-10300/udp) solo hacia las IP del proveedor (ver [Red y puertos](../instalacion/red-y-puertos.md)).
- Pon en **Máx. Canales Simultáneos** el número de canales contratados y activa "Canales máximos por troncal" en la política antifraude.
- Usa nombres de troncal estables: cambiar el nombre cambia el endpoint y rompe el dialplan hasta que se regenere.
- Prefiere RFC4733 para DTMF salvo que el proveedor indique otra cosa.
- En tipo Personalizado usa solo sintaxis PJSIP Wizard. El formulario detecta directivas de chan_sip (`type=peer`, `insecure=`, `canreinvite=`...) y ofrece **Aplicar conversión PJSIP**.

## Problemas frecuentes

- **Estado "Rechazado".** Usuario, contraseña o Client URI incorrectos, o el proveedor exige un From User distinto. Revisa con [Depuración VoIP](../operacion/depuracion-voip.md).
- **"No Encontrado" después de guardar.** El wizard no creó el endpoint. Revisa **Ver configuración PJSIP**, usa **Regenerar configuración PJSIP** y busca errores del wizard en el log de Asterisk.
- **La llamada conecta sin audio o con audio en un solo sentido.** Tipo sin NAT en un servidor con IP privada, o IP pública mal detectada en `trunk-nat-transport`.
- **"Sin ruta para ..." y locución de servicio no disponible.** La troncal está bien, pero ninguna ruta saliente coincide con el número marcado.
- **"Todos los circuitos ocupados".** Se alcanzó **Máx. Canales Simultáneos** de la troncal o el límite total de la política antifraude.
- **Las llamadas entrantes van siempre al IVR 9000.** El DID que envía el proveedor no coincide con ninguna ruta entrante.

## Ver también

- [Rutas y dialplan](./rutas-y-dialplan.md)
- [Seguridad y antifraude](./seguridad-antifraude.md)
- [Glosario](../general/glosario.md)
- [Arquitectura](../general/arquitectura.md)
- [Red y puertos](../instalacion/red-y-puertos.md)
- [Depuración VoIP](../operacion/depuracion-voip.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
- [API: telefonía](../api/telefonia.md)
