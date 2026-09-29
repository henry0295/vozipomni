<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Exportar y programar reportes</h1>
        <p class="text-sm text-gray-500 mt-1">Descarga datos en CSV/Excel al instante, guarda reportes o prográmalos para recibirlos por correo.</p>
      </div>
      <UButton icon="i-heroicons-plus" @click="openForm()">Nuevo reporte</UButton>
    </div>

    <!-- Exportación inmediata -->
    <UCard>
      <template #header>
        <div class="flex items-center gap-2">
          <UIcon name="i-heroicons-arrow-down-tray" class="w-5 h-5 text-primary-500" />
          <h3 class="font-semibold">Exportación inmediata</h3>
        </div>
      </template>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
        <UFormGroup label="Datos">
          <USelect v-model="exp.dataset" :options="datasets" />
        </UFormGroup>
        <UFormGroup label="Período">
          <USelect v-model="exp.period" :options="periods" />
        </UFormGroup>
        <UFormGroup v-if="exp.period === 'custom'" label="Desde">
          <UInput v-model="exp.start_date" type="date" />
        </UFormGroup>
        <UFormGroup v-if="exp.period === 'custom'" label="Hasta">
          <UInput v-model="exp.end_date" type="date" />
        </UFormGroup>
        <UFormGroup label="Campaña">
          <USelect v-model="exp.campaign" :options="[{ label: 'Todas', value: '' }, ...campaignOptions]" />
        </UFormGroup>
        <UFormGroup label="Agente">
          <USelect v-model="exp.agent" :options="[{ label: 'Todos', value: '' }, ...agentOptions]" />
        </UFormGroup>
        <UFormGroup label="Cola">
          <USelect v-model="exp.queue" :options="[{ label: 'Todas', value: '' }, ...queueOptions]" />
        </UFormGroup>
        <UFormGroup label="Dirección">
          <USelect v-model="exp.direction" :options="directions" />
        </UFormGroup>
      </div>
      <div class="flex flex-wrap gap-2 mt-4">
        <UButton icon="i-heroicons-table-cells" :loading="exporting === 'xlsx'" :disabled="!!exporting" @click="doExport('xlsx')">Descargar Excel</UButton>
        <UButton icon="i-heroicons-document-text" color="gray" variant="outline" :loading="exporting === 'csv'" :disabled="!!exporting" @click="doExport('csv')">Descargar CSV</UButton>
      </div>
    </UCard>

    <!-- Reportes guardados / programados -->
    <UCard>
      <template #header>
        <div class="flex flex-wrap items-center gap-3">
          <UTabs v-model="tab" :items="[{ label: 'Generados' }, { label: 'Programados' }]" class="w-72" @change="load" />
          <UButton icon="i-heroicons-arrow-path" color="gray" variant="ghost" size="sm" :loading="loading" class="ml-auto" @click="load">Actualizar</UButton>
        </div>
      </template>

      <UTable :rows="rows" :columns="tab === 0 ? columns : scheduledColumns" :loading="loading"
              :empty-state="{ icon: 'i-heroicons-document-chart-bar', label: tab === 0 ? 'No hay reportes generados' : 'No hay reportes programados' }">
        <template #report_type-data="{ row }">{{ typeLabel(row.report_type) }}</template>
        <template #format-data="{ row }"><UBadge color="gray" variant="soft">{{ formatLabel(row.format) }}</UBadge></template>
        <template #range-data="{ row }">
          <span class="text-xs">{{ fmtDate(row.date_from) }} → {{ fmtDate(row.date_to) }}</span>
        </template>
        <template #status-data="{ row }">
          <UBadge :color="statusColor(row.status)" variant="soft">{{ statusLabel(row.status) }}</UBadge>
          <p v-if="row.status === 'failed' && row.error_message" class="text-xs text-red-500 mt-1 max-w-xs truncate" :title="row.error_message">{{ row.error_message }}</p>
        </template>
        <template #file_size-data="{ row }">{{ row.file_size ? fmtSize(row.file_size) : '—' }}</template>
        <template #schedule_frequency-data="{ row }">{{ freqLabel(row.schedule_frequency) }}</template>
        <template #created_at-data="{ row }">{{ new Date(row.created_at).toLocaleString('es-CO') }}</template>
        <template #actions-data="{ row }">
          <div class="flex gap-1 justify-end">
            <UButton v-if="tab === 0" icon="i-heroicons-arrow-down-tray" size="xs" color="primary" variant="ghost"
                     :disabled="row.status !== 'completed' || row.format === 'json'" :loading="downloading === row.id"
                     title="Descargar" @click="downloadReport(row)" />
            <UButton v-if="tab === 0" icon="i-heroicons-arrow-path" size="xs" color="gray" variant="ghost"
                     title="Regenerar" @click="regenerate(row)" />
            <UButton v-if="tab === 1" icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost"
                     title="Editar" @click="openForm(row)" />
            <UButton v-if="canDelete" icon="i-heroicons-trash" size="xs" color="red" variant="ghost"
                     title="Eliminar" @click="remove(row)" />
          </div>
        </template>
      </UTable>
      <div v-if="total > rows.length" class="flex justify-center pt-4">
        <UPagination v-model="page" :page-count="pageSize" :total="total" @update:model-value="load" />
      </div>
    </UCard>

    <!-- Crear / editar -->
    <UModal v-model="form.open" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ form.id ? 'Editar reporte programado' : 'Nuevo reporte' }}</h3></template>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <UFormGroup label="Nombre" required class="md:col-span-2">
            <UInput v-model="form.name" placeholder="Ej: Llamadas diarias campaña Cobranza" />
          </UFormGroup>
          <UFormGroup label="Tipo">
            <USelect v-model="form.report_type" :options="reportTypes" />
          </UFormGroup>
          <UFormGroup label="Formato">
            <USelect v-model="form.format" :options="[{ label: 'Excel (.xlsx)', value: 'excel' }, { label: 'CSV', value: 'csv' }]" />
          </UFormGroup>
          <UFormGroup label="Campaña">
            <USelect v-model="form.campaign" :options="[{ label: 'Todas', value: '' }, ...campaignOptions]" />
          </UFormGroup>
          <UFormGroup label="Agente">
            <USelect v-model="form.agent" :options="[{ label: 'Todos', value: '' }, ...agentOptions]" />
          </UFormGroup>
          <UFormGroup label="Cola">
            <USelect v-model="form.queue" :options="[{ label: 'Todas', value: '' }, ...queueOptions]" />
          </UFormGroup>
          <UFormGroup label="Dirección">
            <USelect v-model="form.direction" :options="directions" />
          </UFormGroup>

          <div class="md:col-span-2">
            <UCheckbox v-model="form.is_scheduled" label="Programar (se genera automáticamente y se envía por correo)" :disabled="!!form.id" />
          </div>

          <template v-if="form.is_scheduled">
            <UFormGroup label="Frecuencia" class="md:col-span-2"
                        hint="Diario 01:30 (día anterior) · Semanal los lunes (semana anterior) · Mensual el día 1 (mes anterior)">
              <USelect v-model="form.schedule_frequency" :options="frequencies" />
            </UFormGroup>
          </template>
          <template v-else>
            <UFormGroup label="Desde" required><UInput v-model="form.date_from" type="date" /></UFormGroup>
            <UFormGroup label="Hasta" required><UInput v-model="form.date_to" type="date" /></UFormGroup>
          </template>
        </div>
        <UAlert v-if="form.is_scheduled" class="mt-4" icon="i-heroicons-envelope" color="primary" variant="soft"
                description="El archivo se envía al correo del usuario que crea el reporte. Verifica que tu perfil tenga email y que el servidor tenga EMAIL_HOST configurado." />
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="form.open = false">Cancelar</UButton>
            <UButton :loading="form.saving" :disabled="!form.name.trim()" @click="save">
              {{ form.id ? 'Guardar' : (form.is_scheduled ? 'Programar' : 'Generar') }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const http = useHttp()
const toast = useToast()
const authStore = useAuthStore()

const canDelete = computed(() => {
  const u: any = authStore.user
  return !!u && (u.is_superuser || ['admin', 'supervisor'].includes(u.role))
})

const today = () => new Date().toISOString().slice(0, 10)
const daysAgo = (n: number) => new Date(Date.now() - n * 86400000).toISOString().slice(0, 10)

const datasets = ref<{ label: string, value: string }[]>([
  { label: 'Detalle de llamadas', value: 'calls' },
  { label: 'Rendimiento de agentes', value: 'agents' },
  { label: 'Resumen diario', value: 'daily' },
  { label: 'Resumen por cola', value: 'queues' },
])
const periods = [
  { label: 'Hoy', value: 'today' },
  { label: 'Ayer', value: 'yesterday' },
  { label: 'Esta semana', value: 'thisweek' },
  { label: 'Semana pasada', value: 'lastweek' },
  { label: 'Últimos 7 días', value: 'last7days' },
  { label: 'Últimos 30 días', value: 'last30days' },
  { label: 'Este mes', value: 'thismonth' },
  { label: 'Mes pasado', value: 'lastmonth' },
  { label: 'Personalizado', value: 'custom' },
]
const directions = [
  { label: 'Todas', value: '' },
  { label: 'Entrantes', value: 'inbound' },
  { label: 'Salientes', value: 'outbound' },
]
const reportTypes = [
  { label: 'Llamadas (detalle)', value: 'calls' },
  { label: 'Agentes', value: 'agent' },
  { label: 'Colas', value: 'queue' },
  { label: 'Campaña (detalle)', value: 'campaign' },
  { label: 'Resumen diario', value: 'custom' },
]
const frequencies = [
  { label: 'Diario', value: 'daily' },
  { label: 'Semanal', value: 'weekly' },
  { label: 'Mensual', value: 'monthly' },
]

const campaignOptions = ref<any[]>([])
const agentOptions = ref<any[]>([])
const queueOptions = ref<any[]>([])

const exp = reactive({
  dataset: 'calls', period: 'last7days', start_date: daysAgo(7), end_date: today(),
  campaign: '', agent: '', queue: '', direction: '',
})
const exporting = ref<'' | 'csv' | 'xlsx'>('')

const tab = ref(0)
const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 50 // PAGE_SIZE de DRF
const loading = ref(false)
const downloading = ref<number | null>(null)
let pollTimer: ReturnType<typeof setTimeout> | null = null

const columns = [
  { key: 'name', label: 'Nombre' },
  { key: 'report_type', label: 'Tipo' },
  { key: 'format', label: 'Formato' },
  { key: 'range', label: 'Período' },
  { key: 'status', label: 'Estado' },
  { key: 'file_size', label: 'Tamaño' },
  { key: 'created_by_name', label: 'Creado por' },
  { key: 'created_at', label: 'Creado' },
  { key: 'actions', label: '' },
]
const scheduledColumns = [
  { key: 'name', label: 'Nombre' },
  { key: 'report_type', label: 'Tipo' },
  { key: 'format', label: 'Formato' },
  { key: 'schedule_frequency', label: 'Frecuencia' },
  { key: 'created_by_name', label: 'Creado por' },
  { key: 'created_at', label: 'Creado' },
  { key: 'actions', label: '' },
]

const form = reactive({
  open: false, saving: false, id: null as number | null,
  name: '', report_type: 'calls', format: 'excel',
  campaign: '' as any, agent: '' as any, queue: '' as any, direction: '',
  date_from: daysAgo(7), date_to: today(),
  is_scheduled: false, schedule_frequency: 'daily',
})

const typeLabel = (v: string) => reportTypes.find(t => t.value === v)?.label || v
const formatLabel = (v: string) => ({ excel: 'Excel', csv: 'CSV', json: 'JSON', pdf: 'PDF' } as any)[v] || v
const freqLabel = (v: string) => frequencies.find(f => f.value === v)?.label || v || '—'
const statusLabel = (v: string) => ({ pending: 'Pendiente', processing: 'Procesando', completed: 'Listo', failed: 'Fallido' } as any)[v] || v
const statusColor = (v: string) => ({ pending: 'gray', processing: 'amber', completed: 'green', failed: 'red' } as any)[v] || 'gray'
const fmtDate = (v: string) => v ? new Date(v).toLocaleDateString('es-CO') : '—'
const fmtSize = (b: number) => b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`

async function loadCatalogs() {
  const [ds, camps, agents, queues] = await Promise.allSettled([
    http.get('/reports/datasets/'),
    http.get('/campaigns/', { page_size: 200 }),
    http.get('/agents/', { page_size: 500 }),
    http.get('/queues/', { page_size: 200 }),
  ])
  if (ds.status === 'fulfilled' && Array.isArray(ds.value) && ds.value.length) datasets.value = ds.value
  if (camps.status === 'fulfilled')
    campaignOptions.value = http.results(camps.value).map((c: any) => ({ label: c.name, value: String(c.id) }))
  if (agents.status === 'fulfilled')
    agentOptions.value = http.results(agents.value).map((a: any) => ({
      label: `${a.user_details?.name || a.agent_id}${a.sip_extension ? ' (' + a.sip_extension + ')' : ''}`,
      value: String(a.id),
    }))
  if (queues.status === 'fulfilled')
    queueOptions.value = http.results(queues.value).map((q: any) => ({ label: q.name, value: String(q.id) }))
}

async function doExport(format: 'csv' | 'xlsx') {
  if (exp.period === 'custom' && !exp.start_date) {
    toast.add({ title: 'Selecciona la fecha inicial', color: 'amber' })
    return
  }
  exporting.value = format
  try {
    const query: Record<string, any> = { dataset: exp.dataset, format, period: exp.period }
    if (exp.period === 'custom') { query.start_date = exp.start_date; query.end_date = exp.end_date }
    for (const k of ['campaign', 'agent', 'queue', 'direction'] as const) if (exp[k]) query[k] = exp[k]
    await http.download('/reports/export/', query, `${exp.dataset}.${format}`)
  } catch (e: any) {
    toast.add({ title: 'No se pudo exportar', description: await http.blobErrorMessage(e), color: 'red' })
  } finally { exporting.value = '' }
}

async function load() {
  if (pollTimer) { clearTimeout(pollTimer); pollTimer = null }
  loading.value = true
  try {
    const data: any = await http.get('/reports/', {
      is_scheduled: tab.value === 1 ? 'true' : 'false',
      page: page.value,
      ordering: '-created_at',
    })
    rows.value = http.results(data)
    total.value = data?.count ?? rows.value.length
    // Si hay reportes en proceso, refrescar en unos segundos
    if (tab.value === 0 && rows.value.some(r => ['pending', 'processing'].includes(r.status))) {
      pollTimer = setTimeout(load, 5000)
    }
  } catch (e: any) {
    toast.add({ title: 'Error cargando reportes', description: http.errorMessage(e), color: 'red' })
  } finally { loading.value = false }
}

function openForm(r?: any) {
  const f = r?.filters || {}
  Object.assign(form, {
    open: true, saving: false, id: r?.id ?? null,
    name: r?.name ?? '',
    report_type: r?.report_type ?? 'calls',
    format: r?.format === 'csv' ? 'csv' : 'excel',
    campaign: f.campaign ? String(f.campaign) : '',
    agent: f.agent ? String(f.agent) : '',
    queue: f.queue ? String(f.queue) : '',
    direction: f.direction ?? '',
    date_from: r?.date_from?.slice(0, 10) ?? daysAgo(7),
    date_to: r?.date_to?.slice(0, 10) ?? today(),
    is_scheduled: r ? !!r.is_scheduled : tab.value === 1,
    schedule_frequency: r?.schedule_frequency || 'daily',
  })
}

async function save() {
  if (!form.is_scheduled && (!form.date_from || !form.date_to)) {
    toast.add({ title: 'Selecciona el rango de fechas', color: 'amber' })
    return
  }
  form.saving = true
  try {
    const filters: Record<string, any> = {}
    for (const k of ['campaign', 'agent', 'queue'] as const) if (form[k]) filters[k] = Number(form[k])
    if (form.direction) filters.direction = form.direction
    // Los programados recalculan el período en cada ejecución; se guarda uno de referencia
    const from = form.is_scheduled ? daysAgo(1) : form.date_from
    const to = form.is_scheduled ? daysAgo(1) : form.date_to
    const body = {
      name: form.name.trim(),
      report_type: form.report_type,
      format: form.format,
      filters,
      date_from: `${from}T00:00:00`,
      date_to: `${to}T23:59:59`,
      is_scheduled: form.is_scheduled,
      schedule_frequency: form.is_scheduled ? form.schedule_frequency : '',
    }
    if (form.id) await http.patch(`/reports/${form.id}/`, body)
    else await http.post('/reports/', body)
    toast.add({
      title: form.is_scheduled ? 'Reporte programado' : 'Generando reporte',
      description: form.is_scheduled ? undefined : 'Aparecerá como "Listo" en unos segundos.',
      color: 'green',
    })
    form.open = false
    tab.value = form.is_scheduled ? 1 : 0
    await load()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { form.saving = false }
}

async function downloadReport(r: any) {
  downloading.value = r.id
  try {
    await http.download(`/reports/${r.id}/download/`, undefined, `${r.name}.${r.format === 'csv' ? 'csv' : 'xlsx'}`)
  } catch (e: any) {
    toast.add({ title: 'No se pudo descargar', description: await http.blobErrorMessage(e), color: 'red' })
  } finally { downloading.value = null }
}

async function regenerate(r: any) {
  try {
    await http.post(`/reports/${r.id}/generate/`)
    r.status = 'processing'
    toast.add({ title: 'Regenerando reporte', color: 'green' })
    if (pollTimer) clearTimeout(pollTimer)
    pollTimer = setTimeout(load, 4000)
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  }
}

async function remove(r: any) {
  if (!confirm(`¿Eliminar el reporte "${r.name}"?`)) return
  try {
    await http.del(`/reports/${r.id}/`)
    await load()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  }
}

onMounted(() => { loadCatalogs(); load() })
onBeforeUnmount(() => { if (pollTimer) clearTimeout(pollTimer) })
</script>
