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
          </div>
          <UIcon name="i-heroicons-user-group" class="h-12 w-12 text-green-500" />
        </div>
      </UCard>

      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Llamadas en Cola</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.queuedCalls }}</p>
          </div>
          <UIcon name="i-heroicons-phone" class="h-12 w-12 text-sky-500" />
        </div>
      </UCard>

      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Llamadas Hoy</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.callsToday }}</p>
          </div>
          <UIcon name="i-heroicons-phone-arrow-up-right" class="h-12 w-12 text-blue-500" />
        </div>
      </UCard>

      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Tiempo Promedio</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.avgTime }}</p>
          </div>
          <UIcon name="i-heroicons-clock" class="h-12 w-12 text-purple-500" />
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
            <UBadge :color="agent.status === 'available' ? 'green' : 'yellow'">
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
              <UIcon name="i-heroicons-phone" class="h-8 w-8 text-sky-500" />
              <div>
                <p class="font-medium text-gray-900">{{ call.number }}</p>
                <p class="text-sm text-gray-600">{{ call.duration }}</p>
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
  queuedCalls: 0,
  callsToday: 0,
  avgTime: '0:00'
})

const recentAgents = ref<{ id: number; name: string; extension: string; status: string; statusLabel: string }[]>([])
const recentCalls = ref<{ id: number; number: string; duration: string; type: string; typeLabel: string }[]>([])

const statusLabels: Record<string, string> = {
  available: 'Disponible',
  busy: 'En llamada',
  oncall: 'En llamada',
  break: 'En pausa',
  wrapup: 'Post-llamada',
  offline: 'Desconectado'
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const loadDashboard = async () => {
  const { getDashboardStats, getCalls } = useCalls()
  const { getAgents } = useAgents()

  const [statsResult, callsResult, agentsResult] = await Promise.all([
    getDashboardStats(),
    getCalls({ page_size: 5, ordering: '-start_time' }),
    getAgents({ page_size: 5 })
  ])

  if (statsResult.data) {
    stats.activeAgents = statsResult.data.activeAgents || 0
    stats.queuedCalls = statsResult.data.queueCalls || 0
    stats.callsToday = statsResult.data.callsToday || 0
    stats.avgTime = formatDuration((statsResult.data.avgTalkTime || 0) * 60)
  }

  if (agentsResult.data) {
    recentAgents.value = agentsResult.data.map(agent => ({
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
      number: call.caller_id || call.called_number,
      duration: formatDuration(call.talk_time || call.duration || 0),
      type: call.direction,
      typeLabel: call.direction === 'inbound' ? 'Entrante' : 'Saliente'
    }))
  }
}

onMounted(() => {
  loadDashboard()
})
</script>
