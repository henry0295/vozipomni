<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Condiciones de Horario</h1>
      <UButton
        icon="i-heroicons-plus"
        color="primary"
        @click="openCreateModal"
      >
        Crear Condición
      </UButton>
    </div>

    <!-- Filtros -->
    <UCard class="divide-y">
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
          <h3 class="font-semibold mb-3">Grupos de Horarios</h3>
          <div class="space-y-3 max-h-60 overflow-y-auto">
            <div v-for="(group, index) in form.time_groups" :key="index" class="border rounded p-3 bg-gray-50 dark:bg-gray-800">
              <div class="flex justify-between items-start mb-2">
                <div>
                  <p class="font-semibold text-sm">{{ group.name || `Grupo ${index + 1}` }}</p>
                  <p class="text-xs text-gray-500">{{ group.days }} - {{ group.start_time }} a {{ group.end_time }}</p>
                </div>
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  size="xs"
                  color="red"
                  @click="deleteTimeGroup(index)"
                />
              </div>
            </div>
          </div>
          <div class="mt-3 p-3 border rounded bg-blue-50 dark:bg-blue-900/20">
            <p class="text-sm font-semibold mb-2">Ejemplo: Horario Comercial</p>
            <ul class="text-xs space-y-1">
              <li>• Lunes-Viernes 8:00-18:00</li>
              <li>• Sábado 9:00-14:00</li>
              <li>• Domingo/Festivos: fuera de horario</li>
            </ul>
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
import { ref, computed } from 'vue'

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

const destinationTypes = [
  { label: 'IVR', value: 'ivr' },
  { label: 'Cola', value: 'queue' },
  { label: 'Extensión', value: 'extension' },
  { label: 'Buzón de Voz', value: 'voicemail' },
  { label: 'Anuncio', value: 'announcement' }
]

const conditions = ref<TimeCondition[]>([
  {
    id: 1,
    name: 'Horario Comercial',
    time_groups: [
      { name: 'Lunes-Viernes', days: 'Mon-Fri', start_time: '08:00', end_time: '18:00' },
      { name: 'Sábado', days: 'Sat', start_time: '09:00', end_time: '14:00' }
    ],
    true_destination_type: 'queue',
    true_destination: 'sales-queue',
    false_destination_type: 'voicemail',
    false_destination: '100',
    is_active: true
  }
])

const searchQuery = ref('')
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)

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

const saveCondition = async () => {
  isSaving.value = true
  await new Promise(resolve => setTimeout(resolve, 500))
  
  if (editingId.value) {
    const index = conditions.value.findIndex(c => c.id === editingId.value)
    if (index > -1) {
      conditions.value[index] = { ...form.value, id: editingId.value } as TimeCondition
    }
  } else {
    const newCondition: TimeCondition = {
      ...form.value,
      id: Math.max(...conditions.value.map(c => c.id), 0) + 1
    } as TimeCondition
    conditions.value.push(newCondition)
  }
  
  isSaving.value = false
  isModalOpen.value = false
}

const deleteCondition = (id: number) => {
  conditions.value = conditions.value.filter(c => c.id !== id)
}

const deleteTimeGroup = (index: number) => {
  form.value.time_groups.splice(index, 1)
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
</script>
