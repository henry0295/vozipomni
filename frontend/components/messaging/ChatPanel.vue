<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- Encabezado -->
    <div class="flex items-center justify-between gap-3 px-4 py-3 border-b border-gray-200 bg-white">
      <div class="flex items-center gap-3 min-w-0">
        <UButton v-if="showBack" icon="i-heroicons-arrow-left" color="gray" variant="ghost" size="sm" @click="emit('back')" />
        <UAvatar :alt="conv?.display_name || '?'" size="md" />
        <div class="min-w-0">
          <p class="font-semibold truncate">{{ conv?.display_name || '…' }}</p>
          <p class="text-xs text-gray-500 truncate">
            +{{ conv?.contact_identifier }}
            <span v-if="conv?.channel_name"> · {{ conv.channel_name }}</span>
            <span v-if="conv?.campaign_name"> · {{ conv.campaign_name }}</span>
          </p>
        </div>
      </div>
      <div class="flex items-center gap-1 flex-shrink-0">
        <UBadge v-if="conv" :color="statusColor(conv.status)" variant="soft" size="xs">{{ conv.status_display || conv.status }}</UBadge>
        <UBadge v-if="conv && conv.channel_type === 'whatsapp'" :color="conv.window_open ? 'green' : 'amber'" variant="soft" size="xs"
                :title="conv.window_open ? 'Puedes enviar texto libre' : 'Solo plantillas: han pasado más de 24 h desde el último mensaje del cliente'">
          {{ conv.window_open ? 'Ventana 24 h abierta' : 'Ventana cerrada' }}
        </UBadge>
        <UButton v-if="conv && !conv.agent && conv.status !== 'closed' && canTake" size="xs" icon="i-heroicons-hand-raised" :loading="acting === 'take'" @click="take">Tomar</UButton>
        <UButton v-if="phone" size="xs" color="green" variant="soft" icon="i-heroicons-phone" title="Llamar" @click="emit('call', phone)" />
        <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-information-circle" @click="showInfo = !showInfo" />
        <UButton v-if="conv && conv.status !== 'closed'" size="xs" color="gray" variant="outline" icon="i-heroicons-check-circle" :loading="acting === 'close'" @click="close">Cerrar</UButton>
        <UButton v-else-if="conv" size="xs" color="gray" variant="outline" icon="i-heroicons-arrow-uturn-left" :loading="acting === 'reopen'" @click="reopen">Reabrir</UButton>
      </div>
    </div>

    <div class="flex flex-1 min-h-0">
      <!-- Mensajes -->
      <div class="flex-1 flex flex-col min-w-0">
        <div ref="scroller" class="flex-1 overflow-y-auto p-4 space-y-2 bg-[#efeae2]">
          <div v-if="loading" class="text-center text-gray-500 text-sm py-8">Cargando mensajes…</div>
          <template v-else>
            <template v-for="(m, idx) in messages" :key="m.id">
              <div v-if="showDay(idx)" class="flex justify-center my-2">
                <span class="text-xs bg-white/80 text-gray-600 px-2 py-0.5 rounded shadow-sm">{{ dayLabel(m.sent_at) }}</span>
              </div>
              <div class="flex" :class="m.direction === 'outbound' ? 'justify-end' : 'justify-start'">
                <div class="max-w-[75%] rounded-lg px-3 py-2 shadow-sm"
                     :class="m.direction === 'outbound' ? (m.status === 'failed' ? 'bg-red-50 border border-red-200' : 'bg-[#d9fdd3]') : 'bg-white'">
                  <p v-if="m.direction === 'outbound' && m.sender_name" class="text-[11px] font-semibold text-green-700 mb-0.5">{{ m.sender_name }}</p>
                  <MessagingMessageMedia v-if="m.has_media && isMedia(m.message_type)" :message="m" :reload-key="mediaReload[m.id] || 0" class="mb-1" />
                  <div v-if="m.message_type === 'template'" class="flex items-center gap-1 text-[11px] text-gray-500 mb-0.5">
                    <UIcon name="i-heroicons-document-text" class="w-3 h-3" /> Plantilla {{ m.metadata?.template_name }}
                  </div>
                  <p v-if="m.body" class="text-sm whitespace-pre-wrap break-words">{{ m.body }}</p>
                  <p v-else-if="!m.has_media" class="text-sm italic text-gray-500">[{{ typeLabel(m.message_type) }}]</p>
                  <div class="flex items-center justify-end gap-1 mt-0.5">
                    <span class="text-[10px] text-gray-500">{{ timeLabel(m.sent_at) }}</span>
                    <template v-if="m.direction === 'outbound'">
                      <UIcon v-if="m.status === 'pending'" name="i-heroicons-clock" class="w-3 h-3 text-gray-400" title="Enviando" />
                      <UIcon v-else-if="m.status === 'sent'" name="i-heroicons-check" class="w-3 h-3 text-gray-500" title="Enviado" />
                      <span v-else-if="m.status === 'delivered'" class="text-[11px] text-gray-500 leading-none" title="Entregado">✓✓</span>
                      <span v-else-if="m.status === 'read'" class="text-[11px] text-sky-500 leading-none" title="Leído">✓✓</span>
                      <UIcon v-else-if="m.status === 'failed'" name="i-heroicons-exclamation-circle" class="w-3 h-3 text-red-500" title="Fallido" />
                    </template>
                  </div>
                  <div v-if="m.status === 'failed'" class="mt-1 flex items-start gap-2">
                    <p class="text-[11px] text-red-600 flex-1">{{ m.error_message || 'No se pudo enviar' }}</p>
                    <UButton size="2xs" color="red" variant="soft" icon="i-heroicons-arrow-path" :loading="retrying === m.id" @click="retry(m)">Reintentar</UButton>
                  </div>
                </div>
              </div>
            </template>
            <p v-if="!messages.length" class="text-center text-gray-500 text-sm py-8">Sin mensajes</p>
          </template>
        </div>

        <!-- Compositor -->
        <div v-if="conv && conv.status !== 'closed'" class="border-t border-gray-200 bg-white p-3">
          <UAlert v-if="conv.channel_type === 'whatsapp' && !conv.window_open" class="mb-2" color="amber" variant="soft" icon="i-heroicons-clock">
            <template #description>
              <div class="flex items-center justify-between gap-2">
                <span class="text-xs">Han pasado más de 24 h desde el último mensaje del cliente. Solo puedes enviar una plantilla aprobada hasta que responda.</span>
                <UButton size="xs" color="amber" @click="openTemplates">Enviar plantilla</UButton>
              </div>
            </template>
          </UAlert>
          <div class="flex items-end gap-2">
            <UDropdown :items="quickReplyItems" :popper="{ placement: 'top-start' }">
              <UButton icon="i-heroicons-bolt" color="gray" variant="ghost" title="Respuestas rápidas" />
            </UDropdown>
            <UButton v-if="conv.channel_type === 'whatsapp'" icon="i-heroicons-document-text" color="gray" variant="ghost" title="Enviar plantilla" @click="openTemplates" />
            <UTextarea v-model="draft" :rows="2" autoresize :maxrows="6" class="flex-1"
                       :disabled="conv.channel_type === 'whatsapp' && !conv.window_open"
                       placeholder="Escribe un mensaje… (Enter para enviar, Shift+Enter nueva línea)"
                       @keydown.enter.exact.prevent="send" />
            <UButton icon="i-heroicons-paper-airplane" color="green" :loading="sending"
                     :disabled="!draft.trim() || (conv.channel_type === 'whatsapp' && !conv.window_open)" @click="send" />
          </div>
        </div>
        <div v-else-if="conv" class="border-t border-gray-200 bg-gray-50 p-3 text-center text-sm text-gray-500">
          Conversación cerrada {{ conv.closed_at ? '· ' + new Date(conv.closed_at).toLocaleString('es-CO') : '' }}
        </div>
      </div>

      <!-- Info del contacto -->
      <div v-if="showInfo && conv" class="w-64 border-l border-gray-200 bg-white p-4 space-y-3 overflow-y-auto text-sm">
        <h4 class="font-semibold">Contacto</h4>
        <div><p class="text-gray-500 text-xs">Nombre</p><p>{{ conv.display_name }}</p></div>
        <div><p class="text-gray-500 text-xs">WhatsApp</p><p>+{{ conv.contact_identifier }}</p></div>
        <template v-if="conv.contact_details">
          <div v-if="conv.contact_details.email"><p class="text-gray-500 text-xs">Email</p><p>{{ conv.contact_details.email }}</p></div>
          <div v-if="conv.contact_details.company"><p class="text-gray-500 text-xs">Empresa</p><p>{{ conv.contact_details.company }}</p></div>
          <div v-if="conv.contact_details.city"><p class="text-gray-500 text-xs">Ciudad</p><p>{{ conv.contact_details.city }}</p></div>
          <UBadge v-if="conv.contact_details.is_vip" color="amber" variant="soft">VIP</UBadge>
        </template>
        <p v-else class="text-xs text-gray-400">No está vinculado a un contacto de la base.</p>
        <div><p class="text-gray-500 text-xs">Agente</p><p>{{ conv.agent_name || 'Sin asignar' }}</p></div>
        <div><p class="text-gray-500 text-xs">Iniciada</p><p>{{ new Date(conv.started_at).toLocaleString('es-CO') }}</p></div>
      </div>
    </div>

    <!-- Plantillas -->
    <UModal v-model="tplModal">
      <UCard>
        <template #header><h3 class="font-semibold">Enviar plantilla de WhatsApp</h3></template>
        <MessagingTemplateForm v-if="tplModal" v-model="tplValue" :line-id="conv?.whatsapp_line_id" />
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="tplModal = false">Cancelar</UButton>
            <UButton icon="i-heroicons-paper-airplane" color="green" :loading="sending" :disabled="!tplValue?.valid" @click="sendTemplate">Enviar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
/**
 * Vista de una conversación: historial, envío de texto (ventana 24 h),
 * envío de plantillas, reintentos y acciones (tomar / cerrar / reabrir).
 *
 * El padre reenvía los eventos del WebSocket /ws/messaging/ con handleEvent().
 */
const props = withDefaults(defineProps<{
  conversationId: number
  showBack?: boolean
  canTake?: boolean
}>(), { showBack: false, canTake: true })
const emit = defineEmits(['back', 'changed', 'call'])

const http = useHttp()
const toast = useToast()

const conv = ref<any>(null)
const messages = ref<any[]>([])
const loading = ref(false)
const sending = ref(false)
const acting = ref('')
const retrying = ref<number | null>(null)
const draft = ref('')
const showInfo = ref(false)
const scroller = ref<HTMLElement>()
const mediaReload = reactive<Record<number, number>>({})
const tplModal = ref(false)
const tplValue = ref<any>(null)

const phone = computed(() => conv.value?.contact_details?.phone || conv.value?.contact_identifier || '')

const quickReplies = [
  'Hola, gracias por escribirnos. ¿En qué te puedo ayudar?',
  'Con gusto, permíteme un momento mientras reviso la información.',
  '¿Hay algo más en lo que te pueda ayudar?',
  'Gracias por comunicarte con nosotros. ¡Que tengas un excelente día!',
]
const quickReplyItems = computed(() => [quickReplies.map(text => ({
  label: text.length > 50 ? text.slice(0, 50) + '…' : text,
  click: () => { draft.value = draft.value ? `${draft.value} ${text}` : text },
}))])

const MEDIA_TYPES = ['image', 'audio', 'video', 'document', 'sticker']
const isMedia = (t: string) => MEDIA_TYPES.includes(t)
const TYPE_LABELS: Record<string, string> = {
  image: 'Imagen', audio: 'Audio', video: 'Video', document: 'Documento', sticker: 'Sticker',
  location: 'Ubicación', contacts: 'Contacto', interactive: 'Respuesta interactiva', button: 'Botón',
  reaction: 'Reacción', system: 'Sistema', unknown: 'Mensaje no soportado',
}
const typeLabel = (t: string) => TYPE_LABELS[t] || t
const statusColor = (s: string) => ({ open: 'green', waiting: 'amber', closed: 'gray' } as any)[s] || 'gray'
const timeLabel = (v: string) => new Date(v).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
const dayLabel = (v: string) => {
  const d = new Date(v)
  const today = new Date()
  const y = new Date(Date.now() - 86400000)
  if (d.toDateString() === today.toDateString()) return 'Hoy'
  if (d.toDateString() === y.toDateString()) return 'Ayer'
  return d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })
}
const showDay = (idx: number) =>
  idx === 0 || new Date(messages.value[idx - 1].sent_at).toDateString() !== new Date(messages.value[idx].sent_at).toDateString()

function scrollBottom() {
  nextTick(() => { if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight })
}

async function loadConversation() {
  conv.value = await http.get(`/messaging/conversations/${props.conversationId}/`)
}

async function loadMessages(silent = false) {
  if (!silent) loading.value = true
  try {
    const nearBottom = !scroller.value ||
      scroller.value.scrollHeight - scroller.value.scrollTop - scroller.value.clientHeight < 120
    messages.value = await http.get(`/messaging/conversations/${props.conversationId}/messages/`) as any[]
    if (!silent || nearBottom) scrollBottom()
  } catch (e: any) {
    toast.add({ title: 'Error cargando mensajes', description: http.errorMessage(e), color: 'red' })
  } finally { loading.value = false }
}

async function reload() {
  try {
    await Promise.all([loadConversation(), loadMessages()])
  } catch (e: any) {
    toast.add({ title: 'No se pudo abrir la conversación', description: http.errorMessage(e), color: 'red' })
  }
}

function upsertMessage(m: any) {
  const i = messages.value.findIndex(x => x.id === m.id)
  if (i >= 0) messages.value[i] = m
  else messages.value.push(m)
  scrollBottom()
}

async function send() {
  const body = draft.value.trim()
  if (!body || sending.value) return
  sending.value = true
  try {
    const m = await http.post(`/messaging/conversations/${props.conversationId}/messages/`, { body })
    draft.value = ''
    upsertMessage(m)
    if (!conv.value.agent) await loadConversation()
    emit('changed')
  } catch (e: any) {
    const d = e?.data
    if (d?.code === 'window_closed') {
      conv.value.window_open = false
      toast.add({ title: 'Ventana de 24 h cerrada', description: 'Envía una plantilla aprobada para retomar la conversación.', color: 'amber' })
      openTemplates()
    } else if (d && d.id) {
      // 502: el mensaje se guardó pero Meta lo rechazó
      upsertMessage(d)
      draft.value = ''
      toast.add({ title: 'WhatsApp rechazó el mensaje', description: d.error_message, color: 'red' })
    } else {
      toast.add({ title: 'No se pudo enviar', description: http.errorMessage(e), color: 'red' })
    }
  } finally { sending.value = false }
}

function openTemplates() {
  tplValue.value = null
  tplModal.value = true
}

async function sendTemplate() {
  if (!tplValue.value?.valid) return
  sending.value = true
  try {
    const m = await http.post(`/messaging/conversations/${props.conversationId}/send-template/`, {
      template_id: tplValue.value.template_id,
      body_params: tplValue.value.body_params,
      header_params: tplValue.value.header_params,
    })
    upsertMessage(m)
    tplModal.value = false
    emit('changed')
  } catch (e: any) {
    const d = e?.data
    if (d && d.id) { upsertMessage(d); tplModal.value = false }
    toast.add({ title: 'No se pudo enviar la plantilla', description: d?.error_message || http.errorMessage(e), color: 'red' })
  } finally { sending.value = false }
}

async function retry(m: any) {
  retrying.value = m.id
  try {
    upsertMessage(await http.post(`/messaging/messages/${m.id}/retry/`))
  } catch (e: any) {
    toast.add({ title: 'No se pudo reintentar', description: http.errorMessage(e), color: 'red' })
  } finally { retrying.value = null }
}

async function act(action: 'take' | 'close' | 'reopen') {
  acting.value = action
  try {
    await http.post(`/messaging/conversations/${props.conversationId}/${action}/`)
    await loadConversation()
    emit('changed')
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { acting.value = '' }
}
const take = () => act('take')
const close = () => act('close')
const reopen = () => act('reopen')

/** Eventos del WebSocket para esta conversación */
let reloadTimer: ReturnType<typeof setTimeout> | null = null
function handleEvent(evt: any) {
  if (!evt || evt.conversation_id !== props.conversationId) return
  if (evt.event === 'message.status') {
    const m = messages.value.find(x => x.id === evt.message_id)
    if (m) {
      m.status = evt.message_status
      if (evt.error) m.error_message = evt.error
      return
    }
  }
  if (evt.event === 'message.media') {
    mediaReload[evt.message_id] = (mediaReload[evt.message_id] || 0) + 1
    const m = messages.value.find(x => x.id === evt.message_id)
    if (m) { m.has_media = true; return }
  }
  // Nuevo mensaje / cambios de estado: recargar con debounce
  if (reloadTimer) clearTimeout(reloadTimer)
  reloadTimer = setTimeout(() => {
    loadMessages(true)
    loadConversation().catch(() => {})
  }, 300)
}

defineExpose({ handleEvent, reload })

watch(() => props.conversationId, () => { draft.value = ''; showInfo.value = false; reload() }, { immediate: true })
onBeforeUnmount(() => { if (reloadTimer) clearTimeout(reloadTimer) })
</script>
