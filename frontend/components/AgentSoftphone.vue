<template>
  <div class="agent-softphone p-2.5">
    <UCard :ui="{ body: { padding: 'p-3' }, header: { padding: 'px-3 py-2' } }">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold flex items-center gap-1.5">
            <UIcon name="i-heroicons-phone" class="h-4 w-4" />
            Teléfono
          </h3>
          <UBadge :color="connectionColor" size="xs">
            {{ connectionStatus }}
          </UBadge>
        </div>
      </template>

      <!-- Estado sin llamada activa -->
      <div v-if="!hasActiveCall" class="space-y-3">
        <!-- Marcador -->
        <div class="space-y-2">
          <UInput
            v-model="dialNumber"
            size="lg"
            placeholder="Número a marcar"
            :disabled="!canMakeCall"
            @keyup.enter="makeCall"
          >
            <template #leading>
              <UIcon name="i-heroicons-phone" class="h-4 w-4" />
            </template>
          </UInput>

          <!-- Teclado numérico compacto -->
          <div class="grid grid-cols-3 gap-1.5">
            <UButton
              v-for="digit in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']"
              :key="digit"
              size="sm"
              color="gray"
              variant="outline"
              :disabled="!canMakeCall"
              class="h-9 text-base font-semibold"
              @click="addDigit(digit)"
            >
              {{ digit }}
            </UButton>
          </div>

          <!-- Botones Llamar / Borrar -->
          <div class="grid grid-cols-2 gap-2">
            <UButton
              block
              size="md"
              color="green"
              icon="i-heroicons-phone"
              :disabled="!canMakeCall || !dialNumber"
              @click="makeCall"
            >
              Llamar
            </UButton>
            <UButton
              block
              size="md"
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
        <div v-if="quickContacts.length" class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <p class="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2">Llamada Rápida</p>
          <div class="grid grid-cols-2 gap-1.5">
            <UButton
              v-for="contact in quickContacts"
              :key="contact.extension"
              variant="soft"
              color="blue"
              size="sm"
              :disabled="!canMakeCall"
              @click="quickCall(contact.extension)"
            >
              <div class="text-left w-full overflow-hidden">
                <p class="font-medium text-xs truncate">{{ contact.name }}</p>
                <p class="text-xs opacity-75">Ext: {{ contact.extension }}</p>
              </div>
            </UButton>
          </div>
        </div>
      </div>

      <!-- Llamada activa -->
      <div v-else class="space-y-3">
        <!-- Información de la llamada -->
        <div class="text-center py-3 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 rounded-lg">
          <div class="mb-2">
            <UAvatar
              :alt="currentSession?.remoteIdentity"
              size="lg"
              class="mx-auto"
            />
          </div>
          <h4 class="text-base font-bold text-gray-800 dark:text-gray-100 mb-0.5 px-2 truncate">
            {{ currentSession?.remoteIdentity }}
          </h4>
          <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
            {{ callDirectionLabel }}
          </p>
          <div class="flex items-center justify-center gap-2">
            <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span class="text-base font-mono font-semibold text-gray-700 dark:text-gray-200">
              {{ formatDuration(callDuration) }}
            </span>
          </div>
        </div>

        <!-- Llamada entrante sin contestar -->
        <div v-if="!currentSession?.isEstablished && currentSession?.direction === 'incoming'" class="grid grid-cols-2 gap-2">
          <UButton
            block
            size="md"
            color="green"
            icon="i-heroicons-phone"
            @click="answerCall"
          >
            Contestar
          </UButton>
          <UButton
            block
            size="md"
            color="red"
            icon="i-heroicons-phone-x-mark"
            @click="rejectCall"
          >
            Rechazar
          </UButton>
        </div>

        <!-- Botón Colgar -->
        <UButton
          v-if="currentSession?.isEstablished || currentSession?.direction === 'outgoing'"
          block
          size="md"
          color="red"
          icon="i-heroicons-phone-x-mark"
          @click="hangupCall"
        >
          Colgar
        </UButton>

        <!-- Controles de llamada establecida -->
        <div v-if="currentSession?.isEstablished" class="space-y-2">
          <!-- Controles principales -->
          <div class="grid grid-cols-3 gap-1.5">
            <UButton
              block
              size="sm"
              :color="currentSession?.isMuted ? 'red' : 'gray'"
              variant="soft"
              :icon="currentSession?.isMuted ? 'i-heroicons-microphone-slash' : 'i-heroicons-microphone'"
              @click="toggleMute"
            >
              {{ currentSession?.isMuted ? 'Activar' : 'Silenciar' }}
            </UButton>

            <UButton
              block
              size="sm"
              :color="currentSession?.isOnHold ? 'yellow' : 'gray'"
              variant="soft"
              :icon="currentSession?.isOnHold ? 'i-heroicons-play' : 'i-heroicons-pause'"
              @click="toggleHold"
            >
              {{ currentSession?.isOnHold ? 'Reanudar' : 'Retener' }}
            </UButton>

            <UButton
              block
              size="sm"
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
              :color="dtmfPressed === digit ? 'primary' : 'gray'"
              :variant="dtmfPressed === digit ? 'solid' : 'outline'"
              class="transition-all"
              :class="{ 'scale-95': dtmfPressed === digit }"
              @click="sendDTMF(digit)"
            >
              {{ digit }}
            </UButton>
          </div>

          <!-- Transferencia -->
          <div class="rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-900/20 p-2.5 space-y-1.5">
            <p class="text-xs font-semibold text-blue-700 dark:text-blue-300">Transferir a:</p>
            <div class="flex gap-1.5">
              <UInput
                v-model="transferNumber"
                placeholder="Extensión o número"
                size="sm"
                class="flex-1"
              >
                <template #leading>
                  <UIcon name="i-heroicons-arrow-right-circle" class="h-3.5 w-3.5" />
                </template>
              </UInput>
              <UButton
                size="sm"
                color="blue"
                variant="soft"
                icon="i-heroicons-arrow-right-circle"
                :disabled="!transferNumber"
                @click="transferCall"
              >
                Rápida
              </UButton>
              <UButton
                size="sm"
                color="indigo"
                variant="soft"
                icon="i-heroicons-users"
                @click="openConsultiveTransfer"
              >
                Agentes
              </UButton>
            </div>
          </div>

          <!-- Conferencia a 3 -->
          <div class="rounded-lg border border-purple-200 bg-purple-50 dark:bg-purple-900/20 p-2.5 space-y-1.5">
            <p class="text-xs font-semibold text-purple-700 dark:text-purple-300">Conferencia a 3:</p>
            <div class="flex gap-1.5">
              <UInput
                v-model="conferenceNumber"
                placeholder="Número del 3er participante"
                size="sm"
                class="flex-1"
              />
              <UButton
                size="sm"
                color="purple"
                variant="soft"
                icon="i-heroicons-user-group"
                :disabled="!conferenceNumber || conferenceLoading"
                :loading="conferenceLoading"
                @click="startConference"
              >
                Conferencia
              </UButton>
            </div>
          </div>

          <!-- Botón colgar (dentro de controles establecidos, se oculta con el de arriba duplicado) -->
        </div>
      </div>
    </UCard>

    <!-- Modal: Transfer Consultivo -->
    <UModal v-model="showConsultiveModal">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="font-semibold">Agentes disponibles</h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="showConsultiveModal = false" />
          </div>
        </template>
        <div v-if="loadingAgents" class="text-center py-6">
          <UIcon name="i-heroicons-arrow-path" class="animate-spin w-6 h-6 mx-auto" />
        </div>
        <div v-else-if="availableAgents.length === 0" class="text-center py-6 text-gray-500">
          No hay agentes disponibles en este momento
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="agent in availableAgents"
            :key="agent.id"
            class="flex items-center justify-between p-3 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 cursor-pointer transition"
            @click="transferToAgent(agent)"
          >
            <div>
              <p class="font-medium text-sm">{{ agent.name }}</p>
              <p class="text-xs text-gray-500">Ext: {{ agent.sip_extension }} · {{ agent.calls_today }} llamadas hoy</p>
            </div>
            <UBadge color="green" size="xs">Disponible</UBadge>
          </div>
        </div>
      </UCard>
    </UModal>
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
const conferenceNumber = ref('')
const conferenceLoading = ref(false)
const showDtmf = ref(false)
const showConsultiveModal = ref(false)
const availableAgents = ref<any[]>([])
const loadingAgents = ref(false)
const dtmfPressed = ref<string | null>(null)

// Persistir estado en sessionStorage
const loadPersistedState = () => {
  if (typeof window !== 'undefined' && sessionStorage.getItem('softphone_dialNumber')) {
    dialNumber.value = sessionStorage.getItem('softphone_dialNumber') || ''
  }
}

const persistDialNumber = () => {
  if (typeof window !== 'undefined') {
    sessionStorage.setItem('softphone_dialNumber', dialNumber.value)
  }
}

watch(dialNumber, persistDialNumber)

// Notificar fallos de llamada SIP
watch(() => webrtc.lastCallError.value, (error) => {
  if (error) {
    useToast().add({ title: 'Llamada fallida', description: error, color: 'red', icon: 'i-heroicons-phone-x-mark' })
  }
})

// Notificar cuando la llamada se establece (confirmed)
watch(() => webrtc.currentSession.value?.isEstablished, (established) => {
  if (established) {
    const remote = webrtc.currentSession.value?.remoteIdentity || ''
    useToast().add({
      title: 'Llamada conectada',
      description: remote ? `En línea con ${remote}` : 'Llamada activa',
      color: 'green',
      icon: 'i-heroicons-phone'
    })
  }
})

// Contactos rápidos — cargados desde /api/telephony/extensions/
const quickContacts = ref<{ name: string; extension: string }[]>([])

const loadQuickContacts = async () => {
  try {
    const { $api } = useNuxtApp()
    const data = await $api('/telephony/extensions/', { query: { is_active: true } })
    const items = Array.isArray(data) ? data : (data?.results ?? [])
    quickContacts.value = items.map((ext: any) => ({
      name: ext.callerid || ext.name || ext.extension,
      extension: String(ext.extension)
    }))
  } catch {
    quickContacts.value = []
  }
}

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

// Tonos DTMF via Web Audio API (frecuencias estándar ITU-T Q.23)
const DTMF_FREQS: Record<string, [number, number]> = {
  '1': [697, 1209], '2': [697, 1336], '3': [697, 1477],
  '4': [770, 1209], '5': [770, 1336], '6': [770, 1477],
  '7': [852, 1209], '8': [852, 1336], '9': [852, 1477],
  '*': [941, 1209], '0': [941, 1336], '#': [941, 1477]
}

const playDTMFTone = (digit: string) => {
  try {
    const freqs = DTMF_FREQS[digit]
    if (!freqs) return
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    const duration = 0.12

    const gain = ctx.createGain()
    gain.connect(ctx.destination)
    gain.gain.setValueAtTime(0.15, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration)

    for (const freq of freqs) {
      const osc = ctx.createOscillator()
      osc.connect(gain)
      osc.frequency.value = freq
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + duration)
    }

    setTimeout(() => ctx.close(), (duration + 0.15) * 1000)
  } catch {
    // Audio no disponible, no bloquear la UI
  }
}

const addDigit = (digit: string) => {
  dialNumber.value += digit
  playDTMFTone(digit)
}

const clearDigit = () => {
  dialNumber.value = dialNumber.value.slice(0, -1)
}

const makeCall = () => {
  if (!dialNumber.value) return
  const result = webrtc.call(dialNumber.value)
  if (!result.success) alert(`Error al llamar: ${result.error}`)
}

const quickCall = (extension: string) => {
  dialNumber.value = extension
  makeCall()
}

const answerCall = () => {
  const result = webrtc.answer()
  if (!result.success) alert(`Error al contestar: ${result.error}`)
}

const rejectCall = () => {
  const result = webrtc.reject()
  if (!result.success) alert(`Error al rechazar: ${result.error}`)
}

const hangupCall = async () => {
  const result = webrtc.hangup()
  if (!result.success) {
    alert(`Error al colgar: ${result.error}`)
  } else {
    // Notificar al backend para colgar el canal en Asterisk
    // Esto asegura que la llamada termine en ambos extremos
    const callData = agentStore.currentCall
    if (callData?.callId) {
      try {
        const { $api } = useNuxtApp()
        await $api('/calls/hangup/', {
          method: 'POST',
          body: { call_id: callData.callId }
        })
        console.log('Hangup enviado al backend correctamente')
      } catch (err) {
        console.warn('No se pudo notificar hangup al backend:', err)
        // No bloquear la UI, la llamada WebRTC ya se cortó
      }
    }
    
    dialNumber.value = ''
    transferNumber.value = ''
    conferenceNumber.value = ''
    showDtmf.value = false
  }
}

const toggleMute = () => {
  const result = webrtc.toggleMute()
  if (!result.success) alert(`Error al silenciar: ${result.error}`)
}

const toggleHold = () => {
  const result = webrtc.toggleHold()
  if (!result.success) alert(`Error al retener: ${result.error}`)
}

const sendDTMF = (digit: string) => {
  const result = webrtc.sendDTMF(digit)
  if (!result.success) {
    useToast().add({ title: `Error al enviar DTMF: ${result.error}`, color: 'red' })
  } else {
    // Feedback visual
    dtmfPressed.value = digit
    setTimeout(() => {
      dtmfPressed.value = null
    }, 200)
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

// Transfer consultivo: listar agentes disponibles
const openConsultiveTransfer = async () => {
  showConsultiveModal.value = true
  loadingAgents.value = true
  try {
    const { $api } = useNuxtApp()
    const data = await $api('/cc/available-agents/')
    availableAgents.value = (data as any).available_agents || []
  } catch (err) {
    console.error('Error loading available agents:', err)
    availableAgents.value = []
  } finally {
    loadingAgents.value = false
  }
}

const transferToAgent = async (agent: any) => {
  try {
    const { $api } = useNuxtApp()
    const session = currentSession.value
    
    await $api('/cc/consultive-transfer/', {
      method: 'POST',
      body: {
        channel: (session as any)?.channel || '',
        extension: agent.sip_extension,
      },
    })
    
    showConsultiveModal.value = false
    useToast().add({ title: 'Llamada transferida', color: 'green' })
  } catch (e: any) {
    useToast().add({ 
      title: 'Error al transferir',
      description: e?.data?.error || e.message,
      color: 'red'
    })
  }
}

// Conferencia a 3
const startConference = async () => {
  if (!conferenceNumber.value) return
  
  conferenceLoading.value = true
  try {
    const { $api } = useNuxtApp()
    const session = currentSession.value
    
    await $api('/cc/conference/', {
      method: 'POST',
      body: {
        channel: (session as any)?.channel || '',
        third_party: conferenceNumber.value,
        agent_id: agentStore.agent?.id,
      },
    })
    
    conferenceNumber.value = ''
    useToast().add({ title: 'Conferencia iniciada', color: 'green' })
  } catch (e: any) {
    useToast().add({ 
      title: 'Error al crear conferencia',
      description: e?.data?.error || e.message,
      color: 'red'
    })
  } finally {
    conferenceLoading.value = false
  }
}

const formatDuration = webrtc.formatDuration

// Registrar WebRTC cuando el agente hace login (immediate: actúa si ya está logueado al montar)
watch(() => agentStore.isLoggedIn, (isLoggedIn) => {
  if (isLoggedIn && agentStore.agent) {
    const config = useRuntimeConfig()
    const apiBase = config.public.apiBase as string

    // Obtener el origin para construir la URL WSS del proxy nginx
    // Si apiBase es relativa ("/api"), usar window.location.origin
    // Si apiBase es absoluta ("https://host/api"), extraer el origin de ella
    let pageOrigin: string
    if (apiBase.startsWith('http')) {
      const u = new URL(apiBase)
      pageOrigin = u.origin  // "https://192.168.101.228"
    } else {
      // URL relativa — sólo funciona en browser; SSR usa fallback
      pageOrigin = (typeof window !== 'undefined' ? window.location.origin : 'https://localhost')
    }

    const wsUrl = pageOrigin.replace(/^https:\/\//, 'wss://').replace(/^http:\/\//, 'ws://') + '/sip/ws'
    const sipHost = pageOrigin.replace(/^https?:\/\//, '').split(':')[0]

    webrtc.register({
      wsUrl,
      sipServer: sipHost,
      sipPort: 443,
      sipUser: agentStore.agent.sip_extension,
      sipPassword: agentStore.agent.sip_password || agentStore.agent.sip_extension,
      sipExtension: agentStore.agent.sip_extension,
      displayName: agentStore.agent.user_details?.first_name || 'Agente'
    })
  } else {
    webrtc.unregister()
  }
}, { immediate: true })

onUnmounted(() => {
  webrtc.unregister()
  // Limpiar sessionStorage al cerrar
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem('softphone_dialNumber')
  }
})

// Cargar estado persistido al montar
onMounted(() => {
  loadPersistedState()
  loadQuickContacts()
})
</script>

<style scoped>
/* altura natural para no ocupar toda la columna */
</style>
