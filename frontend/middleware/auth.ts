export default defineNuxtRouteMiddleware(async (to) => {
  const authStore = useAuthStore()

  // Cargar desde localStorage si aún no se ha hecho
  if (process.client && !authStore.token) {
    authStore.loadFromStorage()
  }

  // Verificar si hay token
  if (!authStore.token) {
    // No hay token, redirigir a login
    if (to.path !== '/login') {
      return navigateTo('/login')
    }
    return
  }

  // Cargar usuario desde storage si falta
  if (process.client && !authStore.user) {
    authStore.loadFromStorage()
  }

  const role = authStore.user?.role

  // Los agentes no deben acceder al panel administrativo.
  // Cualquier ruta distinta a /agent/* redirige a su consola.
  if (role === 'agent' && !to.path.startsWith('/agent')) {
    return navigateTo('/agent/console', { replace: true })
  }

  // Usuarios no agentes no deben navegar a la consola de agente.
  if (role && role !== 'agent' && to.path.startsWith('/agent')) {
    return navigateTo('/dashboard', { replace: true })
  }

  // Hay token, continuar
})
