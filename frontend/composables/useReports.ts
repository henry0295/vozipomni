/**
 * Composable para reportes y KPIs del Contact Center.
 *
 * Endpoints consumidos:
 *   GET /api/reports/kpis/?period=...
 *   GET /api/reports/calls-by-hour/?period=...
 *   GET /api/reports/calls-by-queue/?period=...
 *   GET /api/reports/agent-performance/?period=...
 *   GET /api/reports/call-summary/?period=...
 *   GET /api/reports/dashboard-stats/
 */

export interface KPIs {
  totalCalls: number
  answeredCalls: number
  missedCalls: number
  abandonedCalls: number
  failedCalls: number
  answerRate: number
  abandonRate: number
  avgTalkTime: number
  avgWaitTime: number
  avgHoldTime: number
  avgHandleTime: number
  serviceLevel: number
  slaThreshold: number
  inboundCalls: number
  outboundCalls: number
  totalTalkTime: number
  activeAgents: number
  availableAgents: number
  period: { start: string; end: string }
}

export interface HourlyData {
  hour: number
  label: string
  total: number
  answered: number
  missed: number
  inbound: number
  outbound: number
}

export interface QueueData {
  queueId: number | null
  queueName: string
  total: number
  answered: number
  missed: number
  avgWait: number
  avgTalk: number
}

export interface AgentPerformance {
  agentId: number
  agentName: string
  extension: string
  status: string
  totalCalls: number
  answeredCalls: number
  missedCalls: number
  answerRate: number
  avgTalkTime: number
  avgWaitTime: number
  totalTalkTime: number
  callsToday: number
  talkTimeToday: number
}

export interface DailySummary {
  date: string
  total: number
  answered: number
  missed: number
  inbound: number
  outbound: number
  avgTalkTime: number
  totalTalkTime: number
}

export interface DashboardStats {
  callsToday: number
  answeredToday: number
  missedToday: number
  activeCalls: number
  queuedCalls: number
  inboundToday: number
  outboundToday: number
  answerRate: number
  avgTalkTime: number
  avgWaitTime: number
  totalTalkTime: number
  activeAgents: number
  availableAgents: number
  busyAgents: number
}

export const useReports = () => {
  const { apiFetch } = useApi()

  const buildQuery = (period: string, startDate?: string, endDate?: string) => {
    const q: Record<string, string> = { period }
    if (period === 'custom' && startDate) q.start_date = startDate
    if (period === 'custom' && endDate) q.end_date = endDate
    return q
  }

  const getKPIs = async (period = 'today', startDate?: string, endDate?: string) => {
    const { data, error } = await apiFetch<KPIs>('/reports/kpis/', {
      query: buildQuery(period, startDate, endDate),
    })
    return { data: data.value, error: error.value }
  }

  const getCallsByHour = async (period = 'today', startDate?: string, endDate?: string) => {
    const { data, error } = await apiFetch<HourlyData[]>('/reports/calls-by-hour/', {
      query: buildQuery(period, startDate, endDate),
    })
    return { data: data.value || [], error: error.value }
  }

  const getCallsByQueue = async (period = 'today', startDate?: string, endDate?: string) => {
    const { data, error } = await apiFetch<QueueData[]>('/reports/calls-by-queue/', {
      query: buildQuery(period, startDate, endDate),
    })
    return { data: data.value || [], error: error.value }
  }

  const getAgentPerformance = async (period = 'today', startDate?: string, endDate?: string) => {
    const { data, error } = await apiFetch<AgentPerformance[]>('/reports/agent-performance/', {
      query: buildQuery(period, startDate, endDate),
    })
    return { data: data.value || [], error: error.value }
  }

  const getCallSummary = async (period = 'last7days', startDate?: string, endDate?: string) => {
    const { data, error } = await apiFetch<DailySummary[]>('/reports/call-summary/', {
      query: buildQuery(period, startDate, endDate),
    })
    return { data: data.value || [], error: error.value }
  }

  const getDashboardStats = async () => {
    const { data, error } = await apiFetch<DashboardStats>('/reports/dashboard-stats/')
    return { data: data.value, error: error.value }
  }

  return {
    getKPIs,
    getCallsByHour,
    getCallsByQueue,
    getAgentPerformance,
    getCallSummary,
    getDashboardStats,
  }
}
