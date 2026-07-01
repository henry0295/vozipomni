<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Extensiones</h1>
      <div class="flex gap-2">
        <UButton
          v-if="error"
          icon="i-heroicons-arrow-path"
          @click="loadExtensions"
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
          Agregar Extensión
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
        <p class="text-gray-500">Cargando extensiones...</p>
      </div>
    </UCard>

    <!-- Filtros -->
    <UCard v-if="!loading" class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por extensión o nombre..."
            icon="i-heroicons-magnifying-glass"
          />
          <USelect
            v-model="extensionFilter"
            :options="[
              { label: 'Todos', value: null },
              { label: 'SIP (Softphone)', value: 'PJSIP' },
              { label: 'WebRTC (Navegador)', value: 'WEBRTC' }
            ]"
            option-attribute="label"
            value-attribute="value"
            placeholder="Filtrar por tipo"
          />
          <USelect
            v-model="statusFilter"
            :options="[
              { label: 'Todos', value: null },
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
              <th class="px-4 py-3 text-left font-semibold">Extensión</th>
              <th class="px-4 py-3 text-left font-semibold">Nombre</th>
              <th class="px-4 py-3 text-left font-semibold">Tipo</th>
              <th class="px-4 py-3 text-left font-semibold">Email</th>
              <th class="px-4 py-3 text-left font-semibold">Buzón</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="ext in filteredExtensions" :key="ext.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3 font-mono font-semibold">{{ ext.extension }}</td>
              <td class="px-4 py-3">{{ ext.name }}</td>
              <td class="px-4 py-3">
                <UBadge color="blue" variant="subtle">{{ ext.extension_type }}</UBadge>
              </td>
              <td class="px-4 py-3 text-xs">{{ ext.email || '-' }}</td>
              <td class="px-4 py-3">
                <UBadge v-if="ext.voicemail_enabled" color="green" variant="subtle">Habilitado</UBadge>
                <span v-else class="text-gray-500">-</span>
              </td>
              <td class="px-4 py-3">
                <UBadge :color="ext.is_active ? 'green' : 'gray'" variant="subtle">
                  {{ ext.is_active ? 'Activa' : 'Inactiva' }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editExtension(ext)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteExtension(ext.id)"
                />
              </td>
            </tr>
            <tr v-if="filteredExtensions.length === 0 && !loading">
              <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                No hay extensiones configuradas
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- ============================== -->
    <!-- MODAL CREAR/EDITAR EXTENSIÓN   -->
    <!-- ============================== -->
    <UModal v-model="isModalOpen" :ui="{ width: 'sm:max-w-4xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">
              {{ editingId ? 'Editar Extensión' : 'Nueva Extensión' }}
            </h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="isModalOpen = false" />
          </div>
        </template>

        <!-- Tabs de secciones -->
        <UTabs :items="extensionTabs" v-model="activeExtensionTab">
          <!-- ===== TAB 1: INFORMACIÓN BÁSICA ===== -->
          <template #basica="{ item }">
            <div class="space-y-5 py-4">
              <!-- Tipo de Extensión -->
              <UFormGroup label="Tipo de Extensión" required help="Selecciona el dispositivo que usarás para conectarte">
                <USelectMenu
                  v-model="form.extension_type"
                  :options="extensionTypeOptions"
                  value-attribute="value"
                  option-attribute="label"
                  @update:model-value="onTypeChange"
                />
              </UFormGroup>

              <!-- Descripción del tipo seleccionado -->
              <UAlert
                :icon="form.extension_type === 'WEBRTC' ? 'i-heroicons-globe-alt' : 'i-heroicons-device-phone-mobile'"
                :color="form.extension_type === 'WEBRTC' ? 'blue' : 'green'"
                variant="subtle"
                :title="form.extension_type === 'WEBRTC' ? 'WebRTC - Llamadas desde el navegador' : 'SIP - Softphone tradicional'"
                :description="form.extension_type === 'WEBRTC' 
                  ? 'RECOMENDADO para agentes que trabajan desde el navegador. Usa WSS (WebSocket Secure) y códecs optimizados (Opus). No requiere configuración de softphone.' 
                  : 'Para aplicaciones SIP como Zoiper, Linphone, X-Lite. Usa UDP/TCP y códecs tradicionales (ulaw, alaw, g722).'"
              />

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Número de Extensión" required help="Ej: 100, 101, 1001">
                  <UInput v-model="form.extension" placeholder="100" />
                </UFormGroup>

                <UFormGroup label="Nombre Completo" required help="Nombre del usuario o agente">
                  <UInput v-model="form.name" placeholder="Juan Pérez" />
                </UFormGroup>
              </div>

              <UFormGroup label="Caller ID" help="Identificación mostrada en llamadas. Formato: Nombre <Número>">
                <UInput v-model="form.callerid" placeholder="Juan Perez <100>" />
              </UFormGroup>

              <div class="flex items-center space-x-4 pt-2">
                <UCheckbox v-model="form.is_active" label="Extensión Activa" />
              </div>
            </div>
          </template>

          <!-- ===== TAB 2: AUTENTICACIÓN ===== -->
          <template #autenticacion="{ item }">
            <div class="space-y-5 py-4">
              <!-- Sección de credenciales -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-key" class="text-blue-500" />
                  <h4 class="font-medium text-gray-800">Credenciales SIP</h4>
                </div>

                <UFormGroup label="Contraseña SIP" required help="Mínimo 8 caracteres. Usa letras, números y símbolos.">
                  <UInput v-model="form.secret" type="password" placeholder="••••••••" />
                  <template #hint>
                    <UButton 
                      size="xs" 
                      color="gray" 
                      variant="ghost"
                      @click="generatePassword"
                    >
                      Generar contraseña segura
                    </UButton>
                  </template>
                </UFormGroup>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Transporte" help="Auto-seleccionado según tipo">
                    <USelectMenu
                      v-model="form.transport"
                      :options="transportOptions"
                      value-attribute="value"
                      option-attribute="label"
                      :disabled="form.extension_type === 'WEBRTC'"
                    />
                  </UFormGroup>

                  <UFormGroup label="Máx. Contactos" help="Dispositivos simultáneos">
                    <UInput v-model.number="form.max_contacts" type="number" min="1" max="5" />
                  </UFormGroup>
                </div>
              </div>

              <!-- Contexto de marcación -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-map" class="text-green-500" />
                  <h4 class="font-medium text-gray-800">Contexto de Marcación</h4>
                </div>

                <UFormGroup label="Contexto" help="Define qué puede marcar esta extensión">
                  <USelectMenu
                    v-model="form.context"
                    :options="contextOptions"
                    value-attribute="value"
                    option-attribute="label"
                  />
                </UFormGroup>

                <UAlert 
                  icon="i-heroicons-information-circle" 
                  color="blue" 
                  variant="subtle"
                  description="from-internal permite llamadas internas y salientes. from-external solo llamadas entrantes. custom requiere dialplan personalizado."
                />
              </div>
            </div>
          </template>

          <!-- ===== TAB 3: CÓDECS Y AVANZADO ===== -->
          <template #avanzado="{ item }">
            <div class="space-y-5 py-4">
              <UFormGroup label="Códecs de Audio" help="Orden de preferencia, separados por coma">
                <UInput v-model="form.codecs" placeholder="ulaw,alaw,g722" />
              </UFormGroup>

              <UAlert 
                icon="i-heroicons-speaker-wave" 
                color="blue" 
                variant="subtle"
                title="Códecs Recomendados"
              >
                <template #description>
                  <ul class="list-disc list-inside text-sm space-y-1">
                    <li><strong>WebRTC:</strong> opus,ulaw,alaw (Opus para mejor calidad)</li>
                    <li><strong>SIP/Softphone:</strong> ulaw,alaw,g722 (compatibilidad máxima)</li>
                    <li><strong>G.722:</strong> HD voice (mayor ancho de banda)</li>
                  </ul>
                </template>
              </UAlert>
            </div>
          </template>

          <!-- ===== TAB 4: BUZÓN DE VOZ ===== -->
          <template #buzon="{ item }">
            <div class="space-y-5 py-4">
              <div class="flex items-center space-x-4">
                <UCheckbox v-model="form.voicemail_enabled" label="Habilitar Buzón de Voz" />
              </div>

              <div v-if="form.voicemail_enabled" class="space-y-4 border border-blue-200 bg-blue-50 rounded-lg p-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-envelope" class="text-blue-600" />
                  <h4 class="font-medium text-blue-800">Configuración del Buzón</h4>
                </div>

                <UFormGroup 
                  label="Email para Notificaciones" 
                  help="Recibirá grabaciones de mensajes de voz"
                  :required="form.voicemail_enabled"
                >
                  <UInput v-model="form.email" type="email" placeholder="usuario@empresa.com" />
                </UFormGroup>

                <UAlert 
                  icon="i-heroicons-information-circle" 
                  color="blue" 
                  variant="subtle"
                  description="Los mensajes de voz se enviarán como archivos adjuntos al email configurado. El usuario puede acceder marcando *97 desde su extensión."
                />
              </div>

              <UAlert 
                v-else
                icon="i-heroicons-no-symbol" 
                color="gray" 
                variant="subtle"
                description="El buzón de voz está deshabilitado. Las llamadas no contestadas seguirán el enrutamiento configurado."
              />
            </div>
          </template>
        </UTabs>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="gray" variant="outline" @click="isModalOpen = false" :disabled="isSaving">
              Cancelar
            </UButton>
            <UButton color="sky" @click="saveExtension" :loading="isSaving">
              {{ editingId ? 'Guardar Cambios' : 'Crear Extensión' }}
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

interface Extension {
  id: number
  extension: string
  name: string
  extension_type: string
  secret: string
  context: string
  transport: string
  callerid: string
  email: string
  voicemail_enabled: boolean
  is_active: boolean
  max_contacts: number
  codecs: string
}

const extensions = ref<Extension[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const extensionFilter = ref<string | null>(null)
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)
const activeExtensionTab = ref(0)

const { apiFetch } = useApi()

// Opciones para tabs del modal
const extensionTabs = [
  { slot: 'basica', label: 'Información Básica', icon: 'i-heroicons-identification' },
  { slot: 'autenticacion', label: 'Autenticación', icon: 'i-heroicons-key' },
  { slot: 'avanzado', label: 'Códecs y Avanzado', icon: 'i-heroicons-cog' },
  { slot: 'buzon', label: 'Buzón de Voz', icon: 'i-heroicons-envelope' }
]

const extensionTypeOptions = [
  { label: 'SIP (Softphone - Zoiper, Linphone, X-Lite)', value: 'PJSIP' },
  { label: 'WebRTC (Navegador - Agentes web)', value: 'WEBRTC' }
]

const transportOptions = [
  { label: 'UDP (Predeterminado)', value: 'transport-udp' },
  { label: 'TCP', value: 'transport-tcp' },
  { label: 'WSS (WebRTC)', value: 'transport-wss' }
]

const contextOptions = [
  { label: 'from-internal (Llamadas internas y salientes)', value: 'from-internal' },
  { label: 'from-external (Solo llamadas entrantes)', value: 'from-external' },
  { label: 'custom (Personalizado)', value: 'custom' }
]

const form = ref({
  extension: '',
  name: '',
  extension_type: 'PJSIP',
  secret: '',
  context: 'from-internal',
  transport: 'transport-udp',
  callerid: '',
  email: '',
  voicemail_enabled: false,
  is_active: true,
  max_contacts: 1,
  codecs: 'ulaw,alaw,g722'
})

// Generar contraseña segura
const generatePassword = () => {
  const length = 12
  const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
  let password = ''
  for (let i = 0; i < length; i++) {
    password += charset.charAt(Math.floor(Math.random() * charset.length))
  }
  form.value.secret = password
}

// Auto-ajustar transport al cambiar tipo de extensión
const onTypeChange = () => {
  if (form.value.extension_type === 'WEBRTC') {
    form.value.transport = 'transport-wss'
    form.value.codecs = 'opus,ulaw,alaw'
  } else {
    form.value.transport = 'transport-udp'
    form.value.codecs = 'ulaw,alaw,g722'
  }
}

const filteredExtensions = computed(() => {
  return extensions.value.filter(ext => {
    const matchesSearch =
      ext.extension.includes(searchQuery.value) ||
      ext.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesType = extensionFilter.value === null || ext.extension_type === extensionFilter.value
    const matchesStatus = statusFilter.value === null || ext.is_active === statusFilter.value
    return matchesSearch && matchesType && matchesStatus
  })
})

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
}

const editExtension = (ext: Extension) => {
  form.value = { ...ext }
  editingId.value = ext.id
  isModalOpen.value = true
}

const loadExtensions = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<any>('/telephony/extensions/')
  if (fetchError.value) {
    error.value = 'Error al cargar las extensiones'
    console.error('Error loading extensions:', fetchError.value)
  } else {
    const raw = data.value
    extensions.value = Array.isArray(raw) ? raw : (raw?.results || [])
  }
  loading.value = false
}

const saveExtension = async () => {
  isSaving.value = true
  error.value = null
  try {
    if (editingId.value) {
      const { error: saveError } = await apiFetch(`/telephony/extensions/${editingId.value}/`, {
        method: 'PUT',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar la extensión')
    } else {
      const { error: saveError } = await apiFetch('/telephony/extensions/', {
        method: 'POST',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar la extensión')
    }
    await loadExtensions()
    isModalOpen.value = false
  } catch (err) {
    error.value = 'Error al guardar la extensión'
    console.error('Error saving extension:', err)
  } finally {
    isSaving.value = false
  }
}

const deleteExtension = async (id: number) => {
  if (confirm('¿Estás seguro de que deseas eliminar esta extensión?')) {
    try {
      const { error: delError } = await apiFetch(`/telephony/extensions/${id}/`, { method: 'DELETE' })
      if (delError.value) throw new Error('Error al eliminar la extensión')
      await loadExtensions()
    } catch (err) {
      error.value = 'Error al eliminar la extensión'
      console.error('Error deleting extension:', err)
    }
  }
}

const resetForm = () => {
  form.value = {
    extension: '',
    name: '',
    extension_type: 'PJSIP',
    secret: '',
    context: 'from-internal',
    transport: 'transport-udp',
    callerid: '',
    email: '',
    voicemail_enabled: false,
    is_active: true,
    max_contacts: 1,
    codecs: 'ulaw,alaw,g722'
  }
  editingId.value = null
}

onMounted(() => loadExtensions())
</script>
