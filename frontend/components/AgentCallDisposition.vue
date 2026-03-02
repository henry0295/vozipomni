<template>
  <div class="call-disposition-panel">
    <UCard>
      <template #header>
        <h3 class="text-lg font-semibold">Disposición de Llamada</h3>
      </template>

      <div v-if="showDisposition" class="space-y-4">
        <!-- Información de la llamada -->
        <div class="p-4 bg-blue-50 rounded-lg">
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p class="text-gray-600">Cliente:</p>
              <p class="font-semibold">{{ callInfo.customer || 'Desconocido' }}</p>
            </div>
            <div>
              <p class="text-gray-600">Número:</p>
              <p class="font-semibold">{{ callInfo.number }}</p>
            </div>
            <div>
              <p class="text-gray-600">Duración:</p>
              <p class="font-semibold">{{ callInfo.duration }}</p>
            </div>
            <div>
              <p class="text-gray-600">Campaña:</p>
              <p class="font-semibold">{{ callInfo.campaign || 'N/A' }}</p>
            </div>
          </div>
        </div>

        <!-- Disposiciones disponibles -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-gray-700">Resultado de la llamada *</label>
          <div class="grid grid-cols-2 gap-2">
            <UButton
              v-for="disposition in dispositions"
              :key="disposition.code"
              block
              :color="selectedDisposition?.code === disposition.code ? 'primary' : 'gray'"
              :variant="selectedDisposition?.code === disposition.code ? 'solid' : 'outline'"
              @click="selectDisposition(disposition)"
            >
              <div class="text-left w-full">
                <p class="font-medium">{{ disposition.name }}</p>
                <p v-if="disposition.description" class="text-xs opacity-75">{{ disposition.description }}</p>
              </div>
            </UButton>
          </div>
        </div>

        <!-- Callback - si la disposición lo requiere -->
        <div v-if="selectedDisposition?.requires_callback" class="space-y-2">
          <label class="text-sm font-medium text-gray-700">Programar callback</label>
          <div class="grid grid-cols-2 gap-2">
            <UInput
              v-model="callbackDate"
              type="date"
              placeholder="Fecha"
            />
            <UInput
              v-model="callbackTime"
              type="time"
              placeholder="Hora"
            />
          </div>
        </div>

        <!-- Notas -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-gray-700">Notas de la llamada</label>
          <UTextarea
            v-model="notes"
            :rows="4"
            placeholder="Ingrese observaciones o detalles importantes de la llamada..."
          />
        </div>

        <!-- Información adicional del contacto -->
        <div v-if="currentCampaign?.form_fields" class="space-y-3 p-4 bg-gray-50 rounded-lg">
          <p class="text-sm font-medium text-gray-700">Información del Contacto</p>
          <div
            v-for="field in currentCampaign.form_fields"
            :key="field.name"
            class="space-y-1"
          >
            <label class="text-sm text-gray-600">{{ field.label }}</label>
            <UInput
              v-if="field.type === 'text' || field.type === 'email' || field.type === 'tel'"
              v-model="formData[field.name]"
              :type="field.type"
              :placeholder="field.placeholder"
            />
            <UTextarea
              v-else-if="field.type === 'textarea'"
              v-model="formData[field.name]"
              :rows="2"
              :placeholder="field.placeholder"
            />
            <USelect
              v-else-if="field.type === 'select'"
              v-model="formData[field.name]"
              :options="field.options"
            />
          </div>
        </div>

        <!-- Botones de acción -->
        <div class="flex gap-2 pt-2">
          <UButton
            block
            size="lg"
            color="primary"
            :disabled="!selectedDisposition || isSaving"
            :loading="isSaving"
            @click="saveDisposition"
          >
            Guardar y Continuar
          </UButton>
        </div>

        <!-- Timer de wrapup -->
        <div class="text-center">
          <p class="text-xs text-gray-500">
            Tiempo restante: <span class="font-mono font-semibold">{{ wrapupTimeRemaining }}s</span>
          </p>
        </div>
      </div>

      <!-- Estado sin llamada para disposición -->
      <div v-else class="text-center py-8 text-gray-500">
        <UIcon name="i-heroicons-clipboard-document-list" class="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>No hay llamada para calificar</p>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '~/stores/agent'

const agentStore = useAgentStore()

// Props
interface Props {
  callInfo?: {
    customer?: string
    number: string
    duration: string
    campaign?: string
    contactId?: number
  }
  campaignId?: number
}

const props = withDefaults(defineProps<Props>(), {
  callInfo: () => ({ number: '', duration: '00:00', customer: '', campaign: '' })
})

// Emits
const emit = defineEmits<{
  dispositionSaved: [data: any]
}>()

// State
const selectedDisposition = ref<any>(null)
const notes = ref('')
const callbackDate = ref('')
const callbackTime = ref('')
const formData = ref<Record<string, any>>({})
const isSaving = ref(false)
const wrapupTimeRemaining = ref(10)
const currentCampaign = ref<any>(null)

// Timer de wrapup
let wrapupTimer: any = null

// Disposiciones disponibles (se cargan según la campaña)
const dispositions = ref([
  {
    id: 1,
    code: 'CONNECTED',
    name: 'Contactado',
    description: 'Cliente contactado exitosamente',
    is_success: true,
    requires_callback: false
  },
  {
    id: 2,
    code: 'NOT_AVAILABLE',
    name: 'No Disponible',
    description: 'Cliente no puede atender',
    is_success: false,
    requires_callback: true
  },
  {
    id: 3,
    code: 'NO_ANSWER',
    name: 'No Contesta',
    description: 'No hubo respuesta',
    is_success: false,
    requires_callback: false
  },
  {
    id: 4,
    code: 'BUSY',
    name: 'Ocupado',
    description: 'Línea ocupada',
    is_success: false,
    requires_callback: true
  },
  {
    id: 5,
    code: 'SALE',
    name: 'Venta',
    description: 'Venta realizada',
    is_success: true,
    requires_callback: false
  },
  {
    id: 6,
    code: 'NOT_INTERESTED',
    name: 'No Interesado',
    description: 'Cliente no está interesado',
    is_success: false,
    requires_callback: false
  },
  {
    id: 7,
    code: 'CALLBACK',
    name: 'Callback',
    description: 'Cliente solicita ser contactado',
    is_success: false,
    requires_callback: true
  },
  {
    id: 8,
    code: 'WRONG_NUMBER',
    name: 'Número Erróneo',
    description: 'Número equivocado',
    is_success: false,
    requires_callback: false
  }
])

// Computed
const showDisposition = computed(() => {
  return agentStore.status === 'wrapup' || agentStore.currentCall !== null
})

// Methods
const selectDisposition = (disposition: any) => {
  selectedDisposition.value = disposition
}

const saveDisposition = async () => {
  if (!selectedDisposition.value) {
    alert('Debe seleccionar una disposición')
    return
  }

  isSaving.value = true

  try {
    // Preparar datos
    const dispositionData = {
      disposition_code: selectedDisposition.value.code,
      disposition_name: selectedDisposition.value.name,
      notes: notes.value,
      contact_id: props.callInfo.contactId,
      campaign_id: props.campaignId,
      callback_date: selectedDisposition.value.requires_callback && callbackDate.value
        ? `${callbackDate.value} ${callbackTime.value || '09:00'}`
        : null,
      form_data: formData.value
    }

    // Aquí se enviaría a la API
    // const { saveCampaignDisposition } = useCampaigns()
    // await saveCampaignDisposition(dispositionData)

    // Emitir evento
    emit('dispositionSaved', dispositionData)

    // Limpiar formulario
    resetForm()

    // Volver a disponible
    await agentStore.changeStatus('available')
  } catch (err: any) {
    alert(`Error al guardar disposición: ${err.message}`)
  } finally {
    isSaving.value = false
  }
}

const resetForm = () => {
  selectedDisposition.value = null
  notes.value = ''
  callbackDate.value = ''
  callbackTime.value = ''
  formData.value = {}
}

const startWrapupTimer = () => {
  wrapupTimeRemaining.value = 10
  
  wrapupTimer = setInterval(() => {
    wrapupTimeRemaining.value--
    
    if (wrapupTimeRemaining.value <= 0) {
      stopWrapupTimer()
      // Auto-guardar si no ha guardado
      if (selectedDisposition.value) {
        saveDisposition()
      }
    }
  }, 1000)
}

const stopWrapupTimer = () => {
  if (wrapupTimer) {
    clearInterval(wrapupTimer)
    wrapupTimer = null
  }
}

// Cargar disposiciones de la campaña
const loadCampaignDispositions = async (campaignId: number) => {
  try {
    // const { getCampaign } = useCampaigns()
    // const campaign = await getCampaign(campaignId)
    // currentCampaign.value = campaign
    // if (campaign.dispositions) {
    //   dispositions.value = campaign.dispositions
    // }
  } catch (err) {
    console.error('Error loading campaign dispositions:', err)
  }
}

// Watchers
watch(() => agentStore.status, (newStatus) => {
  if (newStatus === 'wrapup') {
    startWrapupTimer()
  } else {
    stopWrapupTimer()
    resetForm()
  }
})

watch(() => props.campaignId, (newCampaignId) => {
  if (newCampaignId) {
    loadCampaignDispositions(newCampaignId)
  }
})

// Lifecycle
onMounted(() => {
  if (agentStore.status === 'wrapup') {
    startWrapupTimer()
  }
  if (props.campaignId) {
    loadCampaignDispositions(props.campaignId)
  }
})

onUnmounted(() => {
  stopWrapupTimer()
})
</script>

<style scoped>
.call-disposition-panel {
  height: 100%;
}
</style>
