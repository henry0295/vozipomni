<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Envíos masivos de WhatsApp</h1>
        <p class="text-sm text-gray-500 mt-1">Plantillas aprobadas a una lista de contactos, respetando el consentimiento (opt-in) y la lista negra.</p>
      </div>
      <div class="flex gap-2">
        <UButton icon="i-heroicons-arrow-left" color="gray" variant="ghost" to="/messaging">Bandeja</UButton>
        <UButton icon="i-heroicons-plus" color="green" @click="openForm()">Nuevo envío</UButton>
      </div>
    </div>

    <UAlert color="primary" variant="soft" icon="i-heroicons-shield-check"
            description="Meta exige consentimiento previo para mensajes de marketing. Marca 'Acepta WhatsApp' en los contactos (o impórtalos con esa columna). Los clientes pueden darse de baja respondiendo BAJA (configurable por línea)." />

    <UCard>
      <UTable :rows="rows" :columns="columns" :loading="loading"
              :empty-state="{ icon: 'i-heroicons-megaphone', label: 'Aún no hay envíos masivos' }">
        <template #name-data="{ row }">
          <div>
            <p class="font-medium">{{ row.name }}</p>
            <p class="text-xs text-gray-500">{{ row.line_name }} · <span class="font-mono">{{ row.template_name }}</span> · {{ row.contact_list_name || 'Sin lista' }}</p>
          </div>
        </template>
        <template #status-data="{ row }">
          <UBadge :color="statusColor(row.status)" variant="soft">{{ statusLabel(row.status) }}</UBadge>
          <p v-if="row.status === 'scheduled' && row.scheduled_at" class="text-xs text-gray-500 mt-1">{{ fmt(row.scheduled_at) }}</p>
          <p v-if="row.last_error" class="text-xs text-red-500 mt-1 max-w-xs truncate" :title="row.last_error">{{ row.last_error }}</p>
        </template>
        <template #progress-data="{ row }">
          <div class="w-56 space-y-1">
            <UProgress :value="row.total_recipients - row.stats.pending" :max="Math.max(1, row.total_recipients)" size="sm" color="green" />
            <p class="text-xs text-gray-500">
              {{ row.total_recipients - row.stats.pending }}/{{ row.total_recipients }} ·
              <span class="text-green-600">{{ row.stats.delivered }} entregados</span> ·
              <span class="text-sky-600">{{ row.stats.read }} leídos</span> ·
              <span class="text-violet-600">{{ row.stats.replied }} respondieron</span>
              <span v-if="row.stats.failed" class="text-red-600"> · {{ row.stats.failed }} fallidos</span>
            </p>
            <p v-if="row.skipped_count" class="text-xs text-gray-400">{{ row.skipped_count }} omitidos (sin opt-in, DNC o sin teléfono)</p>
          </div>
        </template>
        <template #created_at-data="{ row }">
          <span class="text-xs">{{ fmt(row.created_at) }}<br><span class="text-gray-400">{{ row.created_by_name }}</span></span>
        </template>
        <template #actions-data="{ row }">
          <div class="flex gap-1 justify-end">
            <UButton v-if="['draft','scheduled'].includes(row.status)" size="xs" icon="i-heroicons-play" color="green" :loading="busy === row.id" @click="act(row, 'start')">Enviar ahora</UButton>
            <UButton v-if="row.status === 'running'" size="xs" icon="i-heroicons-pause" color="amber" variant="soft" :loading="busy === row.id" @click="act(row, 'pause')">Pausar</UButton>
            <UButton v-if="row.status === 'paused'" size="xs" icon="i-heroicons-play" color="green" variant="soft" :loading="busy === row.id" @click="act(row, 'resume')">Reanudar</UButton>
            <UButton v-if="row.total_recipients" size="xs" icon="i-heroicons-list-bullet" color="gray" variant="ghost" aria-label="Destinatarios" @click="openRecipients(row)" />
            <UButton v-if="['draft','scheduled','paused'].includes(row.status)" size="xs" icon="i-heroicons-pencil" color="gray" variant="ghost" aria-label="Editar" @click="openForm(row)" />
            <UButton v-if="['running','paused','scheduled'].includes(row.status)" size="xs" icon="i-heroicons-stop" color="red" variant="ghost" aria-label="Cancelar" @click="act(row, 'cancel')" />
            <UButton v-if="row.status !== 'running'" size="xs" icon="i-heroicons-trash" color="red" variant="ghost" aria-label="Eliminar" @click="remove(row)" />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Crear / editar -->
    <UModal v-model="form.open" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ form.id ? 'Editar envío' : 'Nuevo envío masivo' }}</h3></template>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="space-y-3">
            <UFormGroup label="Nombre" required><UInput v-model="form.name" placeholder="Promo octubre" /></UFormGroup>
            <UFormGroup label="Línea" required><USelect v-model="form.line" :options="lineOptions" placeholder="Selecciona" /></UFormGroup>
            <UFormGroup label="Plantilla aprobada" required>
              <USelect v-model="form.template" :options="templateOptions" :placeholder="templateOptions.length ? 'Selecciona' : 'Sin plantillas aprobadas'" />
            </UFormGroup>
            <UFormGroup label="Lista de contactos" required><USelect v-model="form.contact_list" :options="listOptions" placeholder="Selecciona" /></UFormGroup>
            <UCheckbox v-model="form.require_opt_in" label="Solo contactos con consentimiento (recomendado)" />
            <UAlert v-if="audience" :color="audience.eligible ? 'green' : 'amber'" variant="soft"
                    :description="`${audience.eligible} de ${audience.total} contactos recibirán el mensaje · ${audience.opted_in} con opt-in · ${audience.dnc} en DNC`" />
            <div class="grid grid-cols-2 gap-3">
              <UFormGroup label="Mensajes por minuto" hint="Tu límite depende del nivel de la línea">
                <UInput v-model.number="form.rate_per_minute" type="number" min="1" max="1000" />
              </UFormGroup>
              <UFormGroup label="Programar (opcional)"><UInput v-model="form.scheduled_at" type="datetime-local" /></UFormGroup>
            </div>
          </div>
          <div class="space-y-3">
            <template v-if="selectedTemplate">
              <div v-if="selectedTemplate.header_param_count" class="space-y-2">
                <p class="text-xs text-gray-500">Variables del encabezado</p>
                <UInput v-for="i in selectedTemplate.header_param_count" :key="`h${i}`" v-model="form.header_params[i - 1]" size="sm" :placeholder="`{{${i}}} ej: {first_name}`" />
              </div>
              <div v-if="selectedTemplate.body_param_count" class="space-y-2">
                <p class="text-xs text-gray-500">Variables del mensaje — usa datos del contacto: <code>{first_name}</code> <code>{last_name}</code> <code>{full_name}</code> <code>{company}</code> <code>{city}</code> <code>{custom.campo}</code> o texto fijo</p>
                <UInput v-for="i in selectedTemplate.body_param_count" :key="`b${i}`" v-model="form.body_params[i - 1]" size="sm" :placeholder="`{{${i}}}`" />
              </div>
              <p class="text-xs text-gray-500">Vista previa (con datos de ejemplo)</p>
              <div class="rounded-lg p-3 bg-[#e5ddd5]">
                <div class="bg-white rounded-lg shadow p-3 space-y-1">
                  <p v-if="selectedTemplate.header_text" class="font-semibold text-sm">{{ fill(selectedTemplate.header_text, form.header_params) }}</p>
                  <p class="text-sm whitespace-pre-line">{{ fill(selectedTemplate.body_text, form.body_params) }}</p>
                </div>
              </div>
            </template>
            <p v-else class="text-sm text-gray-400">Selecciona una plantilla para configurar sus variables.</p>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="form.open = false">Cancelar</UButton>
            <UButton :loading="form.saving" :disabled="!formValid" @click="save">{{ form.scheduled_at ? 'Programar' : 'Guardar borrador' }}</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Destinatarios -->
    <UModal v-model="rcpt.open" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between gap-3">
            <h3 class="font-semibold">Destinatarios · {{ rcpt.broadcast?.name }}</h3>
            <USelect v-model="rcpt.status" :options="rcptStatusOptions" size="sm" class="w-40" @change="loadRecipients" />
          </div>
        </template>
        <UTable :rows="rcpt.rows" :columns="rcptColumns" :loading="rcpt.loading">
          <template #status-data="{ row }"><UBadge :color="rcptColor(row.status)" variant="soft" size="xs">{{ row.status }}</UBadge></template>
          <template #error-data="{ row }"><span class="text-xs text-red-500">{{ row.error }}</span></template>
          <template #sent_at-data="{ row }"><span class="text-xs">{{ row.sent_at ? fmt(row.sent_at) : '—' }}</span></template>
        </UTable>
        <div v-if="rcpt.total > rcpt.rows.length" class="flex justify-center pt-3">
          <UPagination v-model="rcpt.page" :page-count="50" :total="rcpt.total" @update:model-value="loadRecipients" />
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
useHead({ title: 'Envíos masivos - VozipOmni' })

const http = useHttp()
const toast = useToast()

const rows = ref<any[]>([])
const loading = ref(false)
const busy = ref<number | null>(null)
const lines = ref<any[]>([])
const templates = ref<any[]>([])
const lists = ref<any[]>([])
const audience = ref<any>(null)
let timer: ReturnType<typeof setInterval> | null = null

const columns = [
  { key: 'name', label: 'Envío' }, { key: 'status', label: 'Estado' }, { key: 'progress', label: 'Progreso' },
  { key: 'created_at', label: 'Creado' }, { key: 'actions', label: '' },
]
const rcptColumns = [
  { key: 'contact_name', label: 'Contacto' }, { key: 'phone', label: 'Teléfono' }, { key: 'status', label: 'Estado' },
  { key: 'sent_at', label: 'Enviado' }, { key: 'error', label: 'Error' },
]
const rcptStatusOptions = [
  { label: 'Todos', value: '' }, { label: 'Pendientes', value: 'pending' }, { label: 'Enviados', value: 'sent' },
  { label: 'Entregados', value: 'delivered' }, { label: 'Leídos', value: 'read' }, { label: 'Fallidos', value: 'failed' },
]

const STATUS: Record<string, [string, string]> = {
  draft: ['Borrador', 'gray'], scheduled: ['Programado', 'sky'], running: ['Enviando', 'amber'],
  paused: ['Pausado', 'orange'], completed: ['Completado', 'green'], cancelled: ['Cancelado', 'gray'], failed: ['Fallido', 'red'],
}
const statusLabel = (s: string) => STATUS[s]?.[0] || s
const statusColor = (s: string) => STATUS[s]?.[1] || 'gray'
const rcptColor = (s: string) => ({ pending: 'gray', sent: 'sky', delivered: 'green', read: 'emerald', failed: 'red' } as any)[s] || 'gray'
const fmt = (v: string) => new Date(v).toLocaleString('es-CO')

const SAMPLE: Record<string, string> = { first_name: 'Ana', last_name: 'Gómez', full_name: 'Ana Gómez', company: 'ACME', city: 'Bogotá', phone: '573001234567' }
const fill = (text: string, params: string[]) => (text || '').replace(/\{\{(\d+)\}\}/g, (m, n) => {
  const p = params[Number(n) - 1]
  if (!p) return m
  return p.replace(/\{([a-z_]+(?:\.[\w-]+)?)\}/g, (_x, k) => k.startsWith('custom.') ? `[${k.slice(7)}]` : (SAMPLE[k] ?? `{${k}}`))
})

const form = reactive({
  open: false, saving: false, id: null as number | null, name: '', line: '', template: '', contact_list: '',
  require_opt_in: true, rate_per_minute: 60, scheduled_at: '', body_params: [] as string[], header_params: [] as string[],
})

const lineOptions = computed(() => lines.value.filter(l => l.is_active).map(l => ({ label: l.name, value: String(l.id) })))
const templateOptions = computed(() => templates.value
  .filter(t => String(t.line) === form.line)
  .map(t => ({ label: `${t.name} (${t.language}) · ${t.category}`, value: String(t.id) })))
const listOptions = computed(() => lists.value.map(l => ({ label: `${l.name} (${l.total_contacts})`, value: String(l.id) })))
const selectedTemplate = computed(() => templates.value.find(t => String(t.id) === form.template) || null)
const formValid = computed(() => {
  const t = selectedTemplate.value
  if (!form.name.trim() || !form.line || !t || !form.contact_list) return false
  const bp = Array.from({ length: t.body_param_count || 0 }, (_, i) => (form.body_params[i] || '').trim())
  const hp = Array.from({ length: t.header_param_count || 0 }, (_, i) => (form.header_params[i] || '').trim())
  return bp.every(Boolean) && hp.every(Boolean)
})

watch(() => form.line, (v, old) => { if (old && v !== old) form.template = '' })
watch(() => [form.contact_list, form.require_opt_in], async () => {
  audience.value = null
  if (!form.contact_list) return
  try {
    audience.value = await http.post('/messaging/whatsapp/broadcasts/preview/', {
      contact_list: Number(form.contact_list), require_opt_in: form.require_opt_in,
    })
  } catch { /* opcional */ }
})

async function load() {
  loading.value = rows.value.length === 0
  try {
    rows.value = http.results(await http.get('/messaging/whatsapp/broadcasts/'))
  } finally { loading.value = false }
}

async function loadCatalogs() {
  const [l, t, c] = await Promise.allSettled([
    http.get('/messaging/whatsapp/lines/'),
    http.get('/messaging/whatsapp/templates/', { status: 'APPROVED' }),
    http.get('/contact-lists/'),
  ])
  if (l.status === 'fulfilled') lines.value = http.results(l.value)
  if (t.status === 'fulfilled') templates.value = http.results(t.value)
  if (c.status === 'fulfilled') lists.value = http.results(c.value)
}

function toLocalInput(v?: string | null) {
  if (!v) return ''
  const d = new Date(v)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

function openForm(b?: any) {
  Object.assign(form, {
    open: true, saving: false, id: b?.id ?? null, name: b?.name ?? '',
    line: b ? String(b.line) : (lineOptions.value[0]?.value || ''),
    template: b ? String(b.template) : '', contact_list: b?.contact_list ? String(b.contact_list) : '',
    require_opt_in: b?.require_opt_in ?? true, rate_per_minute: b?.rate_per_minute ?? 60,
    scheduled_at: toLocalInput(b?.scheduled_at), body_params: [...(b?.body_params || [])], header_params: [...(b?.header_params || [])],
  })
}

async function save() {
  const t = selectedTemplate.value
  form.saving = true
  try {
    const body = {
      name: form.name.trim(), line: Number(form.line), template: Number(form.template),
      contact_list: Number(form.contact_list), require_opt_in: form.require_opt_in,
      rate_per_minute: form.rate_per_minute || 60,
      scheduled_at: form.scheduled_at ? new Date(form.scheduled_at).toISOString() : null,
      body_params: form.body_params.slice(0, t?.body_param_count || 0),
      header_params: form.header_params.slice(0, t?.header_param_count || 0),
    }
    if (form.id) await http.patch(`/messaging/whatsapp/broadcasts/${form.id}/`, body)
    else await http.post('/messaging/whatsapp/broadcasts/', body)
    form.open = false
    toast.add({ title: form.scheduled_at ? 'Envío programado' : 'Borrador guardado', description: form.scheduled_at ? undefined : 'Usa "Enviar ahora" para iniciarlo.', color: 'green' })
    await load()
  } catch (e: any) { toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' }) }
  finally { form.saving = false }
}

async function act(b: any, action: 'start' | 'pause' | 'resume' | 'cancel') {
  if (action === 'start' && !confirm(`¿Iniciar el envío "${b.name}" ahora?`)) return
  if (action === 'cancel' && !confirm(`¿Cancelar el envío "${b.name}"? Los pendientes no se enviarán.`)) return
  busy.value = b.id
  try {
    await http.post(`/messaging/whatsapp/broadcasts/${b.id}/${action}/`)
    await load()
  } catch (e: any) { toast.add({ title: 'No se pudo completar', description: http.errorMessage(e), color: 'red' }) }
  finally { busy.value = null }
}

async function remove(b: any) {
  if (!confirm(`¿Eliminar el envío "${b.name}"?`)) return
  try {
    await http.del(`/messaging/whatsapp/broadcasts/${b.id}/`)
    await load()
  } catch (e: any) { toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' }) }
}

const rcpt = reactive({ open: false, loading: false, broadcast: null as any, rows: [] as any[], total: 0, page: 1, status: '' })
async function openRecipients(b: any) {
  Object.assign(rcpt, { open: true, broadcast: b, rows: [], total: 0, page: 1, status: '' })
  await loadRecipients()
}
async function loadRecipients() {
  rcpt.loading = true
  try {
    const q: any = { page: rcpt.page }
    if (rcpt.status) q.status = rcpt.status
    const data: any = await http.get(`/messaging/whatsapp/broadcasts/${rcpt.broadcast.id}/recipients/`, q)
    rcpt.rows = http.results(data)
    rcpt.total = data?.count ?? rcpt.rows.length
  } finally { rcpt.loading = false }
}

onMounted(() => {
  load()
  loadCatalogs()
  // Refrescar el progreso mientras haya envíos activos
  timer = setInterval(() => {
    if (rows.value.some(r => ['running', 'scheduled'].includes(r.status))) load()
  }, 10000)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>
