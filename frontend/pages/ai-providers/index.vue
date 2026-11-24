<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Inteligencia artificial</h1>
        <p class="text-sm text-gray-500">Proveedores de IA que usan los bots para entender a los clientes</p>
      </div>
      <UButton v-if="isAdmin" icon="i-heroicons-plus" @click="openForm()">Nuevo proveedor</UButton>
    </div>

    <UCard>
      <div class="flex items-start gap-3 text-sm">
        <UIcon name="i-heroicons-microphone" class="w-5 h-5 text-primary-500 mt-0.5" />
        <div>
          <p class="font-medium">Transcripción de notas de voz: local</p>
          <p class="text-gray-500">
            Los audios que envían los clientes se transcriben en este servidor (servicio <code>transcriber</code>, modelo Whisper).
            No se envían a terceros. El texto aparece debajo del audio en la bandeja y el bot lo procesa como si el cliente lo hubiera escrito.
          </p>
        </div>
      </div>
    </UCard>

    <UCard>
      <UTable :rows="items" :columns="columns" :loading="loading"
              :empty-state="{ icon: 'i-heroicons-sparkles', label: 'No hay proveedores de IA' }">
        <template #provider_type-data="{ row }">{{ typeLabel(row.provider_type) }}</template>
        <template #mask_personal_data-data="{ row }">
          <UBadge :color="row.mask_personal_data ? 'green' : 'orange'" variant="soft">{{ row.mask_personal_data ? 'Sí' : 'No' }}</UBadge>
        </template>
        <template #tokens_this_month-data="{ row }">
          {{ row.tokens_this_month.toLocaleString() }}<span v-if="row.monthly_token_limit" class="text-gray-400"> / {{ row.monthly_token_limit.toLocaleString() }}</span>
        </template>
        <template #is_active-data="{ row }">
          <UBadge :color="row.is_active ? 'green' : 'gray'" variant="soft">{{ row.is_active ? 'Activo' : 'Inactivo' }}</UBadge>
        </template>
        <template #actions-data="{ row }">
          <div class="flex gap-1 justify-end">
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-signal" title="Probar conexión" :loading="testing === row.id" @click="test(row)" />
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-beaker" title="Probar clasificación" @click="openTry(row)" />
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-document-text" title="Uso" @click="openUsage(row)" />
            <UButton v-if="isAdmin" size="xs" color="gray" variant="ghost" icon="i-heroicons-pencil" @click="openForm(row)" />
            <UButton v-if="isAdmin" size="xs" color="red" variant="ghost" icon="i-heroicons-trash" @click="remove(row)" />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Crear / editar -->
    <UModal v-model="form.open" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ form.id ? 'Editar proveedor' : 'Nuevo proveedor de IA' }}</h3></template>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Nombre" required><UInput v-model="form.name" placeholder="OpenAI producción" /></UFormGroup>
            <UFormGroup label="Tipo"><USelect v-model="form.provider_type" :options="TYPES" /></UFormGroup>
          </div>
          <UFormGroup :label="form.provider_type === 'openai' ? 'URL (opcional)' : 'URL del servicio'" :hint="urlHint" :required="form.provider_type !== 'openai'">
            <UInput v-model="form.base_url" :placeholder="urlPlaceholder" />
          </UFormGroup>
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup :label="form.provider_type === 'azure_openai' ? 'Deployment' : 'Modelo'" required>
              <UInput v-model="form.model" :placeholder="form.provider_type === 'openai_compatible' ? 'llama3.1:8b' : 'gpt-4o-mini'" />
            </UFormGroup>
            <UFormGroup label="API key" :hint="form.has_api_key ? 'Configurada — vacío para no cambiarla' : (form.provider_type === 'openai_compatible' ? 'Opcional en Ollama' : '')">
              <UInput v-model="form.api_key" type="password" autocomplete="off" />
            </UFormGroup>
            <UFormGroup v-if="form.provider_type === 'azure_openai'" label="Versión de API"><UInput v-model="form.api_version" /></UFormGroup>
            <UFormGroup label="Temperatura" hint="0 = respuestas consistentes"><UInput v-model.number="form.temperature" type="number" step="0.1" min="0" max="2" /></UFormGroup>
            <UFormGroup label="Tiempo de espera (s)"><UInput v-model.number="form.timeout_seconds" type="number" min="5" max="120" /></UFormGroup>
            <UFormGroup label="Límite mensual de tokens" hint="0 = sin límite"><UInput v-model.number="form.monthly_token_limit" type="number" min="0" /></UFormGroup>
          </div>
          <UCheckbox v-model="form.mask_personal_data" label="Ocultar datos personales antes de enviar (documentos, teléfonos, emails, tarjetas)" />
          <UCheckbox v-model="form.is_active" label="Activo" />
          <UAlert color="blue" variant="soft" icon="i-heroicons-shield-check"
                  description="Para datos sensibles (salud, financieros) use un modelo local (Ollama/vLLM en su red) o Azure OpenAI con residencia de datos, y mantenga activo el ocultamiento de datos personales." />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="form.open = false">Cancelar</UButton>
            <UButton :loading="form.saving" @click="save">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Probar clasificación -->
    <UModal v-model="tryForm.open">
      <UCard>
        <template #header><h3 class="font-semibold">Probar clasificación — {{ tryForm.provider?.name }}</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Mensaje del cliente"><UTextarea v-model="tryForm.text" :rows="3" placeholder="desde ayer no tengo internet, el ticket 4521 sigue igual" /></UFormGroup>
          <UFormGroup label="Intenciones (una por línea: id | descripción)">
            <UTextarea v-model="tryForm.intents" :rows="4" class="font-mono text-xs" />
          </UFormGroup>
          <UFormGroup label="Datos a extraer (una por línea: nombre | descripción)">
            <UTextarea v-model="tryForm.fields" :rows="2" class="font-mono text-xs" />
          </UFormGroup>
          <pre v-if="tryForm.result" class="bg-gray-100 rounded p-2 text-xs overflow-x-auto">{{ JSON.stringify(tryForm.result, null, 2) }}</pre>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="tryForm.open = false">Cerrar</UButton>
            <UButton :loading="tryForm.loading" @click="runTry">Clasificar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Uso -->
    <UModal v-model="usage.open" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">Uso reciente — {{ usage.provider?.name }}</h3></template>
        <UTable :rows="usage.items" :columns="usageColumns">
          <template #created_at-data="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
          <template #status-data="{ row }"><UBadge :color="row.status === 'success' ? 'green' : 'red'" variant="soft">{{ row.status }}</UBadge></template>
          <template #error-data="{ row }"><span class="text-xs text-red-600">{{ row.error }}</span></template>
        </UTable>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })

const http = useHttp()
const toast = useToast()
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'admin')

const TYPES = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'Azure OpenAI', value: 'azure_openai' },
  { label: 'Compatible con OpenAI (Ollama, vLLM, Gemini…)', value: 'openai_compatible' },
]
const typeLabel = (v: string) => TYPES.find(t => t.value === v)?.label || v
const columns = [
  { key: 'name', label: 'Nombre' }, { key: 'provider_type', label: 'Tipo' }, { key: 'model', label: 'Modelo' },
  { key: 'mask_personal_data', label: 'Oculta datos' }, { key: 'tokens_this_month', label: 'Tokens este mes' },
  { key: 'is_active', label: 'Estado' }, { key: 'actions', label: '' },
]
const usageColumns = [
  { key: 'created_at', label: 'Fecha' }, { key: 'purpose', label: 'Uso' }, { key: 'status', label: 'Resultado' },
  { key: 'result', label: 'Intención' }, { key: 'tokens', label: 'Tokens' }, { key: 'duration_ms', label: 'ms' },
  { key: 'error', label: 'Error' },
]

const items = ref<any[]>([])
const loading = ref(false)
const testing = ref<number | null>(null)

async function load() {
  loading.value = true
  try { items.value = http.results(await http.get('/chatbot/ai-providers/')) } finally { loading.value = false }
}

const blank = () => ({
  open: false, saving: false, id: null as number | null, name: '', provider_type: 'openai', base_url: '',
  model: 'gpt-4o-mini', api_key: '', has_api_key: false, api_version: '2024-06-01', temperature: 0,
  timeout_seconds: 30, monthly_token_limit: 0, mask_personal_data: true, is_active: true,
})
const form = reactive(blank())
const urlPlaceholder = computed(() => ({
  openai: 'https://api.openai.com/v1',
  azure_openai: 'https://mi-recurso.openai.azure.com',
  openai_compatible: 'http://10.0.0.5:11434/v1',
} as Record<string, string>)[form.provider_type])
const urlHint = computed(() => ({
  openai: 'Vacío usa api.openai.com',
  azure_openai: 'Endpoint del recurso de Azure OpenAI',
  openai_compatible: 'Ollama: http://host:11434/v1 · Gemini: https://generativelanguage.googleapis.com/v1beta/openai',
} as Record<string, string>)[form.provider_type])

function openForm(p?: any) {
  Object.assign(form, blank(), { open: true })
  if (p) Object.assign(form, { ...p, api_key: '', open: true, saving: false })
}

async function save() {
  if (!form.name.trim() || !form.model.trim()) return toast.add({ title: 'Nombre y modelo son obligatorios', color: 'orange' })
  form.saving = true
  const { open, saving, id, has_api_key, ...body } = form as any
  for (const k of ['tokens_this_month', 'created_at', 'updated_at']) delete body[k]
  try {
    if (id) await http.patch(`/chatbot/ai-providers/${id}/`, body)
    else await http.post('/chatbot/ai-providers/', body)
    toast.add({ title: 'Proveedor guardado', color: 'green' })
    form.open = false
    await load()
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar', description: http.errorMessage(e), color: 'red' })
  } finally { form.saving = false }
}

async function test(p: any) {
  testing.value = p.id
  try {
    const r: any = await http.post(`/chatbot/ai-providers/${p.id}/test/`)
    toast.add({ title: 'Conexión correcta', description: `Respondió en ${r.duration_ms} ms`, color: 'green' })
  } catch (e: any) {
    toast.add({ title: 'Falló la conexión', description: e?.data?.error || http.errorMessage(e), color: 'red', timeout: 10000 })
  } finally { testing.value = null }
}

const tryForm = reactive({
  open: false, loading: false, provider: null as any, text: '', result: null as any,
  intents: 'soporte | Fallas técnicas, algo no funciona\nestado_ticket | Pregunta por un ticket existente\nfacturacion | Facturas, pagos, cobros\nasesor | Quiere hablar con una persona',
  fields: 'ticket_id | Número del ticket, si lo menciona',
})
function openTry(p: any) { Object.assign(tryForm, { open: true, provider: p, result: null }) }
const parseLines = (s: string) => s.split('\n').map(l => l.split('|').map(x => x.trim())).filter(([a]) => a)
async function runTry() {
  if (!tryForm.text.trim()) return
  tryForm.loading = true
  try {
    tryForm.result = await http.post(`/chatbot/ai-providers/${tryForm.provider.id}/classify/`, {
      text: tryForm.text,
      intents: parseLines(tryForm.intents).map(([id, desc]) => ({ id, name: id, description: desc || '' })),
      fields: parseLines(tryForm.fields).map(([name, desc]) => ({ name, description: desc || '' })),
    })
  } catch (e: any) {
    tryForm.result = { error: e?.data?.error || http.errorMessage(e) }
  } finally { tryForm.loading = false }
}

const usage = reactive({ open: false, provider: null as any, items: [] as any[] })
async function openUsage(p: any) {
  Object.assign(usage, { open: true, provider: p, items: [] })
  usage.items = await http.get(`/chatbot/ai-providers/${p.id}/usage/`)
}

async function remove(p: any) {
  if (!confirm(`¿Eliminar el proveedor "${p.name}"? Los bloques de IA que lo usan saldrán por «Error».`)) return
  try { await http.del(`/chatbot/ai-providers/${p.id}/`); await load() } catch (e: any) {
    toast.add({ title: 'No se pudo eliminar', description: http.errorMessage(e), color: 'red' })
  }
}

onMounted(load)
</script>
