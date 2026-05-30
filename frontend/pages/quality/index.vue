<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Gestión de Calidad</h1>
        <p class="text-sm text-gray-500 mt-1">Evaluaciones de llamadas y desempeño de agentes</p>
      </div>
      <div class="flex gap-2">
        <USelectMenu
          v-model="filterDays"
          :options="[{label:'7 días',value:7},{label:'15 días',value:15},{label:'30 días',value:30}]"
          value-attribute="value"
          option-attribute="label"
          @change="loadStats"
        />
        <UButton icon="i-heroicons-arrow-path" color="gray" variant="ghost" :loading="loading" @click="loadStats" />
      </div>
    </div>

    <!-- KPI Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <UCard class="text-center">
        <p class="text-3xl font-bold text-blue-600">{{ stats.total_evaluations || 0 }}</p>
        <p class="text-sm text-gray-500 mt-1">Evaluaciones totales</p>
      </UCard>
      <UCard class="text-center">
        <p class="text-3xl font-bold text-green-600">{{ formatScore(stats.average_score) }}</p>
        <p class="text-sm text-gray-500 mt-1">Puntaje promedio</p>
      </UCard>
      <UCard class="text-center">
        <p class="text-3xl font-bold text-purple-600">{{ stats.agents_evaluated || 0 }}</p>
        <p class="text-sm text-gray-500 mt-1">Agentes evaluados</p>
      </UCard>
      <UCard class="text-center">
        <p class="text-3xl font-bold" :class="passRateColor">{{ formatScore(stats.pass_rate) }}%</p>
        <p class="text-sm text-gray-500 mt-1">Tasa de aprobación</p>
      </UCard>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Top agentes -->
      <UCard>
        <template #header>
          <h3 class="font-semibold">Top Agentes por Calidad</h3>
        </template>
        <div v-if="loading" class="text-center py-6">
          <UIcon name="i-heroicons-arrow-path" class="animate-spin w-6 h-6 mx-auto" />
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="(agent, idx) in stats.top_agents || []"
            :key="agent.agent_id"
            class="flex items-center gap-3 p-2 rounded-lg"
            :class="idx === 0 ? 'bg-yellow-50' : idx === 1 ? 'bg-gray-50' : ''"
          >
            <span class="text-lg font-bold text-gray-400 w-6">{{ idx + 1 }}</span>
            <UAvatar :alt="agent.name" size="sm" />
            <div class="flex-1 min-w-0">
              <p class="font-medium text-sm truncate">{{ agent.name }}</p>
              <UProgress
                :value="agent.avg_score"
                :max="100"
                :color="agent.avg_score >= 80 ? 'green' : agent.avg_score >= 60 ? 'yellow' : 'red'"
                size="xs"
              />
            </div>
            <span class="font-semibold text-sm tabular-nums">{{ formatScore(agent.avg_score) }}</span>
          </div>
          <p v-if="!(stats.top_agents?.length)" class="text-center text-gray-400 py-4 text-sm">
            Sin datos de evaluaciones
          </p>
        </div>
      </UCard>

      <!-- Tendencia diaria -->
      <UCard>
        <template #header>
          <h3 class="font-semibold">Tendencia de puntaje diario</h3>
        </template>
        <div v-if="loading" class="text-center py-6">
          <UIcon name="i-heroicons-arrow-path" class="animate-spin w-6 h-6 mx-auto" />
        </div>
        <div v-else-if="!(stats.daily_trend?.length)" class="text-center text-gray-400 py-8 text-sm">
          Sin datos para el período
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="day in (stats.daily_trend || [])"
            :key="day.date"
            class="flex items-center gap-3"
          >
            <span class="text-xs text-gray-500 w-24 shrink-0">{{ formatDay(day.date) }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
              <div
                class="h-full rounded-full transition-all"
                :class="day.avg_score >= 80 ? 'bg-green-500' : day.avg_score >= 60 ? 'bg-yellow-400' : 'bg-red-400'"
                :style="{ width: day.avg_score + '%' }"
              />
            </div>
            <span class="text-xs font-semibold w-10 text-right">{{ formatScore(day.avg_score) }}</span>
            <span class="text-xs text-gray-400 w-12 text-right">{{ day.count }} eval</span>
          </div>
        </div>
      </UCard>
    </div>

    <!-- Distribución por categoría -->
    <UCard v-if="stats.category_breakdown?.length">
      <template #header>
        <h3 class="font-semibold">Puntaje por categoría</h3>
      </template>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div
          v-for="cat in stats.category_breakdown"
          :key="cat.category"
          class="text-center p-4 rounded-lg bg-gray-50"
        >
          <p class="text-2xl font-bold" :class="scoreColor(cat.avg_score)">{{ formatScore(cat.avg_score) }}</p>
          <p class="text-sm text-gray-600 mt-1 capitalize">{{ cat.category }}</p>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const stats = ref<any>({})
const loading = ref(false)
const filterDays = ref(30)

const authHeaders = () => ({ Authorization: 'Bearer ' + localStorage.getItem('auth_token') })

const loadStats = async () => {
  loading.value = true
  try {
    const data = await $fetch(`/api/cc/quality-stats/?days=${filterDays.value}`, { headers: authHeaders() })
    stats.value = data
  } catch { stats.value = {} }
  finally { loading.value = false }
}

const formatScore = (v: any) => {
  if (v === undefined || v === null) return '—'
  return Number(v).toFixed(1)
}

const passRateColor = computed(() => {
  const v = stats.value.pass_rate || 0
  return v >= 80 ? 'text-green-600' : v >= 60 ? 'text-yellow-600' : 'text-red-600'
})

const scoreColor = (v: number) => {
  if (v >= 80) return 'text-green-600'
  if (v >= 60) return 'text-yellow-600'
  return 'text-red-600'
}

const formatDay = (iso: string) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' })
}

onMounted(loadStats)
</script>
