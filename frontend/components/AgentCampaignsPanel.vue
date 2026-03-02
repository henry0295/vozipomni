<template>
  <div class="campaigns-panel">
    <UCard>
      <template #header>
        <h3 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-heroicons-megaphone" />
          Campañas Activas
        </h3>
      </template>

      <!-- Lista de campañas -->
      <div v-if="campaigns.length > 0" class="space-y-3">
        <div
          v-for="campaign in campaigns"
          :key="campaign.id"
          class="campaign-card"
          :class="{ 'active': campaign.id === selectedCampaignId }"
          @click="selectCampaign(campaign)"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <h4 class="font-semibold text-gray-800">{{ campaign.name }}</h4>
                <UBadge :color="getCampaignTypeColor(campaign.campaign_type)" size="xs">
                  {{ getCampaignTypeLabel(campaign.campaign_type) }}
                </UBadge>
              </div>
              
              <p class="text-sm text-gray-600 mb-3">{{ campaign.description }}</p>

              <!-- Estadísticas de la campaña -->
              <div class="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <p class="text-gray-500">Contactos</p>
                  <p class="font-semibold text-gray-700">{{ campaign.total_contacts }}</p>
                </div>
                <div>
                  <p class="text-gray-500">Contactados</p>
                  <p class="font-semibold text-blue-600">{{ campaign.contacted }}</p>
                </div>
                <div>
                  <p class="text-gray-500">Exitosos</p>
                  <p class="font-semibold text-green-600">{{ campaign.successful }}</p>
                </div>
              </div>

              <!-- Progreso -->
              <div class="mt-3">
                <div class="flex items-center justify-between text-xs mb-1">
                  <span class="text-gray-600">Avance</span>
                  <span class="font-semibold text-gray-700">{{ campaign.progress }}%</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2">
                  <div
                    class="bg-blue-600 h-2 rounded-full transition-all"
                    :style="{ width: `${campaign.progress}%` }"
                  />
                </div>
              </div>

              <!-- Script de la campaña (si está seleccionada) -->
              <div v-if="campaign.id === selectedCampaignId && campaign.script" class="mt-3 p-3 bg-blue-50 rounded-lg">
                <p class="text-xs font-medium text-blue-800 mb-2">Script:</p>
                <p class="text-sm text-blue-900 whitespace-pre-wrap">{{ campaign.script }}</p>
              </div>
            </div>

            <!-- Indicador de selección -->
            <div v-if="campaign.id === selectedCampaignId" class="ml-2">
              <div class="w-3 h-3 bg-blue-500 rounded-full" />
            </div>
          </div>
        </div>
      </div>

      <!-- Sin campañas -->
      <div v-else class="text-center py-8 text-gray-500">
        <UIcon name="i-heroicons-megaphone" class="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>No hay campañas activas</p>
      </div>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '~/stores/agent'

// State
const campaigns = ref<any[]>([])
const selectedCampaignId = ref<number | null>(null)
const isLoading = ref(false)

const agentStore = useAgentStore()

// Methods
const loadCampaigns = async () => {
  if (!agentStore.agent) return

  isLoading.value = true
  try {
    // Cargar campañas asignadas al agente
    // const { getCampaigns } = useCampaigns()
    // const result = await getCampaigns({ 
    //   agent_id: agentStore.agent.id,
    //   status: 'active'
    // })
    
    // Mock data mientras se implementa la API
    campaigns.value = [
      {
        id: 1,
        name: 'Campaña de Ventas 2024',
        description: 'Promoción de productos nuevos',
        campaign_type: 'progressive',
        total_contacts: 1000,
        contacted: 450,
        successful: 120,
        progress: 45,
        script: 'Buenos días, mi nombre es {AGENT_NAME} de {COMPANY}. ¿Cómo está el día de hoy?\n\nLe llamo para ofrecerle nuestra nueva línea de productos...'
      },
      {
        id: 2,
        name: 'Encuesta de Satisfacción',
        description: 'Evaluación post-venta',
        campaign_type: 'preview',
        total_contacts: 500,
        contacted: 300,
        successful: 250,
        progress: 60,
        script: 'Hola, soy {AGENT_NAME}. ¿Tiene un momento para una breve encuesta sobre nuestro servicio?'
      }
    ]

    // Seleccionar la primera campaña por defecto
    if (campaigns.value.length > 0 && !selectedCampaignId.value) {
      selectedCampaignId.value = campaigns.value[0].id
    }
  } catch (err) {
    console.error('Error loading campaigns:', err)
  } finally {
    isLoading.value = false
  }
}

const selectCampaign = (campaign: any) => {
  selectedCampaignId.value = campaign.id
}

const getCampaignTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    manual: 'Manual',
    preview: 'Preview',
    progressive: 'Progresivo',
    predictive: 'Predictivo'
  }
  return labels[type] || type
}

const getCampaignTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    manual: 'gray',
    preview: 'blue',
    progressive: 'green',
    predictive: 'purple'
  }
  return colors[type] || 'gray'
}

// Computed
const selectedCampaign = computed(() => {
  return campaigns.value.find(c => c.id === selectedCampaignId.value)
})

// Auto-refresh cada 30 segundos
let refreshInterval: any = null

onMounted(() => {
  loadCampaigns()
  
  refreshInterval = setInterval(() => {
    loadCampaigns()
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

// Exponer campaña seleccionada
defineExpose({
  selectedCampaign,
  selectedCampaignId
})
</script>

<style scoped>
.campaign-card {
  @apply p-4 rounded-lg border-2 border-gray-200 cursor-pointer transition-all hover:border-blue-300 hover:shadow-sm;
}

.campaign-card.active {
  @apply border-blue-500 bg-blue-50;
}
</style>
