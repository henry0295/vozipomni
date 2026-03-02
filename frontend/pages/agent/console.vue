<template>
  <div class="agent-console">
    <!-- Header con información del agente -->
    <div class="console-header">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <UButton
            icon="i-heroicons-arrow-left"
            color="gray"
            variant="ghost"
            to="/dashboard"
          />
          <div>
            <h1 class="text-2xl font-bold text-gray-800">Consola de Agente</h1>
            <p class="text-sm text-gray-600">{{ currentDateTime }}</p>
          </div>
        </div>

        <!-- Botón de logout -->
        <UButton
          v-if="agentStore.isLoggedIn"
          color="red"
          variant="soft"
          icon="i-heroicons-arrow-right-on-rectangle"
          @click="handleLogout"
        >
          Cerrar Sesión
        </UButton>
      </div>
    </div>

    <!-- Pantalla de login del agente -->
    <div v-if="!agentStore.isLoggedIn" class="login-screen">
      <UCard class="max-w-md mx-auto">
        <template #header>
          <div class="text-center">
            <UIcon name="i-heroicons-user-circle" class="h-16 w-16 mx-auto mb-4 text-blue-600" />
            <h2 class="text-2xl font-bold">Iniciar Sesión de Agente</h2>
            <p class="text-sm text-gray-600 mt-2">Seleccione su perfil para comenzar</p>
          </div>
        </template>

        <div class="space-y-4">
          <USelectMenu
            v-model="selectedAgent"
            :options="availableAgents"
            placeholder="Seleccionar agente"
            size="lg"
          >
            <template #label>
              <div v-if="selectedAgent" class="flex items-center gap-3">
                <UAvatar :alt="selectedAgent.agent_id" size="sm" />
                <div>
                  <p class="font-medium">{{ selectedAgent.user_details?.first_name || selectedAgent.agent_id }}</p>
                  <p class="text-xs text-gray-500">Ext: {{ selectedAgent.sip_extension }}</p>
                </div>
              </div>
            </template>

            <template #option="{ option }">
              <div class="flex items-center gap-3">
                <UAvatar :alt="option.agent_id" size="sm" />
                <div>
                  <p class="font-medium">{{ option.user_details?.first_name || option.agent_id }}</p>
                  <p class="text-xs text-gray-500">Ext: {{ option.sip_extension }}</p>
                </div>
              </div>
            </template>
          </USelectMenu>

          <UButton
            block
            size="lg"
            :disabled="!selectedAgent"
            :loading="isLoggingIn"
            @click="handleLogin"
          >
            Iniciar Sesión
          </UButton>
        </div>
      </UCard>
    </div>

    <!-- Consola principal -->
    <div v-else class="console-main">
      <div class="console-grid">
        <!-- Columna izquierda -->
        <div class="console-left">
          <div class="space-y-4">
            <!-- Panel de estado del agente -->
            <AgentStatusPanel />

            <!-- Softphone -->
            <AgentSoftphone />
          </div>
        </div>

        <!-- Columna central -->
        <div class="console-center">
          <div class="space-y-4">
            <!-- Campaña activa y script -->
            <AgentCampaignsPanel ref="campaignsPanel" />

            <!-- Información del contacto actual (durante llamada) -->
            <UCard v-if="agentStore.currentCall">
              <template #header>
                <h3 class="text-lg font-semibold">Información del Contacto</h3>
              </template>

              <div class="space-y-3">
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <p class="text-sm text-gray-600">Nombre</p>
                    <p class="font-semibold">{{ currentContact.name || 'Desconocido' }}</p>
                  </div>
                  <div>
                    <p class="text-sm text-gray-600">Teléfono</p>
                    <p class="font-semibold">{{ currentContact.phone }}</p>
                  </div>
                  <div>
                    <p class="text-sm text-gray-600">Email</p>
                    <p class="font-semibold">{{ currentContact.email || 'N/A' }}</p>
                  </div>
                  <div>
                    <p class="text-sm text-gray-600">Empresa</p>
                    <p class="font-semibold">{{ currentContact.company || 'N/A' }}</p>
                  </div>
                </div>

                <!-- Historial de llamadas del contacto -->
                <div class="pt-3 border-t">
                  <p class="text-sm font-medium text-gray-700 mb-2">Historial de Llamadas</p>
                  <div class="space-y-2 max-h-40 overflow-y-auto">
                    <div
                      v-for="call in currentContact.callHistory"
                      :key="call.id"
                      class="text-xs p-2 bg-gray-50 rounded"
                    >
                      <div class="flex justify-between">
                        <span class="font-medium">{{ call.date }}</span>
                        <UBadge :color="call.disposition === 'CONNECTED' ? 'green' : 'gray'" size="xs">
                          {{ call.disposition }}
                        </UBadge>
                      </div>
                      <p class="text-gray-600 mt-1">{{ call.notes }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </UCard>

            <!-- Panel de notas rápidas -->
            <UCard>
              <template #header>
                <h3 class="text-lg font-semibold">Notas Rápidas</h3>
              </template>

              <UTextarea
                v-model="quickNotes"
                :rows="6"
                placeholder="Escriba notas importantes durante la llamada..."
              />
            </UCard>
          </div>
        </div>

        <!-- Columna derecha -->
        <div class="console-right">
          <!-- Disposición de llamada -->
          <AgentCallDisposition
            :call-info="callDispositionInfo"
            :campaign-id="currentCampaignId"
            @disposition-saved="handleDispositionSaved"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '~/stores/agent'
import type { Agent } from '~/types'

// Middleware para requerir autenticación
definePageMeta({
  middleware: 'auth',
  layout: 'agent'
})

const agentStore = useAgentStore()
const { getAgents } = useAgents()

// State
const selectedAgent = ref<Agent | null>(null)
const availableAgents = ref<Agent[]>([])
const isLoggingIn = ref(false)
const currentDateTime = ref('')
const quickNotes = ref('')
const campaignsPanel = ref<any>(null)

// Información del contacto actual (mock)
const currentContact = ref({
  name: '',
  phone: '',
  email: '',
  company: '',
  callHistory: [] as any[]
})

// Computed
const currentCampaignId = computed(() => {
  return campaignsPanel.value?.selectedCampaignId || null
})

const callDispositionInfo = computed(() => {
  if (!agentStore.currentCall) return null
  
  return {
    customer: currentContact.value.name,
    number: agentStore.currentCall.remoteNumber,
    duration: formatDuration(agentStore.callDuration),
    campaign: campaignsPanel.value?.selectedCampaign?.name,
    contactId: currentContact.value.id
  }
})

// Methods
const loadAvailableAgents = async () => {
  const authStore = useAuthStore()
  if (!authStore.user) return

  try {
    const { data } = await getAgents({
      user: authStore.user.id,
      webrtc_enabled: true
    })

    if (data) {
      availableAgents.value = data
    }
  } catch (err) {
    console.error('Error loading agents:', err)
  }
}

const handleLogin = async () => {
  if (!selectedAgent.value) return

  isLoggingIn.value = true
  try {
    const result = await agentStore.login(selectedAgent.value)
    
    if (!result.success) {
      alert(`Error al iniciar sesión: ${result.error}`)
    }
  } catch (err: any) {
    alert(`Error: ${err.message}`)
  } finally {
    isLoggingIn.value = false
  }
}

const handleLogout = async () => {
  if (!confirm('¿Está seguro que desea cerrar la sesión de agente?')) return

  await agentStore.logout()
  selectedAgent.value = null
}

const handleDispositionSaved = (data: any) => {
  console.log('Disposition saved:', data)
  quickNotes.value = ''
  currentContact.value = {
    name: '',
    phone: '',
    email: '',
    company: '',
    callHistory: []
  }
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const updateDateTime = () => {
  const now = new Date()
  currentDateTime.value = now.toLocaleString('es-CO', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Auto-refresh fecha/hora
let dateTimeInterval: any = null

// Lifecycle
onMounted(() => {
  loadAvailableAgents()
  updateDateTime()
  
  dateTimeInterval = setInterval(updateDateTime, 1000)

  // Si el usuario ya tiene un agente asignado, auto-login
  const authStore = useAuthStore()
  if (authStore.user?.is_active_agent) {
    loadAvailableAgents().then(() => {
      if (availableAgents.value.length === 1) {
        selectedAgent.value = availableAgents.value[0]
        handleLogin()
      }
    })
  }
})

onUnmounted(() => {
  if (dateTimeInterval) {
    clearInterval(dateTimeInterval)
  }
})
</script>

<style scoped>
.agent-console {
  @apply min-h-screen bg-gray-50;
}

.console-header {
  @apply bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-10 shadow-sm;
}

.login-screen {
  @apply flex items-center justify-center min-h-[80vh] p-6;
}

.console-main {
  @apply p-6;
}

.console-grid {
  @apply grid grid-cols-1 lg:grid-cols-3 gap-6;
}

.console-left {
  @apply lg:col-span-1;
}

.console-center {
  @apply lg:col-span-1;
}

.console-right {
  @apply lg:col-span-1;
}

@media (max-width: 1024px) {
  .console-grid {
    @apply grid-cols-1;
  }
}
</style>
