<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Agentes</h1>
      <div class="flex gap-2">
        <UButton
          v-if="error"
          icon="i-heroicons-arrow-path"
          @click="loadAgents"
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
          Nuevo Agente
        </UButton>
      </div>
    </div>

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle">
      {{ error }}
    </UAlert>

    <!-- Filtros -->
    <UCard v-if="!loading" class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            icon="i-heroicons-magnifying-glass"
            placeholder="Buscar agente..."
          />
          <USelect
            v-model="statusFilter"
            :options="[
              { label: 'Todos', value: '' },
              { label: 'Disponible', value: 'available' },
              { label: 'En llamada', value: 'busy' },
              { label: 'Descanso', value: 'break' },
              { label: 'Desconectado', value: 'offline' }
            ]"
            option-attribute="label"
            value-attribute="value"
            placeholder="Estado"
          />
        </div>
      </template>

      <UCard v-if="loading" class="flex justify-center items-center py-12">
        <div class="text-center space-y-2">
          <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto" />
          <p class="text-gray-500">Cargando agentes...</p>
        </div>
      </UCard>

      <!-- Tabla -->
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th class="px-4 py-3 text-left font-semibold">Agente</th>
              <th class="px-4 py-3 text-left font-semibold">ID Agente</th>
              <th class="px-4 py-3 text-left font-semibold">Extensión SIP</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-left font-semibold">Llamadas Hoy</th>
              <th class="px-4 py-3 text-left font-semibold">WebRTC</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="agent in filteredAgents" :key="agent.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3">
                <div class="flex items-center space-x-3">
                  <UAvatar :alt="agent.name" size="sm" />
                  <div>
                    <p class="font-medium">{{ agent.name }}</p>
                    <p class="text-xs text-gray-500">{{ agent.email }}</p>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 font-mono">{{ agent.agent_id }}</td>
              <td class="px-4 py-3 font-mono">{{ agent.sip_extension }}</td>
              <td class="px-4 py-3">
                <UBadge :color="getStatusColor(agent.status)" variant="subtle">
                  {{ getStatusLabel(agent.status) }}
                </UBadge>
              </td>
              <td class="px-4 py-3">{{ agent.calls_today || 0 }}</td>
              <td class="px-4 py-3">
                <UBadge v-if="agent.webrtc_enabled" color="green" variant="subtle">Sí</UBadge>
                <span v-else class="text-gray-500">No</span>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editAgent(agent)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteAgent(agent.id)"
                />
              </td>
            </tr>
            <tr v-if="filteredAgents.length === 0 && !loading">
              <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                No hay agentes configurados
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- Modal crear/editar -->
    <USlideover v-model="isModalOpen" :title="editingId ? 'Editar Agente' : 'Nuevo Agente'" @close="resetForm">
      <div class="flex flex-col h-full">
        <div class="flex-1 overflow-y-auto p-4 space-y-6 pb-24">
        
        <!-- Alert de error dentro del modal -->
        <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle" :close-button="{ icon: 'i-heroicons-x-mark-20-solid', color: 'red', variant: 'link' }" @close="error = null">
          <template #title>
            Error al guardar
          </template>
          <template #description>
            {{ error }}
          </template>
        </UAlert>

        <!-- Información del Usuario -->
        <div class="space-y-4">
          <h3 class="text-lg font-semibold border-b pb-2">Información del Usuario</h3>
          
          <UFormGroup label="Nombre" required help="Nombre completo del agente">
            <UInput v-model="form.first_name" placeholder="Ej: Juan" />
          </UFormGroup>

          <UFormGroup label="Apellido" required>
            <UInput v-model="form.last_name" placeholder="Ej: Pérez" />
          </UFormGroup>

          <UFormGroup label="Email" required>
            <UInput v-model="form.email" type="email" placeholder="agente@ejemplo.com" />
          </UFormGroup>

          <UFormGroup label="Usuario" required help="Nombre de usuario para inicio de sesión">
            <UInput v-model="form.username" placeholder="Ej: jperez" />
          </UFormGroup>

          <UFormGroup label="Contraseña" :required="!editingId" help="Dejar vacío para mantener contraseña actual">
            <UInput v-model="form.password" type="password" placeholder="Mínimo 8 caracteres" />
          </UFormGroup>
        </div>

        <!-- Información del Agente -->
        <div class="space-y-4">
          <h3 class="text-lg font-semibold border-b pb-2">Configuración de Agente</h3>
          
          <UFormGroup label="ID de Agente" required :help="!editingId ? 'Auto-generado (editable)' : 'Identificador único del agente'">
            <div class="flex gap-2">
              <div class="flex-1 relative">
                <UInput 
                  v-model="form.agent_id" 
                  placeholder="Ej: AGT001"
                  @input="onAgentIdChange"
                  :disabled="editingId !== null"
                />
                <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none gap-2">
                  <span v-if="agentIdStatus === 'checking' && !editingId" class="text-xs text-gray-500">
                    <UIcon name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
                  </span>
                  <span v-else-if="agentIdStatus === 'available' && !editingId" class="text-xs text-green-600 font-medium flex items-center gap-1">
                    <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
                    <span class="hidden sm:inline">OK</span>
                  </span>
                  <span v-else-if="agentIdStatus === 'unavailable' && !editingId" class="text-xs text-red-600 font-medium flex items-center gap-1">
                    <UIcon name="i-heroicons-x-circle" class="w-4 h-4" />
                    <span class="hidden sm:inline">En uso</span>
                  </span>
                </div>
              </div>
              <UButton 
                v-if="!editingId"
                icon="i-heroicons-arrow-path"
                size="sm"
                color="gray"
                variant="outline"
                @click="regenerateAgentId"
                title="Regenerar ID"
              />
            </div>
          </UFormGroup>

          <UFormGroup label="Extensión SIP" required :help="!editingId ? 'Auto-generada (editable)' : 'Número de extensión telefónica'">
            <div class="flex gap-2">
              <div class="flex-1 relative">
                <UInput 
                  v-model="form.sip_extension" 
                  placeholder="Ej: 100" 
                  type="text"
                  @input="onExtensionChange"
                  :disabled="editingId !== null"
                />
                <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none gap-2">
                  <span v-if="extensionStatus === 'checking' && !editingId" class="text-xs text-gray-500">
                    <UIcon name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" />
                  </span>
                  <span v-else-if="extensionStatus === 'available' && !editingId" class="text-xs text-green-600 font-medium flex items-center gap-1">
                    <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
                    <span class="hidden sm:inline">OK</span>
                  </span>
                  <span v-else-if="extensionStatus === 'unavailable' && !editingId" class="text-xs text-red-600 font-medium flex items-center gap-1">
                    <UIcon name="i-heroicons-x-circle" class="w-4 h-4" />
                    <span class="hidden sm:inline">En uso</span>
                  </span>
                </div>
              </div>
              <UButton 
                v-if="!editingId"
                icon="i-heroicons-arrow-path"
                size="sm"
                color="gray"
                variant="outline"
                @click="regenerateExtension"
                title="Regenerar extensión"
              />
            </div>
          </UFormGroup>

          <UFormGroup label="Contraseña SIP" :required="!editingId" help="Contraseña para autenticación SIP/WebRTC">
            <UInput v-model="form.sip_password" type="password" placeholder="Contraseña segura SIP" />
          </UFormGroup>

          <UFormGroup label="Máx. Llamadas Simultáneas" help="Número máximo de llamadas que puede manejar">
            <UInput v-model.number="form.max_concurrent_calls" type="number" min="1" max="10" />
          </UFormGroup>

          <div class="space-y-2">
            <UCheckbox v-model="form.webrtc_enabled" label="Habilitar WebRTC" />
            <p class="text-xs text-gray-500 ml-6">Permite llamadas desde el navegador web</p>
          </div>

          <div class="space-y-2">
            <UCheckbox v-model="form.auto_answer" label="Auto-respuesta" />
            <p class="text-xs text-gray-500 ml-6">Contesta llamadas automáticamente</p>
          </div>

          <div class="space-y-2">
            <UCheckbox v-model="form.recording_enabled" label="Grabación de llamadas" />
            <p class="text-xs text-gray-500 ml-6">Graba todas las llamadas del agente</p>
          </div>
        </div>
        </div>

        <div class="flex flex-col gap-2 p-4 border-t bg-white dark:bg-gray-900">
          <UAlert 
            v-if="!isFormValid && !editingId" 
            color="amber" 
            icon="i-heroicons-exclamation-triangle"
            :ui="{ description: 'text-xs' }"
          >
            <template #description>
              Completa todos los campos requeridos: {{ missingFields }}
            </template>
          </UAlert>
          
          <div class="flex gap-2">
            <UButton 
              color="primary" 
              @click="saveAgent" 
              :loading="isSaving"
              :disabled="!isFormValid"
              class="flex-1"
            >
              {{ editingId ? 'Actualizar' : 'Crear Agente' }}
            </UButton>
            <UButton color="gray" @click="isModalOpen = false" class="flex-1">
              Cancelar
            </UButton>
          </div>
        </div>
      </div>
    </USlideover>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

definePageMeta({
  middleware: ['auth']
})

useHead({ title: 'Agentes' })

interface AgentRow {
  id: number
  agent_id: string
  name: string
  email: string
  sip_extension: string
  status: string
  calls_today: number
  webrtc_enabled: boolean
}

const agents = ref<AgentRow[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const statusFilter = ref('')
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  // Usuario
  username: '',
  password: '',
  first_name: '',
  last_name: '',
  email: '',
  // Agente
  agent_id: '',
  sip_extension: '',
  sip_password: '',
  max_concurrent_calls: 1,
  webrtc_enabled: true,
  auto_answer: false,
  recording_enabled: true
})

// Validación en tiempo real
const agentIdStatus = ref<'idle' | 'checking' | 'available' | 'unavailable'>('idle')
const extensionStatus = ref<'idle' | 'checking' | 'available' | 'unavailable'>('idle')
const checkingTimeout = ref<any>(null)

const isFormValid = computed(() => {
  if (editingId.value) {
    // En edición, solo verificar campos básicos de agente
    return form.value.agent_id && form.value.sip_extension
  }
  // En creación, todos los campos de usuario son requeridos
  const hasRequiredFields = form.value.username &&
    form.value.password &&
    form.value.first_name &&
    form.value.last_name &&
    form.value.email &&
    form.value.agent_id &&
    form.value.sip_extension &&
    form.value.sip_password
  
  // Verificar que no haya campos no disponibles
  const idsAvailable = agentIdStatus.value !== 'unavailable' && extensionStatus.value !== 'unavailable'
  
  return hasRequiredFields && idsAvailable
})

const missingFields = computed(() => {
  if (editingId.value) return ''
  
  const missing = []
  if (!form.value.first_name) missing.push('Nombre')
  if (!form.value.last_name) missing.push('Apellido')
  if (!form.value.email) missing.push('Email')
  if (!form.value.username) missing.push('Usuario')
  if (!form.value.password) missing.push('Contraseña')
  if (!form.value.agent_id) missing.push('ID de Agente')
  if (!form.value.sip_extension) missing.push('Extensión SIP')
  if (!form.value.sip_password) missing.push('Contraseña SIP')
  
  if (agentIdStatus.value === 'unavailable') missing.push('ID de Agente (ya en uso)')
  if (extensionStatus.value === 'unavailable') missing.push('Extensión SIP (ya en uso)')
  
  return missing.join(', ')
})

const filteredAgents = computed(() => {
  return agents.value.filter(agent => {
    const matchesSearch =
      agent.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      agent.agent_id.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      agent.sip_extension.includes(searchQuery.value)
    const matchesStatus = !statusFilter.value || agent.status === statusFilter.value
    return matchesSearch && matchesStatus
  })
})

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    available: 'green',
    busy: 'yellow',
    break: 'orange',
    offline: 'gray'
  }
  return colors[status] || 'gray'
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    available: 'Disponible',
    busy: 'En llamada',
    break: 'Descanso',
    offline: 'Desconectado'
  }
  return labels[status] || status
}

// Auto-generar siguiente ID y extensión disponibles
const loadNextAvailable = async () => {
  const { getNextAvailable } = useAgents()
  const result = await getNextAvailable()
  
  if (result.data && !editingId.value) {
    form.value.agent_id = result.data.agent_id
    form.value.sip_extension = result.data.sip_extension
    agentIdStatus.value = 'available'
    extensionStatus.value = 'available'
  }
}

// Regenerar ID de agente
const regenerateAgentId = async () => {
  const { getNextAvailable } = useAgents()
  const result = await getNextAvailable()
  
  if (result.data) {
    form.value.agent_id = result.data.agent_id
    agentIdStatus.value = 'available'
  }
}

// Regenerar extensión SIP
const regenerateExtension = async () => {
  const { getNextAvailable } = useAgents()
  const result = await getNextAvailable()
  
  if (result.data) {
    form.value.sip_extension = result.data.sip_extension
    extensionStatus.value = 'available'
  }
}

// Validar disponibilidad de agent_id
const checkAgentIdAvailability = async (agentId: string) => {
  if (!agentId || editingId.value) {
    agentIdStatus.value = 'idle'
    return
  }
  
  agentIdStatus.value = 'checking'
  const { checkAvailability } = useAgents()
  const result = await checkAvailability({ agent_id: agentId })
  
  if (result.data) {
    agentIdStatus.value = result.data.agent_id_available ? 'available' : 'unavailable'
  } else {
    agentIdStatus.value = 'idle'
  }
}

// Validar disponibilidad de extensión
const checkExtensionAvailability = async (extension: string) => {
  if (!extension || editingId.value) {
    extensionStatus.value = 'idle'
    return
  }
  
  extensionStatus.value = 'checking'
  const { checkAvailability } = useAgents()
  const result = await checkAvailability({ sip_extension: extension })
  
  if (result.data) {
    extensionStatus.value = result.data.sip_extension_available ? 'available' : 'unavailable'
  } else {
    extensionStatus.value = 'idle'
  }
}

// Validación con debounce
const onAgentIdChange = () => {
  if (checkingTimeout.value) {
    clearTimeout(checkingTimeout.value)
  }
  
  checkingTimeout.value = setTimeout(() => {
    checkAgentIdAvailability(form.value.agent_id)
  }, 500)
}

const onExtensionChange = () => {
  if (checkingTimeout.value) {
    clearTimeout(checkingTimeout.value)
  }
  
  checkingTimeout.value = setTimeout(() => {
    checkExtensionAvailability(form.value.sip_extension)
  }, 500)
}

const openCreateModal = async () => {
  resetForm()
  error.value = null
  await loadNextAvailable()
  isModalOpen.value = true
  
  // Scroll al inicio del modal después de abrirlo
  setTimeout(() => {
    const modalContent = document.querySelector('.flex-1.overflow-y-auto')
    if (modalContent) {
      modalContent.scrollTop = 0
    }
  }, 100)
  
  // Debug: mostrar estado del formulario en consola
  console.log('📋 Formulario de creación abierto')
  console.log('📝 Valores iniciales:', form.value)
  console.log('✅ Formulario válido:', isFormValid.value)
  console.log('📌 Campos faltantes:', missingFields.value)
}

const editAgent = (agent: AgentRow) => {
  form.value = {
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    email: agent.email || '',
    agent_id: agent.agent_id,
    sip_extension: agent.sip_extension,
    sip_password: '',
    max_concurrent_calls: 1,
    webrtc_enabled: agent.webrtc_enabled,
    auto_answer: false,
    recording_enabled: true
  }
  editingId.value = agent.id
  isModalOpen.value = true
}

const loadAgents = async () => {
  loading.value = true
  error.value = null
  const { getAgents } = useAgents()
  const result = await getAgents({ page_size: 200 })
  if (result.error) {
    error.value = 'Error al cargar agentes'
    agents.value = []
  } else {
    agents.value = (result.data || []).map((agent: any) => ({
      id: agent.id,
      agent_id: agent.agent_id || '',
      name: agent.user_details?.name || agent.agent_id || '-',
      email: agent.user_details?.email || '-',
      sip_extension: agent.sip_extension || '',
      status: agent.status || 'offline',
      calls_today: agent.calls_today || 0,
      webrtc_enabled: agent.webrtc_enabled || false
    }))
  }
  loading.value = false
}

const saveAgent = async () => {
  isSaving.value = true
  error.value = null
  
  try {
    const { createAgent, updateAgent } = useAgents()
    const toast = useToast()
    
    // Validación adicional
    if (!editingId.value) {
      if (form.value.password && form.value.password.length < 8) {
        error.value = 'La contraseña debe tener al menos 8 caracteres'
        isSaving.value = false
        return
      }
      if (!form.value.sip_password || form.value.sip_password.length < 6) {
        error.value = 'La contraseña SIP debe tener al menos 6 caracteres'
        isSaving.value = false
        return
      }
    }
    
    let result
    if (editingId.value) {
      // Al actualizar, solo enviar campos que cambien
      const updateData: any = {
        agent_id: form.value.agent_id,
        sip_extension: form.value.sip_extension,
        max_concurrent_calls: form.value.max_concurrent_calls,
        webrtc_enabled: form.value.webrtc_enabled,
        auto_answer: form.value.auto_answer,
        recording_enabled: form.value.recording_enabled
      }
      
      // Solo incluir contraseñas si se proporcionaron
      if (form.value.password) {
        updateData.password = form.value.password
      }
      if (form.value.sip_password) {
        updateData.sip_password = form.value.sip_password
      }
      if (form.value.first_name) {
        updateData.first_name = form.value.first_name
      }
      if (form.value.last_name) {
        updateData.last_name = form.value.last_name
      }
      if (form.value.email) {
        updateData.email = form.value.email
      }
      
      result = await updateAgent(editingId.value, updateData)
      
      if (result.error) {
        // Procesar error del servidor
        let errorMsg = 'Error al actualizar el agente'
        
        if (result.error.data) {
          if (result.error.data.detail) {
            errorMsg = result.error.data.detail
          } else if (result.error.data.message) {
            errorMsg = result.error.data.message
          } else if (typeof result.error.data === 'object') {
            // Errores de validación por campo
            const fieldErrors = []
            for (const [field, messages] of Object.entries(result.error.data)) {
              if (Array.isArray(messages)) {
                fieldErrors.push(`${messages.join(', ')}`)
              } else {
                fieldErrors.push(`${messages}`)
              }
            }
            if (fieldErrors.length > 0) {
              errorMsg = fieldErrors.join('. ')
            }
          }
        } else if (result.error.message) {
          errorMsg = result.error.message
        }
        
        throw new Error(errorMsg)
      }
      
      toast.add({
        title: 'Agente actualizado',
        description: `El agente ${form.value.agent_id} ha sido actualizado correctamente`,
        color: 'green'
      })
    } else {
      // Crear nuevo agente con todos los datos
      result = await createAgent(form.value)
      
      if (result.error) {
        // Procesar error del servidor
        let errorMsg = 'Error al crear el agente'
        
        if (result.error.data) {
          if (result.error.data.detail) {
            errorMsg = result.error.data.detail
          } else if (result.error.data.message) {
            errorMsg = result.error.data.message
          } else if (typeof result.error.data === 'object') {
            // Errores de validación por campo
            const fieldErrors = []
            for (const [field, messages] of Object.entries(result.error.data)) {
              if (Array.isArray(messages)) {
                fieldErrors.push(`${messages.join(', ')}`)
              } else {
                fieldErrors.push(`${messages}`)
              }
            }
            if (fieldErrors.length > 0) {
              errorMsg = fieldErrors.join('. ')
            }
          }
        } else if (result.error.message) {
          errorMsg = result.error.message
        }
        
        throw new Error(errorMsg)
      }
      
      toast.add({
        title: 'Agente creado',
        description: `El agente ${form.value.agent_id} ha sido creado exitosamente. Extensión SIP: ${form.value.sip_extension}`,
        color: 'green',
        timeout: 5000
      })
    }
    
    await loadAgents()
    isModalOpen.value = false
    resetForm()
  } catch (err: any) {
    // Extraer mensaje de error más detallado
    console.error('Error completo al guardar agente:', err)
    console.error('Error data:', err.data)
    console.error('Error message:', err.message)
    
    let errorMessage = 'Error al guardar el agente'
    
    if (err.message) {
      errorMessage = err.message
    } else if (err.data) {
      if (typeof err.data === 'string') {
        errorMessage = err.data
      } else if (err.data.detail) {
        errorMessage = err.data.detail
      } else if (err.data.message) {
        errorMessage = err.data.message
      } else if (typeof err.data === 'object') {
        // Errores de validación por campo de Django REST Framework
        const fieldErrors = []
        for (const [field, messages] of Object.entries(err.data)) {
          if (Array.isArray(messages)) {
            fieldErrors.push(`${field}: ${messages.join(', ')}`)
          } else {
            fieldErrors.push(`${field}: ${messages}`)
          }
        }
        if (fieldErrors.length > 0) {
          errorMessage = fieldErrors.join('; ')
        }
      }
    }
    
    error.value = errorMessage
    
    // Mostrar toast de error también para mayor visibilidad
    const toast = useToast()
    toast.add({
      title: 'Error al guardar agente',
      description: errorMessage,
      color: 'red',
      timeout: 8000,
      icon: 'i-heroicons-exclamation-triangle'
    })
    
    console.error('Error saving agent:', err)
  } finally {
    isSaving.value = false
  }
}

const deleteAgent = async (id: number) => {
  if (!confirm('¿Estás seguro de eliminar este agente?')) return
  const { deleteAgent: deleteAgentApi } = useAgents()
  const result = await deleteAgentApi(id)
  if (result.error) {
    error.value = 'Error al eliminar el agente'
  } else {
    await loadAgents()
  }
}

const resetForm = () => {
  form.value = {
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    email: '',
    agent_id: '',
    sip_extension: '',
    sip_password: '',
    max_concurrent_calls: 1,
    webrtc_enabled: true,
    auto_answer: false,
    recording_enabled: true
  }
  editingId.value = null
  error.value = null
  agentIdStatus.value = 'idle'
  extensionStatus.value = 'idle'
  if (checkingTimeout.value) {
    clearTimeout(checkingTimeout.value)
  }
}

onMounted(() => loadAgents())

// Debug: mostrar en consola cuando cambie la validez del formulario
watch(isFormValid, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    console.log('🔄 isFormValid cambió:', oldVal, '→', newVal)
    console.log('📌 Campos faltantes:', missingFields.value)
    console.log('📝 Valores actuales:', {
      first_name: form.value.first_name,
      last_name: form.value.last_name,
      email: form.value.email,
      username: form.value.username,
      password: form.value.password ? '***' : '',
      agent_id: form.value.agent_id,
      sip_extension: form.value.sip_extension,
      sip_password: form.value.sip_password ? '***' : ''
    })
  }
})

</script>
