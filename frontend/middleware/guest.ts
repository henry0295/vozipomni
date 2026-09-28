import { homeForRole } from '~/utils/navigation'

export default defineNuxtRouteMiddleware((to) => {
  const { isAuthenticated, user } = useAuth()

  // Si ya hay sesión, las páginas de invitado (login, recuperar contraseña) no aplican
  if (isAuthenticated.value && ['/login', '/forgot-password', '/reset-password'].includes(to.path)) {
    return navigateTo(homeForRole(user.value?.role))
  }
})
