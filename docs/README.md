# Documentación de VozipOmni

VozipOmni es una plataforma de contact center omnicanal: telefonía WebRTC para agentes, colas ACD, IVR, marcador predictivo y progresivo, campañas, WhatsApp, correo, chat web y redes sociales, grabaciones, calidad, reportes y antifraude. Esta carpeta reúne toda la documentación, separada por público y tarea. Si es la primera vez que la lee, empiece por la [introducción](./general/introduccion.md).

## Por dónde empezar

| Si usted es... | Lea primero |
|---|---|
| Responsable de instalar el servidor | [Requisitos](./instalacion/requisitos.md) y [Instalación](./instalacion/instalacion.md) |
| Administrador de la plataforma | [Usuarios y roles](./administracion/usuarios-y-roles.md), [Troncales SIP](./administracion/troncales-sip.md) y [Rutas y dialplan](./administracion/rutas-y-dialplan.md) |
| Agente | [Manual del agente](./manuales/manual-agente.md) |
| Supervisor | [Manual del supervisor](./manuales/manual-supervisor.md) |
| Analista | [Manual del analista](./manuales/manual-analista.md) |
| Operador del servidor (soporte) | [Solución de problemas](./operacion/solucion-de-problemas.md) y [Depuración VoIP](./operacion/depuracion-voip.md) |
| Desarrollador | [Entorno local](./desarrollo/entorno-local.md) y [Estructura del código](./desarrollo/estructura-del-codigo.md) |
| Integrador (API) | [API REST](./api/README.md) |

## General

| Documento | Contenido |
|---|---|
| [Introducción](./general/introduccion.md) | Qué es VozipOmni, módulos y roles. |
| [Arquitectura](./general/arquitectura.md) | Componentes, diagramas y flujos de registro y llamadas. |
| [Glosario](./general/glosario.md) | Términos de telefonía y fórmulas de los KPIs. |

## Instalación

| Documento | Contenido |
|---|---|
| [Requisitos](./instalacion/requisitos.md) | Hardware, sistema operativo, red y dominio. |
| [Instalación](./instalacion/instalacion.md) | Instalación con `deploy.sh` y lista de verificación. |
| [Actualización](./instalacion/actualizacion.md) | `deploy.sh --update`, verificación y cómo volver atrás. |
| [Variables de entorno](./instalacion/variables-entorno.md) | Todas las variables del `.env`. |
| [Red y puertos](./instalacion/red-y-puertos.md) | Puertos por servicio, firewall, NAT y TURN. |
| [SSL y HTTPS](./instalacion/ssl-https.md) | Certificados y por qué WebRTC exige HTTPS. |

## Administración

| Documento | Contenido |
|---|---|
| [Usuarios y roles](./administracion/usuarios-y-roles.md) | Usuarios, roles y contraseñas. |
| [Agentes](./administracion/agentes.md) | Agentes, extensiones SIP, grupos y pausas. |
| [Troncales SIP](./administracion/troncales-sip.md) | Conexión con proveedores y PBX. |
| [Rutas y dialplan](./administracion/rutas-y-dialplan.md) | Rutas salientes, entrantes (DIDs) y destinos personalizados. |
| [Colas](./administracion/colas.md) | Colas ACD, miembros y nivel de servicio. |
| [IVR](./administracion/ivr.md) | Menús de voz y audios. |
| [Campañas](./administracion/campanas.md) | Campañas, marcadores, AMD, formularios y calificaciones. |
| [Contactos](./administracion/contactos.md) | Listas, importación y lista negra (DNC). |
| [Seguridad y antifraude](./administracion/seguridad-antifraude.md) | Política de llamadas salientes, alertas y protecciones de red. |
| [Omnicanal](./administracion/omnicanal.md) | WhatsApp, correo, chat web, Messenger e Instagram. |
| [Grabaciones y calidad](./administracion/grabaciones-y-calidad.md) | Grabación, retención y evaluaciones. |
| [Reportes](./administracion/reportes.md) | Pestañas de KPIs, exportación y reportes programados. |

## Manuales por rol

| Documento | Contenido |
|---|---|
| [Manual del agente](./manuales/manual-agente.md) | Consola, llamadas, pausas, calificación y chats. |
| [Manual del supervisor](./manuales/manual-supervisor.md) | Monitor en vivo, escucha y susurro, calidad y auditoría. |
| [Manual del analista](./manuales/manual-analista.md) | Cómo leer cada KPI y recetas de análisis. |

## Operación

| Documento | Contenido |
|---|---|
| [Servicios Docker](./operacion/servicios-docker.md) | Contenedores, volúmenes y comandos. |
| [Monitoreo](./operacion/monitoreo.md) | Salud, Prometheus, Grafana, tareas programadas y CLI de Asterisk. |
| [Respaldos](./operacion/respaldos.md) | Qué respaldar, cómo y cómo restaurar. |
| [Solución de problemas](./operacion/solucion-de-problemas.md) | Síntoma, causa y solución por área. |
| [Depuración VoIP](./operacion/depuracion-voip.md) | sngrep, tcpdump, trazas SIP y RTP. |
| [Mantenimiento](./operacion/mantenimiento.md) | Rutinas, disco, logs, rotación de secretos y certificados. |

## Desarrollo

| Documento | Contenido |
|---|---|
| [Entorno local](./desarrollo/entorno-local.md) | Levantar el proyecto en una máquina de desarrollo. |
| [Estructura del código](./desarrollo/estructura-del-codigo.md) | Qué hay en cada carpeta y qué scripts están vigentes. |
| [Backend](./desarrollo/backend.md) | Django, API, permisos, Celery, Channels y listener AMI. |
| [Frontend](./desarrollo/frontend.md) | Nuxt, navegación por rol, clientes HTTP y softphone. |
| [Telefonía interna](./desarrollo/telefonia-interna.md) | Configuración generada, dialplan, Kamailio, ticket WS y TURN. |
| [Marcador](./desarrollo/marcador.md) | Motor de marcación, AMD y antifraude. |
| [Pruebas y CI](./desarrollo/pruebas-y-ci.md) | Pruebas existentes y flujo de integración continua. |
| [Contribuir](./desarrollo/contribuir.md) | Ramas, commits, reglas de seguridad y despliegue. |
| [Problemas conocidos](./desarrollo/problemas-conocidos.md) | Fallos del código detectados al documentar, pendientes de corregir. |

## API

| Documento | Contenido |
|---|---|
| [API REST](./api/README.md) | Convenciones, autenticación, errores, límites y roles. |
| [Autenticación](./api/autenticacion.md) | Login JWT, refresco, logout y contraseñas. |
| [Usuarios y agentes](./api/usuarios-y-agentes.md) | Usuarios, agentes, grupos y pausas. |
| [Telefonía](./api/telefonia.md) | Llamadas, troncales, rutas, IVR, WebRTC y antifraude. |
| [Colas](./api/colas.md) | Colas, estadísticas y miembros. |
| [Campañas y contactos](./api/campanas-y-contactos.md) | Campañas, calificaciones, contactos, DNC y callbacks. |
| [Grabaciones y calidad](./api/grabaciones-y-calidad.md) | Grabaciones, plantillas y evaluaciones. |
| [Reportes](./api/reportes.md) | KPIs, analítica y exportación. |
| [Mensajería](./api/mensajeria.md) | Bandeja omnicanal y configuración de canales. |
| [Supervisor](./api/supervisor.md) | Supervisión en vivo y auditoría. |
| [WebSockets](./api/websockets.md) | Eventos en tiempo real. |
| [Webhooks](./api/webhooks.md) | Webhook de Meta y webhooks salientes. |

La documentación interactiva de la API (Swagger) está en `https://<IP_DEL_SERVIDOR>/api/docs/`.

## Historial de cambios

[CHANGELOG.md](./CHANGELOG.md).

## Convenciones de esta documentación

- Los valores sensibles se muestran como marcadores: `<IP_DEL_SERVIDOR>`, `<TOKEN>`, `<CONTRASEÑA>`. Nunca pegue claves reales en documentos, tickets o chats.
- Los comandos de servidor asumen la instalación en `/opt/vozipomni` y se ejecutan como root o con `sudo`.
- Cuando un comportamiento del código es una limitación conocida, el documento lo dice con "según el código revisado". La lista consolidada está en [Problemas conocidos](./desarrollo/problemas-conocidos.md).
