<template>
  <div class="webphone-container">
    <!-- Phone Status Bar -->
    <div class="phone-status" :class="statusClass">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <UIcon :name="statusIcon" class="h-5 w-5" />
          <span class="font-medium">{{ statusText }}</span>
        </div>
        <div v-if="currentCall" class="text-sm">
          {{ callDuration }}
        </div>
      </div>
    </div>

    <!-- Active Call Display -->
    <div v-if="currentCall" class="active-call">
      <div class="call-info">
        <div class="text-lg font-semibold">{{ currentCall.remoteIdentity }}</div>
        <div class="text-sm text-gray-600">{{ currentCall.direction === 'incoming' ? 'Llamada entrante' : 'Llamando...' }}</div>
      </div>

      <!-- Call Controls -->
      <div class="call-controls">
        <UButton
          v-if="!currentCall.isEstablished"
          color="green"
          size="lg"
          icon="i-heroicons-phone"
          @click="answerCall"
        >
          Contestar
        </UButton>

        <UButton
          v-if="currentCall.isEstablished"
          :color="isMuted ? 'yellow' : 'gray'"
          size="lg"
          :icon="isMuted ? 'i-heroicons-microphone-slash' : 'i-heroicons-microphone'"
          @click="toggleMute"
        >
          {{ isMuted ? 'Desmutear' : 'Silenciar' }}
        </UButton>

        <UButton
          v-if="currentCall.isEstablished"
          :color="isOnHold ? 'blue' : 'gray'"
          size="lg"
          icon="i-heroicons-pause"
          @click="toggleHold"
        >
          {{ isOnHold ? 'Reanudar' : 'Pausar' }}
        </UButton>

        <UButton
          color="red"
          size="lg"
          icon="i-heroicons-phone-x-mark"
          @click="hangup"
        >
          Colgar
        </UButton>
      </div>

      <!-- Transfer Controls -->
      <div v-if="currentCall.isEstablished" class="transfer-controls">
        <UInput
          v-model="transferNumber"
          placeholder="Número para transferir"
          icon="i-heroicons-arrow-right-circle"
        />
        <UButton
          color="blue"
          icon="i-heroicons-arrow-right-circle"
          @click="transferCall"
          :disabled="!transferNumber"
        >
          Transferir
        </UButton>
      </div>
    </div>

    <!-- Dialer Pad -->
    <div v-if="!currentCall" class="dialer-pad">
      <UInput
        v-model="dialNumber"
        size="xl"
        placeholder="Ingrese número"
        class="mb-4"
        :disabled="!isRegistered"
      />

      <div class="grid grid-cols-3 gap-2 mb-4">
        <UButton
          v-for="digit in dialPadDigits"
          :key="digit"
          size="lg"
          color="gray"
          @click="dialDigit(digit)"
          :disabled="!isRegistered"
        >
          {{ digit }}
        </UButton>
      </div>

      <UButton
        block
        size="lg"
        color="green"
        icon="i-heroicons-phone"
        @click="makeCall"
        :disabled="!dialNumber || !isRegistered"
      >
        Llamar
      </UButton>
    </div>

    <!-- Settings -->
    <div class="phone-settings">
      <UButton
        color="gray"
        variant="ghost"
        icon="i-heroicons-cog-6-tooth"
        @click="showSettings = !showSettings"
      >
        Configuración
      </UButton>
    </div>

    <!-- Settings Modal -->
    <UModal v-model="showSettings">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Configuración del WebPhone</h3>
        </template>

        <div class="space-y-4">
          <UFormGroup label="Estado de Registro">
            <div class="flex items-center gap-2">
              <div
                class="w-3 h-3 rounded-full"
                :class="isRegistered ? 'bg-green-500' : 'bg-red-500'"
              ></div>
              <span>{{ isRegistered ? 'Registrado' : 'No registrado' }}</span>
            </div>
          </UFormGroup>

          <UFormGroup label="Extensión">
            <UInput v-model="sipSettings.extension" disabled />
          </UFormGroup>

          <UFormGroup label="Servidor SIP">
            <UInput v-model="sipSettings.server" disabled />
          </UFormGroup>

          <UFormGroup label="Dispositivo de Audio">
            <USelect
              v-model="selectedAudioDevice"
              :options="audioDevices"
              option-attribute="label"
            />
          </UFormGroup>

          <UFormGroup label="Dispositivo de Micrófono">
            <USelect
              v-model="selectedMicDevice"
              :options="micDevices"
              option-attribute="label"
            />
          </UFormGroup>
        </div>

        <template #footer>
          <UButton @click="showSettings = false">Cerrar</UButton>
          <UButton
            v-if="!isRegistered"
            color="green"
            @click="register"
          >
            Registrar
          </UButton>
          <UButton
            v-else
            color="red"
            @click="unregister"
          >
            Desregistrar
          </UButton>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import JsSIP from 'jssip'

const { user } = useAuth()
const config = useRuntimeConfig()

// State
const isRegistered = ref(false)
const currentCall = ref<any>(null)
const dialNumber = ref('')
const transferNumber = ref('')
const isMuted = ref(false)
const isOnHold = ref(false)
const showSettings = ref(false)
const callDuration = ref('00:00')
const selectedAudioDevice = ref<string>('')
const selectedMicDevice = ref<string>('')
const audioDevices = ref<any[]>([])
const micDevices = ref<any[]>([])

let sipUA: any = null
let durationInterval: any = null

const dialPadDigits = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']

// SIP Settings
const sipSettings = computed(() => ({
  extension: user.value?.extension || '1000',
  server: config.public.wsBase?.replace('/ws', '') || 'wss://localhost:8080',
  password: user.value?.sip_password || 'password'
}))

// Status computed properties
const statusClass = computed(() => {
  if (currentCall.value?.isEstablished) return 'bg-green-500 text-white'
  if (currentCall.value) return 'bg-yellow-500 text-white'
  if (isRegistered.value) return 'bg-blue-500 text-white'
  return 'bg-gray-500 text-white'
})

const statusIcon = computed(() => {
  if (currentCall.value?.isEstablished) return 'i-heroicons-phone'
  if (currentCall.value) return 'i-heroicons-phone-arrow-up-right'
  if (isRegistered.value) return 'i-heroicons-signal'
  return 'i-heroicons-signal-slash'
})

const statusText = computed(() => {
  if (currentCall.value?.isEstablished) return 'En llamada'
  if (currentCall.value) return 'Llamando...'
  if (isRegistered.value) return 'Disponible'
  return 'Desconectado'
})

// Initialize WebPhone
onMounted(async () => {
  await initializeWebPhone()
  await getMediaDevices()
})

onUnmounted(() => {
  if (sipUA) {
    sipUA.stop()
  }
  clearInterval(durationInterval)
})

async function initializeWebPhone() {
  try {
    const socket = new JsSIP.WebSocketInterface(`${sipSettings.value.server}`)
    
    const configuration = {
      sockets: [socket],
      uri: `sip:${sipSettings.value.extension}@${sipSettings.value.server}`,
      password: sipSettings.value.password,
      display_name: user.value?.name || 'Agent',
      session_timers: false,
      register: true
    }

    sipUA = new JsSIP.UA(configuration)

    // Event Listeners
    sipUA.on('registered', () => {
      isRegistered.value = true
      console.log('WebPhone registered')
    })

    sipUA.on('unregistered', () => {
      isRegistered.value = false
      console.log('WebPhone unregistered')
    })

    sipUA.on('registrationFailed', (e: any) => {
      console.error('Registration failed:', e)
      isRegistered.value = false
    })

    sipUA.on('newRTCSession', (data: any) => {
      const session = data.session

      if (session.direction === 'incoming') {
        handleIncomingCall(session)
      } else {
        handleOutgoingCall(session)
      }
    })

    sipUA.start()
  } catch (error) {
    console.error('Error initializing WebPhone:', error)
  }
}

function handleIncomingCall(session: any) {
  currentCall.value = {
    session,
    direction: 'incoming',
    remoteIdentity: session.remote_identity.uri.user,
    isEstablished: false
  }

  session.on('accepted', () => {
    currentCall.value.isEstablished = true
    startCallDuration()
  })

  session.on('ended', endCall)
  session.on('failed', endCall)
}

function handleOutgoingCall(session: any) {
  currentCall.value = {
    session,
    direction: 'outgoing',
    remoteIdentity: dialNumber.value,
    isEstablished: false
  }

  session.on('progress', () => {
    console.log('Call in progress...')
  })

  session.on('accepted', () => {
    currentCall.value.isEstablished = true
    startCallDuration()
  })

  session.on('ended', endCall)
  session.on('failed', endCall)
}

function makeCall() {
  if (!sipUA || !dialNumber.value) return

  const options = {
    mediaConstraints: {
      audio: true,
      video: false
    }
  }

  sipUA.call(`sip:${dialNumber.value}@${sipSettings.value.server}`, options)
}

function answerCall() {
  if (!currentCall.value?.session) return

  const options = {
    mediaConstraints: {
      audio: true,
      video: false
    }
  }

  currentCall.value.session.answer(options)
}

function hangup() {
  if (currentCall.value?.session) {
    currentCall.value.session.terminate()
  }
}

function endCall() {
  currentCall.value = null
  dialNumber.value = ''
  isMuted.value = false
  isOnHold.value = false
  clearInterval(durationInterval)
}

function toggleMute() {
  if (!currentCall.value?.session) return

  if (isMuted.value) {
    currentCall.value.session.unmute()
  } else {
    currentCall.value.session.mute()
  }
  isMuted.value = !isMuted.value
}

function toggleHold() {
  if (!currentCall.value?.session) return

  if (isOnHold.value) {
    currentCall.value.session.unhold()
  } else {
    currentCall.value.session.hold()
  }
  isOnHold.value = !isOnHold.value
}

function transferCall() {
  if (!currentCall.value?.session || !transferNumber.value) return

  currentCall.value.session.refer(`sip:${transferNumber.value}@${sipSettings.value.server}`)
  transferNumber.value = ''
}

function dialDigit(digit: string) {
  dialNumber.value += digit

  // Send DTMF if in call
  if (currentCall.value?.isEstablished) {
    currentCall.value.session.sendDTMF(digit)
  }
}

function startCallDuration() {
  let seconds = 0
  durationInterval = setInterval(() => {
    seconds++
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    callDuration.value = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }, 1000)
}

function register() {
  if (sipUA) {
    sipUA.register()
  }
}

function unregister() {
  if (sipUA) {
    sipUA.unregister()
  }
}

async function getMediaDevices() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    
    audioDevices.value = devices
      .filter(d => d.kind === 'audiooutput')
      .map(d => ({ label: d.label || `Speaker ${d.deviceId}`, value: d.deviceId }))
    
    micDevices.value = devices
      .filter(d => d.kind === 'audioinput')
      .map(d => ({ label: d.label || `Microphone ${d.deviceId}`, value: d.deviceId }))

    if (audioDevices.value.length > 0) {
      selectedAudioDevice.value = audioDevices.value[0].value
    }
    if (micDevices.value.length > 0) {
      selectedMicDevice.value = micDevices.value[0].value
    }
  } catch (error) {
    console.error('Error getting media devices:', error)
  }
}
</script>

<style scoped>
.webphone-container {
  @apply bg-white rounded-lg shadow-lg p-4 max-w-md mx-auto;
}

.phone-status {
  @apply p-3 rounded-lg mb-4;
}

.active-call {
  @apply space-y-4 mb-4;
}

.call-info {
  @apply text-center p-4 bg-gray-50 rounded-lg;
}

.call-controls {
  @apply flex gap-2 justify-center flex-wrap;
}

.transfer-controls {
  @apply flex gap-2;
}

.dialer-pad {
  @apply mb-4;
}

.phone-settings {
  @apply border-t pt-4;
}
</style>
