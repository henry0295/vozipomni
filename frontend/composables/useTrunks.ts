import type { SipTrunk } from '~/types'
import { extractResults } from '~/composables/useApi'

export const useTrunks = () => {
  const { apiFetch } = useApi()

  // Obtener todos los troncales
  const getTrunks = async (params: any = {}) => {
    const { data, error } = await apiFetch<any>('/trunks/', {
      query: params
    })
    const { items, count } = extractResults<SipTrunk>(data.value)
    return { data: items, total: count, error: error.value }
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
    const { data, error } = await apiFetch(`/trunks/${id}/test_connection/`, {
      method: 'POST'
    })
    return { data: data.value, error: error.value }
  }

  // Obtener estados de registro de todas las troncales (bulk)
  const getTrunkStatuses = async () => {
    const { data, error } = await apiFetch<Record<string, { status: string; class: string; detail?: string }>>('/telephony/trunks/statuses/')
    return { data: data.value, error: error.value }
  }

  // Forzar re-registro
  const forceRegister = async (id: number) => {
    const { data, error } = await apiFetch(`/telephony/trunks/${id}/force_register/`, {
      method: 'POST'
    })
    return { data: data.value, error: error.value }
  }

  // Preview configuración PJSIP
  const previewConfig = async (id: number) => {
    const { data, error } = await apiFetch(`/telephony/trunks/${id}/preview_config/`)
    return { data: data.value, error: error.value }
  }

  // Regenerar configuración PJSIP de todas las troncales
  const regenerateConfig = async () => {
    const { data, error } = await apiFetch('/telephony/trunks/regenerate_config/', {
      method: 'POST'
    })
    return { data: data.value, error: error.value }
  }

  return {
    getTrunks,
    getTrunk,
    createTrunk,
    updateTrunk,
    deleteTrunk,
    toggleTrunkStatus,
    testTrunkConnection,
    getTrunkStatuses,
    forceRegister,
    previewConfig,
    regenerateConfig
  }
}