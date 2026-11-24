<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Conectores</h1>
        <p class="text-sm text-gray-500">Sistemas externos que pueden usar los bots (GLPI, APIs de citas, CRM…)</p>
      </div>
      <UButton v-if="isAdmin" icon="i-heroicons-plus" @click="openForm()">Nuevo conector</UButton>
    </div>

    <UCard>
      <UTable :rows="items" :columns="columns" :loading="loading"
              :empty-state="{ icon: 'i-heroicons-bolt', label: 'No hay conectores' }">
        <template #connector_type-data="{ row }">
          <UBadge :color="row.connector_type === 'glpi' ? 'blue' : 'gray'" variant="soft">
            {{ row.connector_type === 'glpi' ? 'GLPI' : 'HTTP' }}
          </UBadge>
        </template>
        <template #actions_count-data="{ row }">{{ row.actions.length }}</template>
        <template #is_active-data="{ row }">
          <UBadge :color="row.is_active ? 'green' : 'gray'" variant="soft">{{ row.is_active ? 'Activo' : 'Inactivo' }}</UBadge>
        </template>
        <template #actions-data="{ row }">
          <div class="flex gap-1 justify-end">
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-signal" title="Probar conexión" :loading="testing === row.id" @click="test(row)" />
            <UButton v-if="isAdmin" size="xs" color="gray" variant="ghost" icon="i-heroicons-beaker" title="Probar acción" @click="openRun(row)" />
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-document-text" title="Registro" @click="openLogs(row)" />
            <UButton v-if="isAdmin" size="xs" color="gray" variant="ghost" icon="i-heroicons-pencil" @click="openForm(row)" />
            <UButton v-if="isAdmin" size="xs" color="red" variant="ghost" icon="i-heroicons-trash" @click="remove(row)" />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Crear / editar -->
    <UModal v-model="form.open" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ form.id ? 'Editar conector' : 'Nuevo conector' }}</h3></template>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Nombre" required><UInput v-model="form.name" placeholder="GLPI Soporte" /></UFormGroup>
            <UFormGroup label="Tipo">
              <USelect v-model="form.connector_type" :disabled="!!form.id"
                       :options="[{ label: 'GLPI', value: 'glpi' }, { label: 'API HTTP genérica', value: 'http' }]" />
            </UFormGroup>
          </div>
          <UFormGroup label="URL base" required
                      :hint="form.connector_type === 'glpi' ? 'Termina en /apirest.php' : 'Las rutas de cada acción se agregan a esta URL'">
            <UInput v-model="form.base_url" :placeholder="form.connector_type === 'glpi' ? 'https://soporte.empresa.com/apirest.php' : 'https://api.empresa.com/v1'" />
          </UFormGroup>

          <template v-if="form.connector_type === 'glpi'">
            <div class="grid grid-cols-2 gap-3">
              <UFormGroup label="App-Token" :hint="secretHint('app_token')"><UInput v-model="form.secrets.app_token" type="password" autocomplete="off" /></UFormGroup>
              <UFormGroup label="Token de usuario (bot)" :hint="secretHint('user_token')"><UInput v-model="form.secrets.user_token" type="password" autocomplete="off" /></UFormGroup>
              <UFormGroup label="Tipo de ticket por defecto">
                <USelect v-model="form.glpi.default_type" :options="[{ label: 'Incidente', value: 1 }, { label: 'Solicitud', value: 2 }]" />
              </UFormGroup>
              <UFormGroup label="Urgencia por defecto">
                <USelect v-model="form.glpi.default_urgency" :options="[1,2,3,4,5].map(v => ({ label: ['Muy baja','Baja','Media','Alta','Muy alta'][v-1], value: v }))" />
              </UFormGroup>
              <UFormGroup label="Id categoría por defecto (opcional)"><UInput v-model.number="form.glpi.default_category_id" type="number" /></UFormGroup>
              <UFormGroup label="Id origen «WhatsApp» (opcional)" hint="Configuración › Desplegables › Orígenes"><UInput v-model.number="form.glpi.requesttype_id" type="number" /></UFormGroup>
              <UFormGroup label="Id entidad (opcional)"><UInput v-model.number="form.glpi.entity_id" type="number" /></UFormGroup>
              <UFormGroup label="URL de GLPI para enlaces (opcional)"><UInput v-model="form.glpi.front_url" placeholder="https://soporte.empresa.com" /></UFormGroup>
            </div>
            <UAlert color="blue" variant="soft" icon="i-heroicons-information-circle"
                    description="En GLPI: Configuración › General › API → habilitar la API REST y «inicio de sesión con token externo», crear un cliente de API (App-Token). El usuario del bot necesita un perfil que pueda crear tickets y consultar usuarios; su token está en Preferencias › Token de API remota." />
          </template>

          <template v-else>
            <UFormGroup label="Credenciales (JSON)" hint="Se guardan cifradas. Úselas como {{secret.nombre}}. Vacío = sin cambios">
              <UTextarea v-model="form.secretsJson" :rows="2" class="font-mono" placeholder='{"token": "..."}' />
            </UFormGroup>
            <UFormGroup label="Configuración: cabeceras y acciones (JSON)">
              <UTextarea v-model="form.configJson" :rows="12" class="font-mono text-xs" />
            </UFormGroup>
          </template>

          <div class="grid grid-cols-3 gap-3">
            <UFormGroup label="Tiempo de espera (s)"><UInput v-model.number="form.timeout_seconds" type="number" min="3" max="60" /></UFormGroup>
            <UCheckbox v-model="form.verify_ssl" label="Verificar certificado SSL" class="mt-6" />
            <UCheckbox v-model="form.is_active" label="Activo" class="mt-6" />
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="form.open = false">Cancelar</UButton>
            <UButton :loading="form.saving" @click="save">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Probar acción -->
    <UModal v-model="run.open">
      <UCard>
        <template #header><h3 class="font-semibold">Probar acción — {{ run.connector?.name }}</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Acción">
            <USelect v-model="run.action" :options="(run.connector?.actions || []).map((a: any) => ({ label: a.label, value: a.name }))" />
          </UFormGroup>
          <UFormGroup v-for="inp in runInputs" :key="inp.name" :label="inp.label">
            <UInput v-model="run.params[inp.name]" />
          </UFormGroup>
          <pre v-if="run.result" class="bg-gray-100 rounded p-2 text-xs overflow-x-auto max-h-64">{{ JSON.stringify(run.result, null, 2) }}</pre>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="run.open = false">Cerrar</UButton>
            <UButton :loading="run.loading" :disabled="!run.action" @click="execute">Ejecutar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Registro -->
    <UModal v-model="logs.open" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">Registro de llamadas — {{ logs.connector?.name }}</h3></template>
        <UTable :rows="logs.items" :columns="logColumns">
          <template #created_at-data="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
          <template #status-data="{ row }">
            <UBadge :color="row.status === 'success' ? 'green' : row.status === 'empty' ? 'amber' : 'red'" variant="soft">{{ row.status }}</UBadge>
          </template>
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

const columns = [
  { key: 'name', label: 'Nombre' }, { key: 'connector_type', label: 'Tipo' }, { key: 'base_url', label: 'URL' },
  { key: 'actions_count', label: 'Acciones' }, { key: 'is_active', label: 'Estado' }, { key: 'actions', label: '' },
]
const logColumns = [
  { key: 'created_at', label: 'Fecha' }, { key: 'action', label: 'Acción' }, { key: 'status', label: 'Resultado' },
  { key: 'duration_ms', label: 'ms' }, { key: 'source', label: 'Origen' }, { key: 'error', label: 'Error' },
]
const MASK = '••••••'
const HTTP_EXAMPLE = JSON.stringify({
  headers: { Authorization: 'Bearer {{secret.token}}' },
  actions: [{
    name: 'consultar_citas', label: 'Consultar citas', method: 'GET',
    path: '/pacientes/{{documento}}/citas', inputs: ['documento'],
    result_path: 'data', returns_list: true,
  }],
}, null, 2)

const items = ref<any[]>([])
const loading = ref(false)
const testing = ref<number | null>(null)

async function load() {
  loading.value = true
  try { items.value = http.results(await http.get('/chatbot/connectors/')) } finally { loading.value = false }
}

const blank = () => ({
  open: false, saving: false, id: null as number | null, name: '', connector_type: 'glpi', base_url: '',
  timeout_seconds: 15, verify_ssl: true, is_active: true, secret_keys: [] as string[],
  secrets: { app_token: '', user_token: '' } as Record<string, string>, secretsJson: '', configJson: HTTP_EXAMPLE,
  glpi: { default_type: 1, default_urgency: 3, default_category_id: null, requesttype_id: null, entity_id: null, front_url: '' } as any,
})
const form = reactive(blank())
const secretHint = (k: string) => form.secret_keys.includes(k) ? 'Configurado — vacío para no cambiarlo' : ''

function openForm(c?: any) {
  Object.assign(form, blank(), { open: true })
  if (!c) return
  Object.assign(form, {
    id: c.id, name: c.name, connector_type: c.connector_type, base_url: c.base_url,
    timeout_seconds: c.timeout_seconds, verify_ssl: c.verify_ssl, is_active: c.is_active, secret_keys: c.secret_keys,
  })
  if (c.connector_type === 'glpi') form.glpi = { ...form.glpi, ...(c.config || {}) }
  else form.configJson = JSON.stringify(c.config || {}, null, 2)
}

async function save() {
  if (!form.name.trim() || !form.base_url.trim()) return toast.add({ title: 'Nombre y URL son obligatorios', color: 'orange' })
  let config: any = {}
  let secrets: Record<string, string> = {}
  if (form.connector_type === 'glpi') {
    config = Object.fromEntries(Object.entries(form.glpi).filter(([, v]) => v !== null && v !== ''))
    for (const k of ['app_token', 'user_token']) secrets[k] = form.secrets[k] || (form.secret_keys.includes(k) ? MASK : '')
  } else {
    try { config = JSON.parse(form.configJson || '{}') } catch { return toast.add({ title: 'La configuración no es JSON válido', color: 'orange' }) }
    if (form.secretsJson.trim()) {
      try { secrets = JSON.parse(form.secretsJson) } catch { return toast.add({ title: 'Las credenciales no son JSON válido', color: 'orange' }) }
    } else {
      secrets = Object.fromEntries(form.secret_keys.map(k => [k, MASK]))
    }
  }
  form.saving = true
  const body = { name: form.name.trim(), connector_type: form.connector_type, base_url: form.base_url.trim(), config, secrets,
    timeout_seconds: form.timeout_seconds, verify_ssl: form.verify_ssl, is_active: form.is_active }
  try {
    if (form.id) await http.patch(`/chatbot/connectors/${form.id}/`, body)
    else await http.post('/chatbot/connectors/', body)
    toast.add({ title: 'Conector guardado', color: 'green' })
    form.open = false
    await load()
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar', description: http.errorMessage(e), color: 'red' })
  } finally { form.saving = false }
}

async function test(c: any) {
  testing.value = c.id
  try {
    const r: any = await http.post(`/chatbot/connectors/${c.id}/test/`)
    toast.add({ title: 'Conexión correcta', description: r.data?.message || `HTTP ${r.data?.http_status ?? ''}`, color: 'green' })
  } catch (e: any) {
    toast.add({ title: 'Falló la conexión', description: e?.data?.error || http.errorMessage(e), color: 'red', timeout: 10000 })
  } finally { testing.value = null }
}

const run = reactive({ open: false, loading: false, connector: null as any, action: '', params: {} as Record<string, string>, result: null as any })
const runInputs = computed(() => run.connector?.actions.find((a: any) => a.name === run.action)?.inputs || [])
function openRun(c: any) { Object.assign(run, { open: true, connector: c, action: c.actions[0]?.name || '', params: {}, result: null }) }
async function execute() {
  run.loading = true
  try {
    run.result = await http.post(`/chatbot/connectors/${run.connector.id}/run/`, { action: run.action, params: run.params })
  } catch (e: any) {
    run.result = e?.data || { error: http.errorMessage(e) }
  } finally { run.loading = false }
}

const logs = reactive({ open: false, connector: null as any, items: [] as any[] })
async function openLogs(c: any) {
  Object.assign(logs, { open: true, connector: c, items: [] })
  logs.items = await http.get(`/chatbot/connectors/${c.id}/logs/`)
}

async function remove(c: any) {
  if (!confirm(`¿Eliminar el conector "${c.name}"? Los bloques que lo usan quedarán sin conector.`)) return
  try { await http.del(`/chatbot/connectors/${c.id}/`); await load() } catch (e: any) {
    toast.add({ title: 'No se pudo eliminar', description: http.errorMessage(e), color: 'red' })
  }
}

onMounted(load)
</script>
