<template>
  <Transition name="slide-right">
    <div
      v-if="visible && contact"
      class="fixed top-20 right-4 z-50 w-80 shadow-2xl rounded-xl overflow-hidden"
    >
      <UCard class="border-l-4 border-blue-500">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UIcon name="i-heroicons-user-circle" class="text-blue-500 w-5 h-5" />
              <span class="font-semibold text-sm">Llamada entrante</span>
              <UBadge color="blue" size="xs" variant="soft">Screen Pop</UBadge>
            </div>
            <UButton icon="i-heroicons-x-mark" size="xs" color="gray" variant="ghost" @click="dismiss" />
          </div>
        </template>

        <!-- Info del contacto -->
        <div class="space-y-3">
          <div class="flex items-start gap-3">
            <UAvatar :alt="contact.name" size="lg" />
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-gray-900 truncate">{{ contact.name }}</p>
              <p class="text-sm text-gray-500">{{ callerPhone }}</p>
              <div class="flex gap-1 mt-1 flex-wrap">
                <UBadge v-if="contact.is_vip" color="yellow" size="xs">VIP</UBadge>
                <UBadge v-if="contact.dnc_opt_out" color="red" size="xs">DNC</UBadge>
              </div>
            </div>
          </div>

          <!-- Campos clave -->
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div v-if="contact.email" class="col-span-2">
              <span class="text-gray-500">Email:</span>
              <span class="ml-1 font-medium truncate">{{ contact.email }}</span>
            </div>
            <div v-if="contact.company">
              <span class="text-gray-500">Empresa:</span>
              <span class="ml-1 font-medium">{{ contact.company }}</span>
            </div>
            <div v-if="contact.timezone">
              <span class="text-gray-500">TZ:</span>
              <span class="ml-1 font-medium">{{ contact.timezone }}</span>
            </div>
          </div>

          <!-- Últimas llamadas -->
          <div v-if="recentCalls.length" class="border-t pt-2">
            <p class="text-xs font-medium text-gray-600 mb-2">Últimas llamadas</p>
            <div class="space-y-1">
              <div
                v-for="call in recentCalls"
                :key="call.id"
                class="flex items-center justify-between text-xs"
              >
                <span class="text-gray-500">{{ formatDate(call.start_time) }}</span>
                <UBadge :color="callStatusColor(call.status)" size="xs">{{ call.status }}</UBadge>
                <span class="text-gray-500">{{ call.duration }}s</span>
              </div>
            </div>
          </div>

          <!-- Acciones -->
          <div class="flex gap-2 pt-1">
            <UButton
              size="xs"
              color="blue"
              variant="soft"
              icon="i-heroicons-eye"
              class="flex-1"
              @click="viewContact"
            >
              Ver contacto
            </UButton>
            <UButton
              size="xs"
              color="gray"
              variant="soft"
              icon="i-heroicons-clock"
              class="flex-1"
              @click="scheduleCallback"
            >
              Callback
            </UButton>
          </div>
        </div>
      </UCard>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '~/stores/agent'
import { useRouter } from 'vue-router'

const agentStore = useAgentStore()
const router = useRouter()

const visible = ref(false)
const contact = ref<any>(null)
const callerPhone = ref('')
const recentCalls = ref<any[]>([])
let dismissTimer: ReturnType<typeof setTimeout> | null = null
let ws: WebSocket | null = null

const authHeaders = () => ({ Authorization: 'Bearer ' + localStorage.getItem('auth_token') })

const fetchScreenPop = async (phone: string) => {
  try {
    const data = await $fetch(`/api/cc/screen-pop/?phone=${encodeURIComponent(phone)}`, {
      headers: authHeaders(),
    })
    contact.value = (data as any).contact || null
    recentCalls.value = (data as any).recent_calls || []
    callerPhone.value = phone
    if (contact.value) {
      visible.value = true
      // Auto-dismiss después de 15s
      if (dismissTimer) clearTimeout(dismissTimer)
      dismissTimer = setTimeout(dismiss, 15000)
    }
  } catch {
    // Contacto no encontrado — mostrar solo el número
    contact.value = { name: phone, is_vip: false, dnc_opt_out: false }
    callerPhone.value = phone
    recentCalls.value = []
    visible.value = true
  }
}

const dismiss = () => {
  visible.value = false
  if (dismissTimer) clearTimeout(dismissTimer)
}

const viewContact = () => {
  if (contact.value?.id) {
    router.push(`/contacts/${contact.value.id}`)
  }
  dismiss()
}

const scheduleCallback = () => {
  router.push({ path: '/callbacks', query: { phone: callerPhone.value } })
  dismiss()
}

const formatDate = (iso: string) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const callStatusColor = (status: string) => {
  const map: Record<string, string> = { completed: 'green', abandoned: 'red', answered: 'blue', busy: 'yellow' }
  return map[status] || 'gray'
}

// WebSocket para Screen Pop en tiempo real
const connectWS = () => {
  if (!agentStore.agent?.id) return
  const token = localStorage.getItem('auth_token') || ''
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${wsProto}://${location.host}/ws/agent/${agentStore.agent.id}/?token=${token}`)

  ws.onmessage = (evt) => {
    try {
      const msg = JSON.parse(evt.data)
      if (msg.type === 'screen_pop' || msg.type === 'incoming_call') {
        const phone = msg.caller_id || msg.phone || msg.callerNumber || ''
        if (phone) fetchScreenPop(phone)
      }
    } catch { /* ignore */ }
  }

  ws.onclose = () => {
    // Reconectar después de 3s si el agente sigue logueado
    if (agentStore.isLoggedIn) setTimeout(connectWS, 3000)
  }
}

onMounted(() => {
  if (agentStore.isLoggedIn) connectWS()
})

watch(() => agentStore.isLoggedIn, (v) => {
  if (v) connectWS()
  else {
    ws?.close()
    ws = null
  }
})

onUnmounted(() => {
  ws?.close()
  if (dismissTimer) clearTimeout(dismissTimer)
})
</script>

<style scoped>
.slide-right-enter-active,
.slide-right-leave-active {
  transition: all 0.3s ease;
}
.slide-right-enter-from,
.slide-right-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
