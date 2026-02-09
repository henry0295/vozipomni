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

      // Guardar en localStorage
      if (process.client) {
        localStorage.setItem('auth_token', token)
        localStorage.setItem('auth_user', JSON.stringify(user))
        if (refreshToken) {
          localStorage.setItem('auth_refresh_token', refreshToken)
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

      // Limpiar localStorage
      if (process.client) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_user')
        localStorage.removeItem('auth_refresh_token')
      }
    },

    loadFromStorage() {
      if (process.client) {
        const token = localStorage.getItem('auth_token')
        const userStr = localStorage.getItem('auth_user')
        const refreshToken = localStorage.getItem('auth_refresh_token')

        if (token && userStr) {
          try {
            this.token = token
            this.user = JSON.parse(userStr)
            if (refreshToken) {
              this.refreshToken = refreshToken
            }
          } catch (error) {
            console.error('Error loading auth from storage:', error)
            this.clearAuth()
          }
        }
      }
    }
  }
})
