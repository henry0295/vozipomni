# Introducción a VozipOmni

VozipOmni es una plataforma de contact center omnicanal que se instala en un servidor Linux propio con Docker. Reúne en una sola interfaz web la telefonía (softphone WebRTC en el navegador, colas, IVR, marcador automático), los canales digitales (WhatsApp, correo, chat web, Messenger e Instagram), la supervisión en vivo, la calidad y los reportes. Este documento explica qué hace el sistema, qué roles existen y qué parte de la documentación le sirve a cada perfil.

## Qué es VozipOmni

- Backend en Django 4.2 con Django REST Framework, Channels (Daphne) para tiempo real y Celery (worker + beat) para tareas en segundo plano.
- Frontend en Nuxt 3 con Nuxt UI.
- Telefonía con Asterisk 21 (PBX y ACD), Kamailio 5.7 (proxy SIP para WebRTC), RTPEngine (puente de medios WebRTC a RTP) y coturn (TURN para agentes detrás de NAT).
- Datos en PostgreSQL 14 y Redis 7. Métricas con Prometheus y Grafana.
- Un motor de marcación propio en Python asyncio (`dialer_engine/`).

Los agentes solo necesitan un navegador moderno con micrófono y acceso HTTPS al servidor: no hay que instalar softphones ni configurar teléfonos IP. El detalle técnico está en [Arquitectura](arquitectura.md).

## Módulos y funcionalidades

| Módulo | Qué incluye |
|---|---|
| Telefonía WebRTC | Softphone JsSIP integrado en la consola del agente. Se conecta por `wss://<servidor>/sip/ws` con un ticket firmado por el backend y usa credenciales TURN temporales. Codecs G.711 (PCMU/PCMA). |
| Troncales y enrutamiento | Troncales SIP generadas con el PJSIP Wizard de Asterisk (puertos 5161/5162), rutas entrantes por DID, rutas salientes por patrón, extensiones, buzones de voz, condiciones de horario y destinos personalizados. La configuración se genera desde la web y se recarga en Asterisk. |
| Colas ACD | Colas de Asterisk (`Queue()`) con música en espera, tiempo máximo de espera y umbral de nivel de servicio por cola. |
| IVR | Menús con opciones por dígito hacia colas, extensiones u otros IVR, con mensajes de opción inválida y de tiempo agotado. |
| Campañas y marcador | Tipos de campaña: entrante, saliente, manual y preview. Tipos de marcador: predictivo, progresivo, preview y manual. El predictivo puede usar AMD (detección de contestador) con acción colgar o dejar un mensaje. El motor también soporta difusión de mensajes (call blasting). |
| Contactos | Listas de contactos, lista negra (DNC), callbacks y formularios de campaña. |
| Omnicanal | Bandeja unificada para WhatsApp Business (Cloud API de Meta, con plantillas y envíos masivos), correo (lectura IMAP), chat web, Facebook Messenger e Instagram. Respuestas rápidas, etiquetas y métricas de chat. El modelo de datos también contempla SMS. |
| Grabaciones y calidad | Grabación de llamadas con MixMonitor, reproducción y descarga desde la web, evaluaciones con plantillas y retención automática. La transcripción con Whisper es opcional y no viene instalada en la imagen. |
| Reportes y KPIs | Dashboard, KPIs de llamadas, agentes, colas, campañas, pausas, abandonos y chats; exportación y reportes programados. Las fórmulas están en el [Glosario](glosario.md). |
| Supervisión en vivo | Monitor de agentes y llamadas en tiempo real, escucha silenciosa, susurro al agente e irrupción en la llamada (ChanSpy), forzar pausa o cierre de sesión y auditoría de gestiones. |
| Seguridad y antifraude | Política de llamadas salientes (internacionales, prefijos bloqueados, lista blanca, longitud máxima, canales por troncal, límite global, llamadas por extensión por hora) aplicada en el dialplan y en el marcador, con alertas. Kamailio rechaza y banea orígenes SIP no autorizados. |
| Integraciones | API REST documentada en `/api/docs/` (Swagger), WebSockets para eventos en vivo y webhooks salientes. |

## Roles

Los roles están definidos en `backend/apps/users/models.py` (`ROLE_CHOICES`) y el menú y los permisos por ruta del frontend en `frontend/utils/navigation.ts`. Un usuario nuevo tiene rol `agent` por defecto; los superusuarios siempre quedan con rol `admin`.

| Rol (código) | Nombre | Página de inicio | Acceso principal |
|---|---|---|---|
| `admin` | Administrador | `/dashboard` | Todo el sistema. Exclusivo: troncales SIP, rutas entrantes y salientes, IVR, extensiones, buzones, condiciones de horario, destinos personalizados, seguridad y antifraude, usuarios y roles, WhatsApp Business, canales (email, chat web, redes) y configuración general. |
| `supervisor` | Supervisor | `/supervisor` | Dashboard, monitor en vivo, auditoría, bandeja omnicanal y envíos masivos, agentes, campañas, formularios, contactos, DNC, callbacks, llamadas, calidad (evaluaciones, plantillas, grabaciones), reportes, colas, grupos y pausas, webhooks. |
| `analyst` | Analista | `/dashboard` | Consulta: dashboard, métricas de chat, campañas, llamadas, evaluaciones, grabaciones y reportes (KPIs, exportación y programados). |
| `agent` | Agente | `/agent/console` | Consola del agente (`frontend/pages/agent/console.vue`): softphone, estado y pausas, tipificación de llamadas, campañas, contactos, panel del marcador y panel de conversaciones. Los agentes siempre se redirigen a su consola. |

El filtrado del menú es del lado del cliente; el backend aplica sus propios permisos (por ejemplo, los endpoints de supervisión exigen rol `admin` o `supervisor`). El detalle de cada rol está en [Usuarios y roles](../administracion/usuarios-y-roles.md).

## A quién va dirigida cada sección

| Sección | Público | Contenido |
|---|---|---|
| [General](../README.md) | Todos | Introducción, arquitectura y glosario. |
| Instalación (`docs/instalacion/`) | Administradores de infraestructura | Requisitos, instalación con `deploy.sh`, actualización, variables de entorno, red y puertos, certificados. |
| Administración (`docs/administracion/`) | Rol `admin` y, en parte, `supervisor` | Usuarios, agentes, troncales, rutas, colas, IVR, campañas, contactos, omnicanal, grabaciones, reportes y antifraude. |
| Manuales (`docs/manuales/`) | Usuarios finales | Guías de uso para agente, supervisor y analista. |
| Operación (`docs/operacion/`) | Soporte y operaciones | Servicios Docker, monitoreo, respaldos, solución de problemas, depuración VoIP y mantenimiento. |
| Desarrollo (`docs/desarrollo/`) | Desarrolladores | Entorno local, estructura del código, backend, frontend, telefonía interna, marcador, pruebas y contribución. |
| API (`docs/api/`) | Integradores | Autenticación, endpoints REST, WebSockets y webhooks. |

## Ver también

- [Índice de la documentación](../README.md)
- [Arquitectura](arquitectura.md)
- [Glosario](glosario.md)
- [Requisitos](../instalacion/requisitos.md)
- [Instalación](../instalacion/instalacion.md)
- [Usuarios y roles](../administracion/usuarios-y-roles.md)
- [Manual del agente](../manuales/manual-agente.md)
- [Manual del supervisor](../manuales/manual-supervisor.md)
- [Manual del analista](../manuales/manual-analista.md)
