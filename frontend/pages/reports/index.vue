<template>
  <div>
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Reportes</h1>
        <p class="text-gray-600 mt-2">Análisis y estadísticas del contact center</p>
      </div>
      <UButton
        icon="i-heroicons-arrow-path"
        size="lg"
        color="gray"
        variant="outline"
        :loading="loading"
        @click="loadAllData"
      >
        Actualizar
      </UButton>
    </div>

    <!-- Filtros de fecha -->
    <UCard class="mb-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <USelectMenu
          v-model="filters.period"
          :options="periodOptions"
          value-attribute="value"
          option-attribute="label"
          placeholder="Período"
        />
        <UInput
          v-model="filters.startDate"
          type="date"
          placeholder="Fecha inicio"
          :disabled="filters.period !== 'custom'"
        />
        <UInput
          v-model="filters.endDate"
          type="date"
          placeholder="Fecha fin"
          :disabled="filters.period !== 'custom'"
        />
        <UButton
          block
          :loading="loading"
          @click="loadAllData"
        >
          Aplicar
        </UButton>
      </div>
    </UCard>

    <!-- KPIs principales -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">Total Llamadas</p>
          <p class="text-3xl font-bold text-gray-900 mt-1">{{ kpis.totalCalls }}</p>
        </div>
      </UCard>

      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">Contestadas</p>
          <p class="text-3xl font-bold text-green-600 mt-1">{{ kpis.answeredCalls }}</p>
        </div>
      </UCard>

      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">Perdidas</p>
          <p class="text-3xl font-bold text-red-600 mt-1">{{ kpis.missedCalls }}</p>
        </div>
      </UCard>

      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">Tasa Respuesta</p>
          <p class="text-3xl font-bold text-sky-600 mt-1">{{ kpis.answerRate }}%</p>
        </div>
      </UCard>

      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">Tiempo Promedio</p>
          <p class="text-3xl font-bold text-purple-600 mt-1">{{ formatSeconds(kpis.avgTalkTime) }}</p>
        </div>
      </UCard>

      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">Nivel Servicio</p>
          <p class="text-3xl font-bold mt-1" :class="kpis.serviceLevel >= 80 ? 'text-green-600' : kpis.serviceLevel >= 60 ? 'text-yellow-600' : 'text-red-600'">
            {{ kpis.serviceLevel }}%
          </p>
          <p class="text-xs text-gray-400">≤ {{ kpis.slaThreshold }}s</p>
        </div>
      </UCard>
    </div>

    <!-- KPIs secundarios -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-gray-500">Entrantes</p>
            <p class="text-xl font-bold text-blue-600">{{ kpis.inboundCalls }}</p>
          </div>
          <UIcon name="i-heroicons-phone-arrow-down-left" class="h-8 w-8 text-blue-400" />
        </div>
      </UCard>
      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-gray-500">Salientes</p>
            <p class="text-xl font-bold text-green-600">{{ kpis.outboundCalls }}</p>
          </div>
          <UIcon name="i-heroicons-phone-arrow-up-right" class="h-8 w-8 text-green-400" />
        </div>
      </UCard>
      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-gray-500">AHT (Handle Time)</p>
            <p class="text-xl font-bold text-orange-600">{{ formatSeconds(kpis.avgHandleTime) }}</p>
          </div>
          <UIcon name="i-heroicons-clock" class="h-8 w-8 text-orange-400" />
        </div>
      </UCard>
      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-gray-500">Espera Promedio</p>
            <p class="text-xl font-bold text-amber-600">{{ formatSeconds(kpis.avgWaitTime) }}</p>
          </div>
          <UIcon name="i-heroicons-queue-list" class="h-8 w-8 text-amber-400" />
        </div>
      </UCard>
    </div>

    <!-- Gráficos -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <!-- Llamadas por Hora -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold text-gray-900">Llamadas por Hora</h2>
        </template>
        <div v-if="hourlyData.length" class="space-y-1">
          <div v-for="item in hourlyData" :key="item.hour" class="flex items-center gap-2">
            <span class="text-xs text-gray-500 w-12 text-right">{{ item.label }}</span>
            <div class="flex-1 flex items-center gap-1">
              <div 
                class="h-5 bg-green-500 rounded-sm flex items-center justify-end pr-1 transition-all"
                :style="{ width: barWidth(item.answered, maxHourlyTotal) }"
              >
                <span v-if="item.answered > 0" class="text-[10px] text-white font-medium">{{ item.answered }}</span>
              </div>
              <div 
                class="h-5 bg-red-400 rounded-sm flex items-center justify-end pr-1 transition-all"
                :style="{ width: barWidth(item.missed, maxHourlyTotal) }"
              >
                <span v-if="item.missed > 0" class="text-[10px] text-white font-medium">{{ item.missed }}</span>
              </div>
            </div>
            <span class="text-xs font-medium text-gray-700 w-8 text-right">{{ item.total }}</span>
          </div>
          <div class="flex items-center gap-4 mt-3 pt-3 border-t">
            <div class="flex items-center gap-1"><div class="w-3 h-3 bg-green-500 rounded-sm"></div><span class="text-xs text-gray-500">Contestadas</span></div>
            <div class="flex items-center gap-1"><div class="w-3 h-3 bg-red-400 rounded-sm"></div><span class="text-xs text-gray-500">Perdidas</span></div>
          </div>
        </div>
        <div v-else class="h-64 flex items-center justify-center text-gray-400">
          Sin datos para el período seleccionado
        </div>
      </UCard>

      <!-- Distribución por Cola -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold text-gray-900">Distribución por Cola</h2>
        </template>
        <div v-if="queueData.length" class="space-y-4">
          <div v-for="queue in queueData" :key="queue.queueId" class="space-y-1">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-700">{{ queue.queueName }}</span>
              <span class="text-sm text-gray-500">{{ queue.total }} llamadas</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-4 overflow-hidden flex">
              <div 
                class="bg-green-500 h-4 transition-all flex items-center justify-center"
                :style="{ width: `${queue.total > 0 ? (queue.answered / queue.total * 100) : 0}%` }"
              >
                <span v-if="queue.answered > 0" class="text-[10px] text-white font-medium">{{ queue.answered }}</span>
              </div>
              <div 
                class="bg-red-400 h-4 transition-all flex items-center justify-center"
                :style="{ width: `${queue.total > 0 ? (queue.missed / queue.total * 100) : 0}%` }"
              >
                <span v-if="queue.missed > 0" class="text-[10px] text-white font-medium">{{ queue.missed }}</span>
              </div>
            </div>
            <div class="flex gap-4 text-xs text-gray-500">
              <span>Espera prom: {{ formatSeconds(queue.avgWait) }}</span>
              <span>Conversación prom: {{ formatSeconds(queue.avgTalk) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="h-64 flex items-center justify-center text-gray-400">
          Sin datos de colas para el período
        </div>
      </UCard>
    </div>

    <!-- Rendimiento de Agentes -->
    <UCard class="mb-8">
      <template #header>
        <h2 class="text-lg font-semibold text-gray-900">Rendimiento de Agentes</h2>
      </template>
      <div v-if="agentData.length" class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agente</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ext.</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estado</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Contest.</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Perdidas</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">% Resp.</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">T.Prom</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">T.Total</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="agent in agentData" :key="agent.agentId" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ agent.agentName }}</td>
              <td class="px-4 py-3 text-sm text-gray-500">{{ agent.extension }}</td>
              <td class="px-4 py-3 text-center">
                <UBadge 
                  :color="statusColor(agent.status)" 
                  size="xs"
                >
                  {{ statusLabel(agent.status) }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-sm text-right font-medium">{{ agent.totalCalls }}</td>
              <td class="px-4 py-3 text-sm text-right text-green-600">{{ agent.answeredCalls }}</td>
              <td class="px-4 py-3 text-sm text-right text-red-600">{{ agent.missedCalls }}</td>
              <td class="px-4 py-3 text-sm text-right">
                <span :class="agent.answerRate >= 80 ? 'text-green-600' : agent.answerRate >= 60 ? 'text-yellow-600' : 'text-red-600'">
                  {{ agent.answerRate }}%
                </span>
              </td>
              <td class="px-4 py-3 text-sm text-right text-gray-600">{{ formatSeconds(agent.avgTalkTime) }}</td>
              <td class="px-4 py-3 text-sm text-right text-gray-600">{{ formatDuration(agent.totalTalkTime) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="py-8 text-center text-gray-400">
        Sin datos de agentes para el período
      </div>
    </UCard>

    <!-- Resumen Diario (últimos 7 días) -->
    <UCard>
      <template #header>
        <h2 class="text-lg font-semibold text-gray-900">Resumen por Día</h2>
      </template>
      <div v-if="dailyData.length" class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Contest.</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Perdidas</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Entrantes</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Salientes</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">T.Prom</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="day in dailyData" :key="day.date" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-sm font-medium text-gray-900">{{ formatDate(day.date) }}</td>
              <td class="px-4 py-3 text-sm text-right font-medium">{{ day.total }}</td>
              <td class="px-4 py-3 text-sm text-right text-green-600">{{ day.answered }}</td>
              <td class="px-4 py-3 text-sm text-right text-red-600">{{ day.missed }}</td>
              <td class="px-4 py-3 text-sm text-right text-blue-600">{{ day.inbound }}</td>
              <td class="px-4 py-3 text-sm text-right text-indigo-600">{{ day.outbound }}</td>
              <td class="px-4 py-3 text-sm text-right text-gray-600">{{ formatSeconds(day.avgTalkTime) }}</td>
            </tr>
          </tbody>
          <tfoot class="bg-gray-50">
            <tr>
              <td class="px-4 py-3 text-sm font-bold text-gray-900">Total</td>
              <td class="px-4 py-3 text-sm text-right font-bold">{{ dailyTotals.total }}</td>
              <td class="px-4 py-3 text-sm text-right font-bold text-green-600">{{ dailyTotals.answered }}</td>
              <td class="px-4 py-3 text-sm text-right font-bold text-red-600">{{ dailyTotals.missed }}</td>
              <td class="px-4 py-3 text-sm text-right font-bold text-blue-600">{{ dailyTotals.inbound }}</td>
              <td class="px-4 py-3 text-sm text-right font-bold text-indigo-600">{{ dailyTotals.outbound }}</td>
              <td class="px-4 py-3 text-sm text-right font-bold text-gray-600">—</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <div v-else class="py-8 text-center text-gray-400">
        Sin datos diarios disponibles
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import type { KPIs, HourlyData, QueueData, AgentPerformance, DailySummary } from '~/composables/useReports'

definePageMeta({
  middleware: ['auth']
})

const loading = ref(false)

const filters = reactive({
  period: 'today',
  startDate: '',
  endDate: ''
})

const kpis = reactive<KPIs>({
  totalCalls: 0,
  answeredCalls: 0,
  missedCalls: 0,
  abandonedCalls: 0,
  failedCalls: 0,
  answerRate: 0,
  abandonRate: 0,
  avgTalkTime: 0,
  avgWaitTime: 0,
  avgHoldTime: 0,
  avgHandleTime: 0,
  serviceLevel: 0,
  slaThreshold: 20,
  inboundCalls: 0,
  outboundCalls: 0,
  totalTalkTime: 0,
  activeAgents: 0,
  availableAgents: 0,
  period: { start: '', end: '' },
})

const hourlyData = ref<HourlyData[]>([])
const queueData = ref<QueueData[]>([])
const agentData = ref<AgentPerformance[]>([])
const dailyData = ref<DailySummary[]>([])

const periodOptions = [
  { label: 'Hoy', value: 'today' },
  { label: 'Ayer', value: 'yesterday' },
  { label: 'Últimos 7 días', value: 'last7days' },
  { label: 'Últimos 30 días', value: 'last30days' },
  { label: 'Este mes', value: 'thismonth' },
  { label: 'Personalizado', value: 'custom' }
]

// Computed
const maxHourlyTotal = computed(() => {
  return Math.max(...hourlyData.value.map(h => h.total), 1)
})

const dailyTotals = computed(() => {
  return dailyData.value.reduce(
    (acc, d) => ({
      total: acc.total + d.total,
      answered: acc.answered + d.answered,
      missed: acc.missed + d.missed,
      inbound: acc.inbound + d.inbound,
      outbound: acc.outbound + d.outbound,
    }),
    { total: 0, answered: 0, missed: 0, inbound: 0, outbound: 0 }
  )
})

// Helpers
const formatSeconds = (seconds: number) => {
  if (!seconds || seconds < 0) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const formatDuration = (totalSeconds: number) => {
  if (!totalSeconds) return '0h 0m'
  const hours = Math.floor(totalSeconds / 3600)
  const mins = Math.floor((totalSeconds % 3600) / 60)
  return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' })
}

const barWidth = (value: number, max: number) => {
  if (!value || !max) return '0%'
  return `${Math.max((value / max) * 100, 2)}%`
}

const statusColor = (status: string) => {
  const colors: Record<string, string> = {
    available: 'green',
    busy: 'red',
    oncall: 'orange',
    break: 'yellow',
    wrapup: 'purple',
    offline: 'gray',
  }
  return colors[status] || 'gray'
}

const statusLabel = (status: string) => {
  const labels: Record<string, string> = {
    available: 'Disponible',
    busy: 'Ocupado',
    oncall: 'En Llamada',
    break: 'En Pausa',
    wrapup: 'Post-llamada',
    offline: 'Desconectado',
  }
  return labels[status] || status
}

// Cargar datos
const loadAllData = async () => {
  loading.value = true
  const { getKPIs, getCallsByHour, getCallsByQueue, getAgentPerformance, getCallSummary } = useReports()
  const p = filters.period
  const sd = filters.startDate
  const ed = filters.endDate

  try {
    const [kpisResult, hourlyResult, queueResult, agentResult, dailyResult] = await Promise.all([
      getKPIs(p, sd, ed),
      getCallsByHour(p, sd, ed),
      getCallsByQueue(p, sd, ed),
      getAgentPerformance(p, sd, ed),
      getCallSummary(p === 'today' ? 'last7days' : p, sd, ed),
    ])

    if (kpisResult.data) {
      Object.assign(kpis, kpisResult.data)
    }
    hourlyData.value = hourlyResult.data || []
    queueData.value = queueResult.data || []
    agentData.value = agentResult.data || []
    dailyData.value = dailyResult.data || []
  } catch (e) {
    console.error('Error cargando reportes:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAllData()
})
</script>
