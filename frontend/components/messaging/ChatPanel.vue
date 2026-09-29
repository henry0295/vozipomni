<template>
  <div class="flex flex-col h-full min-h-0">
    <!-- Encabezado -->
    <div class="flex items-center justify-between gap-3 px-4 py-3 border-b border-gray-200 bg-white">
      <div class="flex items-center gap-3 min-w-0">
        <UButton v-if="showBack" icon="i-heroicons-arrow-left" color="gray" variant="ghost" size="sm" aria-label="Volver" @click="emit('back')" />
        <div class="relative flex-shrink-0">
          <UAvatar :alt="conv?.display_name || '?'" size="md" />
          <span v-if="conv" class="absolute -bottom-1 -right-1 rounded-full bg-white p-0.5" :title="channelLabel(conv.channel_type)">
            <UIcon :name="channelIcon(conv.channel_type)" class="w-3.5 h-3.5" :class="channelColor(conv.channel_type)" />
          </span>
        </div>
        <div class="min-w-0">
          <p class="font-semibold truncate">{{ conv?.display_name || '…' }}</p>
          <p class="text-xs text-gray-500 truncate">
            {{ conv ? identifierLabel(conv) : '' }}
            <span v-if="conv?.channel_name"> · {{ conv.channel_name }}</span>
            <span v-if="conv?.campaign_name"> · {{ conv.campaign_name }}</span>
          </p>
          <p v-if="conv?.subject" class="text-xs text-gray-700 truncate font-medium">Asunto: {{ conv.subject }}</p>
          <div v-if="conv?.tags?.length" class="flex flex-wrap gap-1 mt-0.5">
            <UBadge v-for="t in conv.tags" :key="t.id" size="xs" :color="t.color || 'gray'" variant="soft">{{ t.name }}</UBadge>
          </div>
        </div>
      </div>
      <div class="flex items-center gap-1 flex-shrink-0">
        <UBadge v-if="conv" :color="statusColor(conv.status)" variant="soft" size="xs">{{ conv.status_display || conv.status }}</UBadge>
        <UBadge v-if="conv && conv.window_hours" :color="conv.window_open ? 'green' : 'amber'" variant="soft" size="xs"
                :title="conv.window_open ? 'Puedes enviar texto libre' : 'Ventana de mensajería cerrada'">
          {{ conv.window_open ? `Ventana ${windowText(conv)} abierta` : 'Ventana cerrada' }}
        </UBadge>
        <UButton v-if="conv && !conv.agent && conv.status !== 'closed' && canTake" size="xs" icon="i-heroicons-hand-raised" :loading="acting === 'take'" @click="take">Tomar</UButton>
        <UButton v-if="phone" size="xs" color="green" variant="soft" icon="i-heroicons-phone" title="Llamar" aria-label="Llamar" @click="emit('call', phone)" />
        <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-information-circle" aria-label="Información del contacto" @click="showInfo = !showInfo" />
        <UButton v-if="conv && conv.status !== 'closed'" size="xs" color="gray" variant="outline" icon="i-heroicons-check-circle" :loading="acting === 'close'" @click="openClose">Cerrar</UButton>
        <UButton v-else-if="conv" size="xs" color="gray" variant="outline" icon="i-heroicons-arrow-uturn-left" :loading="acting === 'reopen'" @click="reopen">Reabrir</UButton>
      </div>
    </div>

    <div class="flex flex-1 min-h-0">
      <!-- Mensajes -->
      <div class="flex-1 flex flex-col min-w-0">
        <div ref="scroller" class="flex-1 overflow-y-auto p-4 space-y-2 bg-[#efeae2]" aria-live="polite">
          <div v-if="loading" class="text-center text-gray-500 text-sm py-8">Cargando mensajes…</div>
          <template v-else>
            <template v-for="(m, idx) in messages" :key="m.id">
              <div v-if="showDay(idx)" class="flex justify-center my-2">
                <span class="text-xs bg-white/80 text-gray-600 px-2 py-0.5 rounded shadow-sm">{{ dayLabel(m.sent_at) }}</span>
              </div>
              <div class="flex" :class="m.direction === 'outbound' ? 'justify-end' : 'justify-start'">
                <div class="max-w-[75%] rounded-lg px-3 py-2 shadow-sm"
                     :class="m.direction === 'outbound' ? (m.status === 'failed' ? 'bg-red-50 border border-red-200' : 'bg-[#d9fdd3]') : 'bg-white'">
                  <p v-if="m.direction === 'outbound' && (m.sender_name || m.metadata?.system)" class="text-[11px] font-semibold text-green-700 mb-0.5">
                    {{ m.metadata?.system ? (m.metadata?.broadcast_id ? 'Envío masivo' : 'Respuesta automática') : m.sender_name }}
                  </p>
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
          <UAlert v-if="conv.window_hours && !conv.window_open" class="mb-2" color="amber" variant="soft" icon="i-heroicons-clock">
            <template #description>
              <div class="flex items-center justify-between gap-2">
                <span v-if="conv.channel_type === 'whatsapp'" class="text-xs">Han pasado más de 24 h desde el último mensaje del cliente. Solo puedes enviar una plantilla aprobada hasta que responda.</span>
                <span v-else class="text-xs">Han pasado más de 7 días desde el último mensaje del cliente. Meta no permite escribirle hasta que vuelva a escribir.</span>
                <UButton v-if="conv.channel_type === 'whatsapp'" size="xs" color="amber" @click="openTemplates">Enviar plantilla</UButton>
              </div>
            </template>
          </UAlert>

          <!-- Sugerencias de respuestas rápidas al escribir "/" -->
          <div v-if="shortcutMatches.length" class="mb-2 border border-gray-200 rounded-md divide-y max-h-40 overflow-y-auto" role="listbox">
            <button v-for="q in shortcutMatches" :key="q.id" type="button" role="option"
                    class="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-50" @click="applyQuickReply(q, true)">
              <span class="font-mono text-xs text-primary-600 mr-2">{{ q.shortcut }}</span>
              <span class="font-medium">{{ q.title }}</span>
              <span class="text-gray-500 truncate"> — {{ q.body }}</span>
            </button>
          </div>

          <!-- Adjunto seleccionado -->
          <div v-if="pendingFile" class="mb-2 flex items-center gap-2 rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-sm">
            <UIcon :name="pendingFile.type.startsWith('image/') ? 'i-heroicons-photo' : 'i-heroicons-paper-clip'" class="w-4 h-4 text-gray-500" />
            <span class="truncate flex-1">{{ pendingFile.name }} <span class="text-gray-400">({{ fmtSize(pendingFile.size) }})</span></span>
            <span class="text-xs text-gray-400">El texto se envía como descripción</span>
            <UButton size="2xs" color="gray" variant="ghost" icon="i-heroicons-x-mark" aria-label="Quitar adjunto" @click="pendingFile = null" />
          </div>

          <div class="flex items-end gap-2">
            <UDropdown :items="quickReplyItems" :popper="{ placement: 'top-start' }">
              <UButton icon="i-heroicons-bolt" color="gray" variant="ghost" title="Respuestas rápidas" aria-label="Respuestas rápidas" />
            </UDropdown>
            <UButton icon="i-heroicons-paper-clip" color="gray" variant="ghost" title="Adjuntar archivo" aria-label="Adjuntar archivo"
                     :disabled="!composerEnabled || conv.channel_type === 'instagram'" @click="fileInput?.click()" />
            <input ref="fileInput" type="file" class="hidden" :accept="acceptTypes" @change="onFilePicked" />
            <UButton v-if="conv.channel_type === 'whatsapp'" icon="i-heroicons-document-text" color="gray" variant="ghost" title="Enviar plantilla" aria-label="Enviar plantilla" @click="openTemplates" />
            <UTextarea v-model="draft" :rows="2" autoresize :maxrows="6" class="flex-1"
                       :disabled="!composerEnabled"
                       :placeholder="pendingFile ? 'Descripción del archivo (opcional)…' : 'Escribe un mensaje… (Enter envía, Shift+Enter nueva línea, / respuestas rápidas)'"
                       aria-label="Mensaje"
                       @keydown.enter.exact.prevent="submit" />
            <UButton icon="i-heroicons-paper-airplane" color="green" :loading="sending" aria-label="Enviar"
                     :disabled="!composerEnabled || (!draft.trim() && !pendingFile)" @click="submit" />
          </div>
        </div>
        <div v-else-if="conv" class="border-t border-gray-200 bg-gray-50 p-3 text-center text-sm text-gray-500">
          Conversación cerrada {{ conv.closed_at ? '· ' + new Date(conv.closed_at).toLocaleString('es-CO') : '' }}
          <span v-if="conv.disposition_name"> · Tipificación: <strong>{{ conv.disposition_name }}</strong></span>
          <p v-if="conv.close_notes" class="text-xs text-gray-500 mt-1 italic">{{ conv.close_notes }}</p>
        </div>
      </div>

      <!-- Info del contacto -->
      <div v-if="showInfo && conv" class="w-64 border-l border-gray-200 bg-white p-4 space-y-3 overflow-y-auto text-sm">
        <h4 class="font-semibold">Contacto</h4>
        <div><p class="text-gray-500 text-xs">Nombre</p><p>{{ conv.display_name }}</p></div>
        <div><p class="text-gray-500 text-xs">{{ channelLabel(conv.channel_type) }}</p><p class="break-all">{{ identifierLabel(conv) }}</p></div>
        <template v-if="conv.channel_type === 'webchat' && conv.metadata">
          <div v-if="conv.metadata.visitor_email"><p class="text-gray-500 text-xs">Email del visitante</p><p class="break-all">{{ conv.metadata.visitor_email }}</p></div>
          <div v-if="conv.metadata.page_url"><p class="text-gray-500 text-xs">Página</p><p class="break-all text-xs">{{ conv.metadata.page_url }}</p></div>
        </template>
        <template v-if="conv.contact_details">
          <div v-if="conv.contact_details.phone"><p class="text-gray-500 text-xs">Teléfono</p><p>{{ conv.contact_details.phone }}</p></div>
          <div v-if="conv.contact_details.email"><p class="text-gray-500 text-xs">Email</p><p class="break-all">{{ conv.contact_details.email }}</p></div>
          <div v-if="conv.contact_details.company"><p class="text-gray-500 text-xs">Empresa</p><p>{{ conv.contact_details.company }}</p></div>
          <div v-if="conv.contact_details.city"><p class="text-gray-500 text-xs">Ciudad</p><p>{{ conv.contact_details.city }}</p></div>
          <UBadge v-if="conv.contact_details.is_vip" color="amber" variant="soft">VIP</UBadge>
        </template>
        <p v-else class="text-xs text-gray-400">No está vinculado a un contacto de la base.</p>
        <div><p class="text-gray-500 text-xs">Agente</p><p>{{ conv.agent_name || 'Sin asignar' }}</p></div>
        <div><p class="text-gray-500 text-xs">Iniciada</p><p>{{ new Date(conv.started_at).toLocaleString('es-CO') }}</p></div>
        <div v-if="conv.first_response_at"><p class="text-gray-500 text-xs">Primera respuesta</p><p>{{ fmtDuration((new Date(conv.first_response_at).getTime() - new Date(conv.started_at).getTime()) / 1000) }}</p></div>
        <div>
          <p class="text-gray-500 text-xs mb-1">Etiquetas</p>
          <USelectMenu v-model="tagSelection" :options="closeOptions.tags" multiple value-attribute="id" option-attribute="name"
                       placeholder="Agregar etiquetas" size="xs" @update:model-value="saveTags" />
        </div>
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

    <!-- Cierre con tipificación -->
    <UModal v-model="closeModal.open">
      <UCard>
        <template #header><h3 class="font-semibold">Cerrar conversación</h3></template>
        <div class="space-y-4">
          <UFormGroup v-if="closeOptions.dispositions.length" label="Tipificación" :required="closeOptions.disposition_required">
            <div class="grid grid-cols-2 gap-2">
              <button v-for="d in closeOptions.dispositions" :key="d.id" type="button"
                      class="text-left px-3 py-2 rounded-md border text-sm transition-colors"
                      :class="closeModal.disposition_id === d.id ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-500' : 'border-gray-200 hover:bg-gray-50'"
                      :aria-pressed="closeModal.disposition_id === d.id"
                      @click="closeModal.disposition_id = d.id">
                <span class="font-medium">{{ d.name }}</span>
                <UBadge v-if="d.is_success" size="xs" color="green" variant="soft" class="ml-1">Éxito</UBadge>
                <UBadge v-if="d.requires_callback" size="xs" color="amber" variant="soft" class="ml-1">Rellamar</UBadge>
              </button>
            </div>
          </UFormGroup>
          <p v-else class="text-xs text-gray-500">La campaña de esta conversación no tiene calificaciones configuradas.</p>
          <UFormGroup label="Etiquetas">
            <USelectMenu v-model="closeModal.tag_ids" :options="closeOptions.tags" multiple value-attribute="id"
                         option-attribute="name" placeholder="Selecciona etiquetas" />
          </UFormGroup>
          <UFormGroup label="Notas">
            <UTextarea v-model="closeModal.notes" :rows="3" placeholder="Resumen de la gestión (opcional)" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="closeModal.open = false">Cancelar</UButton>
            <UButton :loading="acting === 'close'" :disabled="closeOptions.disposition_required && !closeModal.disposition_id" @click="confirmClose">Cerrar conversación</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
/**
 * Vista de una conversación (WhatsApp, email, chat web, Messenger, Instagram):
 * historial, envío de texto y adjuntos, plantillas, respuestas rápidas,
 * etiquetas, cierre con tipificación y reintentos.
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
const fileInput = ref<HTMLInputElement>()
const pendingFile = ref<File | null>(null)
const mediaReload = reactive<Record<number, number>>({})
const tplModal = ref(false)
const tplValue = ref<any>(null)
const quickReplies = ref<any[]>([])
const closeOptions = reactive<{ dispositions: any[], disposition_required: boolean, tags: any[] }>({
  dispositions: [], disposition_required: false, tags: [],
})
const closeModal = reactive({ open: false, disposition_id: null as number | null, tag_ids: [] as number[], notes: '' })
const tagSelection = ref<number[]>([])

const CHANNELS: Record<string, { label: string, icon: string, color: string }> = {
  whatsapp: { label: 'WhatsApp', icon: 'i-heroicons-chat-bubble-oval-left-ellipsis', color: 'text-green-600' },
  email: { label: 'Email', icon: 'i-heroicons-envelope', color: 'text-sky-600' },
  webchat: { label: 'Chat web', icon: 'i-heroicons-globe-alt', color: 'text-violet-600' },
  messenger: { label: 'Messenger', icon: 'i-heroicons-chat-bubble-left-right', color: 'text-blue-600' },
  instagram: { label: 'Instagram', icon: 'i-heroicons-camera', color: 'text-pink-600' },
}
const channelLabel = (t: string) => CHANNELS[t]?.label || t
const channelIcon = (t: string) => CHANNELS[t]?.icon || 'i-heroicons-chat-bubble-left'
const channelColor = (t: string) => CHANNELS[t]?.color || 'text-gray-500'
const windowText = (c: any) => c.channel_type === 'whatsapp' ? '24 h' : '7 días'
const identifierLabel = (c: any) => {
  if (c.channel_type === 'whatsapp') return `+${c.contact_identifier}`
  if (c.channel_type === 'email') return c.contact_identifier
  if (c.channel_type === 'webchat') return c.metadata?.visitor_email || 'Visitante del sitio web'
  return `ID ${c.contact_identifier}`
}

const composerEnabled = computed(() => !!conv.value && (!conv.value.window_hours || conv.value.window_open))
const phone = computed(() => {
  if (!conv.value) return ''
  if (conv.value.contact_details?.phone) return conv.value.contact_details.phone
  return conv.value.channel_type === 'whatsapp' ? conv.value.contact_identifier : ''
})
const acceptTypes = computed(() => conv.value?.channel_type === 'whatsapp'
  ? 'image/jpeg,image/png,audio/*,video/mp4,video/3gpp,application/pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip'
  : '*/*')

const quickReplyItems = computed(() => {
  const list = quickReplies.value.length
    ? quickReplies.value
    : [{ id: 0, title: 'Sin respuestas rápidas', body: '', disabled: true }]
  return [list.map((q: any) => ({
    label: q.shortcut ? `${q.shortcut} · ${q.title}` : q.title,
    disabled: q.disabled,
    click: () => applyQuickReply(q, false),
  }))]
})
const shortcutMatches = computed(() => {
  const d = draft.value
  if (!d.startsWith('/') || d.includes(' ') || d.includes('\n')) return []
  const term = d.toLowerCase()
  return quickReplies.value.filter(q => (q.shortcut || '').toLowerCase().startsWith(term)
    || (term.length > 1 && q.title.toLowerCase().includes(term.slice(1)))).slice(0, 6)
})

function applyQuickReply(q: any, replace: boolean) {
  if (!q?.body) return
  const name = conv.value?.contact_details?.full_name || conv.value?.contact_name || ''
  const text = q.body.replace(/\{nombre\}/gi, name.split(' ')[0] || '').replace(/\{agente\}/gi, conv.value?.agent_name || '')
  draft.value = replace || !draft.value ? text : `${draft.value} ${text}`
}

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
const fmtSize = (b: number) => b < 1048576 ? `${(b / 1024).toFixed(0)} KB` : `${(b / 1048576).toFixed(1)} MB`
const fmtDuration = (s: number) => {
  if (s == null || isNaN(s)) return '—'
  if (s < 60) return `${Math.round(s)} s`
  if (s < 3600) return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`
  return `${Math.floor(s / 3600)} h ${Math.floor((s % 3600) / 60)} min`
}
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
  tagSelection.value = (conv.value?.tags || []).map((t: any) => t.id)
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

async function loadQuickReplies() {
  try {
    quickReplies.value = http.results(await http.get('/messaging/quick-replies/', {
      for_agent: 1, campaign: conv.value?.campaign || '', channel_type: conv.value?.channel_type || '',
    }))
  } catch { quickReplies.value = [] }
}

async function loadCloseOptions() {
  try {
    const o: any = await http.get(`/messaging/conversations/${props.conversationId}/close-options/`)
    closeOptions.dispositions = o.dispositions || []
    closeOptions.disposition_required = !!o.disposition_required
    closeOptions.tags = o.tags || []
  } catch { /* opcional */ }
}

async function reload() {
  try {
    await Promise.all([loadConversation(), loadMessages()])
    loadQuickReplies()
    loadCloseOptions()
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

function handleSendError(e: any) {
  const d = e?.data
  if (d?.code === 'window_closed') {
    conv.value.window_open = false
    toast.add({ title: 'Ventana de mensajería cerrada', description: d.error, color: 'amber' })
    if (conv.value.channel_type === 'whatsapp') openTemplates()
  } else if (d && d.id) {
    // 502: el mensaje se guardó pero el canal lo rechazó
    upsertMessage(d)
    draft.value = ''
    pendingFile.value = null
    toast.add({ title: 'El canal rechazó el mensaje', description: d.error_message, color: 'red' })
  } else {
    toast.add({ title: 'No se pudo enviar', description: http.errorMessage(e), color: 'red' })
  }
}

function submit() {
  if (shortcutMatches.value.length === 1 && draft.value.trim() === shortcutMatches.value[0].shortcut) {
    applyQuickReply(shortcutMatches.value[0], true)
    return
  }
  if (pendingFile.value) sendFile()
  else send()
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
    handleSendError(e)
  } finally { sending.value = false }
}

function onFilePicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0] || null
  input.value = ''
  if (!file) return
  const maxMb = conv.value?.channel_type === 'email' ? 20 : 100
  if (file.size > maxMb * 1024 * 1024) {
    toast.add({ title: `El archivo supera ${maxMb} MB`, color: 'red' })
    return
  }
  pendingFile.value = file
}

async function sendFile() {
  if (!pendingFile.value || sending.value) return
  sending.value = true
  try {
    const fd = new FormData()
    fd.append('file', pendingFile.value)
    if (draft.value.trim()) fd.append('caption', draft.value.trim())
    const m = await http.post(`/messaging/conversations/${props.conversationId}/attachments/`, fd)
    upsertMessage(m)
    pendingFile.value = null
    draft.value = ''
    emit('changed')
  } catch (e: any) {
    handleSendError(e)
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

async function act(action: 'take' | 'reopen') {
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
const reopen = () => act('reopen')

async function openClose() {
  await loadCloseOptions()
  Object.assign(closeModal, {
    open: true, disposition_id: null, notes: '',
    tag_ids: (conv.value?.tags || []).map((t: any) => t.id),
  })
}

async function confirmClose() {
  acting.value = 'close'
  try {
    await http.post(`/messaging/conversations/${props.conversationId}/close/`, {
      disposition_id: closeModal.disposition_id,
      tag_ids: closeModal.tag_ids,
      notes: closeModal.notes,
    })
    closeModal.open = false
    await loadConversation()
    toast.add({ title: 'Conversación cerrada', color: 'green' })
    emit('changed')
  } catch (e: any) {
    toast.add({ title: 'No se pudo cerrar', description: http.errorMessage(e), color: 'red' })
  } finally { acting.value = '' }
}

async function saveTags(ids: number[]) {
  try {
    const c: any = await http.post(`/messaging/conversations/${props.conversationId}/tags/`, { tag_ids: ids })
    conv.value.tags = c.tags
  } catch (e: any) {
    toast.add({ title: 'No se pudieron guardar las etiquetas', description: http.errorMessage(e), color: 'red' })
  }
}

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

watch(() => props.conversationId, () => {
  draft.value = ''
  pendingFile.value = null
  showInfo.value = false
  reload()
}, { immediate: true })
onBeforeUnmount(() => { if (reloadTimer) clearTimeout(reloadTimer) })
</script>
