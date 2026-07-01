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
    <UModal v-model="isModalOpen" :ui="{ width: 'sm:max-w-5xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">
              {{ editingId ? 'Editar IVR' : 'Nuevo IVR - Menú Interactivo' }}
            </h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="isModalOpen = false" />
          </div>
        </template>

        <UTabs :items="formTabs" v-model="activeTab">
          <!-- TAB 1: INFORMACIÓN BÁSICA -->
          <template #basica>
            <div class="space-y-5 py-4">
              <UAlert
                icon="i-heroicons-information-circle"
                color="blue"
                variant="subtle"
                title="IVR - Menú de Voz Interactivo"
                description="Configure un menú telefónico interactivo que permite a los llamantes seleccionar opciones mediante el teclado DTMF."
              />

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Nombre" required help="Identificador único del IVR">
                  <UInput v-model="form.name" placeholder="IVR Principal" />
                </UFormGroup>

                <UFormGroup label="Extensión" required help="Número de extensión del IVR">
                  <UInput v-model="form.extension" placeholder="100" />
                </UFormGroup>
              </div>
            </div>
          </template>

          <!-- TAB 2: MENSAJES -->
          <template #mensajes>
            <div class="space-y-5 py-4">
              <UAlert
                icon="i-heroicons-speaker-wave"
                color="purple"
                variant="subtle"
                title="Mensajes de Audio"
                description="Configure los mensajes que se reproducirán al llamante en diferentes situaciones."
              />

              <UFormGroup label="Mensaje de Bienvenida" required help="Se reproduce al entrar al IVR">
                <UTextarea 
                  v-model="form.welcome_message" 
                  placeholder="Bienvenido a nuestro centro de contacto. Para ventas presione 1, para soporte presione 2..."
                  :rows="3"
                />
              </UFormGroup>

              <UFormGroup label="Spoken (Audio adicional)" help="Playback opcional antes del menú principal. Ej: custom/ivr-spoken-principal">
                <UInput v-model="form.spoken" placeholder="custom/ivr-spoken-principal" />
              </UFormGroup>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Mensaje - Opción Inválida" help="Se reproduce cuando presionan una opción incorrecta">
                  <UInput v-model="form.invalid_message" placeholder="Opción no válida, intente nuevamente" />
                </UFormGroup>

                <UFormGroup label="Mensaje - Timeout" help="Se reproduce cuando no presionan ninguna opción">
                  <UInput v-model="form.timeout_message" placeholder="Se agotó el tiempo de respuesta" />
                </UFormGroup>
              </div>
            </div>
          </template>

          <!-- TAB 3: OPCIONES DE MENÚ -->
          <template #opciones>
            <div class="space-y-5 py-4">
              <UAlert
                icon="i-heroicons-list-bullet"
                color="amber"
                variant="subtle"
                title="Opciones del Menú DTMF"
                description="Configure las teclas y sus destinos. Ejemplo: 1 → Cola de Ventas, 2 → Cola de Soporte, 0 → Operadora."
              />

              <div class="border border-gray-200 rounded-lg p-4">
                <div class="flex justify-between items-center mb-4">
                  <h4 class="font-medium text-gray-800">Opciones Configuradas</h4>
                  <UButton
                    variant="soft"
                    icon="i-heroicons-plus"
                    size="sm"
                    @click="addMenuOption"
                  >
                    Agregar Opción
                  </UButton>
                </div>
                
                <div class="space-y-3 max-h-96 overflow-y-auto">
                  <div v-for="(key) in menuOptionKeys" :key="key" class="border rounded p-3 bg-gray-50 dark:bg-gray-800 space-y-3">
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

                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <UFormGroup label="Tipo Destino" required>
                        <USelectMenu
                          :model-value="getMenuOptionType(key)"
                          :options="menuDestinationTypes"
                          value-attribute="value"
                          option-attribute="label"
                          @update:model-value="(value) => updateMenuOptionField(key, 'type', String(value))"
                        />
                      </UFormGroup>

                      <UFormGroup label="Destino" required class="md:col-span-2">
                        <USelectMenu
                          v-if="getDestinationOptionsByType(getMenuOptionType(key)).length"
                          :model-value="getMenuOption(key).destination"
                          :options="getDestinationOptionsByType(getMenuOptionType(key))"
                          value-attribute="value"
                          option-attribute="label"
                          searchable
                          placeholder="Seleccione destino"
                          @update:model-value="(value) => updateMenuOptionField(key, 'destination', String(value))"
                        />
                        <UInput
                          v-else
                          :model-value="getMenuOption(key).destination"
                          placeholder="Destino manual"
                          @update:model-value="(value) => updateMenuOptionField(key, 'destination', String(value))"
                        />
                      </UFormGroup>
                    </div>

                    <UFormGroup label="Spoken de la opción (opcional)" help="Texto o nombre corto para referencia operativa">
                      <UInput
                        :model-value="getMenuOption(key).spoken"
                        placeholder="Ej: Ventas"
                        @update:model-value="(value) => updateMenuOptionField(key, 'spoken', String(value))"
                      />
                    </UFormGroup>
                  </div>
                  <div v-if="menuOptionKeys.length === 0" class="text-center text-gray-500 text-sm py-8">
                    No hay opciones configuradas. Haz clic en "Agregar Opción" para crear una.
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- TAB 4: CONFIGURACIÓN -->
          <template #configuracion>
            <div class="space-y-5 py-4">
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Parámetros de Tiempo y Reintentos</h4>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Timeout (segundos)" help="Tiempo máximo de espera por una opción">
                    <UInput v-model.number="form.timeout" type="number" min="1" max="30" />
                  </UFormGroup>

                  <UFormGroup label="Intentos Máximos" help="Número de intentos antes de colgar o transferir">
                    <UInput v-model.number="form.max_attempts" type="number" min="1" max="5" />
                  </UFormGroup>
                </div>
              </div>

              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Estado</h4>
                <UCheckbox v-model="form.is_active" label="IVR Activado" />
              </div>

              <UAlert
                icon="i-heroicons-light-bulb"
                color="sky"
                variant="subtle"
              >
                <template #description>
                  <ul class="text-sm space-y-1">
                    <li><strong>Timeout:</strong> Tiempo que el sistema espera antes de repetir el mensaje</li>
                    <li><strong>Intentos:</strong> Después de alcanzar el máximo, se puede transferir a operadora o colgar</li>
                    <li><strong>Spoken:</strong> Puede usar un audio adicional para guiar mejor al cliente antes de capturar opciones</li>
                    <li><strong>Destinos válidos:</strong> Cola, Extensión, IVR, Buzón, Anuncio, Destino Personalizado</li>
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
            <UButton color="sky" @click="saveIVR" :loading="isSaving">
              {{ editingId ? 'Guardar Cambios' : 'Crear IVR' }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

definePageMeta({
  middleware: ['auth']
})

useHead({ title: 'IVR - Menús Interactivos' })

interface IVR {
  id: number
  name: string
  extension: string
  welcome_message: string
  spoken: string
  invalid_message: string
  timeout_message: string
  timeout: number
  max_attempts: number
  menu_options: Record<string, any>
  is_active: boolean
}

type MenuOptionType = 'queue' | 'extension' | 'ivr' | 'voicemail' | 'announcement' | 'custom_destination'

const ivrs = ref<IVR[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)
const queueOptions = ref<{ label: string; value: string }[]>([])
const extensionOptions = ref<{ label: string; value: string }[]>([])
const ivrOptions = ref<{ label: string; value: string }[]>([])
const voicemailOptions = ref<{ label: string; value: string }[]>([])
const customDestinationOptions = ref<{ label: string; value: string }[]>([])

const { apiFetch } = useApi()

const activeTab = ref(0)

const formTabs = [
  { slot: 'basica', label: 'Información Básica', icon: 'i-heroicons-identification' },
  { slot: 'mensajes', label: 'Mensajes', icon: 'i-heroicons-chat-bubble-left-right' },
  { slot: 'opciones', label: 'Opciones de Menú', icon: 'i-heroicons-list-bullet' },
  { slot: 'configuracion', label: 'Configuración', icon: 'i-heroicons-cog-6-tooth' }
]

const form = ref({
  name: '',
  extension: '',
  welcome_message: '',
  spoken: '',
  invalid_message: 'Opción no válida, intente nuevamente',
  timeout_message: 'Se agotó el tiempo',
  timeout: 5,
  max_attempts: 3,
  menu_options: {} as Record<string, any>,
  is_active: true
})

const menuDestinationTypes = [
  { label: 'Cola', value: 'queue' },
  { label: 'Extensión', value: 'extension' },
  { label: 'IVR', value: 'ivr' },
  { label: 'Buzón de Voz', value: 'voicemail' },
  { label: 'Anuncio', value: 'announcement' },
  { label: 'Destino Personalizado', value: 'custom_destination' },
]

const menuOptionKeys = computed(() => Object.keys(form.value.menu_options).sort())

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
  loadDestinationCatalogs()
  isModalOpen.value = true
}

const editIVR = (ivr: IVR) => {
  form.value = {
    ...ivr,
    spoken: ivr.spoken || '',
    menu_options: normalizeMenuOptions(ivr.menu_options),
  }
  editingId.value = ivr.id
  loadDestinationCatalogs()
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
  const payload = {
    ...form.value,
    menu_options: normalizeMenuOptions(form.value.menu_options),
  }
  try {
    if (editingId.value) {
      const { error: saveError } = await apiFetch(`/telephony/ivr/${editingId.value}/`, {
        method: 'PUT',
        body: payload
      })
      if (saveError.value) throw new Error('Error al guardar el IVR')
    } else {
      const { error: saveError } = await apiFetch('/telephony/ivr/', {
        method: 'POST',
        body: payload
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
    spoken: '',
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
  const keys = Object.keys(form.value.menu_options).map(k => Number(k)).filter(Number.isFinite)
  const nextKey = String((keys.length ? Math.max(...keys) : 0) + 1)
  form.value.menu_options[nextKey] = {
    type: 'extension',
    destination: '',
    spoken: '',
  }
}

const deleteMenuOption = (key: string) => {
  delete form.value.menu_options[key]
}

const normalizeMenuOptions = (options: Record<string, any> | undefined) => {
  const normalized: Record<string, any> = {}
  const source = options || {}

  Object.entries(source).forEach(([digit, option]) => {
    if (typeof option === 'string') {
      normalized[digit] = {
        type: 'extension',
        destination: option,
        spoken: '',
      }
      return
    }

    if (option && typeof option === 'object') {
      normalized[digit] = {
        type: option.type || 'extension',
        destination: option.destination || '',
        spoken: option.spoken || '',
      }
      return
    }

    normalized[digit] = {
      type: 'extension',
      destination: '',
      spoken: '',
    }
  })

  return normalized
}

const getMenuOption = (digit: string) => {
  const option = form.value.menu_options[digit]
  if (!option || typeof option !== 'object') {
    form.value.menu_options[digit] = { type: 'extension', destination: '', spoken: '' }
  }
  return form.value.menu_options[digit]
}

const getMenuOptionType = (digit: string): MenuOptionType => {
  return getMenuOption(digit).type || 'extension'
}

const updateMenuOptionField = (digit: string, field: 'type' | 'destination' | 'spoken', value: string) => {
  const option = getMenuOption(digit)
  option[field] = value
  if (field === 'type') {
    option.destination = ''
  }
}

const getDestinationOptionsByType = (type: string) => {
  switch (type) {
    case 'queue':
      return queueOptions.value
    case 'extension':
      return extensionOptions.value
    case 'ivr':
      return ivrOptions.value.filter(item => item.value !== form.value.extension)
    case 'voicemail':
      return voicemailOptions.value
    case 'custom_destination':
      return customDestinationOptions.value
    case 'announcement':
      return [
        { label: 'beep', value: 'beep' },
        { label: 'demo-congrats', value: 'demo-congrats' },
        { label: 'custom/ivr-bienvenida', value: 'custom/ivr-bienvenida' },
      ]
    default:
      return []
  }
}

const loadDestinationCatalogs = async () => {
  const [ivrRes, queueRes, extRes, vmRes, customRes] = await Promise.all([
    apiFetch<any>('/telephony/ivr/'),
    apiFetch<any>('/queues/'),
    apiFetch<any>('/telephony/extensions/'),
    apiFetch<any>('/telephony/voicemail/'),
    apiFetch<any>('/telephony/custom-destinations/'),
  ])

  const ivrList = Array.isArray(ivrRes.data.value) ? ivrRes.data.value : (ivrRes.data.value?.results || [])
  const queueList = Array.isArray(queueRes.data.value) ? queueRes.data.value : (queueRes.data.value?.results || [])
  const extList = Array.isArray(extRes.data.value) ? extRes.data.value : (extRes.data.value?.results || [])
  const vmList = Array.isArray(vmRes.data.value) ? vmRes.data.value : (vmRes.data.value?.results || [])
  const customList = Array.isArray(customRes.data.value) ? customRes.data.value : (customRes.data.value?.results || [])

  ivrOptions.value = ivrList.map((item: any) => ({ label: `${item.name} (${item.extension})`, value: item.extension }))
  queueOptions.value = queueList.map((item: any) => ({ label: `${item.name} (${item.extension || 'sin ext'})`, value: item.name }))
  extensionOptions.value = extList.map((item: any) => ({ label: `${item.extension} - ${item.name}`, value: item.extension }))
  voicemailOptions.value = vmList.map((item: any) => ({ label: `${item.mailbox} - ${item.name}`, value: item.mailbox }))
  customDestinationOptions.value = customList.map((item: any) => ({
    label: `${item.name} (${item.context},${item.extension},${item.priority})`,
    value: item.name,
  }))
}

onMounted(async () => {
  await Promise.all([loadIVRs(), loadDestinationCatalogs()])
})
</script>
