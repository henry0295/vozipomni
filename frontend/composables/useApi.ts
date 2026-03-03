import type { UseFetchOptions } from 'nuxt/app'

// Helper para extraer datos de respuestas paginadas de Django REST Framework
// Django retorna: { count, next, previous, results: [...] }
export function extractResults<T>(data: any): { items: T[], count: number } {
  if (!data) return { items: [], count: 0 }
  // Si es un array directo (sin paginación)
  if (Array.isArray(data)) return { items: data, count: data.length }
  // Si es objeto paginado de DRF
  if (data.results && Array.isArray(data.results)) {
    return { items: data.results as T[], count: data.count || data.results.length }
  }
  // Fallback: intentar usar como array
  return { items: [], count: 0 }
}

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
    const result = await useFetch(url, params)
    
    // Si hay error, intentar extraer el mensaje detallado del servidor
    if (result.error.value) {
      const serverError = result.error.value as any
      let errorData: any = {}
      
      // Intentar obtener datos del error del servidor
      if (serverError.data) {
        errorData = serverError.data
      } else if (serverError.response?._data) {
        errorData = serverError.response._data
      }
      
      // Crear objeto de error enriquecido
      result.error.value = {
        ...serverError,
        data: errorData,
        message: errorData.detail || errorData.message || serverError.message || 'Error en la solicitud'
      } as any
    }
    
    return result
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
