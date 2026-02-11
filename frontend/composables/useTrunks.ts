import type { SipTrunk } from '~/types'

export const useTrunks = () => {
  const { apiFetch } = useApi()

  // Obtener todos los troncales
  const getTrunks = async (params: any = {}) => {
    const { data, error } = await apiFetch<SipTrunk[]>('/trunks/', {
      query: params
    })
    return { data: data.value, error: error.value }
  }

  // Obtener un troncal específico
  const getTrunk = async (id: number) => {
    const { data, error } = await apiFetch<SipTrunk>(`/trunks/${id}/`)
    return { data: data.value, error: error.value }
  }

  // Crear troncal
  const createTrunk = async (trunkData: Partial<SipTrunk>) => {
    const { data, error } = await apiFetch<SipTrunk>('/trunks/', {
      method: 'POST',
      body: trunkData
    })
    return { data: data.value, error: error.value }
  }

  // Actualizar troncal
  const updateTrunk = async (id: number, trunkData: Partial<SipTrunk>) => {
    const { data, error } = await apiFetch<SipTrunk>(`/trunks/${id}/`, {
      method: 'PATCH',
      body: trunkData
    })
    return { data: data.value, error: error.value }
  }

  // Eliminar troncal
  const deleteTrunk = async (id: number) => {
    const { error } = await apiFetch(`/trunks/${id}/`, {
      method: 'DELETE'
    })
    return { error: error.value }
  }

  // Activar/desactivar troncal
  const toggleTrunkStatus = async (id: number) => {
    const { data, error } = await apiFetch(`/trunks/${id}/toggle_status/`, {
      method: 'POST'
    })
    return { data: data.value, error: error.value }
  }

  // Probar conexión del troncal
  const testTrunkConnection = async (id: number) => {
    const { data, error } = await apiFetch(`/trunks/${id}/test_connection/`)
    return { data: data.value, error: error.value }
  }

  return {
    getTrunks,
    getTrunk,
    createTrunk,
    updateTrunk,
    deleteTrunk,
    toggleTrunkStatus,
    testTrunkConnection
  }
}