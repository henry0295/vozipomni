import type { UseFetchOptions } from 'nuxt/app'

export const useApi = () => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()

  const apiFetch = async <T>(
    url: string,
    options: UseFetchOptions<T> = {}
  ) => {
    const token = authStore.token

    const defaults: UseFetchOptions<T> = {
      baseURL: config.public.apiBase,
      headers: token
        ? { Authorization: `Bearer ${token}` }
        : {},
      onResponseError({ response }) {
        if (response.status === 401) {
          authStore.clearAuth()
          navigateTo('/login')
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
