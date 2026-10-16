# Contactos

Este manual explica cómo se organizan los contactos que marcan las campañas: listas de contactos, campos de cada contacto, formato de importación desde CSV o Excel, estados e intentos, y la lista negra (DNC) que el marcador consulta antes de llamar. Se basa en `frontend/pages/contacts/index.vue`, `frontend/pages/contacts/blacklist.vue`, los modelos de `backend/apps/contacts/models.py`, `ContactService` en `backend/apps/contacts/services.py`, `BulkContactImportView` y `DNCCheckView` en `backend/apps/api/cc_viewsets.py`, el `BlacklistViewSet` de `backend/apps/api/admin_viewsets.py`, el `ContactSerializer` de `backend/apps/api/serializers.py`, `backend/apps/telephony/ami_cdr_listener.py` y `dialer_engine/dialer.py`.

Todo **contacto** pertenece a una **lista de contactos** (`ContactList`), y una campaña usa una lista. La **lista negra** (`Blacklist`) es global: aplica a todas las campañas que tengan DNC activo.

## Acceso

- **Operación → Contactos** (ruta `/contacts`) y **Operación → Lista negra (DNC)** (ruta `/contacts/blacklist`). Visibles para Administrador y Supervisor.
- API: `/api/contact-lists/` y `/api/contacts/` (`IsAdminOrSupervisorOrReadOnly`), `/api/cc/bulk-import/` (`IsAdminOrSupervisor`), `/api/blacklist/` (`IsAdminOrSupervisor`) y `/api/cc/dnc-check/` (cualquier usuario autenticado).

## Listas de contactos

La interfaz revisada no tiene pantalla para crear listas. Créalas por API o en el administrador de Django (`/admin/`, Listas de Contactos):

```bash
curl -X POST https://<DOMINIO>/api/contact-lists/ \
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"name": "Clientes Bogotá 2025", "description": "Base de renovación"}'
```

| Campo | Uso |
|---|---|
| `name` | Único. Es el nombre que aparece en **Lista de Contactos** al crear una campaña. |
| `description` | Informativa. |
| `total_contacts` | Solo lectura. Lo suma la importación masiva; el inicio de campañas Saliente y Preview lo exige mayor que 0. |
| `is_active` | Estado de la lista. |

El contador `total_contacts` solo aumenta con la importación masiva (y con `ContactService.create_contact`). Crear contactos uno a uno con `POST /api/contacts/` no lo actualiza, y borrar contactos no lo reduce.

## Importar contactos

Formato de archivo (`ContactService.import_contacts_from_csv`):

- CSV en UTF-8 separado por comas, con fila de encabezados. También se acepta Excel (`.xlsx`, `.xls`): se lee la primera hoja y la primera fila como encabezados.
- Encabezados reconocidos: `phone` (obligatorio), `first_name`, `last_name`, `email`, `company`, `address`, `city`, `country` y `whatsapp_opt_in`. Las demás columnas se ignoran.
- En CSV los encabezados distinguen mayúsculas y deben ir en minúscula; en Excel se pasan a minúscula automáticamente.
- `country` usa el código de dos letras; si falta, queda `CO`.
- `whatsapp_opt_in` acepta `si`, `sí`, `yes`, `y`, `true`, `1`, `x` o `verdadero` como consentimiento; registra la fecha y el origen `import`.

Ejemplo (datos ficticios):

```csv
phone,first_name,last_name,email,company,city,country,whatsapp_opt_in
3001234567,Ana,Ejemplo,ana@example.com,Empresa Uno,Bogotá,CO,si
6012345678,Luis,Prueba,,,Medellín,CO,no
```

Qué hace el sistema con cada fila:

1. Sin `phone`: se omite con el error "Missing phone number".
2. Valida el número con `phonenumbers` (región por defecto `CO`) y lo guarda en E.164: `3001234567` queda `+573001234567`. Si no es válido: "Invalid phone ...". La validez de los fijos nuevos (`60X` + 7 dígitos) depende de la versión instalada de la librería; prueba con una fila antes de cargar la base.
3. Si el número ya existe en la lista (o se repite en el archivo), se omite sin error.
4. Crea el contacto con estado **Nuevo** y suma los importados a `total_contacts`.

El resultado muestra **Importados**, **Omitidos** y **Errores** (los primeros 10 mensajes vienen en `errors`).

### Importar desde la pantalla

**Operación → Contactos → Importar** abre "Importar contactos (CSV / Excel)". Según el código revisado, la ventana no tiene selector de lista y no envía `contact_list_id`, así que el backend responde "contact_list_id y file son requeridos". Mientras eso se corrige, importa por API:

```bash
curl -X POST https://<DOMINIO>/api/cc/bulk-import/ \
  -H "Authorization: Bearer <TOKEN>" \
  -F contact_list_id=<ID_LISTA> \
  -F skip_duplicates=true \
  -F file=@contactos.csv
```

## Campos del contacto

| Campo | Uso |
|---|---|
| `first_name`, `last_name` | Nombre que ve el agente. |
| `phone`, `phone2`, `phone3` | Teléfonos. El marcador usa `phone` y, si está vacío, el siguiente disponible. La importación solo llena `phone`. |
| `email`, `company`, `position`, `address`, `city`, `country` | Datos adicionales. |
| `status` | Estado (tabla siguiente). |
| `priority` | 0 a 10 por API. El marcador carga primero los de mayor prioridad. |
| `attempts`, `last_attempt`, `next_attempt` | Intentos. Los dos primeros se actualizan solos; `next_attempt` no lo usa el código revisado. |
| `custom_fields` | JSON. Recibe lo que el agente llena en el formulario de la campaña. |
| `timezone` | Zona horaria del contacto para la ventana de llamada del marcador; vacío usa la de la campaña. |
| `is_vip` | Suma el `vip_priority_boost` de la campaña. |
| `dnc_opt_out` | El contacto pidió no ser llamado; el marcador lo salta como si estuviera en la lista negra. |
| `whatsapp_opt_in` | Consentimiento para WhatsApp; es la columna **Acepta WhatsApp** de la tabla. |

Por API, `ContactSerializer` valida el teléfono con el país del contacto (o `CO`), lo guarda en E.164, exige al menos un teléfono y una prioridad entre 0 y 10.

## Estados e intentos

| Valor | Etiqueta | Cuándo |
|---|---|---|
| `new` | Nuevo | Al importar o crear. |
| `pending` | Pendiente | Tras un intento sin éxito que todavía puede reintentarse. |
| `callback` | Rellamada | Por ejemplo, al cerrar un chat con una calificación que requiere rellamada. |
| `contacted` | Contactado | Disponible en el modelo; el código revisado no lo asigna automáticamente. |
| `success` | Exitoso | Ídem; el reporte de campañas lo cuenta como éxito. |
| `failed` | Fallido | Se alcanzó el máximo de intentos. |
| `blacklisted` | Lista Negra | Excluido de envíos masivos de WhatsApp. |

Al terminar cada llamada de campaña, el listener de CDR suma 1 a `attempts` y fija `last_attempt`. Si la llamada terminó como no contestada, ocupada, fallida o contestador y el contacto estaba en Nuevo o Pendiente, lo deja en **Pendiente** mientras `attempts` sea menor que **Intentos por Contacto** (`max_retries`) de la campaña, y en **Fallido** al llegar al tope. Al iniciar una campaña se cargan los contactos en Nuevo, Pendiente o Rellamada.

## Pantalla de Contactos

La tabla muestra **Nombre**, **Contacto**, **Estado**, **Acepta WhatsApp** (interruptor editable) y **Último Contacto**, y el menú de fila permite **Eliminar**. Limitaciones según el código revisado:

- La búsqueda y el filtro **Estado** no se aplican a la consulta, y el filtro ofrece valores (Calificado, Convertido) que el modelo no tiene.
- **Nuevo Contacto**, **Editar**, **Ver detalles** y el botón de llamar no tienen acción implementada. Crea o edita contactos por API o en `/admin/`.

## Lista negra (DNC)

En **Operación → Lista negra (DNC)**:

- **Agregar número**: **Teléfono** y **Motivo** (por ejemplo "Solicitud del cliente, Ley de Habeas Data"). El número se guarda con solo dígitos y `+` inicial, y debe tener al menos 7 dígitos.
- **Verificar un número**: indica **Bloqueado** o **Permitido** y si es por la lista negra o porque el contacto pidió no ser llamado.
- **Importar**: archivo CSV o Excel (columna 1 teléfono, columna 2 motivo opcional; la primera fila se toma como encabezado si no tiene dígitos) o números pegados, uno por línea, con **Motivo para todos**. Si adjuntas archivo, los números pegados se ignoran. El resultado indica importados, existentes e inválidos.
- La tabla permite buscar, filtrar **Activos** / **Inactivos** / **Todos**, activar o desactivar con **Activo**, editar y quitar.

La comparación usa los últimos 10 dígitos, así que `+573001234567` y `3001234567` se tratan como el mismo número. El marcador guarda cada resultado 5 minutos en Redis; los cambios de la lista invalidan esa caché del número afectado. Si la consulta falla, el marcador no bloquea la llamada. La lista negra se aplica a campañas con `dnc_enabled` activo (valor por defecto).

## Buenas prácticas

- Crea una lista por base o por campaña; no mezcles orígenes en la misma lista.
- Guarda el CSV como "CSV delimitado por comas". Excel en español suele usar punto y coma, y el importador solo acepta comas. Si guardas "CSV UTF-8" con BOM, no pongas `phone` como primera columna, o usa `.xlsx`.
- Formatea la columna de teléfonos como texto en Excel para no perder dígitos.
- Los números quedan en E.164 (`+57...`). Crea una ruta saliente que acepte ese formato, por ejemplo patrón `_+57X.` con **Dígitos a Eliminar** `+57` (ver [Rutas y dialplan](./rutas-y-dialplan.md)).
- Registra en la lista negra toda solicitud de no contacto y el motivo.

## Problemas frecuentes

- **"contact_list_id y file son requeridos".** La importación se hizo desde la pantalla; usa la API.
- **Todas las filas dan "Missing phone number".** El encabezado no es exactamente `phone` (mayúsculas, espacios o BOM) o el separador es punto y coma.
- **"Invalid phone ...".** El número no es válido para Colombia ni tiene indicativo de otro país.
- **La campaña no inicia por falta de contactos.** Los contactos se crearon uno a uno por API y `total_contacts` quedó en 0.
- **Un número bloqueado se sigue marcando.** La campaña tiene DNC desactivado o la consulta al backend falló.

## Ver también

- [Campañas](./campanas.md)
- [Rutas y dialplan](./rutas-y-dialplan.md)
- [Seguridad y antifraude](./seguridad-antifraude.md)
- [Usuarios y roles](./usuarios-y-roles.md)
- [Reportes](./reportes.md)
- [Glosario](../general/glosario.md)
- [Solución de problemas](../operacion/solucion-de-problemas.md)
- [API: campañas y contactos](../api/campanas-y-contactos.md)
