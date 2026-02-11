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
      >
        <template #name-data="{ row }">
          <div>
            <div class="font-medium">{{ row.name }}</div>
            <div class="text-sm text-gray-500">{{ row.provider }}</div>
          </div>
        </template>

        <template #status-data="{ row }">
          <UBadge 
            :color="getStatusColor(row.status)"
            :label="row.status"
          />
        </template>

        <template #type-data="{ row }">
          <UBadge 
            :color="row.type === 'Entrante' ? 'blue' : 'purple'"
            :label="row.type"
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
              icon="i-heroicons-eye"
              size="xs"
              color="gray"
              variant="ghost"
              @click="viewTrunk(row)"
            />
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
            {{ editingTrunk ? 'Editar Troncal' : 'Nuevo Troncal' }}
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
                v-model="trunkForm.type"
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
              @click="saveTrunk"
              :loading="saving"
            >
              {{ editingTrunk ? 'Actualizar' : 'Crear' }}
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
const editingTrunk = ref(false)
const searchQuery = ref('')

// Datos demo
const trunks = ref([
  {
    id: 1,
    name: 'Tigo-Principal',
    provider: 'Tigo Colombia',
    type: 'Bidireccional',
    status: 'Activo',
    host: '200.21.225.82',
    port: 5060,
    max_channels: 30,
    concurrent_calls: 8,
    context: 'from-trunk-tigo'
  },
  {
    id: 2,
    name: 'Claro-Backup',
    provider: 'Claro Colombia',
    type: 'Saliente',
    status: 'Activo',
    host: '190.85.45.120',
    port: 5060,
    max_channels: 15,
    concurrent_calls: 3,
    context: 'from-trunk-claro'
  },
  {
    id: 3,
    name: 'ETB-Local',
    provider: 'ETB',
    type: 'Entrante',
    status: 'Mantenimiento',
    host: '181.49.35.77',
    port: 5060,
    max_channels: 10,
    concurrent_calls: 0,
    context: 'from-trunk-etb'
  }
])

// Formulario
const trunkForm = reactive({
  name: '',
  provider: '',
  type: 'Saliente',
  host: '',
  port: 5060,
  username: '',
  password: '',
  max_channels: 10,
  context: 'from-trunk'
})

// Opciones
const typeOptions = [
  { label: 'Entrante', value: 'Entrante' },
  { label: 'Saliente', value: 'Saliente' },
  { label: 'Bidireccional', value: 'Bidireccional' }
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
  trunks.value.filter(t => t.status === 'Activo').length
)

const inactiveTrunks = computed(() => 
  trunks.value.filter(t => t.status === 'Inactivo').length  
)

const maintenanceTrunks = computed(() => 
  trunks.value.filter(t => t.status === 'Mantenimiento').length
)

const filteredTrunks = computed(() => {
  if (!searchQuery.value) return trunks.value
  
  return trunks.value.filter(trunk => 
    trunk.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
    trunk.provider.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

// Funciones utilitarias
const getStatusColor = (status: string) => {
  switch (status) {
    case 'Activo': return 'green'
    case 'Inactivo': return 'red'
    case 'Mantenimiento': return 'yellow'
    default: return 'gray'
  }
}

// Acciones
const viewTrunk = (trunk: any) => {
  console.log('Ver detalles:', trunk)
}

const editTrunk = (trunk: any) => {
  Object.assign(trunkForm, trunk)
  editingTrunk.value = true
  showCreateModal.value = true
}

const toggleTrunk = (trunk: any) => {
  trunk.status = trunk.status === 'Activo' ? 'Inactivo' : 'Activo'
}

const deleteTrunk = (trunk: any) => {
  const index = trunks.value.findIndex(t => t.id === trunk.id)
  if (index > -1) {
    trunks.value.splice(index, 1)
  }
}

const saveTrunk = async () => {
  saving.value = true
  
  // Simular guardado
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  if (editingTrunk.value) {
    const index = trunks.value.findIndex(t => t.id === trunkForm.id)
    if (index > -1) {
      trunks.value[index] = { ...trunkForm }
    }
  } else {
    trunks.value.push({
      ...trunkForm,
      id: trunks.value.length + 1,
      status: 'Activo',
      concurrent_calls: 0
    })
  }
  
  saving.value = false
  closeModal()
}

const closeModal = () => {
  showCreateModal.value = false
  editingTrunk.value = false
  Object.keys(trunkForm).forEach(key => {
    trunkForm[key] = typeof trunkForm[key] === 'number' ? 0 : ''
  })
  trunkForm.port = 5060
  trunkForm.max_channels = 10
  trunkForm.type = 'Saliente'
}

// Metadata de la página  
useHead({
  title: 'Troncales SIP - VozipOmni'
})
</script>