<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Bandeja omnicanal</h1>
        <p class="text-sm text-gray-500 mt-1 flex items-center gap-2">
          Conversaciones de WhatsApp en tiempo real
          <UBadge :color="inbox.isConnected.value ? 'green' : 'gray'" variant="soft" size="xs">
            {{ inbox.isConnected.value ? 'En vivo' : 'Reconectando…' }}
          </UBadge>
        </p>
      </div>
      <div class="flex gap-2">
        <UButton v-if="isAdmin" icon="i-heroicons-cog-6-tooth" color="gray" variant="outline" to="/settings/whatsapp">Configurar WhatsApp</UButton>
        <UButton icon="i-heroicons-plus" color="green" @click="startOpen = true">Nueva conversación</UButton>
      </div>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
      <UCard v-for="k in kpis" :key="k.key" :ui="{ body: { padding: 'p-3 sm:p-3' } }"
             class="cursor-pointer" :class="k.filter && quick === k.filter ? 'ring-2 ring-primary-500' : ''" @click="k.filter && setQuick(k.filter)">
        <p class="text-xs text-gray-500">{{ k.label }}</p>
        <p class="text-2xl font-bold" :class="k.color">{{ inbox.stats.value[k.key] ?? 0 }}</p>
      </UCard>
    </div>

    <UCard :ui="{ body: { padding: 'p-0 sm:p-0' } }">
      <div class="flex h-[calc(100vh-320px)] min-h-[520px]">
        <!-- Lista -->
        <div class="w-full md:w-96 border-r border-gray-200 flex flex-col" :class="selectedId ? 'hidden md:flex' : 'flex'">
          <div class="p-3 space-y-2 border-b border-gray-200">
            <UInput v-model="search" icon="i-heroicons-magnifying-glass" placeholder="Buscar nombre o número" size="sm" @keyup.enter="inbox.load()" />
            <div class="flex gap-2">
              <USelect v-model="statusFilter" size="sm" class="flex-1" :options="statusOptions" @change="inbox.load()" />
              <USelect v-model="lineFilter" size="sm" class="flex-1" :options="[{ label: 'Todas las líneas', value: '' }, ...lineOptions]" @change="inbox.load()" />
            </div>
            <div class="flex gap-1">
              <UButton v-for="q in quickFilters" :key="q.value" size="2xs" :color="quick === q.value ? 'primary' : 'gray'"
                       :variant="quick === q.value ? 'solid' : 'ghost'" @click="setQuick(q.value)">{{ q.label }}</UButton>
            </div>
          </div>
          <div class="flex-1 overflow-y-auto">
            <div v-if="inbox.loading.value && !inbox.conversations.value.length" class="p-6 text-center text-sm text-gray-500">Cargando…</div>
            <button v-for="c in inbox.conversations.value" :key="c.id" type="button"
                    class="w-full text-left px-3 py-3 border-b border-gray-100 hover:bg-gray-50 flex gap-3"
                    :class="{ 'bg-green-50': selectedId === c.id }" @click="selectedId = c.id">
              <UAvatar :alt="c.display_name" size="md" class="flex-shrink-0" />
              <div class="flex-1 min-w-0">
                <div class="flex justify-between gap-2">
                  <p class="font-medium truncate" :class="{ 'font-bold': c.unread_count }">{{ c.display_name }}</p>
                  <span class="text-[11px] text-gray-500 flex-shrink-0">{{ relTime(c.last_message_at || c.started_at) }}</span>
                </div>
                <p class="text-xs text-gray-600 truncate">
                  <span v-if="c.last_message?.direction === 'outbound'" class="text-gray-400">Tú: </span>{{ c.last_message?.body || '—' }}
                </p>
                <div class="flex items-center gap-1 mt-1 flex-wrap">
                  <UBadge size="xs" :color="c.agent ? 'gray' : 'amber'" variant="soft">{{ c.agent_name || 'Sin asignar' }}</UBadge>
                  <UBadge v-if="c.status === 'closed'" size="xs" color="gray" variant="outline">Cerrada</UBadge>
                  <UBadge v-else-if="!c.window_open" size="xs" color="amber" variant="outline">Fuera de 24 h</UBadge>
                  <UBadge v-if="c.unread_count" size="xs" color="green">{{ c.unread_count }}</UBadge>
                </div>
              </div>
            </button>
            <p v-if="!inbox.loading.value && !inbox.conversations.value.length" class="p-6 text-center text-sm text-gray-500">No hay conversaciones con estos filtros</p>
          </div>
        </div>

        <!-- Chat -->
        <div class="flex-1 min-w-0 flex-col" :class="selectedId ? 'flex' : 'hidden md:flex'">
          <template v-if="selectedId">
            <div v-if="selected" class="flex items-center gap-2 px-4 py-2 bg-gray-50 border-b border-gray-200 text-sm">
              <span class="text-gray-500">Asignada a:</span>
              <USelect v-model="assignTo" size="xs" class="w-56" :options="[{ label: 'Sin asignar', value: '' }, ...agentOptions]" />
              <UButton size="xs" :disabled="assignTo === String(selected.agent || '')" :loading="assigning" @click="assign">Reasignar</UButton>
            </div>
            <MessagingChatPanel ref="chat" :key="selectedId" :conversation-id="selectedId" show-back class="flex-1 min-h-0"
                                @back="selectedId = null" @changed="inbox.reload()" />
          </template>
          <div v-else class="flex-1 flex flex-col items-center justify-center text-gray-400 gap-2">
            <UIcon name="i-heroicons-chat-bubble-left-right" class="w-16 h-16" />
            <p>Selecciona una conversación</p>
          </div>
        </div>
      </div>
    </UCard>

    <MessagingStartConversation v-model="startOpen" @started="onStarted" />
  </div>
</template>

<script setup lang="ts">
useHead({ title: 'Bandeja omnicanal - VozipOmni' })

const http = useHttp()
const toast = useToast()
const authStore = useAuthStore()
const isAdmin = computed(() => {
  const u: any = authStore.user
  return !!u && (u.is_superuser || u.role === 'admin')
})

const search = ref('')
const statusFilter = ref('active')
const lineFilter = ref('')
const quick = ref('')
const selectedId = ref<number | null>(null)
const startOpen = ref(false)
const chat = ref<any>(null)
const lines = ref<any[]>([])
const agents = ref<any[]>([])
const assignTo = ref('')
const assigning = ref(false)

const statusOptions = [
  { label: 'Activas', value: 'active' },
  { label: 'Abiertas', value: 'open' },
  { label: 'En espera', value: 'waiting' },
  { label: 'Cerradas', value: 'closed' },
  { label: 'Todas', value: '' },
]
const quickFilters = [
  { label: 'Todas', value: '' },
  { label: 'Sin asignar', value: 'unassigned' },
  { label: 'Mías', value: 'mine' },
]
const kpis = [
  { key: 'open', label: 'Abiertas', color: 'text-green-600' },
  { key: 'waiting', label: 'En espera', color: 'text-amber-600' },
  { key: 'unassigned', label: 'Sin asignar', color: 'text-red-600', filter: 'unassigned' },
  { key: 'mine', label: 'Mías', color: 'text-sky-600', filter: 'mine' },
  { key: 'unread', label: 'Sin leer', color: 'text-gray-900' },
  { key: 'closed_today', label: 'Cerradas hoy', color: 'text-gray-500' },
]

const inbox = useMessaging(() => {
  const q: Record<string, any> = { search: search.value }
  if (statusFilter.value === 'active') q.active = 'true'
  else if (statusFilter.value) q.status = statusFilter.value
  if (lineFilter.value) q.line = lineFilter.value
  if (quick.value === 'unassigned') q.unassigned = 'true'
  if (quick.value === 'mine') q.mine = 'true'
  return q
})
inbox.onEvent((evt) => chat.value?.handleEvent(evt))

const selected = computed(() => inbox.conversations.value.find(c => c.id === selectedId.value) || null)
watch(selected, (c) => { assignTo.value = c?.agent ? String(c.agent) : '' }, { immediate: true })

const lineOptions = computed(() => lines.value.map(l => ({ label: l.name, value: String(l.id) })))
const agentOptions = computed(() => agents.value.map(a => ({
  label: `${a.user_details?.name || a.agent_id}${a.status ? ' · ' + a.status : ''}`, value: String(a.id),
})))

function setQuick(v: string) {
  quick.value = quick.value === v ? '' : v
  inbox.load()
}

const relTime = (v?: string) => {
  if (!v) return ''
  const d = new Date(v)
  const diff = Date.now() - d.getTime()
  if (diff < 60000) return 'ahora'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} min`
  if (d.toDateString() === new Date().toDateString()) return d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit' })
}

async function assign() {
  if (!selected.value) return
  assigning.value = true
  try {
    await http.post(`/messaging/conversations/${selected.value.id}/assign/`, { agent_id: assignTo.value ? Number(assignTo.value) : null })
    toast.add({ title: assignTo.value ? 'Conversación reasignada' : 'Conversación liberada', color: 'green' })
    await inbox.load()
    chat.value?.reload()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { assigning.value = false }
}

async function onStarted(c: any) {
  await inbox.load()
  if (c?.id) selectedId.value = c.id
}

let search_t: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  if (search_t) clearTimeout(search_t)
  search_t = setTimeout(() => inbox.load(), 400)
})

onMounted(async () => {
  inbox.start()
  const [l, a] = await Promise.allSettled([
    http.get('/messaging/whatsapp/lines/'),
    http.get('/agents/'),
  ])
  if (l.status === 'fulfilled') lines.value = http.results(l.value)
  if (a.status === 'fulfilled') agents.value = http.results(a.value)
})
</script>
