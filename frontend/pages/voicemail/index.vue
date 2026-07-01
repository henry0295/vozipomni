<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Buzones de Voz</h1>
      <div class="flex gap-2">
        <UButton
          v-if="error"
          icon="i-heroicons-arrow-path"
          @click="loadVoicemails"
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
          Crear Buzón
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
        <p class="text-gray-500">Cargando buzones de voz...</p>
      </div>
    </UCard>

    <!-- Filtros -->
    <UCard v-if="!loading" class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por buzón o nombre..."
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
              <th class="px-4 py-3 text-left font-semibold">Buzón</th>
              <th class="px-4 py-3 text-left font-semibold">Nombre</th>
              <th class="px-4 py-3 text-left font-semibold">Email</th>
              <th class="px-4 py-3 text-left font-semibold">Notificaciones</th>
              <th class="px-4 py-3 text-left font-semibold">Mensajes Máx</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="voicemail in filteredVoicemails" :key="voicemail.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3 font-mono font-semibold">{{ voicemail.mailbox }}</td>
              <td class="px-4 py-3">{{ voicemail.name }}</td>
              <td class="px-4 py-3 text-xs">{{ voicemail.email }}</td>
              <td class="px-4 py-3">
                <div class="flex gap-1">
                  <UBadge v-if="voicemail.email_attach" color="green" variant="subtle" size="xs">Adjuntar</UBadge>
                  <UBadge v-if="voicemail.email_delete" color="yellow" variant="subtle" size="xs">Eliminar</UBadge>
                </div>
              </td>
              <td class="px-4 py-3">{{ voicemail.max_messages }}</td>
              <td class="px-4 py-3">
                <UBadge :color="voicemail.is_active ? 'green' : 'gray'" variant="subtle">
                  {{ voicemail.is_active ? 'Activo' : 'Inactivo' }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editVoicemail(voicemail)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteVoicemail(voicemail.id)"
                />
              </td>
            </tr>
            <tr v-if="filteredVoicemails.length === 0 && !loading">
              <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                No hay buzones de voz configurados
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
              {{ editingId ? 'Editar Buzón de Voz' : 'Nuevo Buzón de Voz' }}
            </h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="isModalOpen = false" />
          </div>
        </template>

        <!-- Tabs de secciones -->
        <UTabs :items="formTabs" v-model="activeTab">
          <!-- ===== TAB 1: BÁSICA ===== -->
          <template #basica="{ item }">
            <div class="space-y-5 py-4">
              <UAlert 
                icon="i-heroicons-envelope"
                color="blue"
                variant="subtle"
                title="Información Básica"
                description="Define el número de buzón y los datos del propietario. El email se usará para notificaciones de mensajes."
              />

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Número de Buzón" required help="Número único del buzón">
                  <UInput v-model="form.mailbox" placeholder="Ej: 100" />
                </UFormGroup>

                <UFormGroup label="Nombre del Propietario" required help="Nombre o descripción del buzón">
                  <UInput v-model="form.name" placeholder="Ej: Recepción" />
                </UFormGroup>
              </div>

              <UFormGroup label="Email" required help="Email para notificaciones de nuevos mensajes">
                <UInput v-model="form.email" type="email" placeholder="buzón@example.com" />
              </UFormGroup>

              <UFormGroup label="Contraseña de Acceso" required help="Contraseña para acceder al buzón">
                <UInput v-model="form.password" type="password" placeholder="Contraseña" />
              </UFormGroup>
            </div>
          </template>

          <!-- ===== TAB 2: CONFIGURACIÓN ===== -->
          <template #configuracion="{ item }">
            <div class="space-y-5 py-4">
              <UAlert 
                icon="i-heroicons-cog-6-tooth"
                color="purple"
                variant="subtle"
                title="Configuración de Buzón"
                description="Personaliza el comportamiento del buzón y las notificaciones por email."
              />

              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Capacidad y Almacenamiento</h4>

                <UFormGroup label="Mensajes Máximos" required help="Número máximo de mensajes que puede almacenar">
                  <UInput v-model.number="form.max_messages" type="number" min="1" max="200" />
                </UFormGroup>
              </div>

              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Notificaciones por Email</h4>

                <div class="space-y-3">
                  <div class="flex items-start space-x-3">
                    <UCheckbox v-model="form.email_attach" />
                    <div class="flex-1">
                      <label class="font-medium text-sm">Adjuntar audio a notificaciones de email</label>
                      <p class="text-xs text-gray-500">Los mensajes de voz se enviarán como archivo adjunto en el email</p>
                    </div>
                  </div>

                  <div class="flex items-start space-x-3">
                    <UCheckbox v-model="form.email_delete" />
                    <div class="flex-1">
                      <label class="font-medium text-sm">Eliminar mensaje después de enviar por email</label>
                      <p class="text-xs text-gray-500">El mensaje se eliminará del buzón automáticamente tras enviarse por email</p>
                    </div>
                  </div>
                </div>
              </div>

              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 class="font-medium text-gray-800">Estado</h4>

                <div class="flex items-start space-x-3">
                  <UCheckbox v-model="form.is_active" />
                  <div class="flex-1">
                    <label class="font-medium text-sm">Buzón activo</label>
                    <p class="text-xs text-gray-500">Desactiva el buzón temporalmente sin eliminarlo</p>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </UTabs>

        <template #footer>
          <div class="flex justify-end space-x-2">
            <UButton color="gray" @click="isModalOpen = false">Cancelar</UButton>
            <UButton
              icon="i-heroicons-check"
              @click="saveVoicemail"
              color="sky"
              :loading="isSaving"
            >
              {{ editingId ? 'Actualizar Buzón' : 'Crear Buzón' }}
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

useHead({ title: 'Buzones de Voz' })

interface Voicemail {
  id: number
  mailbox: string
  name: string
  email: string
  password: string
  max_messages: number
  email_attach: boolean
  email_delete: boolean
  is_active: boolean
}

const voicemails = ref<Voicemail[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)
const activeTab = ref(0)

const { apiFetch } = useApi()

const form = ref({
  mailbox: '',
  name: '',
  email: '',
  password: '',
  max_messages: 100,
  email_attach: true,
  email_delete: false,
  is_active: true
})

const formTabs = [
  { label: 'Básica', slot: 'basica', icon: 'i-heroicons-identification' },
  { label: 'Configuración', slot: 'configuracion', icon: 'i-heroicons-cog-6-tooth' }
]

const filteredVoicemails = computed(() => {
  return voicemails.value.filter(vm => {
    const matchesSearch =
      vm.mailbox.includes(searchQuery.value) ||
      vm.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesStatus = statusFilter.value === null || vm.is_active === statusFilter.value
    return matchesSearch && matchesStatus
  })
})

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
}

const editVoicemail = (voicemail: Voicemail) => {
  form.value = { ...voicemail }
  editingId.value = voicemail.id
  isModalOpen.value = true
}

const loadVoicemails = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<any>('/telephony/voicemail/')
  if (fetchError.value) {
    error.value = 'Error al cargar los buzones de voz'
    console.error('Error loading voicemails:', fetchError.value)
  } else {
    const raw = data.value
    voicemails.value = Array.isArray(raw) ? raw : (raw?.results || [])
  }
  loading.value = false
}

const saveVoicemail = async () => {
  isSaving.value = true
  error.value = null
  try {
    if (editingId.value) {
      const { error: saveError } = await apiFetch(`/telephony/voicemail/${editingId.value}/`, {
        method: 'PUT',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar el buzón')
    } else {
      const { error: saveError } = await apiFetch('/telephony/voicemail/', {
        method: 'POST',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar el buzón')
    }
    await loadVoicemails()
    isModalOpen.value = false
  } catch (err) {
    error.value = 'Error al guardar el buzón'
    console.error('Error saving voicemail:', err)
  } finally {
    isSaving.value = false
  }
}

const deleteVoicemail = async (id: number) => {
  if (confirm('¿Estás seguro de que deseas eliminar este buzón de voz?')) {
    try {
      const { error: delError } = await apiFetch(`/telephony/voicemail/${id}/`, { method: 'DELETE' })
      if (delError.value) throw new Error('Error al eliminar el buzón')
      await loadVoicemails()
    } catch (err) {
      error.value = 'Error al eliminar el buzón'
      console.error('Error deleting voicemail:', err)
    }
  }
}

const resetForm = () => {
  form.value = {
    mailbox: '',
    name: '',
    email: '',
    password: '',
    max_messages: 100,
    email_attach: true,
    email_delete: false,
    is_active: true
  }
  editingId.value = null
}

onMounted(() => loadVoicemails())
</script>
