<template>
  <div>
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Registro de Llamadas</h1>
        <p class="text-gray-600 mt-2">Historial completo de llamadas del contact center</p>
      </div>
      <UButton
        icon="i-heroicons-arrow-down-tray"
        color="gray"
        variant="outline"
        size="lg"
      >
        Exportar
      </UButton>
    </div>

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle" class="mb-6">
      {{ error }}
    </UAlert>

    <!-- Estadísticas rápidas -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <StatCard
        label="Total Hoy"
        :value="stats.total"
        icon="i-heroicons-phone"
        color="sky"
      />
      <StatCard
        label="Entrantes"
        :value="stats.inbound"
        icon="i-heroicons-phone-arrow-down-left"
        color="green"
      />
      <StatCard
        label="Salientes"
        :value="stats.outbound"
        icon="i-heroicons-phone-arrow-up-right"
        color="blue"
      />
      <StatCard
        label="Perdidas"
        :value="stats.missed"
        icon="i-heroicons-phone-x-mark"
        color="red"
      />
    </div>

    <!-- Filtros -->
    <UCard class="mb-6">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <UInput
          v-model="filters.search"
          icon="i-heroicons-magnifying-glass"
          placeholder="Buscar número..."
        />
        <USelectMenu
          v-model="filters.type"
          :options="typeOptions"
          placeholder="Tipo"
        />
        <USelectMenu
          v-model="filters.status"
          :options="statusOptions"
          placeholder="Estado"
        />
        <UInput
          v-model="filters.date"
          type="date"
          placeholder="Fecha"
        />
        <UButton
          color="gray"
          variant="outline"
          @click="clearFilters"
        >
          Limpiar
        </UButton>
      </div>
    </UCard>

    <!-- Tabla de llamadas -->
    <UCard>
      <UTable
        :rows="calls"
        :columns="columns"
        :loading="loading"
      >
        <template #number-data="{ row }">
          <div class="flex items-center space-x-2">
            <UIcon 
              :name="getCallIcon(row.type)" 
              :class="getCallIconColor(row.type)"
              class="h-5 w-5"
            />
            <div>
              <p class="font-medium text-gray-900">{{ row.number }}</p>
              <p class="text-sm text-gray-600">{{ row.typeLabel }}</p>
            </div>
          </div>
        </template>

        <template #agent-data="{ row }">
          <div v-if="row.agent">
            <p class="text-sm text-gray-900">{{ row.agent }}</p>
            <p class="text-xs text-gray-600">{{ row.queue }}</p>
          </div>
          <span v-else class="text-sm text-gray-500">-</span>
        </template>

        <template #duration-data="{ row }">
          <div class="flex items-center space-x-2">
            <UIcon name="i-heroicons-clock" class="h-4 w-4 text-gray-400" />
            <span class="text-sm text-gray-900">{{ row.duration }}</span>
          </div>
        </template>

        <template #status-data="{ row }">
          <UBadge :color="getStatusColor(row.status)">
            {{ row.statusLabel }}
          </UBadge>
        </template>

        <template #startTime-data="{ row }">
          <span class="text-sm text-gray-600">{{ formatDateTime(row.startTime) }}</span>
        </template>

        <template #actions-data="{ row }">
          <div class="flex gap-2">
            <UButton
              v-if="row.recording"
              icon="i-heroicons-play"
              color="sky"
              variant="ghost"
              size="sm"
              @click="playRecording(row)"
            />
            <UDropdown :items="getActions(row)">
              <UButton
                icon="i-heroicons-ellipsis-vertical"
                color="gray"
                variant="ghost"
                size="sm"
              />
            </UDropdown>
          </div>
        </template>
      </UTable>

      <template #footer>
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-700">
            Mostrando 1 a {{ calls.length }} de {{ totalCalls }} llamadas
          </p>
          <div class="flex gap-2">
            <UButton
              icon="i-heroicons-chevron-left"
              color="gray"
              variant="outline"
              size="sm"
            />
            <UButton
              icon="i-heroicons-chevron-right"
              color="gray"
              variant="outline"
              size="sm"
            />
          </div>
        </div>
      </template>
    </UCard>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth']
})

const loading = ref(false)
const error = ref<string | null>(null)

const stats = reactive({
  total: 0,
  inbound: 0,
  outbound: 0,
  missed: 0
})

const filters = reactive({
  search: '',
  type: null,
  status: null,
  date: ''
})

const typeOptions = [
  { label: 'Entrante', value: 'inbound' },
  { label: 'Saliente', value: 'outbound' },
  { label: 'Interna', value: 'internal' }
]

const statusOptions = [
  { label: 'Contestada', value: 'connected' },
  { label: 'Perdida', value: 'missed' },
  { label: 'Finalizada', value: 'ended' }
]

const columns = [
  { key: 'number', label: 'Número' },
  { key: 'agent', label: 'Agente' },
  { key: 'duration', label: 'Duración' },
  { key: 'status', label: 'Estado' },
  { key: 'startTime', label: 'Fecha y Hora' },
  { key: 'actions', label: '' }
]

const calls = ref<any[]>([])

const totalCalls = ref(0)

const getCallIcon = (type: string) => {
  const icons: Record<string, string> = {
    inbound: 'i-heroicons-phone-arrow-down-left',
    outbound: 'i-heroicons-phone-arrow-up-right',
    internal: 'i-heroicons-phone'
  }
  return icons[type] || 'i-heroicons-phone'
}

const getCallIconColor = (type: string) => {
  const colors: Record<string, string> = {
    inbound: 'text-green-600',
    outbound: 'text-blue-600',
    internal: 'text-purple-600'
  }
  return colors[type] || 'text-gray-600'
}

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    answered: 'green',
    completed: 'blue',
    no_answer: 'red',
    failed: 'red',
    ringing: 'yellow',
    initiated: 'gray'
  }
  return colors[status] || 'gray'
}

const formatDateTime = (dateTime: string) => {
  const date = new Date(dateTime)
  return new Intl.DateTimeFormat('es-CO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

const playRecording = (call: any) => {
  if (call.recording) {
    window.open(call.recording, '_blank')
  }
}

const getActions = (row: any) => [
  [{
    label: 'Ver detalles',
    icon: 'i-heroicons-eye',
    click: () => navigateTo(`/calls/${row.id}`)
  }],
  row.recording ? [{
    label: 'Descargar grabación',
    icon: 'i-heroicons-arrow-down-tray',
    click: () => console.log('Download', row.recording)
  }] : null,
  [{
    label: 'Llamar de nuevo',
    icon: 'i-heroicons-phone',
    click: () => console.log('Call back', row.number)
  }]
].filter(Boolean)

const clearFilters = () => {
  filters.search = ''
  filters.type = null
  filters.status = null
  filters.date = ''
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const loadCalls = async () => {
  loading.value = true
  error.value = null
  const { getCalls } = useCalls()
  const result = await getCalls({ page_size: 50, ordering: '-start_time' })
  if (result.error) {
    error.value = 'Error al cargar llamadas'
    calls.value = []
    totalCalls.value = 0
  } else {
    calls.value = result.data.map(call => ({
      id: call.id,
      number: call.caller_id || call.called_number,
      type: call.direction,
      typeLabel: call.direction === 'inbound' ? 'Entrante' : 'Saliente',
      status: call.status,
      statusLabel: call.status,
      agent: call.agent_name || null,
      queue: call.queue || '-',
      duration: formatDuration(call.talk_time || call.duration || 0),
      startTime: call.start_time,
      recording: call.recording_file || null
    }))
    totalCalls.value = result.total || 0

    stats.total = result.data.length
    stats.inbound = result.data.filter(call => call.direction === 'inbound').length
    stats.outbound = result.data.filter(call => call.direction === 'outbound').length
    stats.missed = result.data.filter(call => call.status === 'no_answer' || call.status === 'failed').length
  }
  loading.value = false
}

onMounted(() => {
  loadCalls()
})
</script>
