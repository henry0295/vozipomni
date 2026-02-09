<template>
  <div>
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Reportes</h1>
        <p class="text-gray-600 mt-2">Análisis y estadísticas del contact center</p>
      </div>
      <UButton
        icon="i-heroicons-arrow-down-tray"
        size="lg"
        color="gray"
        variant="outline"
      >
        Exportar
      </UButton>
    </div>

    <!-- Filtros de fecha -->
    <UCard class="mb-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <USelectMenu
          v-model="filters.period"
          :options="periodOptions"
          placeholder="Período"
        />
        <UInput
          v-model="filters.startDate"
          type="date"
          placeholder="Fecha inicio"
        />
        <UInput
          v-model="filters.endDate"
          type="date"
          placeholder="Fecha fin"
        />
        <UButton
          block
          @click="applyFilters"
        >
          Aplicar
        </UButton>
      </div>
    </UCard>

    <!-- Métricas principales -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <UCard>
        <div class="text-center">
          <UIcon name="i-heroicons-phone" class="h-12 w-12 text-sky-500 mx-auto mb-2" />
          <p class="text-sm text-gray-600">Total de Llamadas</p>
          <p class="text-4xl font-bold text-gray-900 mt-2">1,234</p>
          <p class="text-sm text-green-600 mt-2">↑ 15% vs período anterior</p>
        </div>
      </UCard>

      <UCard>
        <div class="text-center">
          <UIcon name="i-heroicons-clock" class="h-12 w-12 text-purple-500 mx-auto mb-2" />
          <p class="text-sm text-gray-600">Tiempo Promedio</p>
          <p class="text-4xl font-bold text-gray-900 mt-2">5:42</p>
          <p class="text-sm text-red-600 mt-2">↓ 8% vs período anterior</p>
        </div>
      </UCard>

      <UCard>
        <div class="text-center">
          <UIcon name="i-heroicons-chart-bar" class="h-12 w-12 text-green-500 mx-auto mb-2" />
          <p class="text-sm text-gray-600">Tasa de Respuesta</p>
          <p class="text-4xl font-bold text-gray-900 mt-2">94%</p>
          <p class="text-sm text-green-600 mt-2">↑ 3% vs período anterior</p>
        </div>
      </UCard>
    </div>

    <!-- Gráficos y tablas -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <UCard>
        <template #header>
          <h2 class="text-xl font-semibold text-gray-900">Llamadas por Hora</h2>
        </template>
        <div class="h-64 flex items-center justify-center text-gray-400">
          [Gráfico de llamadas por hora]
        </div>
      </UCard>

      <UCard>
        <template #header>
          <h2 class="text-xl font-semibold text-gray-900">Distribución por Cola</h2>
        </template>
        <div class="h-64 flex items-center justify-center text-gray-400">
          [Gráfico de distribución por cola]
        </div>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth']
})

const filters = reactive({
  period: 'today',
  startDate: '',
  endDate: ''
})

const periodOptions = [
  { label: 'Hoy', value: 'today' },
  { label: 'Ayer', value: 'yesterday' },
  { label: 'Últimos 7 días', value: 'last7days' },
  { label: 'Últimos 30 días', value: 'last30days' },
  { label: 'Este mes', value: 'thismonth' },
  { label: 'Personalizado', value: 'custom' }
]

const applyFilters = () => {
  // TODO: Cargar datos con filtros
  console.log('Aplicando filtros:', filters)
}

// TODO: Cargar datos de reportes desde la API
onMounted(() => {
  // fetchReports()
})
</script>
