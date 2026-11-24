<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Base de conocimiento</h1>
        <p class="text-sm text-gray-500">Artículos que usan los bots para responder y los asesores para consultar</p>
      </div>
      <UButton icon="i-heroicons-plus" color="gray" variant="outline" @click="openBase()">Nueva base</UButton>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- Bases -->
      <UCard class="lg:col-span-1">
        <template #header><span class="font-semibold text-sm">Bases</span></template>
        <p v-if="!bases.length" class="text-sm text-gray-500">Cree una base para empezar.</p>
        <button
          v-for="b in bases"
          :key="b.id"
          type="button"
          class="w-full text-left px-3 py-2 rounded-md mb-1 border"
          :class="current?.id === b.id ? 'border-primary-500 bg-primary-50' : 'border-transparent hover:bg-gray-50'"
          @click="selectBase(b)"
        >
          <p class="font-medium text-sm">{{ b.name }}</p>
          <p class="text-xs text-gray-500">
            {{ b.articles_count }} artículos
            <span v-if="b.unanswered_30d" class="text-orange-600"> · {{ b.unanswered_30d }} sin respuesta (30 días)</span>
          </p>
        </button>
      </UCard>

      <!-- Artículos -->
      <div class="lg:col-span-3 space-y-4">
        <UCard v-if="current">
          <div class="flex flex-wrap items-center gap-2">
            <h2 class="font-semibold flex-1">{{ current.name }}</h2>
            <UButton size="sm" icon="i-heroicons-plus" @click="openArticle()">Nuevo artículo</UButton>
            <UButton size="sm" color="gray" variant="outline" icon="i-heroicons-arrow-up-tray" :loading="uploading" @click="fileInput?.click()">
              Cargar documento
            </UButton>
            <input ref="fileInput" type="file" class="hidden" accept=".pdf,.docx,.xlsx,.txt,.md,.csv" @change="upload">
            <UButton v-if="current.glpi_connector" size="sm" color="gray" variant="outline" icon="i-heroicons-arrow-path" :loading="syncing" @click="syncGlpi">
              Sincronizar con GLPI
            </UButton>
            <UButton size="sm" color="gray" variant="ghost" icon="i-heroicons-cog-6-tooth" @click="openBase(current)" />
          </div>
          <p v-if="current.last_synced_at" class="text-xs text-gray-500 mt-1">Última sincronización con GLPI: {{ new Date(current.last_synced_at).toLocaleString() }}</p>
        </UCard>

        <UTabs v-if="current" :items="tabs">
          <template #articles>
            <UCard class="mt-3">
              <UInput v-model="search" icon="i-heroicons-magnifying-glass" placeholder="Buscar en títulos y contenido" class="mb-3" @update:model-value="debouncedLoad" />
              <UTable :rows="articles" :columns="columns" :loading="loading"
                      :empty-state="{ icon: 'i-heroicons-book-open', label: 'Sin artículos. Escriba uno o cargue un documento.' }">
                <template #title-data="{ row }">
                  <p class="font-medium">{{ row.title }}</p>
                  <p class="text-xs text-gray-500 line-clamp-1 max-w-md">{{ row.body }}</p>
                </template>
                <template #source-data="{ row }">
                  <UBadge :color="row.source === 'glpi' ? 'blue' : row.source === 'file' ? 'violet' : 'gray'" variant="soft">
                    {{ { manual: 'Manual', file: 'Documento', glpi: 'GLPI' }[row.source as string] }}
                  </UBadge>
                </template>
                <template #is_published-data="{ row }">
                  <UToggle :model-value="row.is_published" @update:model-value="togglePublished(row, $event)" />
                </template>
                <template #actions-data="{ row }">
                  <div class="flex gap-1 justify-end">
                    <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-pencil" @click="openArticle(row)" />
                    <UButton size="xs" color="red" variant="ghost" icon="i-heroicons-trash" @click="removeArticle(row)" />
                  </div>
                </template>
              </UTable>
            </UCard>
          </template>

          <template #unanswered>
            <UCard class="mt-3">
              <p class="text-sm text-gray-500 mb-3">
                Preguntas de clientes y asesores que la base no pudo responder. Úselas para escribir artículos nuevos.
                Los datos personales aparecen ocultos.
              </p>
              <UTable :rows="unanswered" :columns="unansweredColumns" :empty-state="{ icon: 'i-heroicons-check-circle', label: 'No hay preguntas sin respuesta' }">
                <template #created_at-data="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
                <template #actions-data="{ row }">
                  <UButton size="xs" variant="soft" @click="articleFromQuestion(row)">Crear artículo</UButton>
                </template>
              </UTable>
            </UCard>
          </template>

          <template #test>
            <UCard class="mt-3 space-y-3">
              <UFormGroup label="Pregunta de prueba">
                <div class="flex gap-2">
                  <UInput v-model="test.q" class="flex-1" placeholder="¿Cómo configuro el buzón de voz?" @keydown.enter="runTest" />
                  <UButton :loading="test.loading" @click="runTest">Buscar</UButton>
                </div>
              </UFormGroup>
              <div v-for="h in test.hits" :key="h.chunk_id" class="border rounded p-2 text-sm">
                <div class="flex justify-between"><span class="font-medium">{{ h.title }}</span><span class="text-xs text-gray-400">relevancia {{ h.rank }}</span></div>
                <p class="text-gray-600 whitespace-pre-line text-xs mt-1">{{ h.text }}</p>
              </div>
              <p v-if="test.done && !test.hits.length" class="text-sm text-gray-500">Sin resultados: esta pregunta saldría por «Sin respuesta».</p>
            </UCard>
          </template>
        </UTabs>
      </div>
    </div>

    <!-- Base -->
    <UModal v-model="baseForm.open">
      <UCard>
        <template #header><h3 class="font-semibold">{{ baseForm.id ? 'Editar base' : 'Nueva base de conocimiento' }}</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Nombre" required><UInput v-model="baseForm.name" placeholder="Soporte técnico" /></UFormGroup>
          <UFormGroup label="Descripción"><UTextarea v-model="baseForm.description" :rows="2" /></UFormGroup>
          <UFormGroup label="Sincronizar con la base de conocimiento de GLPI" hint="Importa los artículos de GLPI cada noche">
            <USelect v-model="baseForm.glpi_connector" :options="glpiOptions" />
          </UFormGroup>
          <UCheckbox v-model="baseForm.is_active" label="Activa" />
        </div>
        <template #footer>
          <div class="flex justify-between">
            <UButton v-if="baseForm.id" color="red" variant="ghost" @click="removeBase">Eliminar base</UButton>
            <div class="flex gap-2 ml-auto">
              <UButton color="gray" variant="ghost" @click="baseForm.open = false">Cancelar</UButton>
              <UButton :loading="baseForm.saving" @click="saveBase">Guardar</UButton>
            </div>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Artículo -->
    <UModal v-model="articleForm.open" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ articleForm.id ? 'Editar artículo' : 'Nuevo artículo' }}</h3></template>
        <UAlert v-if="articleForm.source === 'glpi'" color="blue" variant="soft" class="mb-3"
                description="Este artículo viene de GLPI: la próxima sincronización reemplazará los cambios hechos aquí." />
        <div class="space-y-3">
          <UFormGroup label="Título" required hint="Escríbalo como lo preguntaría un cliente">
            <UInput v-model="articleForm.title" placeholder="¿Cómo configuro el desvío de llamadas?" />
          </UFormGroup>
          <UFormGroup label="Contenido" required>
            <UTextarea v-model="articleForm.body" :rows="12" />
          </UFormGroup>
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Categoría"><UInput v-model="articleForm.category" /></UFormGroup>
            <UFormGroup label="Palabras clave" hint="Separadas por coma: sinónimos que usan los clientes">
              <UInput v-model="articleForm.keywords" placeholder="desvío, transferir, redirigir" />
            </UFormGroup>
          </div>
          <UCheckbox v-model="articleForm.is_published" label="Publicado (lo usan bots y asesores)" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="articleForm.open = false">Cancelar</UButton>
            <UButton :loading="articleForm.saving" @click="saveArticle">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })

const http = useHttp()
const toast = useToast()

const tabs = [
  { label: 'Artículos', slot: 'articles', icon: 'i-heroicons-document-text' },
  { label: 'Preguntas sin respuesta', slot: 'unanswered', icon: 'i-heroicons-question-mark-circle' },
  { label: 'Probar búsqueda', slot: 'test', icon: 'i-heroicons-magnifying-glass' },
]
const columns = [
  { key: 'title', label: 'Artículo' }, { key: 'category', label: 'Categoría' },
  { key: 'source', label: 'Origen' }, { key: 'is_published', label: 'Publicado' }, { key: 'actions', label: '' },
]
const unansweredColumns = [
  { key: 'created_at', label: 'Fecha' }, { key: 'question', label: 'Pregunta' },
  { key: 'source', label: 'Origen' }, { key: 'actions', label: '' },
]

const bases = ref<any[]>([])
const current = ref<any>(null)
const articles = ref<any[]>([])
const unanswered = ref<any[]>([])
const connectors = ref<any[]>([])
const loading = ref(false)
const uploading = ref(false)
const syncing = ref(false)
const search = ref('')
const fileInput = ref<HTMLInputElement>()

const glpiOptions = computed(() => [
  { label: '— Sin sincronización —', value: null },
  ...connectors.value.filter(c => c.connector_type === 'glpi').map(c => ({ label: c.name, value: c.id })),
])

async function loadBases() {
  bases.value = http.results(await http.get('/chatbot/knowledge-bases/'))
  if (current.value) current.value = bases.value.find(b => b.id === current.value.id) || null
  if (!current.value && bases.value.length) await selectBase(bases.value[0])
}
async function selectBase(b: any) {
  current.value = b
  search.value = ''
  await Promise.all([loadArticles(), loadUnanswered()])
}
async function loadArticles() {
  if (!current.value) return
  loading.value = true
  try {
    articles.value = http.results(await http.get('/chatbot/knowledge-articles/', {
      knowledge_base: current.value.id, search: search.value || undefined, page_size: 500,
    }))
  } finally { loading.value = false }
}
async function loadUnanswered() {
  if (current.value) unanswered.value = await http.get(`/chatbot/knowledge-bases/${current.value.id}/unanswered/`)
}
let timer: ReturnType<typeof setTimeout> | undefined
function debouncedLoad() { clearTimeout(timer); timer = setTimeout(loadArticles, 300) }

// Bases
const baseForm = reactive({ open: false, saving: false, id: null as number | null, name: '', description: '', glpi_connector: null as number | null, is_active: true })
function openBase(b?: any) {
  Object.assign(baseForm, { open: true, saving: false, id: b?.id ?? null, name: b?.name ?? '', description: b?.description ?? '',
    glpi_connector: b?.glpi_connector ?? null, is_active: b?.is_active ?? true })
}
async function saveBase() {
  if (!baseForm.name.trim()) return toast.add({ title: 'Escriba un nombre', color: 'orange' })
  baseForm.saving = true
  const body = { name: baseForm.name.trim(), description: baseForm.description, glpi_connector: baseForm.glpi_connector, is_active: baseForm.is_active }
  try {
    const saved: any = baseForm.id ? await http.patch(`/chatbot/knowledge-bases/${baseForm.id}/`, body) : await http.post('/chatbot/knowledge-bases/', body)
    baseForm.open = false
    current.value = saved
    await loadBases()
    await selectBase(bases.value.find(b => b.id === saved.id) || saved)
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar', description: http.errorMessage(e), color: 'red' })
  } finally { baseForm.saving = false }
}
async function removeBase() {
  if (!confirm(`¿Eliminar la base "${baseForm.name}" con todos sus artículos?`)) return
  await http.del(`/chatbot/knowledge-bases/${baseForm.id}/`)
  baseForm.open = false
  current.value = null
  await loadBases()
}

// Artículos
const blankArticle = () => ({ open: false, saving: false, id: null as number | null, title: '', body: '', category: '', keywords: '', is_published: true, source: 'manual' })
const articleForm = reactive(blankArticle())
function openArticle(a?: any) {
  Object.assign(articleForm, blankArticle(), { open: true }, a ? {
    id: a.id, title: a.title, body: a.body, category: a.category, keywords: a.keywords, is_published: a.is_published, source: a.source,
  } : {})
}
function articleFromQuestion(q: any) {
  openArticle()
  articleForm.title = q.question.slice(0, 200)
}
async function saveArticle() {
  if (!articleForm.title.trim() || articleForm.body.trim().length < 10) return toast.add({ title: 'Título y contenido son obligatorios', color: 'orange' })
  articleForm.saving = true
  const body = { knowledge_base: current.value.id, title: articleForm.title.trim(), body: articleForm.body,
    category: articleForm.category, keywords: articleForm.keywords, is_published: articleForm.is_published }
  try {
    if (articleForm.id) await http.patch(`/chatbot/knowledge-articles/${articleForm.id}/`, body)
    else await http.post('/chatbot/knowledge-articles/', body)
    toast.add({ title: 'Artículo guardado', color: 'green' })
    articleForm.open = false
    await Promise.all([loadArticles(), loadBases()])
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar', description: http.errorMessage(e), color: 'red' })
  } finally { articleForm.saving = false }
}
async function togglePublished(a: any, v: boolean) {
  await http.patch(`/chatbot/knowledge-articles/${a.id}/`, { is_published: v })
  a.is_published = v
}
async function removeArticle(a: any) {
  if (!confirm(`¿Eliminar "${a.title}"?`)) return
  await http.del(`/chatbot/knowledge-articles/${a.id}/`)
  await Promise.all([loadArticles(), loadBases()])
}
async function upload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !current.value) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const a: any = await http.post(`/chatbot/knowledge-bases/${current.value.id}/upload/`, fd)
    toast.add({ title: 'Documento cargado', description: `Artículo "${a.title}" (${a.body.length.toLocaleString()} caracteres). Revise el título.`, color: 'green' })
    await Promise.all([loadArticles(), loadBases()])
  } catch (err: any) {
    toast.add({ title: 'No se pudo cargar', description: err?.data?.error || http.errorMessage(err), color: 'red', timeout: 10000 })
  } finally { uploading.value = false }
}
async function syncGlpi() {
  syncing.value = true
  try {
    const r: any = await http.post(`/chatbot/knowledge-bases/${current.value.id}/sync-glpi/`)
    toast.add({ title: 'Sincronización completa', description: `${r.created} nuevos · ${r.updated} actualizados · ${r.removed} eliminados`, color: 'green' })
    await Promise.all([loadArticles(), loadBases()])
  } catch (e: any) {
    toast.add({ title: 'Falló la sincronización', description: e?.data?.error || http.errorMessage(e), color: 'red', timeout: 10000 })
  } finally { syncing.value = false }
}

// Prueba
const test = reactive({ q: '', hits: [] as any[], loading: false, done: false })
async function runTest() {
  if (test.q.trim().length < 3) return
  test.loading = true
  try {
    test.hits = await http.get('/chatbot/knowledge/search/', { q: test.q, kb: current.value?.id })
    test.done = true
  } finally { test.loading = false }
}

onMounted(async () => {
  try { connectors.value = http.results(await http.get('/chatbot/connectors/')) } catch { connectors.value = [] }
  await loadBases()
})
</script>
