<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Respuestas rápidas y etiquetas</h1>
        <p class="text-sm text-gray-500 mt-1">Textos predefinidos para los agentes (globales o por campaña) y etiquetas para clasificar conversaciones.</p>
      </div>
      <UButton icon="i-heroicons-arrow-left" color="gray" variant="ghost" to="/messaging">Bandeja</UButton>
    </div>

    <UTabs v-model="tab" :items="[{ label: 'Respuestas rápidas', icon: 'i-heroicons-bolt' }, { label: 'Etiquetas', icon: 'i-heroicons-tag' }]" />

    <!-- Respuestas rápidas -->
    <UCard v-if="tab === 0">
      <template #header>
        <div class="flex flex-wrap gap-2 items-center">
          <USelect v-model="qrCampaign" :options="[{ label: 'Todas', value: '' }, { label: 'Globales', value: 'global' }, ...campaignOptions]" class="w-56" @change="loadReplies" />
          <USelect v-model="qrChannel" :options="channelOptions" class="w-48" @change="loadReplies" />
          <UInput v-model="qrSearch" icon="i-heroicons-magnifying-glass" placeholder="Buscar" class="w-56" @keyup.enter="loadReplies" />
          <UButton icon="i-heroicons-plus" class="ml-auto" @click="openReply()">Nueva respuesta</UButton>
        </div>
      </template>
      <UTable :rows="replies" :columns="replyColumns" :loading="loadingReplies"
              :empty-state="{ icon: 'i-heroicons-bolt', label: 'No hay respuestas rápidas' }">
        <template #shortcut-data="{ row }"><span class="font-mono text-xs">{{ row.shortcut || '—' }}</span></template>
        <template #body-data="{ row }"><p class="text-sm max-w-md whitespace-pre-line line-clamp-2">{{ row.body }}</p></template>
        <template #campaign_name-data="{ row }">{{ row.campaign_name || 'Global' }}</template>
        <template #channel_type-data="{ row }">{{ row.channel_type ? channelMeta(row.channel_type).label : 'Todos' }}</template>
        <template #is_active-data="{ row }"><UToggle :model-value="row.is_active" @update:model-value="toggleReply(row)" /></template>
        <template #actions-data="{ row }">
          <UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost" aria-label="Editar" @click="openReply(row)" />
          <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost" aria-label="Eliminar" @click="removeReply(row)" />
        </template>
      </UTable>
      <p class="text-xs text-gray-500 mt-3">En el chat, el agente escribe el atajo (ej: <code>/saludo</code>) o usa el botón ⚡. Variables disponibles: <code>{nombre}</code> (cliente) y <code>{agente}</code>.</p>
    </UCard>

    <!-- Etiquetas -->
    <UCard v-if="tab === 1">
      <template #header>
        <div class="flex justify-between items-center">
          <p class="text-sm text-gray-500">Las etiquetas se asignan desde el chat o al cerrar la conversación y aparecen en métricas y reportes.</p>
          <UButton icon="i-heroicons-plus" @click="openTag()">Nueva etiqueta</UButton>
        </div>
      </template>
      <UTable :rows="tags" :columns="tagColumns" :loading="loadingTags" :empty-state="{ icon: 'i-heroicons-tag', label: 'No hay etiquetas' }">
        <template #name-data="{ row }"><UBadge :color="row.color" variant="soft">{{ row.name }}</UBadge></template>
        <template #is_active-data="{ row }"><UToggle :model-value="row.is_active" @update:model-value="toggleTag(row)" /></template>
        <template #actions-data="{ row }">
          <UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost" aria-label="Editar" @click="openTag(row)" />
          <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost" aria-label="Eliminar" @click="removeTag(row)" />
        </template>
      </UTable>
    </UCard>

    <UModal v-model="replyForm.open">
      <UCard>
        <template #header><h3 class="font-semibold">{{ replyForm.id ? 'Editar respuesta rápida' : 'Nueva respuesta rápida' }}</h3></template>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Título" required><UInput v-model="replyForm.title" placeholder="Saludo" /></UFormGroup>
            <UFormGroup label="Atajo" hint="Opcional"><UInput v-model="replyForm.shortcut" placeholder="/saludo" /></UFormGroup>
          </div>
          <UFormGroup label="Texto" required>
            <UTextarea v-model="replyForm.body" :rows="4" placeholder="Hola {nombre}, gracias por escribirnos. Soy {agente}, ¿en qué te ayudo?" />
          </UFormGroup>
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Campaña"><USelect v-model="replyForm.campaign" :options="[{ label: 'Global (todas)', value: '' }, ...campaignOptions]" /></UFormGroup>
            <UFormGroup label="Canal"><USelect v-model="replyForm.channel_type" :options="[{ label: 'Todos', value: '' }, ...channelOptions.slice(1)]" /></UFormGroup>
          </div>
          <UFormGroup label="Orden"><UInput v-model.number="replyForm.order" type="number" class="w-24" /></UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="replyForm.open = false">Cancelar</UButton>
            <UButton :loading="replyForm.saving" :disabled="!replyForm.title.trim() || !replyForm.body.trim()" @click="saveReply">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <UModal v-model="tagForm.open">
      <UCard>
        <template #header><h3 class="font-semibold">{{ tagForm.id ? 'Editar etiqueta' : 'Nueva etiqueta' }}</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Nombre" required><UInput v-model="tagForm.name" maxlength="50" placeholder="Reclamo, Venta, Soporte…" /></UFormGroup>
          <UFormGroup label="Color">
            <div class="flex flex-wrap gap-2">
              <button v-for="c in colors" :key="c" type="button" :aria-label="c" :aria-pressed="tagForm.color === c"
                      class="rounded-full" :class="tagForm.color === c ? 'ring-2 ring-offset-1 ring-gray-500' : ''" @click="tagForm.color = c">
                <UBadge :color="c" variant="solid" size="xs">{{ tagForm.name || c }}</UBadge>
              </button>
            </div>
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="tagForm.open = false">Cancelar</UButton>
            <UButton :loading="tagForm.saving" :disabled="!tagForm.name.trim()" @click="saveTag">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { CHANNEL_FILTER_OPTIONS, channelMeta } from '~/utils/channels'

useHead({ title: 'Respuestas rápidas y etiquetas - VozipOmni' })

const http = useHttp()
const toast = useToast()
const tab = ref(0)
const channelOptions = CHANNEL_FILTER_OPTIONS
const colors = ['gray', 'red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 'teal', 'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 'pink']

const campaignOptions = ref<{ label: string, value: string }[]>([])
const replies = ref<any[]>([])
const tags = ref<any[]>([])
const loadingReplies = ref(false)
const loadingTags = ref(false)
const qrCampaign = ref('')
const qrChannel = ref('')
const qrSearch = ref('')

const replyColumns = [
  { key: 'title', label: 'Título' }, { key: 'shortcut', label: 'Atajo' }, { key: 'body', label: 'Texto' },
  { key: 'campaign_name', label: 'Campaña' }, { key: 'channel_type', label: 'Canal' },
  { key: 'is_active', label: 'Activa' }, { key: 'actions', label: '' },
]
const tagColumns = [
  { key: 'name', label: 'Etiqueta' }, { key: 'usage', label: 'Conversaciones' },
  { key: 'is_active', label: 'Activa' }, { key: 'actions', label: '' },
]

const replyForm = reactive({ open: false, saving: false, id: null as number | null, title: '', shortcut: '', body: '', campaign: '', channel_type: '', order: 0 })
const tagForm = reactive({ open: false, saving: false, id: null as number | null, name: '', color: 'gray' })

async function loadReplies() {
  loadingReplies.value = true
  try {
    const q: any = {}
    if (qrCampaign.value) q.campaign = qrCampaign.value
    if (qrChannel.value) q.channel_type = qrChannel.value
    if (qrSearch.value) q.search = qrSearch.value
    replies.value = http.results(await http.get('/messaging/quick-replies/', q))
  } finally { loadingReplies.value = false }
}
async function loadTags() {
  loadingTags.value = true
  try { tags.value = http.results(await http.get('/messaging/tags/')) }
  finally { loadingTags.value = false }
}

function openReply(r?: any) {
  Object.assign(replyForm, {
    open: true, saving: false, id: r?.id ?? null, title: r?.title ?? '', shortcut: r?.shortcut ?? '',
    body: r?.body ?? '', campaign: r?.campaign ? String(r.campaign) : '', channel_type: r?.channel_type ?? '', order: r?.order ?? 0,
  })
}
async function saveReply() {
  replyForm.saving = true
  try {
    const body = {
      title: replyForm.title.trim(), shortcut: replyForm.shortcut.trim(), body: replyForm.body,
      campaign: replyForm.campaign ? Number(replyForm.campaign) : null, channel_type: replyForm.channel_type, order: replyForm.order || 0,
    }
    if (replyForm.id) await http.patch(`/messaging/quick-replies/${replyForm.id}/`, body)
    else await http.post('/messaging/quick-replies/', body)
    replyForm.open = false
    toast.add({ title: 'Guardado', color: 'green' })
    await loadReplies()
  } catch (e: any) { toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' }) }
  finally { replyForm.saving = false }
}
async function toggleReply(r: any) {
  await http.patch(`/messaging/quick-replies/${r.id}/`, { is_active: !r.is_active })
  r.is_active = !r.is_active
}
async function removeReply(r: any) {
  if (!confirm(`¿Eliminar la respuesta "${r.title}"?`)) return
  await http.del(`/messaging/quick-replies/${r.id}/`)
  await loadReplies()
}

function openTag(t?: any) {
  Object.assign(tagForm, { open: true, saving: false, id: t?.id ?? null, name: t?.name ?? '', color: t?.color ?? 'gray' })
}
async function saveTag() {
  tagForm.saving = true
  try {
    const body = { name: tagForm.name.trim(), color: tagForm.color }
    if (tagForm.id) await http.patch(`/messaging/tags/${tagForm.id}/`, body)
    else await http.post('/messaging/tags/', body)
    tagForm.open = false
    await loadTags()
  } catch (e: any) { toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' }) }
  finally { tagForm.saving = false }
}
async function toggleTag(t: any) {
  await http.patch(`/messaging/tags/${t.id}/`, { is_active: !t.is_active })
  t.is_active = !t.is_active
}
async function removeTag(t: any) {
  if (!confirm(`¿Eliminar la etiqueta "${t.name}"? Se quitará de ${t.usage} conversación(es).`)) return
  await http.del(`/messaging/tags/${t.id}/`)
  await loadTags()
}

onMounted(async () => {
  loadReplies()
  loadTags()
  try {
    campaignOptions.value = http.results(await http.get('/campaigns/')).map((c: any) => ({ label: c.name, value: String(c.id) }))
  } catch { /* opcional */ }
})
</script>
