import type { UseFetchOptions } from 'nuxt/app'

export const useApi = () => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  const apiFetch = async <T>(
    url: string,
    options: UseFetchOptions<T> = {}
  ) => {
    // Cargar token desde localStorage si no está en el store
    if (process.client && !authStore.token) {
      authStore.loadFromStorage()
    }

    const token = authStore.token

    const defaults: UseFetchOptions<T> = {
      baseURL: config.public.apiBase,
      headers: token
        ? { Authorization: `Bearer ${token}` }
        : {},
      onResponseError({ response }) {
        if (response.status === 401) {
          // Token inválido o expirado
          if (process.client) {
            authStore.clearAuth()
            navigateTo('/login')
          }
        }
      }
    }

    const params = { ...defaults, ...options }
    return await useFetch(url, params)
  }

  return {
    apiFetch
  }
}

// Composable específico para llamadas a la API
export const useApiCall = async <T>(
  url: string,
  options: UseFetchOptions<T> = {}
) => {
  const { apiFetch } = useApi()
  return await apiFetch<T>(url, options)
}
