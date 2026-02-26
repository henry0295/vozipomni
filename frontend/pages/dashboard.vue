<template>
  <div>
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
      <p class="text-gray-600 mt-2">Bienvenido al panel de control de VozipOmni</p>
    </div>

    <!-- Estadísticas principales -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Agentes Activos</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.activeAgents }}</p>
            <p class="text-xs text-gray-400 mt-1">{{ stats.availableAgents }} disponibles</p>
          </div>
          <UIcon name="i-heroicons-user-group" class="h-12 w-12 text-green-500" />
        </div>
      </UCard>

      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Llamadas en Cola</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.queuedCalls }}</p>
            <p class="text-xs text-gray-400 mt-1">{{ stats.activeCalls }} activas</p>
          </div>
          <UIcon name="i-heroicons-phone" class="h-12 w-12 text-sky-500" />
        </div>
      </UCard>

      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Llamadas Hoy</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.callsToday }}</p>
            <div class="flex gap-2 mt-1">
              <span class="text-xs text-blue-500">{{ stats.inboundToday }} ent.</span>
              <span class="text-xs text-green-500">{{ stats.outboundToday }} sal.</span>
            </div>
          </div>
          <UIcon name="i-heroicons-phone-arrow-up-right" class="h-12 w-12 text-blue-500" />
        </div>
      </UCard>

      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Tasa Respuesta</p>
            <p class="text-3xl font-bold mt-1" :class="stats.answerRate >= 80 ? 'text-green-600' : stats.answerRate >= 60 ? 'text-yellow-600' : 'text-red-600'">
              {{ stats.answerRate }}%
            </p>
            <p class="text-xs text-gray-400 mt-1">T.Prom: {{ formatDuration(stats.avgTalkTime) }}</p>
          </div>
          <UIcon name="i-heroicons-chart-bar" class="h-12 w-12 text-purple-500" />
        </div>
      </UCard>
    </div>

    <!-- Fila extra: contestadas/perdidas/espera -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-gray-500">Contestadas Hoy</p>
            <p class="text-2xl font-bold text-green-600">{{ stats.answeredToday }}</p>
          </div>
          <UIcon name="i-heroicons-check-circle" class="h-10 w-10 text-green-400" />
        </div>
      </UCard>
      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-gray-500">Perdidas Hoy</p>
            <p class="text-2xl font-bold text-red-600">{{ stats.missedToday }}</p>
          </div>
          <UIcon name="i-heroicons-x-circle" class="h-10 w-10 text-red-400" />
        </div>
      </UCard>
      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-gray-500">Espera Promedio</p>
            <p class="text-2xl font-bold text-amber-600">{{ formatDuration(stats.avgWaitTime) }}</p>
          </div>
          <UIcon name="i-heroicons-clock" class="h-10 w-10 text-amber-400" />
        </div>
      </UCard>
    </div>

    <!-- Actividad reciente -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <UCard>
        <template #header>
          <h2 class="text-xl font-semibold text-gray-900">Agentes en Línea</h2>
        </template>
        
        <div v-if="recentAgents.length" class="space-y-3">
          <div v-for="agent in recentAgents" :key="agent.id" class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div class="flex items-center space-x-3">
              <UAvatar :alt="agent.name" size="sm" />
              <div>
                <p class="font-medium text-gray-900">{{ agent.name }}</p>
                <p class="text-sm text-gray-600">{{ agent.extension }}</p>
              </div>
            </div>
            <UBadge :color="agent.status === 'available' ? 'green' : agent.status === 'oncall' ? 'orange' : 'yellow'">
              {{ agent.statusLabel }}
            </UBadge>
          </div>
        </div>
        <div v-else class="text-sm text-gray-500">No hay agentes en linea</div>
      </UCard>

      <UCard>
        <template #header>
          <h2 class="text-xl font-semibold text-gray-900">Llamadas Recientes</h2>
        </template>
        
        <div v-if="recentCalls.length" class="space-y-3">
          <div v-for="call in recentCalls" :key="call.id" class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div class="flex items-center space-x-3">
              <UIcon 
                :name="call.type === 'inbound' ? 'i-heroicons-phone-arrow-down-left' : 'i-heroicons-phone-arrow-up-right'" 
                class="h-8 w-8" 
                :class="call.type === 'inbound' ? 'text-blue-500' : 'text-green-500'" 
              />
              <div>
                <p class="font-medium text-gray-900">{{ call.number }}</p>
                <p class="text-sm text-gray-600">{{ call.duration }} · {{ call.statusLabel }}</p>
              </div>
            </div>
            <UBadge :color="call.type === 'inbound' ? 'blue' : 'green'">
              {{ call.typeLabel }}
            </UBadge>
          </div>
        </div>
        <div v-else class="text-sm text-gray-500">No hay llamadas recientes</div>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth']
})

const stats = reactive({
  activeAgents: 0,
  availableAgents: 0,
  busyAgents: 0,
  queuedCalls: 0,
  activeCalls: 0,
  callsToday: 0,
  answeredToday: 0,
  missedToday: 0,
  inboundToday: 0,
  outboundToday: 0,
  answerRate: 0,
  avgTalkTime: 0,
  avgWaitTime: 0,
  totalTalkTime: 0,
})

const recentAgents = ref<{ id: number; name: string; extension: string; status: string; statusLabel: string }[]>([])
const recentCalls = ref<{ id: number; number: string; duration: string; type: string; typeLabel: string; statusLabel: string }[]>([])

const statusLabels: Record<string, string> = {
  available: 'Disponible',
  busy: 'En llamada',
  oncall: 'En llamada',
  break: 'En pausa',
  wrapup: 'Post-llamada',
  offline: 'Desconectado'
}

const callStatusLabels: Record<string, string> = {
  completed: 'Completada',
  answered: 'Contestada',
  no_answer: 'No contestada',
  busy: 'Ocupado',
  failed: 'Fallida',
  cancelled: 'Cancelada',
  initiated: 'Iniciada',
  ringing: 'Timbrando',
}

const formatDuration = (seconds: number) => {
  if (!seconds || seconds < 0) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const loadDashboard = async () => {
  const { getDashboardStats } = useReports()
  const { getCalls } = useCalls()
  const { getAgents } = useAgents()

  const [dashResult, callsResult, agentsResult] = await Promise.all([
    getDashboardStats(),
    getCalls({ page_size: 5, ordering: '-start_time' }),
    getAgents({ page_size: 10 })
  ])

  if (dashResult.data) {
    Object.assign(stats, dashResult.data)
  }

  if (agentsResult.data) {
    recentAgents.value = agentsResult.data
      .filter(agent => agent.status !== 'offline')
      .map(agent => ({
        id: agent.id,
        name: agent.user_details?.name || agent.agent_id || agent.sip_extension,
        extension: agent.sip_extension,
        status: agent.status,
        statusLabel: statusLabels[agent.status] || agent.status
      }))
  }

  if (callsResult.data) {
    recentCalls.value = callsResult.data.map(call => ({
      id: call.id,
      number: call.direction === 'inbound' ? call.caller_id : call.called_number,
      duration: formatDuration(call.talk_time || call.duration || 0),
      type: call.direction,
      typeLabel: call.direction === 'inbound' ? 'Entrante' : 'Saliente',
      statusLabel: callStatusLabels[call.status] || call.status,
    }))
  }
}

onMounted(() => {
  loadDashboard()

  // Auto-refresh cada 30 segundos
  const interval = setInterval(loadDashboard, 30000)
  onUnmounted(() => clearInterval(interval))
})
</script>
