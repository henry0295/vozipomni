# VozipCX Frontend - Nuxt 3

Frontend moderno para el sistema de Contact Center VozipCX, construido con Nuxt 3, Vue 3 y Nuxt UI.

## 🚀 Tecnologías

- **Nuxt 3** - Framework de Vue.js para aplicaciones web modernas
- **Vue 3** - Framework JavaScript progresivo (Composition API)
- **Nuxt UI** - Biblioteca de componentes UI para Nuxt
- **Tailwind CSS** - Framework de CSS utilitario
- **Pinia** - Estado global para Vue 3
- **TypeScript** - Tipado estático
- **Heroicons / Lucide** - Iconos

## 📁 Estructura del Proyecto

```
frontend/
├── assets/           # Recursos estáticos (CSS, imágenes)
│   └── css/
│       └── main.css
├── components/       # Componentes reutilizables
│   ├── Alert.vue
│   ├── ConfirmModal.vue
│   ├── DataTable.vue
│   └── StatCard.vue
├── composables/      # Composables de Vue
│   ├── useApi.ts
│   ├── useAuth.ts
│   └── useWebSocket.ts
├── layouts/          # Layouts de la aplicación
│   ├── default.vue
│   └── auth.vue
├── middleware/       # Middleware de rutas
│   ├── auth.ts
│   └── guest.ts
├── pages/           # Páginas (rutas automáticas)
│   ├── index.vue
│   ├── login.vue
│   ├── dashboard.vue
│   ├── agents/
│   ├── queues/
│   └── reports/
├── plugins/         # Plugins de Nuxt
│   └── auth.client.ts
├── stores/          # Stores de Pinia
│   └── auth.ts
├── utils/           # Utilidades y helpers
│   ├── constants.ts
│   ├── format.ts
│   ├── helpers.ts
│   └── validation.ts
├── app.vue          # Componente raíz
├── nuxt.config.ts   # Configuración de Nuxt
└── package.json
```

## 🛠️ Instalación

### Requisitos previos

- Node.js 18+ 
- npm o yarn

### Pasos

1. **Instalar dependencias**

```bash
npm install
```

2. **Configurar variables de entorno**

Copia el archivo de ejemplo y configura las variables:

```bash
cp .env.example .env
```

Edita `.env` con tus configuraciones:

```env
NUXT_PUBLIC_API_BASE=http://localhost:8000/api
NUXT_PUBLIC_WS_BASE=ws://localhost:8000/ws
```

3. **Ejecutar en modo desarrollo**

```bash
npm run dev
```

La aplicación estará disponible en `http://localhost:3000`

## 📦 Compilación para Producción

```bash
# Compilar la aplicación
npm run build

# Generar sitio estático (si aplica)
npm run generate

# Previsualizar compilación
npm run preview
```

## 🐳 Docker

### Desarrollo

```bash
docker build -f Dockerfile.dev -t vozipomni-frontend-dev .
docker run -p 3000:3000 -v $(pwd):/app vozipomni-frontend-dev
```

### Producción

```bash
docker build -t vozipomni-frontend .
docker run -p 3000:3000 vozipomni-frontend
```

## 🔌 Conexión con Backend

El frontend está diseñado para ser completamente desacoplado del backend Django:

### API REST

Las llamadas a la API se realizan mediante el composable `useApi`:

```typescript
const { apiFetch } = useApi()

const { data, error } = await apiFetch('/agents/', {
  method: 'GET'
})
```

### WebSocket

Para comunicación en tiempo real:

```typescript
const { connect, send, onMessage } = useWebSocket()

// Conectar
connect('/call-center/')

// Escuchar mensajes
onMessage((data) => {
  console.log('Mensaje recibido:', data)
})

// Enviar mensaje
send({ action: 'update_status', status: 'available' })
```

## 🎨 Componentes UI

### Nuxt UI

El proyecto usa Nuxt UI como biblioteca principal de componentes:

- `UCard` - Tarjetas
- `UButton` - Botones
- `UInput` - Campos de entrada
- `UTable` - Tablas
- `UModal` - Modales
- `UDropdown` - Menús desplegables
- `UBadge` - Insignias
- Y más...

Documentación: [https://ui.nuxt.com](https://ui.nuxt.com)

### Componentes Personalizados

- **DataTable** - Tabla de datos con paginación
- **StatCard** - Tarjeta de estadística
- **ConfirmModal** - Modal de confirmación
- **Alert** - Alertas y notificaciones

## 🔐 Autenticación

El sistema de autenticación está implementado con:

1. **Store de Pinia** (`stores/auth.ts`) - Mantiene el estado de autenticación
2. **Composable** (`composables/useAuth.ts`) - Lógica de autenticación
3. **Middleware** (`middleware/auth.ts`) - Protege rutas
4. **Plugin** (`plugins/auth.client.ts`) - Inicializa auth desde localStorage

### Uso en páginas

```vue
<script setup>
definePageMeta({
  middleware: ['auth'] // Requiere autenticación
})
</script>
```

## 📱 Páginas Principales

- `/` - Redirección a dashboard o login
- `/login` - Página de inicio de sesión
- `/dashboard` - Panel principal
- `/agents` - Gestión de agentes
- `/queues` - Gestión de colas
- `/campaigns` - Campañas
- `/contacts` - Contactos
- `/calls` - Registro de llamadas
- `/recordings` - Grabaciones
- `/reports` - Reportes y estadísticas
- `/settings` - Configuración

## 🎯 Características

✅ **Autenticación JWT** - Login seguro con tokens
✅ **Estado Global** - Pinia para gestión de estado
✅ **Rutas Protegidas** - Middleware de autenticación
✅ **Diseño Responsive** - Móvil, tablet y desktop
✅ **Modo Claro** - UI profesional y limpia
✅ **Componentes Reutilizables** - DRY principle
✅ **TypeScript** - Tipado estático
✅ **SSR Ready** - Renderizado del lado del servidor
✅ **WebSocket Support** - Comunicación en tiempo real
✅ **API REST** - Integración con backend Django

## 🔧 Configuración Avanzada

### Agregar nuevas páginas

Simplemente crea un archivo `.vue` en `pages/`:

```
pages/my-page.vue → /my-page
pages/users/[id].vue → /users/:id
```

### Agregar composables

Crea archivos en `composables/` y úsalos sin importar:

```typescript
// composables/useMyComposable.ts
export const useMyComposable = () => {
  // lógica
}

// En cualquier componente
const { ... } = useMyComposable()
```

### Agregar stores

```typescript
// stores/myStore.ts
export const useMyStore = defineStore('my-store', {
  state: () => ({ ... }),
  actions: { ... }
})
```

## 📝 Scripts Disponibles

- `npm run dev` - Inicia servidor de desarrollo
- `npm run build` - Compila para producción
- `npm run generate` - Genera sitio estático
- `npm run preview` - Previsualiza compilación
- `npm run lint` - Ejecuta linter
- `npm run lint:fix` - Corrige errores de linting

## 🤝 Contribución

1. Crea una rama para tu feature: `git checkout -b feature/nueva-funcionalidad`
2. Realiza tus cambios
3. Commit: `git commit -m 'Add: nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Crea un Pull Request

## 📄 Licencia

Este proyecto es parte de VozipCX Contact Center.
