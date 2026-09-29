<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center gap-4">
      <UButton icon="i-heroicons-arrow-left" color="gray" variant="ghost" @click="navigateTo('/campaigns')">
        Volver
      </UButton>
      <div class="flex-1">
        <h1 class="text-2xl font-bold text-gray-900">{{ campaign?.name || 'Campaña' }}</h1>
        <p class="text-sm text-gray-500 mt-0.5">{{ campaign?.description }}</p>
      </div>
      <div v-if="campaign" class="flex items-center gap-3">
        <UBadge :color="statusColor(campaign.status)" size="lg">{{ statusLabel(campaign.status) }}</UBadge>
        <UButton
          v-if="campaign.status === 'active'"
          color="orange"
          icon="i-heroicons-pause"
          :loading="actionLoading"
          @click="pauseCampaign"
        >
          Pausar
        </UButton>
        <UButton
          v-else-if="campaign.status === 'paused'"
          color="green"
          icon="i-heroicons-play"
          :loading="actionLoading"
          @click="resumeCampaign"
        >
          Reanudar
        </UButton>
        <UButton
          v-else-if="campaign.status === 'draft'"
          color="blue"
          icon="i-heroicons-play"
          :loading="actionLoading"
          @click="startCampaign"
        >
          Iniciar
        </UButton>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin text-gray-400" />
    </div>

    <UAlert v-else-if="error" color="red" icon="i-heroicons-exclamation-triangle">{{ error }}</UAlert>

    <template v-else-if="campaign">
      <!-- KPI Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <UCard>
          <p class="text-xs text-gray-500">Contactos totales</p>
          <p class="text-3xl font-bold text-gray-900">{{ campaign.total_contacts ?? 0 }}</p>
        </UCard>
        <UCard>
          <p class="text-xs text-gray-500">Contactados</p>
          <p class="text-3xl font-bold text-blue-600">{{ campaign.contacted ?? 0 }}</p>
        </UCard>
        <UCard>
          <p class="text-xs text-gray-500">Tasa de éxito</p>
          <p class="text-3xl font-bold text-green-600">{{ campaign.success_rate ?? 0 }}%</p>
        </UCard>
        <UCard>
          <p class="text-xs text-gray-500">Restantes</p>
          <p class="text-3xl font-bold text-gray-700">{{ (campaign.total_contacts ?? 0) - (campaign.contacted ?? 0) }}</p>
        </UCard>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Info campaña -->
        <UCard class="lg:col-span-1">
          <template #header>
            <h2 class="font-semibold text-gray-800">Configuración</h2>
          </template>
          <dl class="space-y-3 text-sm">
            <div class="flex justify-between">
              <dt class="text-gray-500">Tipo</dt>
              <dd><UBadge color="blue" variant="soft" size="xs">{{ typeLabel(campaign.campaign_type) }}</UBadge></dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Marcación</dt>
              <dd><UBadge color="purple" variant="soft" size="xs">{{ typeLabel(campaign.dialer_type) }}</UBadge></dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Cola ACD</dt>
              <dd class="font-medium">{{ campaign.queue_name || '-' }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Lista contactos</dt>
              <dd class="font-medium">{{ campaign.contact_list_name || '-' }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Llamadas máx</dt>
              <dd class="font-mono">{{ campaign.max_concurrent_calls ?? '-' }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Intentos máx</dt>
              <dd class="font-mono">{{ campaign.max_attempts ?? '-' }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Inicio programado</dt>
              <dd>{{ campaign.start_date ? formatDate(campaign.start_date) : '-' }}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-gray-500">Fin programado</dt>
              <dd>{{ campaign.end_date ? formatDate(campaign.end_date) : '-' }}</dd>
            </div>
          </dl>

          <!-- Detección de contestador (AMD) -->
          <div v-if="campaign.dialer_type === 'predictive'" class="mt-4 pt-4 border-t border-gray-100 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-700">Detectar contestador (AMD)</span>
              <UToggle v-model="amd.enabled" aria-label="Detectar contestador" />
            </div>
            <template v-if="amd.enabled">
              <USelect v-model="amd.action" size="sm" :options="[{ label: 'Colgar', value: 'hangup' }, { label: 'Dejar mensaje grabado', value: 'message' }]" />
              <UInput v-if="amd.action === 'message'" v-model="amd.message" size="sm" placeholder="Audio en Asterisk: custom/mensaje-campana" />
            </template>
            <UButton size="xs" :loading="amd.saving" :disabled="!amdDirty" @click="saveAmd">Guardar AMD</UButton>
            <p class="text-xs text-gray-400">Se aplica al reiniciar la campaña (pausar y reanudar).</p>
          </div>
        </UCard>

        <!-- Progreso + llamadas recientes -->
        <div class="lg:col-span-2 space-y-4">
          <!-- Barra de progreso -->
          <UCard>
            <template #header>
              <h2 class="font-semibold text-gray-800">Progreso</h2>
            </template>
            <div class="space-y-3">
              <div class="flex justify-between text-sm mb-1">
                <span class="text-gray-600">Contactados</span>
                <span class="font-medium">{{ campaign.contacted ?? 0 }} / {{ campaign.total_contacts ?? 0 }}</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-3">
                <div
                  class="bg-sky-500 h-3 rounded-full transition-all"
                  :style="{ width: `${campaign.total_contacts ? ((campaign.contacted ?? 0) / campaign.total_contacts) * 100 : 0}%` }"
                />
              </div>
            </div>
          </UCard>

          <!-- Últimas llamadas de la campaña -->
          <UCard>
            <template #header>
              <h2 class="font-semibold text-gray-800">Últimas llamadas</h2>
            </template>
            <UTable
              :rows="calls"
              :columns="callColumns"
              :loading="callsLoading"
              :empty-state="{ icon: 'i-heroicons-phone', label: 'Sin llamadas registradas' }"
            >
              <template #status-data="{ row }">
                <UBadge :color="callStatusColor(row.status)" size="xs">{{ callStatusLabel(row.status) }}</UBadge>
              </template>
              <template #duration-data="{ row }">
                <span class="font-mono text-xs">{{ formatDuration(row.talk_time || row.duration) }}</span>
              </template>
              <template #start_time-data="{ row }">
                <span class="text-xs text-gray-600">{{ formatDateTime(row.start_time) }}</span>
              </template>
              <template #actions-data="{ row }">
                <UButton icon="i-heroicons-eye" size="xs" color="gray" variant="ghost" @click="navigateTo(`/calls/${row.id}`)" />
              </template>
            </UTable>
          </UCard>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })

const route = useRoute()
const toast = useToast()
const loading = ref(true)
const error = ref<string | null>(null)
const campaign = ref<any>(null)
const calls = ref<any[]>([])
const callsLoading = ref(false)
const actionLoading = ref(false)

const callColumns = [
  { key: 'caller_id', label: 'Número' },
  { key: 'agent_name', label: 'Agente' },
  { key: 'status', label: 'Estado' },
  { key: 'duration', label: 'Duración' },
  { key: 'start_time', label: 'Fecha' },
  { key: 'actions', label: '' },
]

function authHeaders() {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const formatDuration = (s: number) => {
  if (!s) return '0:00'
  return `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`
}

const formatDate = (d: string) => new Date(d).toLocaleDateString('es-CO')
const formatDateTime = (d: string) => {
  if (!d) return '-'
  return new Date(d).toLocaleString('es-CO')
}

const typeLabel = (t: string) => ({
  predictive: 'Predictivo', progressive: 'Progresivo', preview: 'Preview',
  manual: 'Manual', inbound: 'Entrante', outbound: 'Saliente',
}[t] ?? t)

const statusLabel = (s: string) => ({
  active: 'Activa', paused: 'Pausada', finished: 'Finalizada',
  draft: 'Borrador', completed: 'Completada',
}[s] ?? s)

const statusColor = (s: string) => ({
  active: 'green', paused: 'orange', finished: 'blue',
  draft: 'gray', completed: 'blue',
}[s] ?? 'gray')

const callStatusLabel = (s: string) => ({
  completed: 'Completada', answered: 'Contestada', no_answer: 'No contestada',
  busy: 'Ocupado', failed: 'Fallida', cancelled: 'Cancelada', machine: 'Contestador',
  voicemail: 'Buzón', abandoned: 'Abandonada',
}[s] ?? s)

const callStatusColor = (s: string) => ({
  completed: 'green', answered: 'green', no_answer: 'orange',
  busy: 'yellow', failed: 'red', cancelled: 'gray', machine: 'violet', voicemail: 'violet', abandoned: 'red',
}[s] ?? 'gray')

const amd = reactive({ enabled: false, action: 'hangup', message: '', saving: false })
const amdDirty = computed(() => !!campaign.value && (
  amd.enabled !== !!campaign.value.amd_enabled || amd.action !== (campaign.value.amd_action || 'hangup')
  || amd.message !== (campaign.value.amd_message || '')))

async function saveAmd() {
  amd.saving = true
  try {
    campaign.value = await $fetch<any>(`/api/campaigns/${route.params.id}/`, {
      method: 'PATCH', headers: authHeaders(),
      body: { amd_enabled: amd.enabled, amd_action: amd.action, amd_message: amd.message },
    })
    toast.add({ title: 'Configuración AMD guardada', color: 'green' })
  } catch (err: any) {
    toast.add({ title: 'No se pudo guardar', description: err?.data?.detail || JSON.stringify(err?.data || {}), color: 'red' })
  } finally { amd.saving = false }
}

watch(campaign, (c: any) => {
  if (!c) return
  amd.enabled = !!c.amd_enabled
  amd.action = c.amd_action || 'hangup'
  amd.message = c.amd_message || ''
})

const loadCampaign = async () => {
  try {
    campaign.value = await $fetch<any>(`/api/campaigns/${route.params.id}/`, { headers: authHeaders() })
  } catch (err: any) {
    error.value = err?.data?.detail ?? 'No se pudo cargar la campaña'
    toast.add({ title: error.value!, color: 'red' })
  } finally {
    loading.value = false
  }
}

const loadCalls = async () => {
  callsLoading.value = true
  try {
    const data = await $fetch<any>(`/api/calls/?campaign=${route.params.id}&ordering=-start_time&page_size=10`, {
      headers: authHeaders(),
    })
    calls.value = Array.isArray(data) ? data : (data?.results ?? [])
  } catch {
    // silencioso
  } finally {
    callsLoading.value = false
  }
}

const pauseCampaign = async () => {
  actionLoading.value = true
  try {
    await $fetch(`/api/campaigns/${route.params.id}/pause/`, { method: 'POST', headers: authHeaders() })
    campaign.value.status = 'paused'
    toast.add({ title: 'Campaña pausada', color: 'orange' })
  } catch {
    toast.add({ title: 'Error al pausar', color: 'red' })
  } finally {
    actionLoading.value = false
  }
}

const resumeCampaign = async () => {
  actionLoading.value = true
  try {
    await $fetch(`/api/campaigns/${route.params.id}/start/`, { method: 'POST', headers: authHeaders() })
    campaign.value.status = 'active'
    toast.add({ title: 'Campaña reanudada', color: 'green' })
  } catch {
    toast.add({ title: 'Error al reanudar', color: 'red' })
  } finally {
    actionLoading.value = false
  }
}

const startCampaign = async () => {
  actionLoading.value = true
  try {
    await $fetch(`/api/campaigns/${route.params.id}/start/`, { method: 'POST', headers: authHeaders() })
    campaign.value.status = 'active'
    toast.add({ title: 'Campaña iniciada', color: 'green' })
  } catch {
    toast.add({ title: 'Error al iniciar', color: 'red' })
  } finally {
    actionLoading.value = false
  }
}

onMounted(async () => {
  await loadCampaign()
  await loadCalls()
})
</script>
