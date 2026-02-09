export default defineNuxtRouteMiddleware(async (to) => {
  const { checkAuth, isAuthenticated } = useAuth()

  // Si ya está autenticado, continuar
  if (isAuthenticated.value) {
    return
  }

  // Intentar verificar la autenticación
  const isAuth = await checkAuth()

  // Si no está autenticado y no está yendo a login, redirigir a login
  if (!isAuth && to.path !== '/login') {
    return navigateTo('/login')
  }
})
