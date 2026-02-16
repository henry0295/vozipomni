<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">IVR - Menús Interactivos</h1>
      <div class="flex gap-2">
        <UButton
          v-if="error"
          icon="i-heroicons-arrow-path"
          @click="loadIVRs"
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
          Crear IVR
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
        <p class="text-gray-500">Cargando IVRs...</p>
      </div>
    </UCard>

    <!-- Filtros -->
    <UCard v-if="!loading" class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por nombre o extensión..."
            icon="i-heroicons-magnifying-glass"
          />
          <USelect
            v-model="statusFilter"
            :options="[
              { label: 'Todos', value: null },
              { label: 'Activos', value: true },
              { label: 'Inactivos', value: false }
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
              <th class="px-4 py-3 text-left font-semibold">Extensión</th>
              <th class="px-4 py-3 text-left font-semibold">Mensaje de Bienvenida</th>
              <th class="px-4 py-3 text-left font-semibold">Opciones</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="ivr in filteredIVRs" :key="ivr.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3 font-semibold">{{ ivr.name }}</td>
              <td class="px-4 py-3 font-mono">{{ ivr.extension }}</td>
              <td class="px-4 py-3 text-xs truncate">{{ ivr.welcome_message }}</td>
              <td class="px-4 py-3 text-center">
                <UBadge color="purple" variant="subtle">{{ Object.keys(ivr.menu_options).length }} opciones</UBadge>
              </td>
              <td class="px-4 py-3">
                <UBadge :color="ivr.is_active ? 'green' : 'gray'" variant="subtle">
                  {{ ivr.is_active ? 'Activo' : 'Inactivo' }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editIVR(ivr)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteIVR(ivr.id)"
                />
              </td>
            </tr>
            <tr v-if="filteredIVRs.length === 0 && !loading">
              <td colspan="6" class="px-4 py-8 text-center text-gray-500">
                No hay IVRs configurados
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- Modal crear/editar -->
    <USlideover v-model="isModalOpen" title="Configurar IVR" @close="resetForm">
      <div class="p-4 space-y-4">
        <UFormGroup label="Nombre">
          <UInput v-model="form.name" placeholder="Ej: IVR Principal" />
        </UFormGroup>

        <UFormGroup label="Extensión">
          <UInput v-model="form.extension" placeholder="Ej: 100" />
        </UFormGroup>

        <UFormGroup label="Mensaje de Bienvenida">
          <UTextarea 
            v-model="form.welcome_message" 
            placeholder="Ej: Bienvenido a nuestro centro de contacto"
            :rows="3"
          />
        </UFormGroup>

        <UFormGroup label="Mensaje - Opción Inválida">
          <UInput v-model="form.invalid_message" placeholder="Opción no válida, intente nuevamente" />
        </UFormGroup>

        <UFormGroup label="Mensaje - Timeout">
          <UInput v-model="form.timeout_message" placeholder="Se agotó el tiempo de respuesta" />
        </UFormGroup>

        <UFormGroup label="Timeout (segundos)">
          <UInput v-model.number="form.timeout" type="number" min="1" max="30" />
        </UFormGroup>

        <UFormGroup label="Intentos Máximos">
          <UInput v-model.number="form.max_attempts" type="number" min="1" max="5" />
        </UFormGroup>

        <div class="border-t pt-4">
          <h3 class="font-semibold mb-3">Opciones del Menú</h3>
          <div class="space-y-3 max-h-80 overflow-y-auto">
            <div v-for="(key) in Object.keys(form.menu_options)" :key="key" class="border rounded p-3 bg-gray-50 dark:bg-gray-800">
              <div class="flex justify-between items-center mb-2">
                <span class="font-semibold">Tecla {{ key }}</span>
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  size="xs"
                  color="red"
                  @click="deleteMenuOption(key)"
                />
              </div>
              <UInput
                v-model="form.menu_options[key]"
                placeholder="Destino (cola, extensión, IVR, etc.)"
                size="sm"
              />
            </div>
          </div>
          <UButton
            variant="soft"
            icon="i-heroicons-plus"
            class="mt-3 w-full"
            @click="addMenuOption"
          >
            Agregar Opción
          </UButton>
        </div>

        <UFormGroup>
          <UCheckbox v-model="form.is_active" label="Activado" />
        </UFormGroup>

        <div class="flex gap-2 pt-4">
          <UButton color="primary" @click="saveIVR" :loading="isSaving">
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

interface IVR {
  id: number
  name: string
  extension: string
  welcome_message: string
  invalid_message: string
  timeout_message: string
  timeout: number
  max_attempts: number
  menu_options: Record<string, string>
  is_active: boolean
}

const ivrs = ref<IVR[]>([])
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
  extension: '',
  welcome_message: '',
  invalid_message: 'Opción no válida, intente nuevamente',
  timeout_message: 'Se agotó el tiempo',
  timeout: 5,
  max_attempts: 3,
  menu_options: {},
  is_active: true
})

const filteredIVRs = computed(() => {
  return ivrs.value.filter(ivr => {
    const matchesSearch =
      ivr.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      ivr.extension.includes(searchQuery.value)
    const matchesStatus = statusFilter.value === null || ivr.is_active === statusFilter.value
    return matchesSearch && matchesStatus
  })
})

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
}

const editIVR = (ivr: IVR) => {
  form.value = { ...ivr, menu_options: { ...ivr.menu_options } }
  editingId.value = ivr.id
  isModalOpen.value = true
}

const loadIVRs = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<any>('/telephony/ivr/')
  if (fetchError.value) {
    error.value = 'Error al cargar los IVR'
    console.error('Error loading IVRs:', fetchError.value)
  } else {
    const raw = data.value
    ivrs.value = Array.isArray(raw) ? raw : (raw?.results || [])
  }
  loading.value = false
}

const saveIVR = async () => {
  isSaving.value = true
  error.value = null
  try {
    if (editingId.value) {
      const { error: saveError } = await apiFetch(`/telephony/ivr/${editingId.value}/`, {
        method: 'PUT',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar el IVR')
    } else {
      const { error: saveError } = await apiFetch('/telephony/ivr/', {
        method: 'POST',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar el IVR')
    }
    await loadIVRs()
    isModalOpen.value = false
  } catch (err) {
    error.value = 'Error al guardar el IVR'
    console.error('Error saving IVR:', err)
  } finally {
    isSaving.value = false
  }
}

const deleteIVR = async (id: number) => {
  if (confirm('¿Estás seguro de que deseas eliminar este IVR?')) {
    try {
      const { error: delError } = await apiFetch(`/telephony/ivr/${id}/`, { method: 'DELETE' })
      if (delError.value) throw new Error('Error al eliminar el IVR')
      await loadIVRs()
    } catch (err) {
      error.value = 'Error al eliminar el IVR'
      console.error('Error deleting IVR:', err)
    }
  }
}

const resetForm = () => {
  form.value = {
    name: '',
    extension: '',
    welcome_message: '',
    invalid_message: 'Opción no válida, intente nuevamente',
    timeout_message: 'Se agotó el tiempo',
    timeout: 5,
    max_attempts: 3,
    menu_options: {},
    is_active: true
  }
  editingId.value = null
}

const addMenuOption = () => {
  const nextKey = String(Object.keys(form.value.menu_options).length + 1)
  form.value.menu_options[nextKey] = ''
}

const deleteMenuOption = (key: string) => {
  delete form.value.menu_options[key]
}

onMounted(() => loadIVRs())
</script>
