import { ref } from 'vue'

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
  // Usar la instancia $api configurada en el plugin con todos los interceptores
  const { $api } = useNuxtApp()

  const apiFetch = async <T>(
    url: string,
    options: any = {}
  ) => {
    try {
      // Usar la instancia $api del plugin que tiene todos los interceptores configurados
      // (autenticación, logging, manejo de errores, etc.)
      const data = await $api<T>(url, options)
      
      // Retornar en formato compatible con useFetch para no romper código existente
      return {
        data: ref(data),
        error: ref(null)
      }
    } catch (error: any) {
      // El plugin ya maneja los errores y muestra toasts, pero retornamos el error
      // para que los componentes puedan manejarlo si lo necesitan
      return {
        data: ref(null),
        error: ref(error)
      }
    }
  }

  return {
    apiFetch
  }
}

// Composable específico para llamadas a la API
export const useApiCall = async <T>(
  url: string,
  options: any = {}
) => {
  const { apiFetch } = useApi()
  return await apiFetch<T>(url, options)
}
