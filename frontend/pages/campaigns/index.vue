<template>
  <div>
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">CampaÃ±as</h1>
        <p class="text-gray-600 mt-2">GestiÃ³n de campaÃ±as de marcaciÃ³n</p>
      </div>
      <UButton icon="i-heroicons-plus" size="lg" @click="openCreateModal">
        Nueva CampaÃ±a
      </UButton>
    </div>

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle" class="mb-6">
      {{ error }}
    </UAlert>

    <UCard v-if="loading" class="flex justify-center items-center py-12 mb-6">
      <div class="text-center space-y-2">
        <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto" />
        <p class="text-gray-500">Cargando campaÃ±as...</p>
      </div>
    </UCard>

    <!-- Tabs de estado -->
    <UTabs :items="tabs" v-model="activeTab" class="mb-6" />

    <!-- Grid de campaÃ±as -->
    <div v-if="!loading && filteredCampaigns.length" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <UCard v-for="campaign in filteredCampaigns" :key="campaign.id">
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
          <div class="flex items-center justify-between text-sm">
            <span class="text-gray-600">Tipo</span>
            <UBadge color="blue" variant="soft">{{ campaign.typeLabel }}</UBadge>
          </div>

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
                :style="{ width: `${campaign.contactsTotal ? (campaign.contactsCalled / campaign.contactsTotal) * 100 : 0}%` }"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
            <div>
              <p class="text-sm text-gray-600">Tasa de Ã©xito</p>
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
              :loading="actionLoading === campaign.id"
              block
              @click="pauseCampaign(campaign)"
            >
              Pausar
            </UButton>
            <UButton
              v-else-if="campaign.status === 'paused'"
              color="green"
              variant="outline"
              :loading="actionLoading === campaign.id"
              block
              @click="resumeCampaign(campaign)"
            >
              Reanudar
            </UButton>
            <UButton
              v-else-if="campaign.status === 'draft'"
              color="blue"
              variant="outline"
              :loading="actionLoading === campaign.id"
              block
              @click="startCampaign(campaign)"
            >
              Iniciar
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

    <div v-else-if="!loading" class="text-sm text-gray-500 py-8 text-center">
      No hay campaÃ±as configuradas
    </div>

    <!-- ============================== -->
    <!-- MODAL: NUEVA CAMPAÑA           -->
    <!-- ============================== -->
    <UModal v-model="showCreateModal" :prevent-close="saving" :ui="{ width: 'sm:max-w-5xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">Nueva Campaña</h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="showCreateModal = false" />
          </div>
        </template>

        <!-- Tabs de secciones -->
        <UTabs :items="campaignTabs" v-model="activeCampaignTab">
          <!-- ===== TAB 1: INFORMACIÓN BÁSICA ===== -->
          <template #basica="{ item }">
            <div class="space-y-5 py-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Nombre de la Campaña" required class="col-span-2">
                  <UInput v-model="newCampaign.name" placeholder="Nombre descriptivo de la campaña" />
                </UFormGroup>

                <UFormGroup label="Descripción" class="col-span-2">
                  <UTextarea v-model="newCampaign.description" placeholder="Descripción opcional" :rows="3" />
                </UFormGroup>

                <UFormGroup label="Tipo de Campaña" required>
                  <USelectMenu
                    v-model="newCampaign.campaign_type"
                    :options="campaignTypeOptions"
                    value-attribute="value"
                    option-attribute="label"
                  />
                </UFormGroup>

                <UFormGroup label="Tipo de Marcación" required>
                  <USelectMenu
                    v-model="newCampaign.dialer_type"
                    :options="dialerTypeOptions"
                    value-attribute="value"
                    option-attribute="label"
                  />
                </UFormGroup>
              </div>

              <!-- Alertas explicativas -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <UAlert 
                  icon="i-heroicons-phone-arrow-up-right" 
                  color="blue" 
                  variant="subtle"
                  title="Campaña Outbound"
                  description="El sistema marca automáticamente a los contactos de la lista configurada."
                />
                <UAlert 
                  icon="i-heroicons-bolt" 
                  color="green" 
                  variant="subtle"
                  title="Marcador Progresivo"
                  description="Marca contactos de forma automática cuando hay agentes disponibles. Balance óptimo entre eficiencia y experiencia."
                />
              </div>
            </div>
          </template>

          <!-- ===== TAB 2: RECURSOS ===== -->
          <template #recursos="{ item }">
            <div class="space-y-5 py-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Cola (ACD)" help="Cola de agentes para esta campaña">
                  <USelectMenu
                    v-model="newCampaign.queue"
                    :options="queueOptions"
                    value-attribute="value"
                    option-attribute="label"
                    placeholder="Seleccionar cola"
                  />
                </UFormGroup>

                <UFormGroup label="Lista de Contactos" help="Base de datos a marcar">
                  <USelectMenu
                    v-model="newCampaign.contact_list"
                    :options="contactListOptions"
                    value-attribute="value"
                    option-attribute="label"
                    placeholder="Seleccionar lista"
                  />
                </UFormGroup>
              </div>

              <UAlert 
                icon="i-heroicons-information-circle" 
                color="blue" 
                variant="subtle"
                description="Asegúrate de tener una cola con agentes asignados y una lista de contactos cargada antes de iniciar la campaña."
              />
            </div>
          </template>

          <!-- ===== TAB 3: PROGRAMACIÓN ===== -->
          <template #programacion="{ item }">
            <div class="space-y-5 py-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Fecha de Inicio" help="Cuándo inicia la campaña">
                  <UInput v-model="newCampaign.start_date" type="date" />
                </UFormGroup>

                <UFormGroup label="Fecha de Fin" help="Cuándo finaliza la campaña">
                  <UInput v-model="newCampaign.end_date" type="date" />
                </UFormGroup>
              </div>

              <UAlert 
                icon="i-heroicons-calendar" 
                color="yellow" 
                variant="subtle"
                description="Puedes dejar las fechas vacías para campaña indefinida. La campaña se pausará automáticamente al llegar a la fecha de fin."
              />
            </div>
          </template>

          <!-- ===== TAB 4: CONFIGURACIÓN AVANZADA ===== -->
          <template #avanzado="{ item }">
            <div class="space-y-5 py-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Llamadas Simultáneas Máx." help="Cuántas llamadas en paralelo">
                  <UInput v-model.number="newCampaign.max_concurrent_calls" type="number" min="1" max="100" />
                </UFormGroup>

                <UFormGroup label="Intentos por Contacto" help="Reintentos antes de marcar como fallido">
                  <UInput v-model.number="newCampaign.max_attempts" type="number" min="1" max="10" />
                </UFormGroup>
              </div>

              <UAlert 
                icon="i-heroicons-cog" 
                color="purple" 
                variant="subtle"
                title="Configuración de Rendimiento"
                description="Ajusta las llamadas simultáneas según tu capacidad de agentes y líneas disponibles. Más llamadas = mayor throughput pero requiere más recursos."
              />
            </div>
          </template>
        </UTabs>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="gray" variant="outline" :disabled="saving" @click="showCreateModal = false">
              Cancelar
            </UButton>
            <UButton color="sky" :loading="saving" @click="createCampaignAction">
              Crear Campaña
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })

const toast = useToast()
const showCreateModal = ref(false)
const activeTab = ref(0)
const activeCampaignTab = ref(0)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const actionLoading = ref<number | null>(null)

const tabs = [
  { label: 'Activas', value: 'active' },
  { label: 'Pausadas', value: 'paused' },
  { label: 'Completadas', value: 'completed' },
  { label: 'Todas', value: 'all' }
]

// Tabs del modal de creación
const campaignTabs = [
  { slot: 'basica', label: 'Información Básica', icon: 'i-heroicons-information-circle' },
  { slot: 'recursos', label: 'Recursos', icon: 'i-heroicons-user-group' },
  { slot: 'programacion', label: 'Programación', icon: 'i-heroicons-calendar' },
  { slot: 'avanzado', label: 'Configuración Avanzada', icon: 'i-heroicons-cog' }
]

const emptyForm = () => ({
  name: '',
  description: '',
  campaign_type: 'outbound',
  dialer_type: 'progressive',
  queue: null as number | null,
  contact_list: null as number | null,
  start_date: '',
  end_date: '',
  max_concurrent_calls: 5,
  max_attempts: 3,
})

const newCampaign = ref(emptyForm())

const campaignTypeOptions = [
  { label: 'Saliente', value: 'outbound' },
  { label: 'Entrante', value: 'inbound' },
  { label: 'Manual', value: 'manual' },
  { label: 'Preview', value: 'preview' },
]

const dialerTypeOptions = [
  { label: 'Progresivo', value: 'progressive' },
  { label: 'Predictivo', value: 'predictive' },
  { label: 'Manual', value: 'manual' },
  { label: 'Preview', value: 'preview' },
]

const queueOptions = ref<{ label: string; value: number }[]>([])
const contactListOptions = ref<{ label: string; value: number }[]>([])
const campaigns = ref<any[]>([])

const filteredCampaigns = computed(() => {
  const tabValue = tabs[activeTab.value].value
  if (tabValue === 'all') return campaigns.value
  return campaigns.value.filter(c => c.status === tabValue)
})

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    active: 'green', paused: 'orange', completed: 'blue', draft: 'gray', finished: 'blue'
  }
  return colors[status] || 'gray'
}

const { apiFetch } = useApi()

function authHeaders() {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const typeLabels: Record<string, string> = {
  predictive: 'Predictivo', progressive: 'Progresivo', preview: 'Preview',
  manual: 'Manual', inbound: 'Entrante', outbound: 'Saliente'
}

const statusLabels: Record<string, string> = {
  active: 'Activa', paused: 'Pausada', finished: 'Finalizada',
  draft: 'Borrador', completed: 'Completada'
}

const loadCampaigns = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<any>('/campaigns/')
  if (fetchError.value) {
    error.value = 'Error al cargar campaÃ±as'
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

const loadOptions = async () => {
  const [queuesRes, listsRes] = await Promise.all([
    $fetch<any>('/api/queues/', { headers: authHeaders() }),
    $fetch<any>('/api/contact-lists/', { headers: authHeaders() }),
  ])
  const queues = Array.isArray(queuesRes) ? queuesRes : (queuesRes?.results ?? [])
  const lists = Array.isArray(listsRes) ? listsRes : (listsRes?.results ?? [])
  queueOptions.value = queues.map((q: any) => ({ label: q.name, value: q.id }))
  contactListOptions.value = lists.map((l: any) => ({ label: l.name, value: l.id }))
}

const openCreateModal = () => {
  newCampaign.value = emptyForm()
  showCreateModal.value = true
}

const createCampaignAction = async () => {
  if (!newCampaign.value.name) {
    toast.add({ title: 'El nombre es requerido', color: 'orange' })
    return
  }
  saving.value = true
  try {
    const payload: any = { ...newCampaign.value }
    if (!payload.queue) delete payload.queue
    if (!payload.contact_list) delete payload.contact_list
    if (!payload.start_date) delete payload.start_date
    if (!payload.end_date) delete payload.end_date

    await $fetch('/api/campaigns/', {
      method: 'POST',
      headers: authHeaders(),
      body: payload,
    })
    toast.add({ title: 'CampaÃ±a creada exitosamente', color: 'green' })
    showCreateModal.value = false
    await loadCampaigns()
  } catch (err: any) {
    const detail = err?.data?.name?.[0] ?? err?.data?.detail ?? 'Error al crear campaÃ±a'
    toast.add({ title: detail, color: 'red' })
  } finally {
    saving.value = false
  }
}

const pauseCampaign = async (campaign: any) => {
  actionLoading.value = campaign.id
  try {
    await $fetch(`/api/campaigns/${campaign.id}/pause/`, { method: 'POST', headers: authHeaders() })
    campaign.status = 'paused'
    campaign.statusLabel = 'Pausada'
    toast.add({ title: `CampaÃ±a "${campaign.name}" pausada`, color: 'orange' })
  } catch {
    toast.add({ title: 'Error al pausar campaÃ±a', color: 'red' })
  } finally {
    actionLoading.value = null
  }
}

const resumeCampaign = async (campaign: any) => {
  actionLoading.value = campaign.id
  try {
    await $fetch(`/api/campaigns/${campaign.id}/start/`, { method: 'POST', headers: authHeaders() })
    campaign.status = 'active'
    campaign.statusLabel = 'Activa'
    toast.add({ title: `CampaÃ±a "${campaign.name}" reanudada`, color: 'green' })
  } catch {
    toast.add({ title: 'Error al reanudar campaÃ±a', color: 'red' })
  } finally {
    actionLoading.value = null
  }
}

const startCampaign = async (campaign: any) => {
  actionLoading.value = campaign.id
  try {
    await $fetch(`/api/campaigns/${campaign.id}/start/`, { method: 'POST', headers: authHeaders() })
    campaign.status = 'active'
    campaign.statusLabel = 'Activa'
    toast.add({ title: `CampaÃ±a "${campaign.name}" iniciada`, color: 'green' })
  } catch {
    toast.add({ title: 'Error al iniciar campaÃ±a', color: 'red' })
  } finally {
    actionLoading.value = null
  }
}

onMounted(() => {
  loadCampaigns()
  loadOptions()
})
</script>
