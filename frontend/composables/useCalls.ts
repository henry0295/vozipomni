import type { Call } from '~/types'

export const useCalls = () => {
  const { apiFetch } = useApi()

  // Obtener todas las llamadas
  const getCalls = async (params: any = {}) => {
    const { data, error } = await apiFetch<{results: Call[], count: number}>('/calls/', {
      query: params
    })
    return { 
      data: data.value?.results || [], 
      total: data.value?.count || 0,
      error: error.value 
    }
  }

  // Obtener una llamada específica
  const getCall = async (id: number) => {
    const { data, error } = await apiFetch<Call>(`/calls/${id}/`)
    return { data: data.value, error: error.value }
  }

  // Obtener estadísticas de dashboard
  const getDashboardStats = async () => {
    // Por ahora calcular desde las llamadas
    const { data: calls } = await getCalls({ page_size: 1000 })
    
    if (!calls) return { data: null, error: 'No se pudieron cargar las estadísticas' }

    const today = new Date()
    today.setHours(0, 0, 0, 0)

    const callsToday = calls.filter(call => 
      new Date(call.start_time) >= today
    )

    const activeAgents = new Set(calls
      .filter(call => call.status === 'answered' || call.status === 'ringing')
      .map(call => call.agent_name)
      .filter(Boolean)
    ).size

    const avgTalkTime = callsToday.length > 0 ? 
      callsToday.reduce((sum, call) => sum + (call.talk_time || 0), 0) / callsToday.length : 0

    const stats = {
      activeAgents,
      queueCalls: calls.filter(call => call.status === 'ringing').length,
      callsToday: callsToday.length,
      avgTalkTime: Math.floor(avgTalkTime / 60) // minutos
    }

    return { data: stats, error: null }
  }

  return {
    getCalls,
    getCall,
    getDashboardStats
  }
}