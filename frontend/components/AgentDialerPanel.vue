<template>
  <div class="dialer-panel">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold flex items-center gap-2">
            <UIcon name="i-heroicons-phone-arrow-up-right" />
            Marcación Automática
          </h3>
          <UBadge :color="dialerStatus === 'active' ? 'green' : 'gray'">
            {{ dialerStatusLabel }}
          </UBadge>
        </div>
      </template>

      <!-- Estado del dialer -->
      <div class="space-y-4">
        <!-- Información de la campaña dialer -->
        <div v-if="activeCampaign" class="p-4 bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg">
          <div class="flex items-start justify-between mb-3">
            <div>
              <h4 class="font-semibold text-blue-900">{{ activeCampaign.name }}</h4>
              <p class="text-sm text-blue-700">{{ getDialerTypeLabel(activeCampaign.dialer_type) }}</p>
            </div>
            <UBadge :color="getDialerTypeColor(activeCampaign.dialer_type)">
              {{ activeCampaign.dialer_type }}
            </UBadge>
          </div>

          <!-- Progreso de la campaña -->
          <div class="space-y-2">
            <div class="flex justify-between text-sm text-blue-800">
              <span>Contactos marcados</span>
              <span class="font-semibold">{{ activeCampaign.contacted }} / {{ activeCampaign.total_contacts }}</span>
            </div>
            <div class="w-full bg-blue-200 rounded-full h-2">
              <div
                class="bg-blue-600 h-2 rounded-full transition-all"
                :style="{ width: `${(activeCampaign.contacted / activeCampaign.total_contacts) * 100}%` }"
              />
            </div>
          </div>
        </div>

        <!-- Sin campaña dialer activa -->
        <div v-else class="text-center py-8 text-gray-500">
          <UIcon name="i-heroicons-phone-arrow-up-right" class="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>No hay campaña de dialer activa</p>
        </div>

        <!-- Estado del agente para dialer -->
        <div v-if="activeCampaign" class="grid grid-cols-2 gap-3">
          <div class="p-3 bg-green-50 rounded-lg">
            <p class="text-xs text-green-600 mb-1">Llamadas Contestadas</p>
            <p class="text-2xl font-bold text-green-700">{{ dialerStats.answered }}</p>
          </div>
          <div class="p-3 bg-yellow-50 rounded-lg">
            <p class="text-xs text-yellow-600 mb-1">Sin Respuesta</p>
            <p class="text-2xl font-bold text-yellow-700">{{ dialerStats.no_answer }}</p>
          </div>
          <div class="p-3 bg-blue-50 rounded-lg">
            <p class="text-xs text-blue-600 mb-1">Ocupado</p>
            <p class="text-2xl font-bold text-blue-700">{{ dialerStats.busy }}</p>
          </div>
          <div class="p-3 bg-purple-50 rounded-lg">
            <p class="text-xs text-purple-600 mb-1">Transferencias</p>
            <p class="text-2xl font-bold text-purple-700">{{ dialerStats.transferred }}</p>
          </div>
        </div>

        <!-- Próxima llamada (Preview/Progressive) -->
        <div v-if="activeCampaign && nextContact && ['preview', 'progressive'].includes(activeCampaign.dialer_type)" class="border-t pt-4">
          <p class="text-sm font-medium text-gray-700 mb-3">Próximo Contacto</p>
          
          <div class="p-4 bg-gray-50 rounded-lg">
            <div class="flex items-start justify-between mb-3">
              <div class="flex-1">
                <h5 class="font-semibold text-gray-800">{{ nextContact.name }}</h5>
                <p class="text-sm text-gray-600">
                  <UIcon name="i-heroicons-phone" class="inline h-3 w-3" />
                  {{ nextContact.phone }}
                </p>
                <p v-if="nextContact.email" class="text-sm text-gray-600">
                  <UIcon name="i-heroicons-envelope" class="inline h-3 w-3" />
                  {{ nextContact.email }}
                </p>
              </div>
            </div>

            <!-- Información adicional del contacto -->
            <div v-if="nextContact.notes" class="mb-3 p-2 bg-blue-50 rounded text-sm">
              <p class="text-xs text-blue-600 font-medium mb-1">Notas previas:</p>
              <p class="text-blue-800">{{ nextContact.notes }}</p>
            </div>

            <!-- Botones de acción (Preview) -->
            <div v-if="activeCampaign.dialer_type === 'preview'" class="flex gap-2">
              <UButton
                block
                color="green"
                icon="i-heroicons-phone"
                :loading="isDialing"
                @click="acceptContact"
              >
                Marcar Ahora
              </UButton>
              <UButton
                block
                color="gray"
                variant="outline"
                icon="i-heroicons-forward"
                @click="skipContact"
              >
                Siguiente
              </UButton>
            </div>

            <!-- Countdown para Progressive -->
            <div v-else-if="activeCampaign.dialer_type === 'progressive'" class="text-center">
              <p class="text-sm text-gray-600 mb-2">Marcación automática en:</p>
              <p class="text-3xl font-bold text-blue-600">{{ countdown }}s</p>
              <UButton
                color="red"
                variant="soft"
                size="sm"
                class="mt-2"
                @click="cancelAutoDial"
              >
                Cancelar
              </UButton>
            </div>
          </div>
        </div>

        <!-- Modo Predictivo (sin vista previa) -->
        <div v-if="activeCampaign && activeCampaign.dialer_type === 'predictive'" class="border-t pt-4">
          <div class="text-center py-6">
            <div class="relative inline-block">
              <div class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></div>
              <UIcon name="i-heroicons-phone" class="relative h-12 w-12 text-blue-600" />
            </div>
            <p class="text-lg font-semibold text-gray-700 mt-4">Marcación Predictiva Activa</p>
            <p class="text-sm text-gray-600 mt-2">Esperando llamada conectada...</p>
          </div>
        </div>

        <!-- Script de la campaña -->
        <div v-if="activeCampaign && activeCampaign.script" class="border-t pt-4">
          <p class="text-sm font-medium text-gray-700 mb-2">Script de Campaña</p>
          <div class="p-3 bg-purple-50 rounded-lg">
            <p class="text-sm text-purple-900 whitespace-pre-wrap">{{ activeCampaign.script }}</p>
          </div>
        </div>

        <!-- Controles del dialer -->
        <div v-if="activeCampaign" class="flex gap-2 pt-4 border-t">
          <UButton
            v-if="dialerStatus === 'paused'"
            block
            color="green"
            icon="i-heroicons-play"
            @click="resumeDialer"
          >
            Reanudar Dialer
          </UButton>
          <UButton
            v-else
            block
            color="yellow"
            icon="i-heroicons-pause"
            @click="pauseDialer"
          >
            Pausar Dialer
          </UButton>
        </div>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '~/stores/agent'

interface DialerCampaign {
  id: number
  name: string
  dialer_type: 'preview' | 'progressive' | 'predictive'
  total_contacts: number
  contacted: number
  script?: string
}

interface NextContact {
  id: number
  name: string
  phone: string
  email?: string
  company?: string
  notes?: string
}

interface DialerStats {
  answered: number
  no_answer: number
  busy: number
  transferred: number
}

// Props
interface Props {
  campaignId?: number
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  callContact: [contact: NextContact]
  skipContact: [contactId: number]
}>()

const agentStore = useAgentStore()

// State
const activeCampaign = ref<DialerCampaign | null>(null)
const nextContact = ref<NextContact | null>(null)
const dialerStatus = ref<'active' | 'paused' | 'stopped'>('stopped')
const isDialing = ref(false)
const countdown = ref(10)
const dialerStats = ref<DialerStats>({
  answered: 0,
  no_answer: 0,
  busy: 0,
  transferred: 0
})

let countdownInterval: any = null

// Computed
const dialerStatusLabel = computed(() => {
  const labels: Record<string, string> = {
    active: 'Activo',
    paused: 'Pausado',
    stopped: 'Detenido'
  }
  return labels[dialerStatus.value] || dialerStatus.value
})

// Methods
const getDialerTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    preview: 'Preview',
    progressive: 'Progresivo',
    predictive: 'Predictivo'
  }
  return labels[type] || type
}

const getDialerTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    preview: 'blue',
    progressive: 'green',
    predictive: 'purple'
  }
  return colors[type] || 'gray'
}

const loadDialerCampaign = async () => {
  if (!props.campaignId) return

  try {
    // Cargar campaña dialer
    // Mock data
    activeCampaign.value = {
      id: props.campaignId,
      name: 'Campaña Progresiva Ventas',
      dialer_type: 'progressive',
      total_contacts: 500,
      contacted: 150,
      script: 'Buenos días, mi nombre es {AGENT_NAME} de {COMPANY}.\n\nLe llamo para ofrecerle información sobre nuestros nuevos productos.\n\n¿Tiene un momento para hablar?'
    }

    dialerStatus.value = 'active'
    loadNextContact()
  } catch (err) {
    console.error('Error loading dialer campaign:', err)
  }
}

const loadNextContact = async () => {
  if (!activeCampaign.value) return

  // Mock next contact
  nextContact.value = {
    id: Date.now(),
    name: 'María González',
    phone: '+573001234567',
    email: 'maria@example.com',
    company: 'Empresa ABC',
    notes: 'Cliente interesado en productos premium. Llamada anterior: Solicitud de información.'
  }

  // Si es progresivo, iniciar countdown
  if (activeCampaign.value.dialer_type === 'progressive') {
    startCountdown()
  }
}

const acceptContact = async () => {
  if (!nextContact.value) return

  isDialing.value = true
  
  // Emitir evento para realizar llamada
  emit('callContact', nextContact.value)
  
  dialerStats.value.answered++
  
  // Limpiar contacto actual
  nextContact.value = null
  
  isDialing.value = false
}

const skipContact = () => {
  if (!nextContact.value) return

  emit('skipContact', nextContact.value.id)
  
  // Cargar siguiente
  loadNextContact()
}

const startCountdown = () => {
  stopCountdown()
  countdown.value = 10

  countdownInterval = setInterval(() => {
    countdown.value--
    
    if (countdown.value <= 0) {
      stopCountdown()
      // Auto-marcar
      acceptContact()
    }
  }, 1000)
}

const stopCountdown = () => {
  if (countdownInterval) {
    clearInterval(countdownInterval)
    countdownInterval = null
  }
}

const cancelAutoDial = () => {
  stopCountdown()
  countdown.value = 10
  skipContact()
}

const pauseDialer = () => {
  dialerStatus.value = 'paused'
  stopCountdown()
}

const resumeDialer = () => {
  dialerStatus.value = 'active'
  
  if (activeCampaign.value?.dialer_type === 'progressive' && nextContact.value) {
    startCountdown()
  } else {
    loadNextContact()
  }
}

// Watch
watch(() => props.campaignId, (newId) => {
  if (newId) {
    loadDialerCampaign()
  } else {
    activeCampaign.value = null
    nextContact.value = null
    dialerStatus.value = 'stopped'
  }
}, { immediate: true })

watch(() => agentStore.status, (newStatus) => {
  // Pausar dialer si el agente no está disponible
  if (newStatus !== 'available' && dialerStatus.value === 'active') {
    pauseDialer()
  }
})

// Lifecycle
onMounted(() => {
  if (props.campaignId) {
    loadDialerCampaign()
  }
})

onUnmounted(() => {
  stopCountdown()
})
</script>

<style scoped>
.dialer-panel {
  height: 100%;
}
</style>
