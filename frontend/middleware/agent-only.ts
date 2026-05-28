/**
 * Middleware que restringe el acceso a rutas exclusivas de agentes.
 * Si el usuario no tiene rol 'agent', redirige a /dashboard.
 */
export default defineNuxtRouteMiddleware(() => {
  if (!process.client) return  // SSR: dejar pasar, el check real es en cliente

  const authStore = useAuthStore()

  // Si no hay usuario aún, cargar desde localStorage
  if (!authStore.user) {
    authStore.loadFromStorage()
  }

  const role = authStore.user?.role
  if (role && role !== 'agent') {
    return navigateTo('/dashboard', { replace: true })
  }
})
