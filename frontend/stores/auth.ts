import { defineStore } from 'pinia'

interface User {
  id: number
  username: string
  email: string
  name: string
  avatar?: string
  role: string
  permissions?: string[]
}

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    token: null,
    refreshToken: null
  }),

  getters: {
    isAuthenticated: (state) => !!state.token && !!state.user
  },

  actions: {
    setAuth(token: string, user: User, refreshToken?: string) {
      this.token = token
      this.user = user
      if (refreshToken) {
        this.refreshToken = refreshToken
      }

      // Guardar en localStorage (compatibilidad) Y en cookies (más seguro)
      if (process.client) {
        localStorage.setItem('auth_token', token)
        localStorage.setItem('auth_user', JSON.stringify(user))
        if (refreshToken) {
          localStorage.setItem('auth_refresh_token', refreshToken)
        }
        // Cookies — el backend las set como httpOnly en producción;
        // aquí las seteamos como fallback para el cliente
        try {
          const accessCookie = useCookie<string>('access_token', {
            maxAge: 8 * 3600,   // 8 horas (igual que ACCESS_TOKEN_LIFETIME)
            sameSite: 'strict',
          })
          accessCookie.value = token
          if (refreshToken) {
            const refreshCookie = useCookie<string>('refresh_token', {
              maxAge: 7 * 24 * 3600,  // 7 días (igual que REFRESH_TOKEN_LIFETIME)
              sameSite: 'strict',
            })
            refreshCookie.value = refreshToken
          }
        } catch {
          // useCookie puede no estar disponible fuera de setup(); ignorar
        }
      }
    },

    setToken(token: string) {
      this.token = token
      if (process.client) {
        localStorage.setItem('auth_token', token)
      }
    },

    setUser(user: User) {
      this.user = user
      if (process.client) {
        localStorage.setItem('auth_user', JSON.stringify(user))
      }
    },

    clearAuth() {
      this.user = null
      this.token = null
      this.refreshToken = null

      // Limpiar localStorage y cookies
      if (process.client) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_user')
        localStorage.removeItem('auth_refresh_token')

        try {
          useCookie('access_token').value = null
          useCookie('refresh_token').value = null
        } catch { /* fuera de setup */ }

        // Limpiar toasts pendientes para evitar notificaciones "fantasma"
        try {
          const toast = useToast()
          toast.toasts.value.forEach(t => toast.remove(t.id))
        } catch {
          // useToast puede no estar disponible fuera de un componente; ignorar
        }
      }
    },

    loadFromStorage() {
      if (process.client) {
        const token = localStorage.getItem('auth_token')
        const userStr = localStorage.getItem('auth_user')
        const refreshToken = localStorage.getItem('auth_refresh_token')

        if (token && userStr) {
          try {
            // Validar que userStr no esté vacío y sea JSON válido
            if (userStr.trim() === '' || userStr === 'undefined' || userStr === 'null') {
              throw new Error('Invalid user data in localStorage')
            }
            
            this.token = token
            this.user = JSON.parse(userStr)
            if (refreshToken) {
              this.refreshToken = refreshToken
            }
          } catch (error) {
            console.error('Error loading auth from storage:', error)
            // Limpiar localStorage corrupto
            this.clearAuth()
          }
        }
      }
    }
  }
})
