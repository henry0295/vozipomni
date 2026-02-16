<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-900">Troncales SIP</h1>
      <UButton
        icon="i-heroicons-plus"
        label="Nuevo Troncal"
        color="sky"
        @click="showCreateModal = true"
      />
    </div>

    <!-- Estado y estadísticas -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <StatCard
        title="Total Troncales"
        :value="trunks.length"
        icon="i-heroicons-server"
        color="blue"
      />
      <StatCard
        title="Activos"
        :value="activeTrunks"
        icon="i-heroicons-check-circle"
        color="green"
      />
      <StatCard
        title="Inactivos"
        :value="inactiveTrunks"
        icon="i-heroicons-x-circle"
        color="red"
      />
      <StatCard
        title="En Mantenimiento"
        :value="maintenanceTrunks"
        icon="i-heroicons-wrench-screwdriver"
        color="yellow"
      />
    </div>

    <!-- Tabla de troncales -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">Lista de Troncales</h3>
          <UInput 
            v-model="searchQuery"
            placeholder="Buscar troncal..."
            icon="i-heroicons-magnifying-glass"
            class="w-64"
          />
        </div>
      </template>

      <UTable 
        :rows="filteredTrunks" 
        :columns="columns"
        :loading="loading"
        :empty-state="{ icon: 'i-heroicons-circle-stack-20-solid', label: 'No hay troncales configurados' }"
      >
        <template #name-data="{ row }">
          <div>
            <div class="font-medium">{{ row.name }}</div>
            <div class="text-sm text-gray-500">{{ row.description || '-' }}</div>
          </div>
        </template>

        <template #status-data="{ row }">
          <UBadge 
            :color="getStatusColor(getStatusLabel(row))"
            :label="getStatusLabel(row)"
          />
        </template>

        <template #type-data="{ row }">
          <UBadge 
            :color="row.trunk_type === 'pbx_lan' ? 'blue' : 'purple'"
            :label="trunkTypeLabels[row.trunk_type] || row.trunk_type"
            variant="subtle"
          />
        </template>

        <template #usage-data="{ row }">
          <div class="flex items-center space-x-2">
            <div class="flex-1 bg-gray-200 rounded-full h-2">
              <div 
                class="bg-sky-500 h-2 rounded-full" 
                :style="{ width: `${(row.concurrent_calls / row.max_channels) * 100}%` }"
              ></div>
            </div>
            <span class="text-sm text-gray-600">
              {{ row.concurrent_calls }}/{{ row.max_channels }}
            </span>
          </div>
        </template>

        <template #actions-data="{ row }">
          <div class="flex items-center space-x-2">
            <UButton
              icon="i-heroicons-pencil"
              size="xs"
              color="sky"
              variant="ghost"
              @click="editTrunk(row)"
            />
            <UButton
              :icon="row.status === 'Activo' ? 'i-heroicons-pause' : 'i-heroicons-play'"
              size="xs"
              :color="row.status === 'Activo' ? 'yellow' : 'green'"
              variant="ghost"
              @click="toggleTrunk(row)"
            />
            <UButton
              icon="i-heroicons-trash"
              size="xs"
              color="red"
              variant="ghost"
              @click="deleteTrunk(row)"
            />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Modal para crear/editar troncal -->
    <UModal v-model="showCreateModal">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">
            {{ editingTrunkId ? 'Editar Troncal' : 'Nuevo Troncal' }}
          </h3>
        </template>

        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <UFormGroup label="Nombre del Troncal" required>
              <UInput v-model="trunkForm.name" />
            </UFormGroup>
            
            <UFormGroup label="Proveedor">
              <UInput v-model="trunkForm.provider" />
            </UFormGroup>
            
            <UFormGroup label="Tipo" required>
              <USelect 
                v-model="trunkForm.trunk_type"
                :options="typeOptions"
              />
            </UFormGroup>
            
            <UFormGroup label="Máx. Canales" required>
              <UInput 
                v-model="trunkForm.max_channels" 
                type="number"
                min="1"
              />
            </UFormGroup>
            
            <UFormGroup label="Host/IP" required>
              <UInput v-model="trunkForm.host" />
            </UFormGroup>
            
            <UFormGroup label="Puerto">
              <UInput 
                v-model="trunkForm.port" 
                type="number"
                placeholder="5060"
              />
            </UFormGroup>
            
            <UFormGroup label="Usuario">
              <UInput v-model="trunkForm.username" />
            </UFormGroup>
            
            <UFormGroup label="Contraseña">
              <UInput 
                v-model="trunkForm.password" 
                type="password"
              />
            </UFormGroup>
          </div>
          
          <UFormGroup label="Contexto Asterisk">
            <UInput 
              v-model="trunkForm.context" 
              placeholder="from-trunk"
            />
          </UFormGroup>
        </div>

        <template #footer>
          <div class="flex justify-end space-x-2">
            <UButton 
              color="gray" 
              @click="closeModal"
            >
              Cancelar
            </UButton>
            <UButton
              icon="i-heroicons-check"
              @click="saveTrunk"
              color="primary"
              :loading="saving"
            >
              {{ editingTrunkId ? 'Actualizar' : 'Crear' }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default',
  middleware: 'auth'
})

// Estados reactivos
const loading = ref(false)
const saving = ref(false)
const showCreateModal = ref(false)
const editingTrunkId = ref<number | null>(null)
const searchQuery = ref('')

const { getTrunks, createTrunk, updateTrunk, deleteTrunk: deleteTrunkApi, toggleTrunkStatus } = useTrunks()

const trunks = ref<SipTrunk[]>([])

// Formulario
const trunkForm = reactive({
  name: '',
  provider: '',
  trunk_type: 'nat_provider',
  host: '',
  port: 5060,
  username: '',
  password: '',
  max_channels: 10,
  context: 'from-trunk'
})

// Opciones
const typeOptions = [
  { label: 'Proveedor con NAT', value: 'nat_provider' },
  { label: 'Proveedor sin NAT', value: 'no_nat_provider' },
  { label: 'PBX en LAN', value: 'pbx_lan' },
  { label: 'Corporativa', value: 'corporate' },
  { label: 'Personalizado', value: 'custom' }
]

// Columnas de la tabla
const columns = [
  { key: 'name', label: 'Nombre / Proveedor' },
  { key: 'host', label: 'Host' },
  { key: 'type', label: 'Tipo' },
  { key: 'status', label: 'Estado' },
  { key: 'usage', label: 'Uso' },
  { key: 'actions', label: 'Acciones' }
]

// Computadas
const activeTrunks = computed(() =>
  trunks.value.filter(t => t.is_active).length
)

const inactiveTrunks = computed(() =>
  trunks.value.filter(t => !t.is_active).length
)

const maintenanceTrunks = computed(() => 0)

const filteredTrunks = computed(() => {
  if (!searchQuery.value) return trunks.value

  return trunks.value.filter(trunk =>
    trunk.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    (trunk.description || '').toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// Funciones utilitarias
const trunkTypeLabels: Record<string, string> = {
  nat_provider: 'Proveedor con NAT',
  no_nat_provider: 'Proveedor sin NAT',
  pbx_lan: 'PBX en LAN',
  corporate: 'Corporativa',
  custom: 'Personalizado'
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'Activo': return 'green'
    case 'Inactivo': return 'red'
    default: return 'gray'
  }
}

const getStatusLabel = (trunk: SipTrunk) => {
  if (trunk.status) return trunk.status
  return trunk.is_active ? 'Activo' : 'Inactivo'
}

// Acciones
const editTrunk = (trunk: any) => {
  trunkForm.name = trunk.name
  trunkForm.provider = trunk.description || ''
  trunkForm.trunk_type = trunk.trunk_type || 'nat_provider'
  trunkForm.host = trunk.host
  trunkForm.port = trunk.port
  trunkForm.username = trunk.outbound_auth_username || ''
  trunkForm.password = ''
  trunkForm.max_channels = trunk.max_channels || 10
  trunkForm.context = trunk.context || 'from-trunk'
  editingTrunkId.value = trunk.id
  showCreateModal.value = true
}

const toggleTrunk = async (trunk: SipTrunk) => {
  const result = await toggleTrunkStatus(trunk.id)
  if (!result.error) {
    await loadTrunks()
  }
}

const deleteTrunk = async (trunk: SipTrunk) => {
  if (!confirm('¿Estás seguro de eliminar esta troncal?')) return
  const result = await deleteTrunkApi(trunk.id)
  if (!result.error) {
    await loadTrunks()
  }
}

const saveTrunk = async () => {
  saving.value = true
  const payload = {
    name: trunkForm.name,
    description: trunkForm.provider,
    trunk_type: trunkForm.trunk_type,
    host: trunkForm.host,
    port: trunkForm.port,
    outbound_auth_username: trunkForm.username,
    outbound_auth_password: trunkForm.password,
    context: trunkForm.context,
    max_channels: trunkForm.max_channels,
    protocol: 'udp'
  }

  if (editingTrunkId.value) {
    await updateTrunk(editingTrunkId.value, payload)
  } else {
    await createTrunk(payload)
  }

  await loadTrunks()
  saving.value = false
  closeModal()
}

const closeModal = () => {
  showCreateModal.value = false
  editingTrunkId.value = null
  Object.keys(trunkForm).forEach(key => {
    trunkForm[key] = typeof trunkForm[key] === 'number' ? 0 : ''
  })
  trunkForm.port = 5060
  trunkForm.max_channels = 10
  trunkForm.trunk_type = 'nat_provider'
}

const loadTrunks = async () => {
  loading.value = true
  const result = await getTrunks()
  trunks.value = result.data || []
  loading.value = false
}

onMounted(() => {
  loadTrunks()
})

// Metadata de la página  
useHead({
  title: 'Troncales SIP - VozipOmni'
})
</script>