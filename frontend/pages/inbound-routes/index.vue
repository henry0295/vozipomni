<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Rutas Entrantes (DIDs)</h1>
      <UButton
        icon="i-heroicons-plus"
        color="primary"
        @click="openCreateModal"
      >
        Agregar Ruta
      </UButton>
    </div>

    <!-- Filtros -->
    <UCard class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por DID o descripción..."
            icon="i-heroicons-magnifying-glass"
          />
          <USelect
            v-model="statusFilter"
            :options="[
              { label: 'Todas', value: null },
              { label: 'Activas', value: true },
              { label: 'Inactivas', value: false }
            ]"
            option-attribute="label"
            value-attribute="value"
            placeholder="Filtrar por estado"
          />
        </div>
      </template>

      <!-- Tabla -->
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th class="px-4 py-3 text-left font-semibold">DID</th>
              <th class="px-4 py-3 text-left font-semibold">Descripción</th>
              <th class="px-4 py-3 text-left font-semibold">Tipo Destino</th>
              <th class="px-4 py-3 text-left font-semibold">Destino</th>
              <th class="px-4 py-3 text-left font-semibold">Prioridad</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="route in filteredRoutes" :key="route.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3 font-mono font-semibold">{{ route.did }}</td>
              <td class="px-4 py-3">{{ route.description }}</td>
              <td class="px-4 py-3">
                <UBadge color="blue" variant="subtle">{{ getDestinationTypeLabel(route.destination_type) }}</UBadge>
              </td>
              <td class="px-4 py-3">{{ route.destination }}</td>
              <td class="px-4 py-3">{{ route.priority }}</td>
              <td class="px-4 py-3">
                <UBadge :color="route.is_active ? 'green' : 'gray'" variant="subtle">
                  {{ route.is_active ? 'Activa' : 'Inactiva' }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editRoute(route)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteRoute(route.id)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- Modal crear/editar -->
    <USlideover v-model="isModalOpen" title="Ruta Entrante" @close="resetForm">
      <div class="p-4 space-y-4">
        <UFormGroup label="DID/Número" help="Número telefónico entrante">
          <UInput v-model="form.did" placeholder="Ej: +573001234567" />
        </UFormGroup>

        <UFormGroup label="Descripción" help="Descripción de la ruta">
          <UInput v-model="form.description" placeholder="Ej: DID principal" />
        </UFormGroup>

        <UFormGroup label="Tipo de Destino">
          <USelect
            v-model="form.destination_type"
            :options="destinationTypes"
            option-attribute="label"
            value-attribute="value"
          />
        </UFormGroup>

        <UFormGroup label="Destino" help="Extensión, cola, IVR, etc.">
          <UInput v-model="form.destination" placeholder="Ej: 100" />
        </UFormGroup>

        <UFormGroup label="Prioridad">
          <UInput v-model.number="form.priority" type="number" min="1" />
        </UFormGroup>

        <UFormGroup label="Condición Horario (Opcional)">
          <UInput v-model="form.time_condition" placeholder="Ej: business_hours" />
        </UFormGroup>

        <UFormGroup>
          <UCheckbox v-model="form.is_active" label="Activada" />
        </UFormGroup>

        <div class="flex gap-2 pt-4">
          <UButton color="primary" @click="saveRoute" :loading="isSaving">
            Guardar
          </UButton>
          <UButton color="gray" @click="isModalOpen = false">
            Cancelar
          </UButton>
        </div>
      </div>
    </USlideover>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface InboundRoute {
  id: number
  did: string
  description: string
  destination_type: string
  destination: string
  priority: number
  time_condition?: string
  is_active: boolean
}

const destinationTypes = [
  { label: 'IVR', value: 'ivr' },
  { label: 'Cola', value: 'queue' },
  { label: 'Extensión', value: 'extension' },
  { label: 'Buzón de Voz', value: 'voicemail' },
  { label: 'Anuncio', value: 'announcement' }
]

const routes = ref<InboundRoute[]>([
  {
    id: 1,
    did: '+573001234567',
    description: 'DID Principal',
    destination_type: 'ivr',
    destination: 'ivr_main',
    priority: 1,
    is_active: true
  },
  {
    id: 2,
    did: '+573001234568',
    description: 'DID Ventas',
    destination_type: 'queue',
    destination: 'sales_queue',
    priority: 2,
    is_active: true
  }
])

const searchQuery = ref('')
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  did: '',
  description: '',
  destination_type: 'queue',
  destination: '',
  priority: 1,
  time_condition: '',
  is_active: true
})

const filteredRoutes = computed(() => {
  return routes.value.filter(route => {
    const matchesSearch =
      route.did.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      route.description.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesStatus = statusFilter.value === null || route.is_active === statusFilter.value
    return matchesSearch && matchesStatus
  })
})

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
}

const editRoute = (route: InboundRoute) => {
  form.value = { ...route }
  editingId.value = route.id
  isModalOpen.value = true
}

const saveRoute = async () => {
  isSaving.value = true
  await new Promise(resolve => setTimeout(resolve, 500))
  
  if (editingId.value) {
    const index = routes.value.findIndex(r => r.id === editingId.value)
    if (index > -1) {
      routes.value[index] = { ...form.value, id: editingId.value } as InboundRoute
    }
  } else {
    const newRoute: InboundRoute = {
      ...form.value,
      id: Math.max(...routes.value.map(r => r.id), 0) + 1
    } as InboundRoute
    routes.value.push(newRoute)
  }
  
  isSaving.value = false
  isModalOpen.value = false
}

const deleteRoute = (id: number) => {
  routes.value = routes.value.filter(r => r.id !== id)
}

const resetForm = () => {
  form.value = {
    did: '',
    description: '',
    destination_type: 'queue',
    destination: '',
    priority: 1,
    time_condition: '',
    is_active: true
  }
  editingId.value = null
}

const getDestinationTypeLabel = (type: string) => {
  return destinationTypes.find(t => t.value === type)?.label || type
}
</script>
