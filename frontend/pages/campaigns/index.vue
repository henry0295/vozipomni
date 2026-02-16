<template>
  <div>
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Campañas</h1>
        <p class="text-gray-600 mt-2">Gestión de campañas de marcación</p>
      </div>
      <UButton
        icon="i-heroicons-plus"
        size="lg"
        @click="showCreateModal = true"
      >
        Nueva Campaña
      </UButton>
    </div>

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle" class="mb-6">
      {{ error }}
    </UAlert>

    <UCard v-if="loading" class="flex justify-center items-center py-12 mb-6">
      <div class="text-center space-y-2">
        <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto" />
        <p class="text-gray-500">Cargando campañas...</p>
      </div>
    </UCard>

    <!-- Tabs de estado -->
    <UTabs 
      :items="tabs" 
      v-model="activeTab"
      class="mb-6"
    />

    <!-- Grid de campañas -->
    <div v-if="!loading && filteredCampaigns.length" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <UCard
        v-for="campaign in filteredCampaigns"
        :key="campaign.id"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-xl font-semibold text-gray-900">{{ campaign.name }}</h3>
              <p class="text-sm text-gray-600 mt-1">{{ campaign.description }}</p>
            </div>
            <UBadge :color="getStatusColor(campaign.status)">
              {{ campaign.statusLabel }}
            </UBadge>
          </div>
        </template>

        <div class="space-y-4">
          <!-- Tipo de campaña -->
          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-600">Tipo</span>
            <UBadge color="blue" variant="soft">{{ campaign.typeLabel }}</UBadge>
          </div>

          <!-- Progreso -->
          <div>
            <div class="flex justify-between text-sm mb-2">
              <span class="text-gray-600">Progreso</span>
              <span class="font-medium text-gray-900">
                {{ campaign.contactsCalled }} / {{ campaign.contactsTotal }}
              </span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div
                class="bg-sky-500 h-2 rounded-full transition-all"
                :style="{ width: `${(campaign.contactsCalled / campaign.contactsTotal) * 100}%` }"
              />
            </div>
          </div>

          <!-- Estadísticas -->
          <div class="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
            <div>
              <p class="text-sm text-gray-600">Tasa de éxito</p>
              <p class="text-2xl font-bold text-green-600">{{ campaign.successRate }}%</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Contactos restantes</p>
              <p class="text-2xl font-bold text-gray-900">
                {{ campaign.contactsTotal - campaign.contactsCalled }}
              </p>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex gap-2">
            <UButton
              v-if="campaign.status === 'active'"
              color="orange"
              variant="outline"
              block
            >
              Pausar
            </UButton>
            <UButton
              v-else-if="campaign.status === 'paused'"
              color="green"
              variant="outline"
              block
            >
              Reanudar
            </UButton>
            <UButton
              color="gray"
              variant="outline"
              block
              @click="navigateTo(`/campaigns/${campaign.id}`)"
            >
              Ver detalles
            </UButton>
          </div>
        </template>
      </UCard>
    </div>

    <div v-else-if="!loading" class="text-sm text-gray-500">No hay campañas configuradas</div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth']
})

const showCreateModal = ref(false)
const activeTab = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const tabs = [
  { label: 'Activas', value: 'active' },
  { label: 'Pausadas', value: 'paused' },
  { label: 'Completadas', value: 'completed' },
  { label: 'Todas', value: 'all' }
]

const campaigns = ref<any[]>([])

const filteredCampaigns = computed(() => {
  const tabValue = tabs[activeTab.value].value
  if (tabValue === 'all') return campaigns.value
  return campaigns.value.filter(c => c.status === tabValue)
})

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'green',
    paused: 'orange',
    completed: 'blue'
  }
  return colors[status] || 'gray'
}

const { apiFetch } = useApi()

const typeLabels: Record<string, string> = {
  predictive: 'Predictivo',
  progressive: 'Progresivo',
  preview: 'Preview',
  manual: 'Manual',
  inbound: 'Entrante',
  outbound: 'Saliente'
}

const statusLabels: Record<string, string> = {
  active: 'Activa',
  paused: 'Pausada',
  finished: 'Finalizada',
  draft: 'Borrador'
}

const loadCampaigns = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<any>('/campaigns/')
  if (fetchError.value) {
    error.value = 'Error al cargar campañas'
    campaigns.value = []
  } else {
    const raw = data.value
    const list = Array.isArray(raw) ? raw : (raw?.results || [])
    campaigns.value = list.map((campaign: any) => ({
      id: campaign.id,
      name: campaign.name,
      description: campaign.description,
      type: campaign.dialer_type || campaign.campaign_type,
      typeLabel: typeLabels[campaign.dialer_type || campaign.campaign_type] || (campaign.dialer_type || campaign.campaign_type),
      status: campaign.status,
      statusLabel: statusLabels[campaign.status] || campaign.status,
      contactsTotal: campaign.total_contacts || 0,
      contactsCalled: campaign.contacted || 0,
      successRate: campaign.success_rate || 0,
      startDate: campaign.start_date,
      endDate: campaign.end_date
    }))
  }
  loading.value = false
}

onMounted(() => {
  loadCampaigns()
})
</script>
