<template>
  <div class="call-disposition-panel">
    <UCard :ui="{ body: { padding: 'p-3' }, header: { padding: 'px-3 py-2' } }">
      <template #header>
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200">Resultado de la llamada *</h3>
      </template>

      <div v-if="showDisposition" class="space-y-3">
        <!-- Disposiciones disponibles — grid 2 columnas compacto -->
        <div class="grid grid-cols-2 gap-1.5">
          <button
            v-for="disposition in dispositions"
            :key="disposition.code"
            class="disposition-btn"
            :class="selectedDisposition?.code === disposition.code ? 'disposition-btn--active' : ''"
            @click="selectDisposition(disposition)"
          >
            <span class="disposition-name">{{ disposition.name }}</span>
            <span v-if="disposition.description" class="disposition-desc">{{ disposition.description }}</span>
          </button>
        </div>

        <!-- Callback — solo cuando lo requiere la disposición -->
        <div v-if="selectedDisposition?.requires_callback" class="rounded-lg border border-blue-200 bg-blue-50 dark:bg-blue-900/20 p-2.5 space-y-1.5">
          <p class="text-xs font-semibold text-blue-700 dark:text-blue-300">Programar callback</p>
          <div class="grid grid-cols-2 gap-1.5">
            <UInput v-model="callbackDate" type="date" size="sm" />
            <UInput v-model="callbackTime" type="time" size="sm" />
          </div>
        </div>

        <!-- Notas de la llamada -->
        <div class="space-y-1">
          <label class="text-xs font-medium text-gray-600 dark:text-gray-400">Notas de la llamada</label>
          <UTextarea
            v-model="notes"
            :rows="3"
            placeholder="Ingrese observaciones o detalles importantes de la llamada..."
            :ui="{ base: 'text-sm' }"
          />
        </div>

        <!-- Campos del formulario de campaña -->
        <div v-if="currentCampaign?.form_fields?.length" class="space-y-2 p-2.5 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <p class="text-xs font-medium text-gray-600 dark:text-gray-400">Información del Contacto</p>
          <div v-for="field in currentCampaign.form_fields" :key="field.name" class="space-y-0.5">
            <label class="text-xs text-gray-500">{{ field.label }}</label>
            <UInput v-if="field.type !== 'textarea' && field.type !== 'select'" v-model="formData[field.name]" :type="field.type" size="sm" :placeholder="field.placeholder" />
            <UTextarea v-else-if="field.type === 'textarea'" v-model="formData[field.name]" :rows="2" size="sm" :placeholder="field.placeholder" />
            <USelect v-else v-model="formData[field.name]" :options="field.options" size="sm" />
          </div>
        </div>

        <!-- Guardar -->
        <UButton
          block
          size="sm"
          color="primary"
          :disabled="!selectedDisposition || isSaving"
          :loading="isSaving"
          @click="saveDisposition"
        >
          Guardar y Continuar
        </UButton>

        <!-- Timer wrapup -->
        <p class="text-center text-xs text-gray-400">
          Tiempo restante: <span class="font-mono font-semibold">{{ wrapupTimeRemaining }}s</span>
        </p>
      </div>

      <!-- Sin llamada -->
      <div v-else class="py-6 text-center text-gray-400">
        <UIcon name="i-heroicons-clipboard-document-list" class="h-10 w-10 mx-auto mb-1.5 opacity-40" />
        <p class="text-xs">No hay llamada para calificar</p>
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

const safeCallInfo = computed(() => props.callInfo ?? { number: '', duration: '00:00', customer: '', campaign: '' })

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
    useToast().add({ title: 'Debe seleccionar una disposición', color: 'orange' })
    return
  }

  if (!agentStore.agent) {
    useToast().add({ title: 'No hay agente logueado', color: 'red' })
    return
  }

  isSaving.value = true

  try {
    const { $api } = useNuxtApp()
    
    // Preparar datos
    const dispositionData = {
      call_id: agentStore.currentCall?.callId,
      disposition_code: selectedDisposition.value.code,
      notes: notes.value,
      contact_id: props.callInfo?.contactId,
      campaign_id: props.campaignId,
      callback_date: selectedDisposition.value.requires_callback && callbackDate.value
        ? `${callbackDate.value}T${callbackTime.value || '09:00'}:00`
        : null,
      form_data: formData.value
    }

    // Guardar vía API
    await $api(`/agents/${agentStore.agent.id}/save_disposition/`, {
      method: 'POST',
      body: dispositionData
    })

    useToast().add({ title: 'Disposición guardada exitosamente', color: 'green' })

    // Emitir evento
    emit('dispositionSaved', dispositionData)

    // Limpiar formulario
    resetForm()

    // Volver a disponible
    await agentStore.changeStatus('available')
  } catch (err: any) {
    useToast().add({ 
      title: 'Error al guardar disposición', 
      description: err?.data?.error || err.message,
      color: 'red'
    })
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
    const { $api } = useNuxtApp()
    const campaign = await $api(`/campaigns/${campaignId}/`)
    
    currentCampaign.value = campaign
    
    // Usar disposiciones de la campaña si existen
    if (campaign.dispositions && campaign.dispositions.length > 0) {
      dispositions.value = campaign.dispositions
    }
  } catch (err) {
    console.error('Error loading campaign dispositions:', err)
    // Mantener disposiciones por defecto
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

/* Botones de disposición compactos con altura fija */
.disposition-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  width: 100%;
  min-height: 52px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1.5px solid #e5e7eb;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.disposition-btn:hover {
  border-color: #6366f1;
  background: #f5f3ff;
}

.disposition-btn--active {
  border-color: #6366f1;
  background: #6366f1;
  color: #fff;
}

.disposition-name {
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.2;
}

.disposition-desc {
  font-size: 0.6875rem;
  opacity: 0.75;
  line-height: 1.2;
  margin-top: 1px;
}

:global(.dark) .disposition-btn {
  background: #1f2937;
  border-color: #374151;
  color: #f9fafb;
}

:global(.dark) .disposition-btn:hover {
  border-color: #818cf8;
  background: #312e81;
}

:global(.dark) .disposition-btn--active {
  background: #4f46e5;
  border-color: #4f46e5;
  color: #fff;
}
</style>
