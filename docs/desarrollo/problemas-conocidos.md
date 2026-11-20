# Problemas conocidos

Esta lista reúne los fallos y limitaciones del código que se detectaron al redactar la documentación, leyendo el código fuente. No se reprodujeron todos en ejecución: cada punto indica qué archivo revisar. Sirve para priorizar correcciones; los documentos de cada módulo describen el comportamiento actual para que nadie se sorprenda en producción. Al corregir un punto, bórrelo de aquí y actualice el documento que lo menciona.

## Seguridad (prioridad alta)

| Problema | Dónde | Efecto |
|---|---|---|
| El servidor WebSocket del puerto 8765 no tiene TLS ni filtro por usuario. | `websocket_server/server.py` | Todo cliente con token válido recibe todos los eventos difundidos. |
| El `docker-compose.yml` de desarrollo tiene contraseñas por defecto y `default.conf` no exige ticket en `/sip/ws`. | `docker-compose.yml`, `docker/nginx/default.conf` | Aceptable solo en una máquina de desarrollo aislada. |

## Telefonía y marcador

| Problema | Dónde | Efecto |
|---|---|---|
| Nadie escribe `campaign:<id>:agents:available` ni `agent:<id>` en Redis. | `dialer_engine/dialer.py` | Las campañas progresivas, predictivas, preview y manuales no marcan porque el marcador ve cero agentes. |
| Una campaña detenida no se puede volver a iniciar sin reiniciar el marcador. | `dialer_engine/dialer.py` (`active_campaigns`) | Hay que reiniciar `vozipomni_dialer`. |
| La pausa de campaña no envía la orden de parada al marcador. | `backend/apps/campaigns/services.py` | El marcador puede seguir llamando tras pausar. |
| El marcador no alcanza el backend para consultar DNC (`BACKEND_URL` y token sin definir en producción) y, si falla, deja pasar la llamada. | `dialer_engine/dialer.py`, `docker-compose.prod.yml` | La lista negra no se aplica desde el marcador. |
| `core` no está en `INSTALLED_APPS`, así que sus receptores de eventos no se conectan. | `backend/config/settings.py`, `backend/core/event_handlers.py` | El inicio de campaña depende solo de la tarea periódica. |
| Dos programaciones de Celery Beat con nombres de tarea distintos. | `backend/config/settings.py`, `backend/config/celery.py` | Tareas como `process_pending_calls` o la retención de grabaciones pueden no ejecutarse. Revise `/admin/django_celery_beat/periodictask/`. |
| `force_break` y `force_logout` del supervisor solo cambian el estado en la base. | `backend/apps/api/supervisor_viewsets.py` | No pausan ni retiran al agente de las colas de Asterisk ni registran historial. |
| La transferencia a agente y la conferencia desde la consola envían `channel` vacío. | `frontend/components/AgentSoftphone.vue` | El servidor responde error; la transferencia "Rápida" sí funciona. |
| La extensión de un IVR no se crea en `[from-internal]` y los mensajes de inválido y timeout usan textos en lugar de audios. | `backend/apps/telephony/asterisk_config.py`, `frontend/pages/ivr/index.vue` | No se puede marcar el IVR desde un softphone y esos mensajes no suenan. |
| En colas, un valor 0 se reemplaza por el predeterminado (`valor or defecto`). | `backend/apps/telephony/asterisk_config.py` | "0 = sin límite" no desactiva el tiempo máximo ni los anuncios. |
| `time_condition` de rutas entrantes y el destino de fallo de destinos personalizados no se usan al generar el dialplan. | `backend/apps/telephony/asterisk_config.py` | Los horarios de las rutas entrantes no tienen efecto. |
| El interruptor **Activo** de troncales llama a `toggle_status/`, que no existe. | `frontend/pages/trunks/index.vue` | Hay que desactivar la troncal por API (`PATCH`). |
| Kamailio decide por longitud: más de 6 dígitos va a Asterisk. | `docker/kamailio/kamailio.cfg` | Extensiones de más de 6 dígitos y códigos cortos externos no funcionan desde el softphone. |

## Campañas y contactos

| Problema | Dónde | Efecto |
|---|---|---|
| El modal de importación no envía `contact_list_id` y no hay pantalla para crear listas. | `frontend/pages/contacts/index.vue` | La importación desde la pantalla siempre falla; hay que usar la API. |
| `POST /api/contacts/` no actualiza `total_contacts`. | `backend/apps/api/viewsets/contacts.py` | Una lista cargada contacto por contacto no deja iniciar la campaña. |
| `start_date` es obligatorio aunque la pantalla diga que es opcional; "Llamadas Simultáneas Máx." no se guarda. | `frontend/pages/campaigns/index.vue`, `backend/apps/campaigns/models.py` | Error genérico al crear la campaña; el campo no tiene efecto. |
| La pestaña **Completadas** filtra por `completed` y el modelo usa `finished`. | `frontend/pages/campaigns/index.vue` | Las campañas finalizadas solo aparecen en **Todas**. |
| La unicidad de la lista negra se valida antes de normalizar el teléfono. | `backend/apps/api/admin_viewsets.py` | Un duplicado con otro formato produce error 500. |
| El encabezado de la pestaña **Dialer** usa datos de ejemplo. | `frontend/components/AgentDialerPanel.vue` | Nombre y avance de campaña no son los reales. |

## Grabaciones, reportes y frontend

| Problema | Dónde | Efecto |
|---|---|---|
| El botón **Descargar Seleccionadas** no tiene acción y el filtro **Agente** filtra solo la página cargada. | `frontend/pages/recordings/index.vue` | Funciones incompletas en la pantalla de grabaciones. |
| `dashboard-stats` y `supervisor/dashboard` calculan "hoy" en UTC. | `backend/apps/reports/views.py`, `backend/apps/api/supervisor_viewsets.py` | "Hoy" empieza a las 19:00 del día anterior en Colombia en esas dos vistas. |
| El plugin `api.ts` no guarda el refresh token rotado. | `frontend/plugins/api.ts` | Tras una rotación, ese camino puede mandar al usuario a `/login`. |
| El contador de post-llamada de la consola es fijo en 10 s. | `frontend/components/AgentCallDisposition.vue` | Ignora el tiempo de post-llamada configurado. |
| El límite de reintentos de reconexión del softphone nunca se alcanza. | `frontend/composables/useWebRTC.ts` | El softphone reintenta indefinidamente. |

## Repositorio y CI

| Problema | Dónde | Efecto |
|---|---|---|
| `test_tasks.py` parchea un `DialerService` que ya no existe. | `backend/apps/campaigns/tests/test_tasks.py` | Pruebas desactualizadas. |
| Varios scripts citados en la documentación están excluidos por `.gitignore` (`install-debug-tools.sh`, `diagnostico-extension.sh`, `generate-dev-ssl.ps1`). | `.gitignore` | No llegan a los servidores con `git clone`. |
| `docker/asterisk/entrypoint.sh` escribe la clave AMI en `manager.conf` dentro del directorio montado del repositorio. | `docker/asterisk/entrypoint.sh` | `git status` muestra el archivo modificado con la clave real; no debe subirse. |

## Ver también

- [Contribuir](./contribuir.md)
- [Pruebas y CI](./pruebas-y-ci.md)
- [Backend](./backend.md)
- [Frontend](./frontend.md)
- [Marcador](./marcador.md)
- [Seguridad y antifraude](../administracion/seguridad-antifraude.md)
