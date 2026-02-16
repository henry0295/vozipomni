<template>
  <div>
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Agentes</h1>
        <p class="text-gray-600 mt-2">Gestión de agentes del contact center</p>
      </div>
      <UButton
        icon="i-heroicons-plus"
        size="lg"
        @click="showCreateModal = true"
      >
        Nuevo Agente
      </UButton>
    </div>

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle" class="mb-6">
      {{ error }}
    </UAlert>

    <!-- Filtros -->
    <UCard class="mb-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <UInput
          v-model="filters.search"
          icon="i-heroicons-magnifying-glass"
          placeholder="Buscar agente..."
        />
        <USelectMenu
          v-model="filters.status"
          :options="statusOptions"
          placeholder="Estado"
        />
        <USelectMenu
          v-model="filters.queue"
          :options="queueOptions"
          placeholder="Cola"
        />
        <UButton
          color="gray"
          variant="outline"
          @click="clearFilters"
        >
          Limpiar filtros
        </UButton>
      </div>
    </UCard>

    <!-- Tabla de agentes -->
    <UCard>
      <UTable
        :rows="agents"
        :columns="columns"
        :loading="loading"
        :empty-state="{ icon: 'i-heroicons-circle-stack-20-solid', label: 'No hay agentes configurados' }"
      >
        <template #name-data="{ row }">
          <div class="flex items-center space-x-3">
            <UAvatar :alt="row.name" size="sm" />
            <div>
              <p class="font-medium text-gray-900">{{ row.name }}</p>
              <p class="text-sm text-gray-600">{{ row.email }}</p>
            </div>
          </div>
        </template>

        <template #status-data="{ row }">
          <UBadge :color="getStatusColor(row.status)">
            {{ row.statusLabel }}
          </UBadge>
        </template>

        <template #actions-data="{ row }">
          <UDropdown :items="getActions(row)">
            <UButton
              icon="i-heroicons-ellipsis-vertical"
              color="gray"
              variant="ghost"
            />
          </UDropdown>
        </template>
      </UTable>
    </UCard>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth']
})

const showCreateModal = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)

const filters = reactive({
  search: '',
  status: null,
  queue: null
})

const statusOptions = [
  { label: 'Disponible', value: 'available' },
  { label: 'En llamada', value: 'busy' },
  { label: 'Descanso', value: 'break' },
  { label: 'Desconectado', value: 'offline' }
]

const queueOptions = []

const columns = [
  { key: 'name', label: 'Agente' },
  { key: 'extension', label: 'Extensión' },
  { key: 'queue', label: 'Cola' },
  { key: 'status', label: 'Estado' },
  { key: 'callsToday', label: 'Llamadas Hoy' },
  { key: 'avgTime', label: 'Tiempo Promedio' },
  { key: 'actions', label: '' }
]

const agents = ref<any[]>([])

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    available: 'green',
    busy: 'yellow',
    break: 'orange',
    offline: 'gray'
  }
  return colors[status] || 'gray'
}

const getActions = (row: any) => [
  [{
    label: 'Ver detalles',
    icon: 'i-heroicons-eye',
    click: () => navigateTo(`/agents/${row.id}`)
  }],
  [{
    label: 'Editar',
    icon: 'i-heroicons-pencil',
    click: () => console.log('Edit', row.id)
  }],
  [{
    label: 'Eliminar',
    icon: 'i-heroicons-trash',
    click: () => deleteAgent(row.id)
  }]
]

const clearFilters = () => {
  filters.search = ''
  filters.status = null
  filters.queue = null
}

const formatAvgTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const loadAgents = async () => {
  loading.value = true
  error.value = null
  const { getAgents } = useAgents()
  const result = await getAgents({ page_size: 200 })
  if (result.error) {
    error.value = 'Error al cargar agentes'
    agents.value = []
  } else {
    agents.value = (result.data || []).map(agent => ({
      id: agent.id,
      name: agent.user_details?.name || agent.agent_id,
      email: agent.user_details?.email || '-',
      extension: agent.sip_extension,
      queue: '-',
      status: agent.status,
      statusLabel: agent.status,
      callsToday: agent.calls_today || 0,
      avgTime: formatAvgTime(agent.talk_time_today || 0)
    }))
  }
  loading.value = false
}

const deleteAgent = async (id: number) => {
  if (!confirm('¿Estás seguro de eliminar este agente?')) return
  const { deleteAgent: deleteAgentApi } = useAgents()
  const result = await deleteAgentApi(id)
  if (!result.error) {
    await loadAgents()
  }
}

onMounted(() => {
  loadAgents()
})
</script>
