<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Panel de Supervisión</h1>
        <p class="text-sm text-gray-500 mt-1">Actualización automática cada 10 s · {{ formatTime(lastUpdate) }}</p>
      </div>
      <div class="flex gap-2">
        <UBadge :color="wsConnected ? 'green' : 'red'" variant="soft">
          {{ wsConnected ? 'En vivo' : 'Desconectado' }}
        </UBadge>
        <UButton icon="i-heroicons-arrow-path" :loading="loading" color="gray" variant="outline" @click="loadDashboard">
          Actualizar
        </UButton>
      </div>
    </div>

    <!-- KPIs principales -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">Agentes Online</p>
          <p class="text-4xl font-bold text-green-600 mt-1">{{ dashboard.agents?.online ?? 0 }}</p>
          <p class="text-xs text-gray-400 mt-1">de {{ dashboard.agents?.total ?? 0 }} total</p>
        </div>
      </UCard>
      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">En Llamada</p>
          <p class="text-4xl font-bold text-blue-600 mt-1">{{ dashboard.agents?.oncall ?? 0 }}</p>
          <p class="text-xs text-gray-400 mt-1">{{ dashboard.agents?.wrapup ?? 0 }} post-llamada</p>
        </div>
      </UCard>
      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">Llamadas Hoy</p>
          <p class="text-4xl font-bold text-gray-900 mt-1">{{ dashboard.calls?.total ?? 0 }}</p>
          <p class="text-xs text-gray-400 mt-1">{{ dashboard.calls?.active_now ?? 0 }} activas ahora</p>
        </div>
      </UCard>
      <UCard>
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">Tasa Respuesta</p>
          <p class="text-4xl font-bold mt-1"
             :class="(dashboard.calls?.answer_rate ?? 0) >= 80 ? 'text-green-600' : (dashboard.calls?.answer_rate ?? 0) >= 60 ? 'text-yellow-600' : 'text-red-600'">
            {{ dashboard.calls?.answer_rate ?? 0 }}%
          </p>
          <p class="text-xs text-gray-400 mt-1">TMO: {{ formatDuration(dashboard.calls?.avg_talk_time ?? 0) }}</p>
        </div>
      </UCard>
    </div>

    <!-- Estado agentes + Colas -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- Mapa de agentes -->
      <div class="lg:col-span-2">
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="font-semibold text-gray-800">Estado de Agentes</h2>
              <div class="flex gap-1 text-xs">
                <span v-for="s in statusLabels" :key="s.key"
                      class="flex items-center gap-1 px-2 py-0.5 rounded-full"
                      :class="s.bg">
                  <span class="w-2 h-2 rounded-full" :class="s.dot" />
                  {{ s.label }} ({{ agentsByStatus[s.key] ?? 0 }})
                </span>
              </div>
            </div>
          </template>

          <!-- Tabla de agentes -->
          <UTable
            :rows="agents"
            :columns="agentColumns"
            :loading="loading"
            :empty-state="{ icon: 'i-heroicons-user-group', label: 'No hay agentes' }"
          >
            <template #status-data="{ row }">
              <UBadge :color="statusColor(row.status)" variant="soft" size="xs">
                {{ statusLabel(row.status) }}
              </UBadge>
            </template>
            <template #talk_time_today-data="{ row }">
              {{ formatDuration(row.talk_time_today) }}
            </template>
            <template #occupancy-data="{ row }">
              <div class="flex items-center gap-2">
                <UProgress :value="row.occupancy" size="xs" class="w-16"
                           :color="row.occupancy >= 80 ? 'green' : row.occupancy >= 60 ? 'yellow' : 'red'" />
                <span class="text-xs">{{ row.occupancy }}%</span>
              </div>
            </template>
            <template #actions-data="{ row }">
              <div class="flex gap-1">
                <UTooltip text="Escuchar">
                  <UButton icon="i-heroicons-eye" size="xs" color="gray" variant="ghost"
                           :disabled="row.status !== 'oncall'"
                           @click="openSpyModal(row, 'spy')" />
                </UTooltip>
                <UTooltip text="Susurrar">
                  <UButton icon="i-heroicons-chat-bubble-left-ellipsis" size="xs" color="blue" variant="ghost"
                           :disabled="row.status !== 'oncall'"
                           @click="openSpyModal(row, 'whisper')" />
                </UTooltip>
                <UTooltip text="Entrar a llamada">
                  <UButton icon="i-heroicons-phone-arrow-up-right" size="xs" color="orange" variant="ghost"
                           :disabled="row.status !== 'oncall'"
                           @click="openSpyModal(row, 'barge')" />
                </UTooltip>
                <UTooltip text="Forzar pausa">
                  <UButton icon="i-heroicons-pause" size="xs" color="yellow" variant="ghost"
                           :disabled="row.status === 'offline' || row.status === 'break'"
                           @click="forceBreak(row)" />
                </UTooltip>
                <UTooltip text="Desconectar">
                  <UButton icon="i-heroicons-x-circle" size="xs" color="red" variant="ghost"
                           :disabled="row.status === 'offline'"
                           @click="forceLogout(row)" />
                </UTooltip>
              </div>
            </template>
          </UTable>
        </UCard>
      </div>

      <!-- Colas en vivo -->
      <div>
        <UCard>
          <template #header>
            <h2 class="font-semibold text-gray-800">Colas en Vivo</h2>
          </template>
          <div v-if="dashboard.queues?.length" class="space-y-3">
            <div v-for="q in dashboard.queues" :key="q.id"
                 class="p-3 bg-gray-50 rounded-lg border border-gray-100">
              <div class="flex justify-between items-center mb-2">
                <span class="font-medium text-sm text-gray-700">{{ q.name }}</span>
                <UBadge :color="q.calls_waiting > 0 ? 'red' : 'green'" variant="soft" size="xs">
                  {{ q.calls_waiting }} esperando
                </UBadge>
              </div>
              <div class="grid grid-cols-2 gap-2 text-xs text-gray-500">
                <span>Agentes listos: <strong class="text-green-600">{{ q.agents_available }}</strong></span>
              </div>
            </div>
          </div>
          <p v-else class="text-sm text-gray-400 text-center py-4">Sin colas activas</p>
        </UCard>

        <!-- Resumen estados -->
        <UCard class="mt-4">
          <template #header><h2 class="font-semibold text-gray-800">Distribución</h2></template>
          <div class="space-y-2">
            <div v-for="s in statusLabels" :key="s.key" class="flex items-center justify-between text-sm">
              <div class="flex items-center gap-2">
                <span class="w-3 h-3 rounded-full" :class="s.dot" />
                <span class="text-gray-600">{{ s.label }}</span>
              </div>
              <span class="font-semibold">{{ dashboard.agents?.[s.key] ?? 0 }}</span>
            </div>
          </div>
        </UCard>
      </div>
    </div>

    <!-- Modal spy/whisper/barge -->
    <UModal v-model="spyModal.open">
      <UCard>
        <template #header>
          <h3 class="font-semibold">
            {{ spyModal.mode === 'spy' ? 'Escuchar llamada' : spyModal.mode === 'whisper' ? 'Susurrar al agente' : 'Entrar a llamada' }}
            — {{ spyModal.agent?.name }}
          </h3>
        </template>
        <div class="space-y-4">
          <p class="text-sm text-gray-600">
            Ingresa tu extensión SIP para conectarte a la llamada activa del agente
            <strong>{{ spyModal.agent?.name }}</strong>.
          </p>
          <UFormGroup label="Tu extensión SIP">
            <UInput v-model="spyModal.extension" placeholder="ej: 1099" type="number" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="spyModal.open = false">Cancelar</UButton>
            <UButton :loading="spyModal.loading" @click="executeSpy">Conectar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'], layout: 'default' })

const loading = ref(false)
const wsConnected = ref(false)
const lastUpdate = ref(new Date())
const dashboard = ref<any>({})
const agents = ref<any[]>([])

const spyModal = ref({ open: false, mode: 'spy', agent: null as any, extension: '', loading: false })

const agentColumns = [
  { key: 'name', label: 'Agente' },
  { key: 'sip_extension', label: 'Ext.' },
  { key: 'status', label: 'Estado' },
  { key: 'calls_today', label: 'Llamadas' },
  { key: 'talk_time_today', label: 'T. Hab.' },
  { key: 'occupancy', label: 'Ocupación' },
  { key: 'actions', label: '' },
]

const statusLabels = [
  { key: 'available', label: 'Disponible', dot: 'bg-green-500', bg: 'bg-green-50 text-green-700' },
  { key: 'oncall', label: 'En llamada', dot: 'bg-blue-500', bg: 'bg-blue-50 text-blue-700' },
  { key: 'wrapup', label: 'Post-llamada', dot: 'bg-purple-500', bg: 'bg-purple-50 text-purple-700' },
  { key: 'break', label: 'Pausa', dot: 'bg-yellow-500', bg: 'bg-yellow-50 text-yellow-700' },
  { key: 'offline', label: 'Desconectado', dot: 'bg-gray-400', bg: 'bg-gray-50 text-gray-600' },
]

const agentsByStatus = computed(() => {
  const result: Record<string, number> = {}
  for (const s of statusLabels) {
    result[s.key] = agents.value.filter(a => a.status === s.key).length
  }
  return result
})

const statusColor = (s: string) => ({ available: 'green', oncall: 'blue', wrapup: 'purple', break: 'yellow', busy: 'orange', offline: 'gray' })[s] ?? 'gray'
const statusLabel = (s: string) => statusLabels.find(l => l.key === s)?.label ?? s

const formatDuration = (secs: number) => {
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}m ${s}s`
}
const formatTime = (d: Date) => d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

async function loadDashboard() {
  loading.value = true
  try {
    const [dash, agentsRes] = await Promise.all([
      $fetch('/api/supervisor/dashboard/', { headers: useAuthHeaders() }),
      $fetch('/api/supervisor/agents/', { headers: useAuthHeaders() }),
    ])
    dashboard.value = dash
    agents.value = (agentsRes as any).agents ?? []
    lastUpdate.value = new Date()
  } catch (e) {
    useToast().add({ title: 'Error cargando supervisor', color: 'red' })
  } finally {
    loading.value = false
  }
}

function openSpyModal(agent: any, mode: string) {
  spyModal.value = { open: true, mode, agent, extension: '', loading: false }
}

async function executeSpy() {
  if (!spyModal.value.extension) return
  const callId = spyModal.value.agent?.current_call_id
  if (!callId) {
    useToast().add({ title: 'El agente no tiene una llamada activa', color: 'orange' })
    return
  }
  spyModal.value.loading = true
  try {
    await $fetch(`/api/supervisor/${callId}/${spyModal.value.mode}/`, {
      method: 'POST',
      headers: useAuthHeaders(),
      body: { supervisor_extension: spyModal.value.extension },
    })
    useToast().add({ title: 'Conectado exitosamente', color: 'green' })
    spyModal.value.open = false
  } catch (e: any) {
    useToast().add({ title: e.data?.error ?? 'Error al conectar', color: 'red' })
  } finally {
    spyModal.value.loading = false
  }
}

async function forceBreak(agent: any) {
  await $fetch(`/api/supervisor/${agent.id}/force_break/`, {
    method: 'POST',
    headers: useAuthHeaders(),
    body: { reason: 'supervisor_forced' },
  })
  useToast().add({ title: `${agent.name} puesto en pausa`, color: 'yellow' })
  await loadDashboard()
}

async function forceLogout(agent: any) {
  if (!confirm(`¿Desconectar a ${agent.name}?`)) return
  await $fetch(`/api/supervisor/${agent.id}/force_logout/`, {
    method: 'POST',
    headers: useAuthHeaders(),
  })
  useToast().add({ title: `${agent.name} desconectado`, color: 'red' })
  await loadDashboard()
}

function useAuthHeaders() {
  const token = process.client ? localStorage.getItem('auth_token') : null
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Auto-refresh cada 10 segundos
let interval: ReturnType<typeof setInterval>
onMounted(() => {
  loadDashboard()
  interval = setInterval(loadDashboard, 10000)
})
onUnmounted(() => clearInterval(interval))
</script>
