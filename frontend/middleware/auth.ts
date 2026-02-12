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

  // Hay token, continuar
  // La validación del token se hará cuando se use la API
})
