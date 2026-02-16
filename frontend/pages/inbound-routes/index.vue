<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Rutas Entrantes (DIDs)</h1>
      <div class="flex gap-2">
        <UButton
          v-if="error"
          icon="i-heroicons-arrow-path"
          @click="loadRoutes"
          :loading="loading"
        >
          Reintentar
        </UButton>
        <UButton
          icon="i-heroicons-plus"
          color="primary"
          @click="openCreateModal"
          :disabled="loading"
        >
          Agregar Ruta
        </UButton>
      </div>
    </div>

    <!-- Estado de carga/error -->
    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle">
      {{ error }}
    </UAlert>

    <UCard v-if="loading" class="flex justify-center items-center py-12">
      <div class="text-center space-y-2">
        <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto" />
        <p class="text-gray-500">Cargando rutas entrantes...</p>
      </div>
    </UCard>

    <!-- Filtros -->
    <UCard v-if="!loading" class="divide-y">
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
import { ref, computed, onMounted } from 'vue'

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

const routes = ref<InboundRoute[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)

const { apiFetch } = useApi()

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
  error.value = null
  try {
    if (editingId.value) {
      const { error: saveError } = await apiFetch(`/telephony/inbound-routes/${editingId.value}/`, {
        method: 'PUT',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar la ruta')
    } else {
      const { error: saveError } = await apiFetch('/telephony/inbound-routes/', {
        method: 'POST',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar la ruta')
    }
    await loadRoutes()
    isModalOpen.value = false
  } catch (err) {
    error.value = 'Error al guardar la ruta'
    console.error('Error saving route:', err)
  } finally {
    isSaving.value = false
  }
}

const deleteRoute = async (id: number) => {
  if (confirm('¿Estás seguro de que deseas eliminar esta ruta?')) {
    try {
      const { error: delError } = await apiFetch(`/telephony/inbound-routes/${id}/`, { method: 'DELETE' })
      if (delError.value) throw new Error('Error al eliminar la ruta')
      await loadRoutes()
    } catch (err) {
      error.value = 'Error al eliminar la ruta'
      console.error('Error deleting route:', err)
    }
  }
}

const loadRoutes = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<InboundRoute[]>('/telephony/inbound-routes/')
  if (fetchError.value) {
    error.value = 'Error al cargar las rutas entrantes'
    console.error('Error loading inbound routes:', fetchError.value)
  } else {
    routes.value = data.value || []
  }
  loading.value = false
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

onMounted(() => loadRoutes())

const getDestinationTypeLabel = (type: string) => {
  return destinationTypes.find(t => t.value === type)?.label || type
}
</script>
