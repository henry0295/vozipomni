<template>
  <div class="agent-softphone">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold flex items-center gap-2">
            <UIcon name="i-heroicons-phone" />
            Teléfono
          </h3>
          <UBadge :color="connectionColor" size="sm">
            {{ connectionStatus }}
          </UBadge>
        </div>
      </template>

      <!-- Estado sin llamada activa -->
      <div v-if="!hasActiveCall" class="space-y-4">
        <!-- Marcador -->
        <div class="space-y-3">
          <UInput
            v-model="dialNumber"
            size="xl"
            placeholder="Número a marcar"
            :disabled="!canMakeCall"
            @keyup.enter="makeCall"
          >
            <template #leading>
              <UIcon name="i-heroicons-phone" />
            </template>
          </UInput>

          <!-- Teclado numérico -->
          <div class="grid grid-cols-3 gap-2">
            <UButton
              v-for="digit in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']"
              :key="digit"
              size="lg"
              color="gray"
              variant="outline"
              :disabled="!canMakeCall"
              @click="addDigit(digit)"
            >
              {{ digit }}
            </UButton>
          </div>

          <!-- Botones de acción -->
          <div class="grid grid-cols-2 gap-2">
            <UButton
              block
              size="lg"
              color="green"
              icon="i-heroicons-phone"
              :disabled="!canMakeCall || !dialNumber"
              @click="makeCall"
            >
              Llamar
            </UButton>
            <UButton
              block
              size="lg"
              color="gray"
              variant="outline"
              icon="i-heroicons-backspace"
              :disabled="!dialNumber"
              @click="clearDigit"
            >
              Borrar
            </UButton>
          </div>
        </div>

        <!-- Llamada rápida a otros agentes -->
        <div class="pt-4 border-t border-gray-200">
          <p class="text-sm font-medium text-gray-700 mb-3">Llamada Rápida</p>
          <div class="grid grid-cols-2 gap-2">
            <UButton
              v-for="contact in quickContacts"
              :key="contact.extension"
              variant="soft"
              color="blue"
              size="sm"
              :disabled="!canMakeCall"
              @click="quickCall(contact.extension)"
            >
              <div class="text-left">
                <p class="font-medium">{{ contact.name }}</p>
                <p class="text-xs opacity-75">Ext: {{ contact.extension }}</p>
              </div>
            </UButton>
          </div>
        </div>
      </div>

      <!-- Llamada activa -->
      <div v-else class="space-y-4">
        <!-- Información de la llamada -->
        <div class="text-center py-6 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg">
          <div class="mb-4">
            <UAvatar
              :alt="currentSession?.remoteIdentity"
              size="2xl"
              class="mx-auto"
            />
          </div>
          <h4 class="text-2xl font-bold text-gray-800 mb-1">
            {{ currentSession?.remoteIdentity }}
          </h4>
          <p class="text-sm text-gray-600 mb-3">
            {{ callDirectionLabel }}
          </p>
          <div class="flex items-center justify-center gap-2">
            <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span class="text-lg font-mono text-gray-700">
              {{ formatDuration(callDuration) }}
            </span>
          </div>
        </div>

        <!-- Llamada entrante sin contestar -->
        <div v-if="!currentSession?.isEstablished && currentSession?.direction === 'incoming'" class="grid grid-cols-2 gap-3">
          <UButton
            block
            size="xl"
            color="green"
            icon="i-heroicons-phone"
            @click="answerCall"
          >
            Contestar
          </UButton>
          <UButton
            block
            size="xl"
            color="red"
            icon="i-heroicons-phone-x-mark"
            @click="rejectCall"
          >
            Rechazar
          </UButton>
        </div>

        <!-- Controles de llamada establecida -->
        <div v-if="currentSession?.isEstablished" class="space-y-3">
          <!-- Controles principales -->
          <div class="grid grid-cols-3 gap-2">
            <UButton
              block
              :color="currentSession?.isMuted ? 'red' : 'gray'"
              variant="soft"
              :icon="currentSession?.isMuted ? 'i-heroicons-microphone-slash' : 'i-heroicons-microphone'"
              @click="toggleMute"
            >
              {{ currentSession?.isMuted ? 'Activar' : 'Silenciar' }}
            </UButton>

            <UButton
              block
              :color="currentSession?.isOnHold ? 'yellow' : 'gray'"
              variant="soft"
              :icon="currentSession?.isOnHold ? 'i-heroicons-play' : 'i-heroicons-pause'"
              @click="toggleHold"
            >
              {{ currentSession?.isOnHold ? 'Reanudar' : 'Retener' }}
            </UButton>

            <UButton
              block
              color="gray"
              variant="soft"
              icon="i-heroicons-calculator"
              @click="showDtmf = !showDtmf"
            >
              DTMF
            </UButton>
          </div>

          <!-- Teclado DTMF -->
          <div v-if="showDtmf" class="grid grid-cols-3 gap-2 p-3 bg-gray-50 rounded-lg">
            <UButton
              v-for="digit in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']"
              :key="digit"
              size="sm"
              color="gray"
              variant="outline"
              @click="sendDTMF(digit)"
            >
              {{ digit }}
            </UButton>
          </div>

          <!-- Transferencia -->
          <div class="p-3 bg-blue-50 rounded-lg">
            <p class="text-sm font-medium text-blue-800 mb-2">Transferir a:</p>
            <div class="flex gap-2">
              <UInput
                v-model="transferNumber"
                placeholder="Extensión o número"
                class="flex-1"
              >
                <template #leading>
                  <UIcon name="i-heroicons-arrow-right-circle" />
                </template>
              </UInput>
              <UButton
                color="blue"
                icon="i-heroicons-arrow-right-circle"
                :disabled="!transferNumber"
                @click="transferCall"
              >
                Transferir
              </UButton>
            </div>
          </div>

          <!-- Botón colgar -->
          <UButton
            block
            size="xl"
            color="red"
            icon="i-heroicons-phone-x-mark"
            @click="hangupCall"
          >
            Colgar
          </UButton>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useWebRTC } from '~/composables/useWebRTC'
import { useAgentStore } from '~/stores/agent'

const agentStore = useAgentStore()
const webrtc = useWebRTC()

// State
const dialNumber = ref('')
const transferNumber = ref('')
const showDtmf = ref(false)

// Contactos rápidos (se pueden cargar desde API)
const quickContacts = ref([
  { name: 'Supervisor', extension: '1000' },
  { name: 'Soporte', extension: '1001' },
  { name: 'Ventas', extension: '1002' },
  { name: 'Servicio', extension: '1003' }
])

// Computed
const hasActiveCall = computed(() => webrtc.hasActiveCall.value)
const canMakeCall = computed(() => webrtc.canMakeCall.value && agentStore.canReceiveCalls)
const currentSession = computed(() => webrtc.currentSession.value)
const callDuration = computed(() => webrtc.callDuration.value)
const connectionStatus = computed(() => {
  if (webrtc.isRegistered.value) return 'Conectado'
  if (webrtc.isConnecting.value) return 'Conectando...'
  return 'Desconectado'
})
const connectionColor = computed(() => {
  if (webrtc.isRegistered.value) return 'green'
  if (webrtc.isConnecting.value) return 'yellow'
  return 'red'
})

const callDirectionLabel = computed(() => {
  if (!currentSession.value) return ''
  return currentSession.value.direction === 'incoming' ? 'Llamada entrante' : 'Llamada saliente'
})

// Methods
const addDigit = (digit: string) => {
  dialNumber.value += digit
}

const clearDigit = () => {
  dialNumber.value = dialNumber.value.slice(0, -1)
}

const makeCall = () => {
  if (!dialNumber.value) return
  
  const result = webrtc.call(dialNumber.value)
  if (!result.success) {
    alert(`Error al llamar: ${result.error}`)
  } else {
    // Mantener el número por si falla
  }
}

const quickCall = (extension: string) => {
  dialNumber.value = extension
  makeCall()
}

const answerCall = () => {
  const result = webrtc.answer()
  if (!result.success) {
    alert(`Error al contestar: ${result.error}`)
  }
}

const rejectCall = () => {
  const result = webrtc.reject()
  if (!result.success) {
    alert(`Error al rechazar: ${result.error}`)
  }
}

const hangupCall = () => {
  const result = webrtc.hangup()
  if (!result.success) {
    alert(`Error al colgar: ${result.error}`)
  } else {
    dialNumber.value = ''
    transferNumber.value = ''
    showDtmf.value = false
  }
}

const toggleMute = () => {
  const result = webrtc.toggleMute()
  if (!result.success) {
    alert(`Error al silenciar: ${result.error}`)
  }
}

const toggleHold = () => {
  const result = webrtc.toggleHold()
  if (!result.success) {
    alert(`Error al retener: ${result.error}`)
  }
}

const sendDTMF = (digit: string) => {
  const result = webrtc.sendDTMF(digit)
  if (!result.success) {
    alert(`Error al enviar DTMF: ${result.error}`)
  }
}

const transferCall = () => {
  if (!transferNumber.value) return
  
  const result = webrtc.transfer(transferNumber.value)
  if (!result.success) {
    alert(`Error al transferir: ${result.error}`)
  } else {
    transferNumber.value = ''
  }
}

const formatDuration = webrtc.formatDuration

// Registrar WebRTC cuando el agente hace login
watch(() => agentStore.isLoggedIn, (isLoggedIn) => {
  if (isLoggedIn && agentStore.agent) {
    // Configurar WebRTC
    const config = useRuntimeConfig()
    const sipServer = config.public.apiBase.replace(/^https?:\/\//, '').replace('/api', '')
    
    webrtc.register({
      sipServer: sipServer.split(':')[0],
      sipPort: 8089, // Puerto WebSocket de Asterisk
      sipUser: agentStore.agent.sip_extension,
      sipPassword: agentStore.agent.sip_extension, // En producción usar password real
      sipExtension: agentStore.agent.sip_extension,
      displayName: agentStore.agent.user_details?.first_name || 'Agente'
    })
  } else {
    // Desregistrar
    webrtc.unregister()
  }
})

// Cleanup
onUnmounted(() => {
  webrtc.unregister()
})
</script>

<style scoped>
.agent-softphone {
  height: 100%;
}
</style>
