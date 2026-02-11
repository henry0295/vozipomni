import type { Recording } from '~/types'

export const useRecordings = () => {
  const { apiFetch } = useApi()

  // Obtener todas las grabaciones
  const getRecordings = async (params: any = {}) => {
    const { data, error } = await apiFetch<{results: Recording[], count: number}>('/recordings/', {
      query: params
    })
    return { 
      data: data.value?.results || [], 
      total: data.value?.count || 0,
      error: error.value 
    }
  }

  // Obtener una grabación específica
  const getRecording = async (id: number) => {
    const { data, error } = await apiFetch<Recording>(`/recordings/${id}/`)
    return { data: data.value, error: error.value }
  }

  // Eliminar grabación
  const deleteRecording = async (id: number) => {
    const { error } = await apiFetch(`/recordings/${id}/`, {
      method: 'DELETE'
    })
    return { error: error.value }
  }

  return {
    getRecordings,
    getRecording,
    deleteRecording
  }
}