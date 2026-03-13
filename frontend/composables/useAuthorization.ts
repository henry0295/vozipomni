import { computed } from 'vue'
import { useAuthStore } from '~/stores/auth'
import { useRouter } from 'vue-router'

export const useAuthorization = () => {
  const authStore = useAuthStore()
  const router = useRouter()

  /**
   * Verifica si el usuario tiene un rol específico
   */
  const hasRole = (role: string | string[]): boolean => {
    if (!authStore.user) return false
    
    if (Array.isArray(role)) {
      return role.includes(authStore.user.role)
    }
    
    return authStore.user.role === role
  }

  /**
   * Verifica si el usuario es administrador
   */
  const isAdmin = computed(() => hasRole('admin'))

  /**
   * Verifica si el usuario es supervisor
   */
  const isSupervisor = computed(() => hasRole('supervisor'))

  /**
   * Verifica si el usuario es agente
   */
  const isAgent = computed(() => hasRole('agent'))

  /**
   * Verifica si el usuario tiene permisos específicos
   */
  const hasPermission = (permission: string | string[]): boolean => {
    if (!authStore.user?.permissions) return false
    
    if (Array.isArray(permission)) {
      return permission.some(p => authStore.user!.permissions!.includes(p))
    }
    
    return authStore.user.permissions.includes(permission)
  }

  /**
   * Verifica si el usuario es admin o supervisor
   */
  const isAdminOrSupervisor = computed(() => {
    return hasRole(['admin', 'supervisor'])
  })

  /**
   * Redirige según el rol del usuario
   */
  const redirectByRole = async () => {
    const userRole = authStore.user?.role
    
    switch (userRole) {
      case 'agent':
        await router.push('/agent/console')
        break
      case 'supervisor':
        await router.push('/supervisor')
        break
      case 'admin':
      default:
        await router.push('/dashboard')
        break
    }
  }

  /**
   * Verifica si el usuario puede acceder a una ruta
   */
  const canAccess = (requiredRoles: string[]): boolean => {
    return hasRole(requiredRoles)
  }

  /**
   * Requiere un rol específico y redirige si no lo tiene
   */
  const requireRole = async (role: string | string[], redirectTo: string = '/dashboard'): Promise<boolean> => {
    if (hasRole(role)) {
      return true
    }
    
    console.warn(`Access denied: User role (${authStore.user?.role}) not in ${JSON.stringify(role)}`)
    await router.push(redirectTo)
    return false
  }

  return {
    // Comprobaciones de rol
    hasRole,
    isAdmin,
    isSupervisor,
    isAgent,
    isAdminOrSupervisor,
    
    // Comprobaciones de permisos
    hasPermission,
    
    // Acceso y redirección
    canAccess,
    requireRole,
    redirectByRole
  }
}
