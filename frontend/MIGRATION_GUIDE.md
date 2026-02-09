# Guía de Migración a Nuxt 3

## ✅ Completado

La migración del frontend de VozipOmni de React a Nuxt 3 se ha completado exitosamente.

## 📋 Cambios Principales

### Tecnologías Migradas

| Antes (React) | Después (Nuxt 3) |
|---------------|------------------|
| React 18 | Vue 3 (Composition API) |
| React Router | Vue Router (automático) |
| Vite | Nuxt / Vite |
| Zustand | Pinia |
| Tailwind CSS | Tailwind CSS + Nuxt UI |
| React Icons | Heroicons / Lucide |
| Axios | useFetch / $fetch |

### Estructura de Carpetas

```
Antes (src/):        Después:
├── components/  →   ├── components/
├── hooks/       →   ├── composables/
├── services/    →   ├── composables/ (useApi)
├── store/       →   ├── stores/
├── utils/       →   ├── utils/
└── App.jsx      →   ├── pages/
                     ├── layouts/
                     ├── middleware/
                     ├── plugins/
                     └── app.vue
```

## 🎨 Características Implementadas

### 1. Layouts Profesionales

✅ Layout principal (`default.vue`) con:
- Header sticky con logo
- Breadcrumbs dinámicos
- Menú de usuario con dropdown
- Sidebar de navegación
- Notificaciones
- Botón de logout

✅ Layout de autenticación (`auth.vue`)
- Diseño centrado
- Gradiente de fondo
- Optimizado para login

### 2. Sistema de Autenticación

✅ Store de Pinia para autenticación
✅ Composable `useAuth` con:
- Login
- Logout
- Refresh token
- Verificación de autenticación

✅ Middleware:
- `auth.ts` - Protege rutas autenticadas
- `guest.ts` - Redirige usuarios autenticados

✅ Persistencia en localStorage

### 3. Integración con Backend

✅ Composable `useApi`:
- Configuración automática de headers
- Manejo de tokens JWT
- Interceptor de errores 401
- Base URL configurable

✅ Composable `useWebSocket`:
- Conexión WebSocket con auth
- Reconexión automática
- Manejo de mensajes
- Desconexión limpia

### 4. Páginas Implementadas

✅ `/` - Página de inicio (redirección)
✅ `/login` - Inicio de sesión
✅ `/dashboard` - Panel principal con estadísticas
✅ `/agents` - Gestión de agentes con tabla
✅ `/queues` - Vista de colas con cards
✅ `/reports` - Reportes y análisis

### 5. Componentes Reutilizables

✅ `DataTable.vue` - Tabla con paginación
✅ `StatCard.vue` - Tarjeta de estadística
✅ `ConfirmModal.vue` - Modal de confirmación
✅ `Alert.vue` - Alertas tipo (info/success/warning/error)

### 6. Utilidades

✅ `constants.ts` - Constantes de la aplicación
✅ `format.ts` - Funciones de formateo
✅ `validation.ts` - Validaciones
✅ `helpers.ts` - Funciones auxiliares

## 🚀 Próximos Pasos

### Para el Desarrollador

1. **Instalar dependencias**
```bash
cd frontend
npm install
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con las URLs correctas del backend
```

3. **Ejecutar en desarrollo**
```bash
npm run dev
```

4. **Verificar conexión con backend**
- Asegurarse de que el backend Django esté corriendo
- Verificar CORS en Django
- Probar login con credenciales existentes

### Páginas Pendientes de Implementar

Las siguientes páginas tienen la estructura base pero necesitan implementación completa:

- [ ] `/campaigns` - Gestión de campañas
- [ ] `/contacts` - Gestión de contactos
- [ ] `/calls` - Registro de llamadas
- [ ] `/recordings` - Reproductor de grabaciones
- [ ] `/trunks` - Configuración de troncales
- [ ] `/settings` - Configuración general
- [ ] `/profile` - Perfil de usuario

### Integraciones Pendientes

- [ ] WebSocket en tiempo real para:
  - Estado de agentes
  - Llamadas en cola
  - Notificaciones
  - Métricas del dashboard

- [ ] Gráficos y visualizaciones:
  - Chart.js o ApexCharts
  - Gráficos de reportes
  - Dashboard en tiempo real

- [ ] Telefonía:
  - Integración JsSIP para softphone
  - Panel de llamada
  - Transferencias
  - Hold/Resume

## ⚠️ Consideraciones Importantes

### Backend Django

**NO se requieren cambios en el backend Django**. El frontend consume las APIs REST existentes.

Verificar que el backend tenga:
- ✅ CORS configurado correctamente
- ✅ Endpoints de autenticación JWT
- ✅ Endpoints REST para cada módulo
- ✅ WebSocket configurado (Django Channels)

### Variables de Entorno

Crear archivo `.env` en `frontend/`:

```env
NUXT_PUBLIC_API_BASE=http://localhost:8000/api
NUXT_PUBLIC_WS_BASE=ws://localhost:8000/ws
```

Para producción:
```env
NUXT_PUBLIC_API_BASE=https://api.vozipomni.com/api
NUXT_PUBLIC_WS_BASE=wss://api.vozipomni.com/ws
```

### Docker

El `Dockerfile` ha sido actualizado para Nuxt 3:
- Multi-stage build
- Optimizado para producción
- Node 20 Alpine

Para reconstruir:
```bash
docker-compose build frontend
docker-compose up frontend
```

## 🎯 Diferencias Clave React vs Vue

### Sintaxis de Componentes

**React:**
```jsx
export default function MyComponent({ title }) {
  const [count, setCount] = useState(0)
  
  return (
    <div>
      <h1>{title}</h1>
      <button onClick={() => setCount(count + 1)}>
        Count: {count}
      </button>
    </div>
  )
}
```

**Vue 3 (Composition API):**
```vue
<template>
  <div>
    <h1>{{ title }}</h1>
    <button @click="count++">
      Count: {{ count }}
    </button>
  </div>
</template>

<script setup>
defineProps(['title'])
const count = ref(0)
</script>
```

### Efectos / Ciclo de Vida

**React:**
```js
useEffect(() => {
  fetchData()
}, [])
```

**Vue:**
```js
onMounted(() => {
  fetchData()
})
```

### Computadas

**React:**
```js
const doubled = useMemo(() => count * 2, [count])
```

**Vue:**
```js
const doubled = computed(() => count.value * 2)
```

### Manejo de Estado

**React (Zustand):**
```js
const useStore = create((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 }))
}))

const { count, increment } = useStore()
```

**Vue (Pinia):**
```js
export const useStore = defineStore('main', {
  state: () => ({ count: 0 }),
  actions: {
    increment() {
      this.count++
    }
  }
})

const store = useStore()
```

## 📚 Recursos

- [Nuxt 3 Documentation](https://nuxt.com)
- [Vue 3 Documentation](https://vuejs.org)
- [Nuxt UI Documentation](https://ui.nuxt.com)
- [Pinia Documentation](https://pinia.vuejs.org)
- [Tailwind CSS](https://tailwindcss.com)

## ✨ Mejoras Implementadas

1. **SEO Mejorado** - SSR y meta tags dinámicos
2. **Performance** - Auto-imports y tree-shaking
3. **DX Mejorado** - TypeScript y auto-completado
4. **Code Splitting** - Automático por página
5. **Optimización** - Lazy loading de componentes
6. **Accesibilidad** - Componentes UI accesibles

¡La migración está completa y lista para desarrollo! 🎉
