import type { Campaign } from '~/types'
import { extractResults } from '~/composables/useApi'

export const useCampaigns = () => {
  const { apiFetch } = useApi()

  // Obtener todas las campañas
  const getCampaigns = async (params: any = {}) => {
    const { data, error } = await apiFetch<any>('/campaigns/', {
      query: params
    })
    const { items, count } = extractResults<Campaign>(data.value)
    return { data: items, total: count, error: error.value }
  }

  // Obtener una campaña específica
  const getCampaign = async (id: number) => {
    const { data, error } = await apiFetch<Campaign>(`/campaigns/${id}/`)
    return { data: data.value, error: error.value }
  }

  // Crear campaña
  const createCampaign = async (campaignData: Partial<Campaign>) => {
    const { data, error } = await apiFetch<Campaign>('/campaigns/', {
      method: 'POST',
      body: campaignData
    })
    return { data: data.value, error: error.value }
  }

  // Actualizar campaña
  const updateCampaign = async (id: number, campaignData: Partial<Campaign>) => {
    const { data, error } = await apiFetch<Campaign>(`/campaigns/${id}/`, {
      method: 'PATCH',
      body: campaignData
    })
    return { data: data.value, error: error.value }
  }

  // Eliminar campaña
  const deleteCampaign = async (id: number) => {
    const { error } = await apiFetch(`/campaigns/${id}/`, {
      method: 'DELETE'
    })
    return { error: error.value }
  }

  // Iniciar campaña
  const startCampaign = async (id: number) => {
    const { data, error } = await apiFetch(`/campaigns/${id}/start/`, {
      method: 'POST'
    })
    return { data: data.value, error: error.value }
  }

  // Pausar campaña
  const pauseCampaign = async (id: number) => {
    const { data, error } = await apiFetch(`/campaigns/${id}/pause/`, {
      method: 'POST'
    })
    return { data: data.value, error: error.value }
  }

  // Obtener estadísticas de campaña
  const getCampaignStats = async (id: number) => {
    const { data, error } = await apiFetch(`/campaigns/${id}/stats/`)
    return { data: data.value, error: error.value }
  }

  // Guardar disposición de llamada
  const saveCampaignDisposition = async (dispositionData: any) => {
    const { data, error } = await apiFetch('/calls/disposition/', {
      method: 'POST',
      body: dispositionData
    })
    return { data: data.value, error: error.value }
  }

  return {
    getCampaigns,
    getCampaign,
    createCampaign,
    updateCampaign,
    deleteCampaign,
    startCampaign,
    pauseCampaign,
    getCampaignStats,
    saveCampaignDisposition
  }
}
