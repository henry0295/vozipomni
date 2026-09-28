<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Gestión de Calidad</h1>
        <p class="text-sm text-gray-500 mt-1">Evaluaciones de llamadas y desempeño de agentes</p>
      </div>
      <div class="flex gap-2 items-center">
        <USelect v-model="filterDays" :options="dayOptions" @change="reloadAll" />
        <USelect v-model="filterTemplate" :options="templateFilterOptions" @change="reloadAll" />
        <UButton icon="i-heroicons-arrow-path" color="gray" variant="ghost" :loading="loading" @click="reloadAll" />
        <UButton v-if="canEvaluate" icon="i-heroicons-plus" @click="openEvaluate">Nueva evaluación</UButton>
      </div>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <UCard class="text-center">
        <p class="text-3xl font-bold text-blue-600">{{ stats.total_evaluations ?? 0 }}</p>
        <p class="text-sm text-gray-500 mt-1">Evaluaciones</p>
      </UCard>
      <UCard class="text-center">
        <p class="text-3xl font-bold" :class="scoreColor(stats.average_score)">{{ fmt(stats.average_score) }}</p>
        <p class="text-sm text-gray-500 mt-1">Puntaje promedio (0-100)</p>
      </UCard>
      <UCard class="text-center">
        <p class="text-3xl font-bold text-purple-600">{{ stats.agents_evaluated ?? 0 }}</p>
        <p class="text-sm text-gray-500 mt-1">Agentes evaluados</p>
      </UCard>
      <UCard class="text-center">
        <p class="text-3xl font-bold" :class="scoreColor(stats.pass_rate)">{{ fmt(stats.pass_rate) }}{{ stats.pass_rate != null ? '%' : '' }}</p>
        <p class="text-sm text-gray-500 mt-1">Aprobación (≥ {{ stats.pass_threshold ?? 80 }})</p>
      </UCard>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <UCard>
        <template #header><h3 class="font-semibold">Top agentes por calidad</h3></template>
        <div class="space-y-3">
          <div
            v-for="(agent, idx) in stats.top_agents || []"
            :key="agent.agent_id"
            class="flex items-center gap-3 p-2 rounded-lg"
            :class="idx === 0 ? 'bg-yellow-50' : ''"
          >
            <span class="text-lg font-bold text-gray-400 w-6">{{ idx + 1 }}</span>
            <UAvatar :alt="agent.name" size="sm" />
            <div class="flex-1 min-w-0">
              <p class="font-medium text-sm truncate">{{ agent.name }} <span class="text-xs text-gray-400">· {{ agent.count }} eval.</span></p>
              <UProgress :value="agent.avg_score" :max="100" size="xs"
                         :color="agent.avg_score >= 80 ? 'green' : agent.avg_score >= 60 ? 'yellow' : 'red'" />
            </div>
            <span class="font-semibold text-sm tabular-nums">{{ fmt(agent.avg_score) }}</span>
          </div>
          <p v-if="!stats.top_agents?.length" class="text-center text-gray-400 py-4 text-sm">Sin evaluaciones en el período</p>
        </div>
      </UCard>

      <UCard>
        <template #header><h3 class="font-semibold">Tendencia diaria</h3></template>
        <div v-if="!stats.daily_trend?.length" class="text-center text-gray-400 py-8 text-sm">Sin datos para el período</div>
        <div v-else class="space-y-2">
          <div v-for="day in stats.daily_trend" :key="day.date" class="flex items-center gap-3">
            <span class="text-xs text-gray-500 w-20 shrink-0">{{ formatDay(day.date) }}</span>
            <div class="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
              <div class="h-full rounded-full"
                   :class="day.avg_score >= 80 ? 'bg-green-500' : day.avg_score >= 60 ? 'bg-yellow-400' : 'bg-red-400'"
                   :style="{ width: Math.min(100, day.avg_score) + '%' }" />
            </div>
            <span class="text-xs font-semibold w-10 text-right">{{ fmt(day.avg_score) }}</span>
            <span class="text-xs text-gray-400 w-14 text-right">{{ day.count }} eval</span>
          </div>
        </div>
      </UCard>
    </div>

    <UCard v-if="stats.category_breakdown?.length && !filterTemplate">
      <template #header><h3 class="font-semibold">Puntaje por criterio (plantilla estándar)</h3></template>
      <div class="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div v-for="cat in stats.category_breakdown" :key="cat.category" class="text-center p-4 rounded-lg bg-gray-50">
          <p class="text-2xl font-bold" :class="scoreColor(cat.avg_score)">{{ fmt(cat.avg_score) }}</p>
          <p class="text-sm text-gray-600 mt-1">{{ cat.label }}</p>
        </div>
      </div>
    </UCard>

    <!-- Evaluaciones -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="font-semibold">Evaluaciones recientes</h3>
          <UInput v-model="search" icon="i-heroicons-magnifying-glass" placeholder="Buscar grabación / llamada" size="sm" @keyup.enter="loadEvaluations" />
        </div>
      </template>
      <UTable :rows="evaluations" :columns="columns" :loading="loadingList"
              :empty-state="{ icon: 'i-heroicons-star', label: 'Aún no hay evaluaciones' }">
        <template #created_at-data="{ row }">{{ formatDate(row.created_at) }}</template>
        <template #template_name-data="{ row }">{{ row.template_name || 'Estándar (5 criterios)' }}</template>
        <template #total_score-data="{ row }">
          <UBadge :color="row.total_score >= 80 ? 'green' : row.total_score >= 60 ? 'yellow' : 'red'" variant="soft">
            {{ fmt(row.total_score) }}
          </UBadge>
        </template>
        <template #actions-data="{ row }">
          <UButton icon="i-heroicons-eye" size="xs" color="gray" variant="ghost" @click="viewEval = row" />
        </template>
      </UTable>
    </UCard>

    <!-- Modal nueva evaluación -->
    <UModal v-model="evalModal.open" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">Nueva evaluación</h3></template>
        <div class="space-y-4">
          <UFormGroup label="Grabación a evaluar" required>
            <USelectMenu v-model="evalModal.recording" :options="pendingRecordings" searchable
                         placeholder="Selecciona una grabación" option-attribute="label" by="id">
              <template #label>{{ evalModal.recording?.label || 'Selecciona una grabación' }}</template>
            </USelectMenu>
            <p v-if="!pendingRecordings.length" class="text-xs text-gray-400 mt-1">No hay grabaciones pendientes de evaluar.</p>
          </UFormGroup>

          <UFormGroup label="Plantilla">
            <USelect v-model="evalModal.templateId" :options="templateOptions" />
          </UFormGroup>

          <div class="space-y-3">
            <div v-for="c in activeCriteria" :key="c.name" class="grid grid-cols-3 items-center gap-3">
              <div class="col-span-2">
                <p class="text-sm font-medium">{{ c.label }}</p>
                <p v-if="c.description" class="text-xs text-gray-400">{{ c.description }}</p>
              </div>
              <UInput v-model.number="evalModal.scores[c.name]" type="number" :min="0" :max="c.max_score">
                <template #trailing><span class="text-xs text-gray-400">/ {{ c.max_score }}</span></template>
              </UInput>
            </div>
          </div>

          <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span class="text-sm text-gray-600">Puntaje resultante</span>
            <span class="text-xl font-bold" :class="scoreColor(previewScore)">{{ fmt(previewScore) }} / 100</span>
          </div>

          <UFormGroup label="Comentarios / retroalimentación">
            <UTextarea v-model="evalModal.comments" :rows="3" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="evalModal.open = false">Cancelar</UButton>
            <UButton :loading="evalModal.saving" :disabled="!evalModal.recording" @click="saveEvaluation">Guardar evaluación</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal detalle -->
    <UModal :model-value="!!viewEval" @update:model-value="viewEval = null">
      <UCard v-if="viewEval">
        <template #header>
          <h3 class="font-semibold">Evaluación · {{ viewEval.agent_name || 'Sin agente' }}</h3>
          <p class="text-xs text-gray-500">{{ viewEval.recording_filename }} · {{ formatDate(viewEval.created_at) }} · por {{ viewEval.evaluator_name }}</p>
        </template>
        <div class="space-y-2">
          <div v-for="(v, k) in detailScores(viewEval)" :key="k" class="flex justify-between text-sm">
            <span class="text-gray-600">{{ k }}</span><span class="font-medium">{{ v }}</span>
          </div>
          <div class="flex justify-between border-t pt-2 font-semibold">
            <span>Total</span><span :class="scoreColor(viewEval.total_score)">{{ fmt(viewEval.total_score) }} / 100</span>
          </div>
          <p v-if="viewEval.comments" class="text-sm text-gray-700 bg-gray-50 p-3 rounded mt-2 whitespace-pre-wrap">{{ viewEval.comments }}</p>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const http = useHttp()
const toast = useToast()
const { user } = useAuth()

const LEGACY = [
  { name: 'greeting', label: 'Saludo', max_score: 5 },
  { name: 'clarity', label: 'Claridad', max_score: 5 },
  { name: 'professionalism', label: 'Profesionalismo', max_score: 5 },
  { name: 'resolution', label: 'Resolución', max_score: 5 },
  { name: 'closing', label: 'Cierre', max_score: 5 },
]

const stats = ref<any>({})
const evaluations = ref<any[]>([])
const templates = ref<any[]>([])
const pendingRecordings = ref<any[]>([])
const loading = ref(false)
const loadingList = ref(false)
const search = ref('')
const filterDays = ref(30)
const filterTemplate = ref<string | number>('')
const viewEval = ref<any>(null)

const canEvaluate = computed(() => ['admin', 'supervisor'].includes(user.value?.role || ''))

const dayOptions = [
  { label: 'Últimos 7 días', value: 7 },
  { label: 'Últimos 15 días', value: 15 },
  { label: 'Últimos 30 días', value: 30 },
  { label: 'Últimos 90 días', value: 90 },
]
const templateFilterOptions = computed(() => [
  { label: 'Todas las plantillas', value: '' },
  ...templates.value.map(t => ({ label: t.name, value: t.id })),
])
const templateOptions = computed(() => [
  { label: 'Estándar (5 criterios, 0-5)', value: '' },
  ...templates.value.filter(t => t.is_active).map(t => ({ label: t.name + (t.is_default ? ' (por defecto)' : ''), value: t.id })),
])

const columns = [
  { key: 'created_at', label: 'Fecha' },
  { key: 'agent_name', label: 'Agente' },
  { key: 'call_id', label: 'Llamada' },
  { key: 'template_name', label: 'Plantilla' },
  { key: 'evaluator_name', label: 'Evaluador' },
  { key: 'total_score', label: 'Puntaje' },
  { key: 'actions', label: '' },
]

const evalModal = reactive({
  open: false,
  saving: false,
  recording: null as any,
  templateId: '' as string | number,
  scores: {} as Record<string, number>,
  comments: '',
})

const activeTemplate = computed(() => templates.value.find(t => t.id === Number(evalModal.templateId)))
const activeCriteria = computed(() => activeTemplate.value?.criteria ?? LEGACY)
const previewScore = computed(() => {
  const crit = activeCriteria.value
  const max = crit.reduce((s: number, c: any) => s + Number(c.max_score || 0), 0) || 1
  const raw = crit.reduce((s: number, c: any) => s + Math.min(Number(evalModal.scores[c.name] || 0), c.max_score), 0)
  return Math.round((raw / max) * 1000) / 10
})

watch(() => evalModal.templateId, () => { evalModal.scores = {} })

const fmt = (v: any) => (v === null || v === undefined ? '—' : Number(v).toFixed(1))
const scoreColor = (v: any) => (v == null ? 'text-gray-400' : v >= 80 ? 'text-green-600' : v >= 60 ? 'text-yellow-600' : 'text-red-600')
const formatDay = (iso: string) => (iso ? new Date(iso + 'T00:00:00').toLocaleDateString('es-CO', { day: '2-digit', month: 'short' }) : '')
const formatDate = (iso: string) => (iso ? new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' }) : '')

const detailScores = (ev: any) => {
  const tpl = templates.value.find(t => t.id === ev.template)
  const crit = tpl?.criteria ?? LEGACY
  const out: Record<string, string> = {}
  for (const c of crit) {
    const v = tpl ? ev.scores_data?.[c.name] : ev[c.name]
    out[c.label] = `${v ?? 0} / ${c.max_score}`
  }
  return out
}

async function loadStats() {
  const query: any = { days: filterDays.value }
  if (filterTemplate.value) query.template = filterTemplate.value
  try { stats.value = await http.get('/cc/quality-stats/', query) } catch { stats.value = {} }
}

async function loadEvaluations() {
  loadingList.value = true
  try {
    const query: any = { page_size: 50 }
    if (search.value) query.search = search.value
    if (filterTemplate.value) query.template = filterTemplate.value
    evaluations.value = http.results(await http.get('/evaluations/', query))
  } catch { evaluations.value = [] } finally { loadingList.value = false }
}

async function loadTemplates() {
  try { templates.value = http.results(await http.get('/evaluation-templates/')) } catch { templates.value = [] }
}

async function reloadAll() {
  loading.value = true
  await Promise.all([loadStats(), loadEvaluations()])
  loading.value = false
}

async function openEvaluate() {
  const def = templates.value.find(t => t.is_default && t.is_active)
  Object.assign(evalModal, { open: true, saving: false, recording: null, templateId: def?.id ?? '', scores: {}, comments: '' })
  try {
    const rows = await http.get<any[]>('/evaluations/pending-recordings/')
    pendingRecordings.value = rows.map(r => ({
      ...r,
      label: `${r.agent_name || 'Sin agente'} · ${r.call_id || r.filename} · ${formatDate(r.created_at)}`,
    }))
  } catch { pendingRecordings.value = [] }
}

async function saveEvaluation() {
  evalModal.saving = true
  try {
    const body: any = { recording: evalModal.recording.id, comments: evalModal.comments }
    if (activeTemplate.value) {
      body.template = activeTemplate.value.id
      body.scores_data = Object.fromEntries(activeCriteria.value.map((c: any) => [c.name, Number(evalModal.scores[c.name] || 0)]))
    } else {
      for (const c of LEGACY) body[c.name] = Number(evalModal.scores[c.name] || 0)
    }
    await http.post('/evaluations/', body)
    toast.add({ title: 'Evaluación guardada', color: 'green' })
    evalModal.open = false
    await reloadAll()
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar', description: http.errorMessage(e), color: 'red' })
  } finally { evalModal.saving = false }
}

onMounted(async () => {
  await loadTemplates()
  await reloadAll()
})
</script>
