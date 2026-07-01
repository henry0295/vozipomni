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
            <tr v-if="filteredRoutes.length === 0 && !loading">
              <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                No hay rutas entrantes configuradas
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- Modal crear/editar -->
    <UModal v-model="isModalOpen" :ui="{ width: 'sm:max-w-4xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">
              {{ editingId ? 'Editar Ruta Entrante' : 'Nueva Ruta Entrante (DID)' }}
            </h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="isModalOpen = false" />
          </div>
        </template>

        <UTabs :items="formTabs" v-model="activeTab">
          <!-- TAB 1: INFORMACIÓN BÁSICA -->
          <template #basica="{ item }">
            <div class="space-y-5 py-4">
              <UAlert
                icon="i-heroicons-information-circle"
                color="blue"
                variant="subtle"
                title="Rutas Entrantes - DIDs"
                description="Configure cómo se rutean las llamadas entrantes según el número marcado (DID). Puede asignar diferentes destinos a cada número."
              />

              <UFormGroup label="Descripción" required help="Nombre descriptivo de esta ruta">
                <UInput v-model="form.description" placeholder="Línea Principal - Ventas" />
              </UFormGroup>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Prioridad" help="Orden de evaluación (menor = primero)">
                  <UInput v-model.number="form.priority" type="number" min="1" />
                </UFormGroup>

                <UFormGroup>
                  <UCheckbox v-model="form.is_active" label="Ruta Activada" />
                </UFormGroup>
              </div>
            </div>
          </template>

          <!-- TAB 2: IDENTIFICACIÓN DID -->
          <template #identificacion="{ item }">
            <div class="space-y-5 py-4">
              <UAlert
                icon="i-heroicons-phone"
                color="purple"
                variant="subtle"
                title="Número DID"
                description="Configure el número telefónico que activará esta ruta. Puede usar patrones como _X. para comodines."
              />

              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Número Telefónico</h4>
                
                <UFormGroup label="DID/Número" required help="Número entrante completo">
                  <UInput v-model="form.did" placeholder="+573001234567" />
                </UFormGroup>
              </div>

              <UAlert
                icon="i-heroicons-light-bulb"
                color="amber"
                variant="subtle"
              >
                <template #description>
                  <ul class="text-sm space-y-1">
                    <li><strong>Formato exacto:</strong> +573001234567 (coincide solo con ese número)</li>
                    <li><strong>Patrón con comodín:</strong> _X. (cualquier número)</li>
                    <li><strong>Prefijo:</strong> _57300XXXXXXX (números que inicien con 57300)</li>
                    <li><strong>Prioridad:</strong> Las coincidencias exactas tienen mayor prioridad que los patrones</li>
                  </ul>
                </template>
              </UAlert>
            </div>
          </template>

          <!-- TAB 3: DESTINO -->
          <template #destino="{ item }">
            <div class="space-y-5 py-4">
              <UAlert
                icon="i-heroicons-arrow-right-circle"
                color="sky"
                variant="subtle"
                title="Configure el Destino"
                description="Defina dónde se enrutarán las llamadas que lleguen a este DID."
              />

              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Destino de la Llamada</h4>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Tipo de Destino" required>
                    <USelect
                      v-model="form.destination_type"
                      :options="destinationTypes"
                      option-attribute="label"
                      value-attribute="value"
                    />
                  </UFormGroup>

                  <UFormGroup label="Destino" required help="Nombre de cola, extensión, IVR, etc.">
                    <UInput v-model="form.destination" placeholder="sales-queue, 100, ivr_main" />
                  </UFormGroup>
                </div>
              </div>

              <div class="border border-blue-200 bg-blue-50 dark:bg-blue-950 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-clock" class="text-blue-600" />
                  <h4 class="font-medium text-blue-800 dark:text-blue-200">Condición de Horario (Opcional)</h4>
                </div>
                
                <UFormGroup label="Condición de Horario" help="Nombre de una condición de horario para ruteo condicional">
                  <UInput v-model="form.time_condition" placeholder="business_hours" />
                </UFormGroup>

                <p class="text-sm text-blue-700 dark:text-blue-300">
                  Si especifica una condición de horario, el destino configurado arriba se usará cuando se cumpla la condición.
                  De lo contrario, se usará el destino alternativo definido en la condición de horario.
                </p>
              </div>

              <UAlert
                icon="i-heroicons-light-bulb"
                color="green"
                variant="subtle"
              >
                <template #description>
                  <ul class="text-sm space-y-1">
                    <li><strong>IVR:</strong> Menú interactivo de voz</li>
                    <li><strong>Cola:</strong> Grupo de agentes para atender llamadas</li>
                    <li><strong>Extensión:</strong> Teléfono directo de un usuario</li>
                    <li><strong>Buzón:</strong> Grabación de mensaje de voz</li>
                    <li><strong>Anuncio:</strong> Reproducción de mensaje grabado</li>
                  </ul>
                </template>
              </UAlert>
            </div>
          </template>
        </UTabs>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="isModalOpen = false">
              Cancelar
            </UButton>
            <UButton color="sky" @click="saveRoute" :loading="isSaving">
              {{ editingId ? 'Guardar Cambios' : 'Crear Ruta' }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })
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

const activeTab = ref(0)

const formTabs = [
  { key: 'basica', label: 'Información Básica', icon: 'i-heroicons-identification' },
  { key: 'identificacion', label: 'Identificación DID', icon: 'i-heroicons-phone' },
  { key: 'destino', label: 'Destino', icon: 'i-heroicons-arrow-right-circle' }
]

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
  const { data, error: fetchError } = await apiFetch<any>('/telephony/inbound-routes/')
  if (fetchError.value) {
    error.value = 'Error al cargar las rutas entrantes'
    console.error('Error loading inbound routes:', fetchError.value)
  } else {
    const raw = data.value
    routes.value = Array.isArray(raw) ? raw : (raw?.results || [])
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
