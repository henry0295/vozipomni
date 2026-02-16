import type { Agent } from '~/types'
import { extractResults } from '~/composables/useApi'

export const useAgents = () => {
  const { apiFetch } = useApi()

  // Obtener todos los agentes
  const getAgents = async (params: any = {}) => {
    const { data, error } = await apiFetch<any>('/agents/', {
      query: params
    })
    const { items, count } = extractResults<Agent>(data.value)
    return { data: items, total: count, error: error.value }
  }

  // Obtener un agente específico
  const getAgent = async (id: number) => {
    const { data, error } = await apiFetch<Agent>(`/agents/${id}/`)
    return { data: data.value, error: error.value }
  }

  // Crear agente
  const createAgent = async (agentData: Partial<Agent>) => {
    const { data, error } = await apiFetch<Agent>('/agents/', {
      method: 'POST',
      body: agentData
    })
    return { data: data.value, error: error.value }
  }

  // Actualizar agente
  const updateAgent = async (id: number, agentData: Partial<Agent>) => {
    const { data, error } = await apiFetch<Agent>(`/agents/${id}/`, {
      method: 'PATCH',
      body: agentData
    })
    return { data: data.value, error: error.value }
  }

  // Eliminar agente
  const deleteAgent = async (id: number) => {
    const { error } = await apiFetch(`/agents/${id}/`, {
      method: 'DELETE'
    })
    return { error: error.value }
  }

  // Login de agente
  const loginAgent = async (id: number) => {
    const { data, error } = await apiFetch(`/agents/${id}/login/`, {
      method: 'POST'
    })
    return { data: data.value, error: error.value }
  }

  // Logout de agente
  const logoutAgent = async (id: number) => {
    const { data, error } = await apiFetch(`/agents/${id}/logout/`, {
      method: 'POST'
    })
    return { data: data.value, error: error.value }
  }

  // Cambiar estado de agente
  const changeAgentStatus = async (id: number, status: string) => {
    const { data, error } = await apiFetch(`/agents/${id}/change_status/`, {
      method: 'POST',
      body: { status }
    })
    return { data: data.value, error: error.value }
  }

  return {
    getAgents,
    getAgent,
    createAgent,
    updateAgent,
    deleteAgent,
    loginAgent,
    logoutAgent,
    changeAgentStatus
  }
}