# Usuarios y roles

Este manual explica cómo el administrador crea, edita, activa y desactiva las cuentas de acceso a VozipCX, qué ve cada rol en el menú, qué puede hacer cada rol en la API y cómo funcionan el cambio y la recuperación de contraseña. Todo lo descrito corresponde a la página `frontend/pages/users/index.vue`, al menú `frontend/utils/navigation.ts`, a los permisos de `backend/core/permissions.py` y a las vistas de `backend/apps/api/admin_viewsets.py`.

## Acceso

- Menú: **Administración → Usuarios y roles** (ruta `/users`).
- Solo el rol **Administrador** ve esta opción. La API equivalente (`/api/users/`) usa el permiso `IsAdminUser`: cualquier otro rol recibe "Se requiere rol de administrador para esta acción."
- Un superusuario de Django (`is_superuser`) tiene acceso total sin importar su rol. El comando `createsuperuser` asigna siempre el rol `admin`.

## Roles disponibles

El modelo `User` (`backend/apps/users/models.py`) define cuatro roles. El valor por defecto al crear un usuario por la API es `agent`.

| Rol (valor interno) | Etiqueta en pantalla | Página de inicio al entrar |
|---|---|---|
| `admin` | Administrador | `/dashboard` |
| `supervisor` | Supervisor | `/supervisor` (Monitor en vivo) |
| `analyst` | Analista | `/dashboard` |
| `agent` | Agente | `/agent/console` |

### Qué ve cada rol en el menú

El menú lateral se filtra con `navigationForRole()`. Además, el middleware global `access.global.ts` impide entrar por URL a un módulo no permitido: muestra el aviso "Acceso restringido — Tu rol no tiene permiso para este módulo." y redirige a la página de inicio del rol.

| Grupo del menú | Administrador | Supervisor | Analista |
|---|---|---|---|
| Dashboard | Sí | Sí | Sí |
| Supervisión (Monitor en vivo, Auditoría de gestiones) | Sí | Sí | No |
| Omnicanal: Bandeja omnicanal, Envíos masivos, Respuestas y etiquetas | Sí | Sí | No |
| Omnicanal: Métricas de chat | Sí | Sí | Sí |
| Operación: Agentes, Formularios de campaña, Contactos, Lista negra (DNC), Callbacks | Sí | Sí | No |
| Operación: Campañas, Llamadas | Sí | Sí | Sí |
| Calidad: Evaluaciones, Grabaciones | Sí | Sí | Sí |
| Calidad: Plantillas de evaluación | Sí | Sí | No |
| Reportes: KPIs y métricas, Exportar / programados | Sí | Sí | Sí |
| Telefonía: Colas | Sí | Sí | No |
| Telefonía: Troncales SIP, Rutas Entrantes (DIDs), Rutas Salientes, IVR Menus, Extensiones, Buzones de Voz, Condiciones Horario, Destinos Personalizados, Seguridad y antifraude | Sí | No | No |
| Administración: Usuarios y roles, WhatsApp Business, Email, chat web y redes, Configuración | Sí | No | No |
| Administración: Grupos y pausas, Webhooks | Sí | Sí | No |

El rol **Agente** no usa el menú administrativo: solo puede abrir `/agent/*` (consola del agente) y `/profile` (Mi Perfil). Cualquier otra ruta lo devuelve a la consola.

### Qué puede hacer cada rol en la API

El menú es una ayuda visual; la autorización real la hace el backend con las clases de `backend/core/permissions.py`:

| Clase de permiso | Regla |
|---|---|
| `IsAdminUser` | Solo `admin` (o superusuario). Se usa en usuarios, troncales, rutas, IVR, extensiones, buzones, destinos personalizados. |
| `IsAdminOrSupervisor` | `admin` o `supervisor`. Se usa, por ejemplo, en la lista negra, la importación masiva de contactos y la auditoría. |
| `IsAdminOrSupervisorOrReadOnly` | Lectura para cualquier usuario autenticado; escritura solo `admin` o `supervisor`. Se usa en agentes, campañas, colas, contactos, grupos y razones de pausa. |
| `IsAdminSupervisorOrAnalyst` | `admin` y `supervisor` leen y escriben; `analyst` solo lee. |
| `IsAgentUser` | Solo usuarios con rol `agent`. |
| `IsOwnerAgentOrAdminSupervisor` | El agente solo opera sobre sus propios objetos; admin y supervisor sobre cualquiera. |

## Crear un usuario

1. Entra a **Administración → Usuarios y roles**.
2. Haz clic en **Nuevo usuario**.
3. Completa el formulario (ver la tabla de campos más abajo). **Usuario**, **Rol** y **Contraseña** son obligatorios.
4. Haz clic en **Guardar**. Verás el aviso "Usuario creado".

Reglas que aplica el backend (`UserAdminSerializer`):

- La contraseña es obligatoria al crear: "La contraseña es obligatoria al crear un usuario."
- La contraseña pasa por los validadores de Django configurados en `AUTH_PASSWORD_VALIDATORS` (el formulario indica "Mínimo 8 caracteres, no solo números").
- El correo no se puede repetir (sin distinguir mayúsculas): "Este correo ya está en uso."

Si eliges el rol **Agente**, el formulario muestra: "Para que un agente pueda atender llamadas créale además su perfil (extensión SIP) en Operación → Agentes." Lee la sección Problemas frecuentes antes de hacerlo: el formulario de Agentes crea su propio usuario y no reutiliza uno existente. La forma recomendada de crear un agente es directamente desde [Agentes](./agentes.md).

## Editar un usuario

1. En la tabla, usa el ícono de lápiz (**Editar**).
2. Cambia los datos y haz clic en **Guardar** ("Usuario actualizado").

Limitaciones:

- El campo **Usuario** no se puede cambiar después de creado.
- No puedes cambiar tu propio rol ("No puedes cambiar tu propio rol.") ni desactivar tu propia cuenta ("No puedes desactivar tu propia cuenta."). En tu propia fila esos controles aparecen deshabilitados.
- La edición no cambia la contraseña; para eso está el ícono de llave.

## Activar y desactivar

- El botón de la columna de acciones alterna entre **Desactivar** y **Activar** (`POST /api/users/{id}/toggle-active/`).
- Al desactivar se pide confirmación: "¿Desactivar a Nombre? No podrá iniciar sesión."
- Un usuario desactivado no puede iniciar sesión, no puede pedir recuperación de contraseña y no obtiene ticket para el WebSocket SIP del softphone (la validación de `sip-ws-auth` exige usuario activo).
- El borrado por API (`DELETE /api/users/{id}/`) tampoco elimina: solo desactiva. Así se conserva el historial de llamadas y gestiones.

La tabla filtra por **Activos**, **Inactivos** o **Todos**, y las tarjetas superiores (Administradores, Supervisores, Analistas, Agentes) cuentan los usuarios activos de cada rol; al hacer clic en una tarjeta se filtra la tabla por ese rol.

## Contraseñas

### Cambio por el administrador

1. En la fila del usuario, haz clic en el ícono de llave (**Cambiar contraseña**).
2. En la ventana "Nueva contraseña · usuario" escribe la clave en **Contraseña** y repítela en **Confirmar**.
3. Haz clic en **Actualizar** (se habilita solo si ambas coinciden).

Se llama a `POST /api/users/{id}/set-password/`, que aplica los mismos validadores de Django. Según el código revisado, esta acción cambia la clave pero no revoca las sesiones que el usuario ya tenga abiertas.

### Cambio por el propio usuario

Cualquier usuario puede cambiar su clave en **Mi Perfil → Cambiar Contraseña** con los campos **Contraseña Actual**, **Nueva Contraseña** y **Confirmar Nueva Contraseña** (`POST /api/auth/change-password/`). Si la clave actual no coincide, el backend responde "La contraseña actual no es correcta."

### Recuperación ("olvidé mi contraseña")

1. En la pantalla de inicio de sesión, el usuario abre `/forgot-password` ("Recuperar contraseña").
2. Escribe su **Correo o usuario** y hace clic en **Enviar enlace**.
3. La respuesta es siempre genérica ("Si la cuenta existe, recibirás un correo con instrucciones.") para no revelar qué cuentas existen.
4. Si la cuenta está activa y tiene correo, el backend envía un mensaje con asunto "VozipCX — Recuperación de contraseña" y un enlace `FRONTEND_URL/reset-password?uid=...&token=...`.
5. En `/reset-password` ("Nueva contraseña") el usuario escribe **Nueva contraseña** y **Confirmar contraseña** y hace clic en **Guardar contraseña**.
6. Al confirmar, el backend guarda la clave y pone en la lista negra todos los refresh tokens del usuario (`OutstandingToken` → `BlacklistedToken`), con lo que las demás sesiones no podrán renovarse. El navegador limpia la sesión local y redirige a `/login`.

Detalles técnicos:

- El token se genera con `default_token_generator` de Django. Deja de ser válido cuando la contraseña cambia o cuando vence `PASSWORD_RESET_TIMEOUT`; `settings.py` no lo define, así que aplica el valor por defecto de Django.
- Si el enlace es inválido o venció: "El enlace es inválido o ha expirado." El usuario puede usar **Solicitar otro enlace**.
- Las dos vistas tienen límite de 5 solicitudes por hora por IP (`password_reset`). Al superarlo, la pantalla muestra "Demasiados intentos. Espera un momento e inténtalo de nuevo."
- Si `EMAIL_HOST` está vacío, Django usa el backend de consola: el correo no sale, se escribe en el log del backend. Configura el SMTP según [Variables de entorno](../instalacion/variables-entorno.md).

### Usuarios sin contraseña utilizable

Cuando un agente se crea por la API sin enviar `password`, el usuario queda con contraseña inutilizable (antes se usaba una clave fija, ya no). No podrá iniciar sesión hasta que un administrador le asigne una con el ícono de llave, o hasta que use la recuperación por correo si tiene uno registrado.

## Sesiones y cierre de sesión

- La autenticación usa JWT (`rest_framework_simplejwt`): token de acceso de 8 horas y refresh token de 7 días, con rotación y lista negra tras rotar (`ROTATE_REFRESH_TOKENS` y `BLACKLIST_AFTER_ROTATION` activos).
- Al cerrar sesión, el frontend envía el refresh token a `POST /api/auth/logout/` y el backend lo pone en la lista negra. El token de acceso vigente expira solo, según su duración.
- El inicio de sesión tiene límite de 5 intentos por minuto por IP (`login`).

## Campos

| Campo | Obligatorio | Descripción |
|---|---|---|
| Nombre / Apellido | No | Nombre mostrado en tablas, reportes y consola. Si están vacíos se muestra el usuario. |
| Usuario | Sí | Nombre de inicio de sesión. No editable después de crear. |
| Correo | No | Necesario para recuperar la contraseña y para recibir alertas (por ejemplo, si la política antifraude no tiene destinatarios propios, sus alertas van a los administradores con correo). Único. |
| Rol | Sí | Administrador, Supervisor, Analista o Agente. Define menú y permisos. |
| Teléfono | No | Dato de contacto. |
| Departamento | No | Dato organizativo; se muestra en la tabla. |
| Contraseña | Sí, al crear | Solo aparece al crear. Para cambiarla después usa el ícono de llave. |
| Usuario activo | No | Si se desmarca, la cuenta no puede iniciar sesión. |

La tabla muestra además la etiqueta **Perfil agente** cuando el usuario tiene un perfil de agente asociado, y la columna **Último acceso**.

## Buenas prácticas

- Crea una cuenta nominal por persona; no compartas cuentas de administrador.
- Mantén al menos dos administradores activos, porque nadie puede desactivarse ni quitarse el rol a sí mismo.
- Registra siempre el correo: sin él no hay recuperación de contraseña ni alertas.
- Asigna el rol mínimo necesario. Un analista solo lee reportes, llamadas, grabaciones y evaluaciones.
- Desactiva en lugar de borrar cuando alguien sale de la operación.
- Configura SMTP antes de pasar a producción y prueba el flujo de recuperación con una cuenta de prueba.

## Problemas frecuentes

- **"Acceso restringido" al abrir un módulo.** El rol no tiene ese módulo en `navigation.ts`. Revisa la tabla de roles o pide a un administrador el cambio de rol.
- **No llega el correo de recuperación.** Verifica que el usuario esté activo y tenga correo, que `EMAIL_HOST` esté configurado y que `FRONTEND_URL` apunte a la URL pública real. Sin SMTP, el mensaje aparece en el log del backend.
- **"Este correo ya está en uso."** Otro usuario ya tiene ese correo (la comparación ignora mayúsculas).
- **Creé el usuario con rol Agente pero no puedo crearle el perfil en Operación → Agentes.** El formulario de Agentes siempre crea un usuario nuevo y rechaza un nombre de usuario existente ("El nombre de usuario ... ya está en uso"). Opciones: crear el agente directamente desde [Agentes](./agentes.md) con otro usuario, o asociar el usuario existente a un perfil de agente desde el administrador de Django (`/admin/`, sección Agentes, campo `user`).
- **El agente no puede iniciar sesión tras crearlo por API.** Probablemente quedó sin contraseña utilizable. Asígnale una con el ícono de llave.
- **"Demasiados intentos" al iniciar sesión o recuperar clave.** Se alcanzó el límite por IP; espera y vuelve a intentar.

## Ver también

- [Agentes](./agentes.md)
- [Seguridad y antifraude](./seguridad-antifraude.md)
- [Manual del agente](../manuales/manual-agente.md)
- [Manual del supervisor](../manuales/manual-supervisor.md)
- [Manual del analista](../manuales/manual-analista.md)
- [Variables de entorno](../instalacion/variables-entorno.md)
- [API: autenticación](../api/autenticacion.md)
- [API: usuarios y agentes](../api/usuarios-y-agentes.md)
- [Glosario](../general/glosario.md)
