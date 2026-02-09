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

const queueOptions = [
  { label: 'Ventas', value: 'sales' },
  { label: 'Soporte', value: 'support' },
  { label: 'Servicio', value: 'service' }
]

const columns = [
  { key: 'name', label: 'Agente' },
  { key: 'extension', label: 'Extensión' },
  { key: 'queue', label: 'Cola' },
  { key: 'status', label: 'Estado' },
  { key: 'callsToday', label: 'Llamadas Hoy' },
  { key: 'avgTime', label: 'Tiempo Promedio' },
  { key: 'actions', label: '' }
]

const agents = ref([
  {
    id: 1,
    name: 'Juan Pérez',
    email: 'juan@example.com',
    extension: '1001',
    queue: 'Ventas',
    status: 'available',
    statusLabel: 'Disponible',
    callsToday: 12,
    avgTime: '4:32'
  },
  {
    id: 2,
    name: 'María García',
    email: 'maria@example.com',
    extension: '1002',
    queue: 'Soporte',
    status: 'busy',
    statusLabel: 'En llamada',
    callsToday: 8,
    avgTime: '6:15'
  }
])

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
    click: () => console.log('Delete', row.id)
  }]
]

const clearFilters = () => {
  filters.search = ''
  filters.status = null
  filters.queue = null
}

// TODO: Cargar agentes desde la API
onMounted(() => {
  // fetchAgents()
})
</script>
