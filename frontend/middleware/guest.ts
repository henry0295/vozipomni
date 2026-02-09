export default defineNuxtRouteMiddleware((to) => {
  const { isAuthenticated } = useAuth()

  // Si está autenticado y va a login, redirigir a dashboard
  if (isAuthenticated.value && to.path === '/login') {
    return navigateTo('/dashboard')
  }
})
