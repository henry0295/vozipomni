export interface User {
  id: number
  username: string
  email: string
  name: string
  avatar?: string
  role: string
  permissions?: string[]
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
}

export const useAuth = () => {
  const authStore = useAuthStore()
  const { apiFetch } = useApi()

  const login = async (credentials: LoginCredentials) => {
    try {
      const { data, error } = await apiFetch<AuthResponse>('/auth/login/', {
        method: 'POST',
        body: credentials
      })

      if (error.value) {
        throw new Error(error.value.message || 'Error al iniciar sesión')
      }

      if (data.value) {
        // Guardar access, refresh token y user
        authStore.setAuth(data.value.access, data.value.user, data.value.refresh)
        return { success: true, user: data.value.user }
      }

      throw new Error('No se recibieron datos de autenticación')
    } catch (err: any) {
      return { 
        success: false, 
        error: err.message || 'Error al iniciar sesión' 
      }
    }
  }

  const logout = async () => {
    try {
      // Llamar al endpoint de logout si existe
      await apiFetch('/auth/logout/', {
        method: 'POST'
      })
    } catch (err) {
      console.error('Error al cerrar sesión:', err)
    } finally {
      authStore.clearAuth()
    }
  }

  const refreshToken = async () => {
    try {
      const refreshToken = authStore.refreshToken
      if (!refreshToken) {
        throw new Error('No refresh token available')
      }

      const { data, error } = await apiFetch<{ access: string }>('/auth/refresh/', {
        method: 'POST',
        body: { refresh: refreshToken }
      })

      if (error.value) {
        throw new Error('Failed to refresh token')
      }

      if (data.value) {
        authStore.setToken(data.value.access)
        return true
      }

      return false
    } catch (err) {
      authStore.clearAuth()
      return false
    }
  }

  const fetchUser = async () => {
    try {
      const { data, error } = await apiFetch<User>('/auth/me/')

      if (error.value) {
        throw new Error('Failed to fetch user')
      }

      if (data.value) {
        authStore.setUser(data.value)
        return data.value
      }

      return null
    } catch (err) {
      console.error('Error fetching user:', err)
      return null
    }
  }

  const checkAuth = async () => {
    if (!authStore.token) {
      return false
    }

    // Intentar obtener los datos del usuario
    const user = await fetchUser()
    return !!user
  }

  return {
    user: computed(() => authStore.user),
    token: computed(() => authStore.token),
    isAuthenticated: computed(() => authStore.isAuthenticated),
    login,
    logout,
    refreshToken,
    fetchUser,
    checkAuth
  }
}
