/**
 * Guardia global de acceso por rol.
 *
 * Complementa (no reemplaza) al middleware nombrado `auth`:
 *  - Rutas públicas: libres.
 *  - Sin sesión: → /login
 *  - Agentes: solo /agent/* y /profile (el resto → consola)
 *  - Resto de roles: se valida contra utils/navigation.ts; si el rol no tiene
 *    acceso al módulo (ej. analista entrando a /trunks) → su página de inicio.
 */
import { PUBLIC_ROUTES, canAccessRoute, homeForRole } from '~/utils/navigation'

export default defineNuxtRouteMiddleware((to) => {
  if (!process.client) return
  if (PUBLIC_ROUTES.includes(to.path)) return

  const authStore = useAuthStore()
  if (!authStore.token) authStore.loadFromStorage()

  if (!authStore.token) {
    return navigateTo('/login')
  }

  const role = authStore.user?.role
  const isAgentConsole = to.path === '/agent' || to.path.startsWith('/agent/')

  if (role === 'agent') {
    if (!isAgentConsole && to.path !== '/profile') {
      return navigateTo('/agent/console', { replace: true })
    }
    return
  }

  if (isAgentConsole) {
    return navigateTo(homeForRole(role), { replace: true })
  }

  if (!canAccessRoute(to.path, role)) {
    try {
      useToast().add({
        title: 'Acceso restringido',
        description: 'Tu rol no tiene permiso para este módulo.',
        color: 'orange',
        timeout: 4000,
      })
    } catch { /* toast no disponible */ }
    return navigateTo(homeForRole(role), { replace: true })
  }
})
