<template>
  <div class="whatsapp-panel">
    <UCard :ui="{ body: { padding: 'p-0 sm:p-0' } }">
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold flex items-center gap-2">
            <UIcon name="i-heroicons-chat-bubble-left-right" class="text-green-600" />
            WhatsApp
          </h3>
          <div class="flex items-center gap-2">
            <UBadge v-if="inbox.stats.value.unread > 0" color="red">{{ inbox.stats.value.unread }} sin leer</UBadge>
            <UBadge :color="inbox.isConnected.value ? 'green' : 'gray'" size="sm" variant="soft">
              {{ inbox.isConnected.value ? 'En vivo' : 'Reconectando…' }}
            </UBadge>
            <UButton size="xs" icon="i-heroicons-plus" color="green" variant="soft" @click="startOpen = true">Nueva</UButton>
          </div>
        </div>
      </template>

      <div class="whatsapp-container">
        <!-- Lista de conversaciones -->
        <div v-if="!selectedId" class="conversations-list">
          <div class="p-3 space-y-2">
            <UInput v-model="search" placeholder="Buscar nombre o número…" icon="i-heroicons-magnifying-glass" size="sm" />
            <div class="flex gap-2 border-b">
              <button v-for="tab in tabs" :key="tab.value" class="tab-button" :class="{ active: activeTab === tab.value }"
                      @click="activeTab = tab.value">
                {{ tab.label }}
                <UBadge v-if="tab.count > 0" size="xs" :color="tab.value === 'unassigned' ? 'amber' : 'gray'">{{ tab.count }}</UBadge>
              </button>
            </div>
          </div>

          <div class="conversations-scroll px-3 pb-3">
            <div v-for="conv in filtered" :key="conv.id" class="conversation-item" :class="{ unread: conv.unread_count > 0 }"
                 @click="selectedId = conv.id">
              <UAvatar :alt="conv.display_name" size="md" class="flex-shrink-0" />
              <div class="flex-1 min-w-0">
                <div class="flex items-start justify-between mb-1 gap-2">
                  <p class="font-semibold text-gray-800 truncate">{{ conv.display_name }}</p>
                  <span class="text-xs text-gray-500 flex-shrink-0">{{ formatTime(conv.last_message_at || conv.started_at) }}</span>
                </div>
                <p class="text-sm text-gray-600 truncate">
                  <span v-if="conv.last_message?.direction === 'outbound'" class="text-gray-400">Tú: </span>{{ conv.last_message?.body || '—' }}
                </p>
                <div class="flex items-center gap-2 mt-1">
                  <UBadge v-if="!conv.agent" size="xs" color="amber" variant="soft">Sin asignar</UBadge>
                  <UBadge v-if="conv.campaign_name" size="xs" color="blue" variant="soft">{{ conv.campaign_name }}</UBadge>
                  <UBadge v-if="!conv.window_open" size="xs" color="gray" variant="outline">Fuera de 24 h</UBadge>
                  <UBadge v-if="conv.unread_count > 0" size="xs" color="red">{{ conv.unread_count }}</UBadge>
                  <UButton v-if="!conv.agent" size="2xs" class="ml-auto" :loading="taking === conv.id" @click.stop="take(conv)">Tomar</UButton>
                </div>
              </div>
            </div>

            <p v-if="inbox.loading.value && !inbox.conversations.value.length" class="text-center text-gray-500 py-8">Cargando…</p>
            <p v-else-if="!filtered.length" class="text-center text-gray-500 py-8">No hay conversaciones</p>
          </div>
        </div>

        <!-- Chat activo -->
        <MessagingChatPanel v-else ref="chat" :key="selectedId" :conversation-id="selectedId" show-back
                            class="chat-view" @back="selectedId = null" @changed="inbox.reload()" @call="callContact" />
      </div>
    </UCard>

    <MessagingStartConversation v-model="startOpen" @started="onStarted" />
  </div>
</template>

<script setup lang="ts">
/**
 * Panel de WhatsApp de la consola del agente, conectado a /api/messaging/.
 * Muestra las conversaciones propias y las sin asignar (para tomarlas),
 * con actualización en tiempo real vía /ws/messaging/.
 */
const http = useHttp()
const toast = useToast()

const selectedId = ref<number | null>(null)
const search = ref('')
const activeTab = ref<'mine' | 'unassigned' | 'unread'>('mine')
const taking = ref<number | null>(null)
const startOpen = ref(false)
const chat = ref<any>(null)

// Conversaciones activas visibles para el agente (propias + sin asignar)
const inbox = useMessaging(() => ({ active: 'true', search: search.value }))
inbox.onEvent((evt) => chat.value?.handleEvent(evt))

const agentStore = useAgentStore()
const myAgentId = computed(() => (agentStore as any).agent?.id ?? (agentStore as any).agentId ?? null)

const isMine = (c: any) => !!c.agent && (myAgentId.value == null || c.agent === myAgentId.value)

const tabs = computed(() => [
  { value: 'mine', label: 'Mis chats', count: inbox.conversations.value.filter(isMine).length },
  { value: 'unassigned', label: 'Sin asignar', count: inbox.conversations.value.filter(c => !c.agent).length },
  { value: 'unread', label: 'Sin leer', count: inbox.conversations.value.filter(c => c.unread_count > 0).length },
] as const)

const filtered = computed(() => {
  const list = inbox.conversations.value
  if (activeTab.value === 'unassigned') return list.filter(c => !c.agent)
  if (activeTab.value === 'unread') return list.filter(c => c.unread_count > 0)
  return list.filter(isMine)
})

async function take(conv: any) {
  taking.value = conv.id
  try {
    await http.post(`/messaging/conversations/${conv.id}/take/`)
    await inbox.load()
    activeTab.value = 'mine'
    selectedId.value = conv.id
  } catch (e: any) {
    toast.add({ title: 'No se pudo tomar', description: http.errorMessage(e), color: 'red' })
    inbox.load()
  } finally { taking.value = null }
}

async function onStarted(c: any) {
  await inbox.load()
  activeTab.value = 'mine'
  if (c?.id) selectedId.value = c.id
}

function callContact(phone: string) {
  try {
    const { call } = useWebRTC()
    call(phone)
  } catch {
    toast.add({ title: 'Softphone no disponible', color: 'amber' })
  }
}

const formatTime = (timestamp?: string) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  if (Date.now() - date.getTime() < 86400000) {
    return date.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
  }
  return date.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit' })
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => inbox.load(), 400)
})

onMounted(() => inbox.start())
</script>

<style scoped>
.whatsapp-container {
  @apply h-[640px] flex;
}

.conversations-list {
  @apply flex-1 flex flex-col min-h-0;
}

.conversations-scroll {
  @apply space-y-2 flex-1 overflow-y-auto;
}

.conversation-item {
  @apply flex items-start gap-3 p-3 rounded-lg border border-gray-200 cursor-pointer transition-all hover:bg-gray-50;
}

.conversation-item.unread {
  @apply bg-green-50 border-green-200;
}

.tab-button {
  @apply px-3 py-2 text-sm font-medium text-gray-600 border-b-2 border-transparent hover:text-gray-900 hover:border-gray-300 transition-colors flex items-center gap-2;
}

.tab-button.active {
  @apply text-green-700 border-green-600;
}

.chat-view {
  @apply flex-1 min-h-0;
}
</style>
