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
      <div class="p-4 space-y-6">
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
          
          <UFormGroup label="ID de Agente" required help="Identificador único del agente (ej: AGT001)">
            <UInput v-model="form.agent_id" placeholder="Ej: AGT001" />
          </UFormGroup>

          <UFormGroup label="Extensión SIP" required help="Número de extensión telefónica (ej: 100)">
            <UInput v-model="form.sip_extension" placeholder="Ej: 100" type="number" />
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

        <div class="flex gap-2 pt-4 border-t">
          <UButton 
            color="primary" 
            @click="saveAgent" 
            :loading="isSaving"
            :disabled="!isFormValid"
          >
            {{ editingId ? 'Actualizar' : 'Crear Agente' }}
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

const isFormValid = computed(() => {
  if (editingId.value) {
    // En edición, solo verificar campos básicos de agente
    return form.value.agent_id && form.value.sip_extension
  }
  // En creación, todos los campos de usuario son requeridos
  return form.value.username &&
    form.value.password &&
    form.value.first_name &&
    form.value.last_name &&
    form.value.email &&
    form.value.agent_id &&
    form.value.sip_extension &&
    form.value.sip_password
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

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
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
        throw new Error('Error al actualizar el agente')
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
        throw new Error('Error al crear el agente')
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
    error.value = err.message || 'Error al guardar el agente. Verifique que el usuario, ID de agente y extensión SIP no estén duplicados.'
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
}

onMounted(() => loadAgents())
</script>
