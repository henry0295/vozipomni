<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Condiciones de Horario</h1>
      <div class="flex gap-2">
        <UButton
          v-if="error"
          icon="i-heroicons-arrow-path"
          @click="loadConditions"
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
          Crear Condición
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
        <p class="text-gray-500">Cargando condiciones de horario...</p>
      </div>
    </UCard>

    <!-- Filtros -->
    <UCard v-if="!loading" class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por nombre..."
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
              <th class="px-4 py-3 text-left font-semibold">Nombre</th>
              <th class="px-4 py-3 text-left font-semibold">Horarios</th>
              <th class="px-4 py-3 text-left font-semibold">Destino True</th>
              <th class="px-4 py-3 text-left font-semibold">Destino False</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="condition in filteredConditions" :key="condition.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3 font-semibold">{{ condition.name }}</td>
              <td class="px-4 py-3 text-xs">
                <UBadge color="purple" variant="subtle">{{ condition.time_groups.length }} grupos</UBadge>
              </td>
              <td class="px-4 py-3 text-xs">
                <div>
                  <span class="font-semibold">{{ condition.true_destination_type }}</span>
                  <span class="text-gray-500">{{ condition.true_destination }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-xs">
                <div>
                  <span class="font-semibold">{{ condition.false_destination_type }}</span>
                  <span class="text-gray-500">{{ condition.false_destination }}</span>
                </div>
              </td>
              <td class="px-4 py-3">
                <UBadge :color="condition.is_active ? 'green' : 'gray'" variant="subtle">
                  {{ condition.is_active ? 'Activa' : 'Inactiva' }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editCondition(condition)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteCondition(condition.id)"
                />
              </td>
            </tr>
            <tr v-if="filteredConditions.length === 0 && !loading">
              <td colspan="6" class="px-4 py-8 text-center text-gray-500">
                No hay condiciones de horario configuradas
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- Modal crear/editar -->
    <USlideover v-model="isModalOpen" title="Condición de Horario" @close="resetForm">
      <div class="p-4 space-y-4 max-h-[calc(100vh-100px)] overflow-y-auto">
        <UFormGroup label="Nombre">
          <UInput v-model="form.name" placeholder="Ej: Horario Comercial" />
        </UFormGroup>

        <div class="border-t pt-4">
          <h3 class="font-semibold mb-3">Destino si se cumple horario</h3>
          
          <UFormGroup label="Tipo de Destino">
            <USelect
              v-model="form.true_destination_type"
              :options="destinationTypes"
              option-attribute="label"
              value-attribute="value"
            />
          </UFormGroup>

          <UFormGroup label="Destino">
            <UInput v-model="form.true_destination" placeholder="Ej: sales-queue, 100, ivr_main" />
          </UFormGroup>
        </div>

        <div class="border-t pt-4">
          <h3 class="font-semibold mb-3">Destino si NO se cumple horario</h3>
          
          <UFormGroup label="Tipo de Destino">
            <USelect
              v-model="form.false_destination_type"
              :options="destinationTypes"
              option-attribute="label"
              value-attribute="value"
            />
          </UFormGroup>

          <UFormGroup label="Destino">
            <UInput v-model="form.false_destination" placeholder="Ej: voicemail, 200, ivr_after_hours" />
          </UFormGroup>
        </div>

        <div class="border-t pt-4">
          <div class="flex justify-between items-center mb-3">
            <h3 class="font-semibold">Grupos de Horarios</h3>
            <UButton
              icon="i-heroicons-plus"
              size="xs"
              variant="outline"
              @click="addTimeGroup"
            >
              Agregar Grupo
            </UButton>
          </div>
          <div class="space-y-3 max-h-60 overflow-y-auto">
            <div v-for="(group, index) in form.time_groups" :key="index" class="border rounded p-3 bg-gray-50 dark:bg-gray-800">
              <div class="flex justify-between items-start mb-2">
                <span class="font-semibold text-sm">Grupo {{ index + 1 }}</span>
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  size="xs"
                  color="red"
                  @click="deleteTimeGroup(index)"
                />
              </div>
              <div class="space-y-2">
                <UFormGroup label="Nombre" :ui="{ label: { base: 'text-xs' } }">
                  <UInput v-model="group.name" placeholder="Ej: Lunes a Viernes" size="sm" />
                </UFormGroup>
                <UFormGroup label="Días" :ui="{ label: { base: 'text-xs' } }">
                  <USelect
                    v-model="group.days"
                    :options="dayOptions"
                    option-attribute="label"
                    value-attribute="value"
                    size="sm"
                  />
                </UFormGroup>
                <div class="grid grid-cols-2 gap-2">
                  <UFormGroup label="Hora Inicio" :ui="{ label: { base: 'text-xs' } }">
                    <UInput v-model="group.start_time" type="time" size="sm" />
                  </UFormGroup>
                  <UFormGroup label="Hora Fin" :ui="{ label: { base: 'text-xs' } }">
                    <UInput v-model="group.end_time" type="time" size="sm" />
                  </UFormGroup>
                </div>
              </div>
            </div>
            <div v-if="form.time_groups.length === 0" class="text-center text-gray-500 text-sm py-4">
              No hay grupos de horarios. Haz clic en "Agregar Grupo" para crear uno.
            </div>
          </div>
        </div>

        <UFormGroup>
          <UCheckbox v-model="form.is_active" label="Activada" />
        </UFormGroup>

        <div class="flex gap-2 pt-4">
          <UButton color="primary" @click="saveCondition" :loading="isSaving">
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

definePageMeta({
  middleware: ['auth']
})

useHead({ title: 'Condiciones de Horario' })

interface TimeGroup {
  name: string
  days: string
  start_time: string
  end_time: string
}

interface TimeCondition {
  id: number
  name: string
  time_groups: TimeGroup[]
  true_destination_type: string
  true_destination: string
  false_destination_type: string
  false_destination: string
  is_active: boolean
}

const dayOptions = [
  { label: 'Lunes a Viernes', value: 'mon-fri' },
  { label: 'Lunes a Sábado', value: 'mon-sat' },
  { label: 'Todos los días', value: 'mon-sun' },
  { label: 'Lunes', value: 'mon' },
  { label: 'Martes', value: 'tue' },
  { label: 'Miércoles', value: 'wed' },
  { label: 'Jueves', value: 'thu' },
  { label: 'Viernes', value: 'fri' },
  { label: 'Sábado', value: 'sat' },
  { label: 'Domingo', value: 'sun' },
  { label: 'Fines de semana', value: 'sat-sun' }
]

const destinationTypes = [
  { label: 'IVR', value: 'ivr' },
  { label: 'Cola', value: 'queue' },
  { label: 'Extensión', value: 'extension' },
  { label: 'Buzón de Voz', value: 'voicemail' },
  { label: 'Anuncio', value: 'announcement' }
]

const conditions = ref<TimeCondition[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)

const { apiFetch } = useApi()

const form = ref({
  name: '',
  time_groups: [],
  true_destination_type: 'queue',
  true_destination: '',
  false_destination_type: 'voicemail',
  false_destination: '',
  is_active: true
})

const filteredConditions = computed(() => {
  return conditions.value.filter(condition => {
    const matchesSearch = condition.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesStatus = statusFilter.value === null || condition.is_active === statusFilter.value
    return matchesSearch && matchesStatus
  })
})

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
}

const editCondition = (condition: TimeCondition) => {
  form.value = { ...condition, time_groups: condition.time_groups.map(tg => ({ ...tg })) }
  editingId.value = condition.id
  isModalOpen.value = true
}

const loadConditions = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<any>('/telephony/time-conditions/')
  if (fetchError.value) {
    error.value = 'Error al cargar las condiciones de horario'
    console.error('Error loading time conditions:', fetchError.value)
  } else {
    const raw = data.value
    conditions.value = Array.isArray(raw) ? raw : (raw?.results || [])
  }
  loading.value = false
}

const saveCondition = async () => {
  isSaving.value = true
  error.value = null
  try {
    if (editingId.value) {
      const { error: saveError } = await apiFetch(`/telephony/time-conditions/${editingId.value}/`, {
        method: 'PUT',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar la condición')
    } else {
      const { error: saveError } = await apiFetch('/telephony/time-conditions/', {
        method: 'POST',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar la condición')
    }
    await loadConditions()
    isModalOpen.value = false
  } catch (err) {
    error.value = 'Error al guardar la condición'
    console.error('Error saving condition:', err)
  } finally {
    isSaving.value = false
  }
}

const deleteCondition = async (id: number) => {
  if (confirm('¿Estás seguro de que deseas eliminar esta condición?')) {
    try {
      const { error: delError } = await apiFetch(`/telephony/time-conditions/${id}/`, { method: 'DELETE' })
      if (delError.value) throw new Error('Error al eliminar la condición')
      await loadConditions()
    } catch (err) {
      error.value = 'Error al eliminar la condición'
      console.error('Error deleting condition:', err)
    }
  }
}

const deleteTimeGroup = (index: number) => {
  form.value.time_groups.splice(index, 1)
}

const addTimeGroup = () => {
  form.value.time_groups.push({
    name: '',
    days: 'mon-fri',
    start_time: '08:00',
    end_time: '18:00'
  })
}

const resetForm = () => {
  form.value = {
    name: '',
    time_groups: [],
    true_destination_type: 'queue',
    true_destination: '',
    false_destination_type: 'voicemail',
    false_destination: '',
    is_active: true
  }
  editingId.value = null
}

onMounted(() => loadConditions())
</script>
