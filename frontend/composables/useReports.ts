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
 *   GET /api/reports/agent-session/?period=...
 *   GET /api/reports/queue-detail/?period=...
 */

export interface KPIs {
  totalCalls: number
  answeredCalls: number
  missedCalls: number
  abandonedCalls: number
  failedCalls: number
  voicemailCalls: number
  transferredCalls: number
  answerRate: number
  abandonRate: number
  missedRate: number
  avgTalkTime: number
  avgWaitTime: number
  avgHoldTime: number
  maxWaitTime: number
  avgHandleTime: number
  totalHoldTime: number
  serviceLevel: number
  slaThreshold: number
  inboundCalls: number
  outboundCalls: number
  totalTalkTime: number
  activeAgents: number
  availableAgents: number
  oncallAgents: number
  breakAgents: number
  avgOccupancy: number
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
  transferredCalls: number
  abandonedCalls: number
  answerRate: number
  avgTalkTime: number
  avgWaitTime: number
  avgHoldTime: number
  totalTalkTime: number
  totalHoldTime: number
  callsToday: number
  talkTimeToday: number
  availableTimeToday: number
  breakTimeToday: number
  oncallTimeToday: number
  wrapupTimeToday: number
  sessionTime: number
  occupancy: number
  loggedInAt: string | null
}

export interface DailySummary {
  date: string
  total: number
  answered: number
  missed: number
  abandoned: number
  voicemail: number
  transferred: number
  inbound: number
  outbound: number
  avgTalkTime: number
  avgHoldTime: number
  totalTalkTime: number
}

export interface DashboardStats {
  callsToday: number
  answeredToday: number
  missedToday: number
  abandonedToday: number
  voicemailToday: number
  transferredToday: number
  activeCalls: number
  queuedCalls: number
  inboundToday: number
  outboundToday: number
  answerRate: number
  abandonRate: number
  avgTalkTime: number
  avgWaitTime: number
  avgHoldTime: number
  totalTalkTime: number
  activeAgents: number
  availableAgents: number
  busyAgents: number
  breakAgents: number
  wrapupAgents: number
}

export interface AgentSession {
  agentId: number
  agentName: string
  extension: string
  currentStatus: string
  sessionTime: number
  availableTime: number
  oncallTime: number
  breakTime: number
  wrapupTime: number
  occupancy: number
  loggedInAt: string | null
  timeline: Array<{
    status: string
    start: string
    end: string | null
    duration: number
  }>
}

export interface QueueDetail {
  queueId: number
  queueName: string
  extension: string
  strategy: string
  totalCalls: number
  answeredCalls: number
  abandonedCalls: number
  voicemailCalls: number
  noAnswerCalls: number
  abandonRate: number
  slaPercentage: number
  slaThreshold: number
  avgWaitTime: number
  maxWaitTime: number
  avgTalkTime: number
  avgHoldTime: number
  totalTalkTime: number
  callsWaiting: number
  agentsAvailable: number
  agentsBusy: number
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

  const getAgentSession = async (period = 'today', startDate?: string, endDate?: string) => {
    const { data, error } = await apiFetch<AgentSession[]>('/reports/agent-session/', {
      query: buildQuery(period, startDate, endDate),
    })
    return { data: data.value || [], error: error.value }
  }

  const getQueueDetail = async (period = 'today', startDate?: string, endDate?: string) => {
    const { data, error } = await apiFetch<QueueDetail[]>('/reports/queue-detail/', {
      query: buildQuery(period, startDate, endDate),
    })
    return { data: data.value || [], error: error.value }
  }

  return {
    getKPIs,
    getCallsByHour,
    getCallsByQueue,
    getAgentPerformance,
    getCallSummary,
    getDashboardStats,
    getAgentSession,
    getQueueDetail,
  }
}
