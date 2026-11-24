<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Bots de autoatención</h1>
        <p class="text-sm text-gray-500">Flujos automáticos para WhatsApp, chat web y redes sociales</p>
      </div>
      <div class="flex gap-2">
        <UButton color="gray" variant="outline" icon="i-heroicons-bolt" to="/connectors">Conectores</UButton>
        <UButton icon="i-heroicons-plus" @click="create.open = true">Nuevo bot</UButton>
      </div>
    </div>

    <UCard>
      <UTable
        :rows="flows"
        :columns="columns"
        :loading="loading"
        :empty-state="{ icon: 'i-heroicons-cpu-chip', label: 'No hay bots. Cree uno desde cero o desde una plantilla.' }"
      >
        <template #name-data="{ row }">
          <NuxtLink :to="`/bots/${row.id}`" class="font-medium text-primary-600 hover:underline">{{ row.name }}</NuxtLink>
          <p class="text-xs text-gray-500 truncate max-w-xs">{{ row.description }}</p>
        </template>
        <template #channels-data="{ row }">
          <span class="text-sm">{{ row.channel_names.join(', ') || '—' }}</span>
        </template>
        <template #version-data="{ row }">
          <UBadge v-if="row.published_number" color="green" variant="soft">v{{ row.published_number }}</UBadge>
          <UBadge v-else color="gray" variant="soft">Sin publicar</UBadge>
          <UBadge v-if="row.has_unpublished_changes && row.published_number" color="orange" variant="soft" class="ml-1">Borrador con cambios</UBadge>
        </template>
        <template #is_active-data="{ row }">
          <UToggle :model-value="row.is_active" @update:model-value="toggleActive(row, $event)" />
        </template>
        <template #actions-data="{ row }">
          <div class="flex gap-1 justify-end">
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-pencil-square" :to="`/bots/${row.id}`" title="Diseñar" />
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-cog-6-tooth" title="Canales" @click="openSettings(row)" />
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-chart-bar" title="Estadísticas" @click="openStats(row)" />
            <UButton size="xs" color="red" variant="ghost" icon="i-heroicons-trash" title="Eliminar" @click="remove(row)" />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Nuevo bot -->
    <UModal v-model="create.open">
      <UCard>
        <template #header><h3 class="font-semibold">Nuevo bot</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Nombre" required><UInput v-model="create.name" placeholder="Bot de soporte" /></UFormGroup>
          <UFormGroup label="Empezar desde">
            <URadioGroup v-model="create.template" :options="templateOptions" />
          </UFormGroup>
          <UFormGroup v-if="create.template === 'glpi_support'" label="Conector GLPI" hint="Se puede elegir después en cada bloque">
            <USelect v-model="create.connector_id" :options="glpiOptions" placeholder="Seleccione" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="create.open = false">Cancelar</UButton>
            <UButton :loading="create.saving" @click="createFlow">Crear y diseñar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Canales y tiempo de sesión -->
    <UModal v-model="settings.open">
      <UCard>
        <template #header><h3 class="font-semibold">Configuración de "{{ settings.flow?.name }}"</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Canales donde atiende" hint="Un canal solo puede tener un bot activo">
            <USelectMenu v-model="settings.channels" :options="channelOptions" multiple value-attribute="value" option-attribute="label" placeholder="Seleccione canales" />
          </UFormGroup>
          <UFormGroup label="Descripción"><UTextarea v-model="settings.description" :rows="2" /></UFormGroup>
          <UFormGroup label="Reiniciar la conversación tras (minutos sin respuesta)">
            <UInput v-model.number="settings.timeout" type="number" min="1" max="1440" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="settings.open = false">Cancelar</UButton>
            <UButton :loading="settings.saving" @click="saveSettings">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Estadísticas -->
    <UModal v-model="stats.open">
      <UCard>
        <template #header><h3 class="font-semibold">Estadísticas de "{{ stats.flow?.name }}"</h3></template>
        <div v-if="stats.data" class="space-y-3 text-sm">
          <p>Conversaciones atendidas por el bot: <strong>{{ stats.data.total }}</strong></p>
          <div class="grid grid-cols-2 gap-2">
            <div v-for="(n, s) in stats.data.by_status" :key="s" class="flex justify-between border rounded px-2 py-1">
              <span>{{ statusLabels[s] || s }}</span><strong>{{ n }}</strong>
            </div>
          </div>
          <div v-if="stats.data.dropoff_nodes.length">
            <p class="font-medium">Bloques donde más abandonan</p>
            <div v-for="[node, n] in stats.data.dropoff_nodes" :key="node" class="flex justify-between text-xs border-b py-1">
              <span>{{ node || '—' }}</span><span>{{ n }}</span>
            </div>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })

const http = useHttp()
const toast = useToast()

const columns = [
  { key: 'name', label: 'Bot' }, { key: 'channels', label: 'Canales' },
  { key: 'version', label: 'Versión' }, { key: 'active_sessions', label: 'Sesiones activas' },
  { key: 'is_active', label: 'Activo' }, { key: 'actions', label: '' },
]
const statusLabels: Record<string, string> = {
  active: 'En curso', busy: 'Consultando sistema', handed_off: 'Pasadas a asesor',
  completed: 'Resueltas por el bot', timeout: 'Abandonadas', error: 'Con error',
}

const flows = ref<any[]>([])
const channels = ref<any[]>([])
const catalog = ref<any>({ templates: [], connectors: [] })
const loading = ref(false)

const channelOptions = computed(() => channels.value.map(c => ({ label: `${c.channel_type} — ${c.name}`, value: c.id })))
const templateOptions = computed(() => [
  { value: '', label: 'Flujo en blanco' },
  ...catalog.value.templates.map((t: any) => ({ value: t.key, label: `${t.name} — ${t.description}` })),
])
const glpiOptions = computed(() => catalog.value.connectors.filter((c: any) => c.type === 'glpi').map((c: any) => ({ label: c.name, value: c.id })))

async function load() {
  loading.value = true
  try {
    const [f, ch, cat] = await Promise.all([
      http.get('/chatbot/flows/'), http.get('/messaging/channels/'), http.get('/chatbot/flows/catalog/'),
    ])
    flows.value = http.results(f)
    channels.value = http.results(ch)
    catalog.value = cat
  } catch (e: any) {
    toast.add({ title: 'Error al cargar', description: http.errorMessage(e), color: 'red' })
  } finally { loading.value = false }
}

const create = reactive({ open: false, saving: false, name: '', template: '', connector_id: null as number | null })
async function createFlow() {
  if (!create.name.trim()) return toast.add({ title: 'Escriba un nombre', color: 'orange' })
  create.saving = true
  try {
    const flow: any = create.template
      ? await http.post('/chatbot/flows/from-template/', { template: create.template, name: create.name, connector_id: create.connector_id })
      : await http.post('/chatbot/flows/', {
        name: create.name,
        draft: { start: 'inicio', nodes: [{ id: 'inicio', type: 'message', data: { title: 'Bienvenida', text: 'Hola {{contact.name}} 👋' }, position: { x: 0, y: 0 } }], edges: [] },
      })
    create.open = false
    await navigateTo(`/bots/${flow.id}`)
  } catch (e: any) {
    toast.add({ title: 'No se pudo crear', description: http.errorMessage(e), color: 'red' })
  } finally { create.saving = false }
}

async function toggleActive(row: any, value: boolean) {
  try {
    const r: any = await http.patch(`/chatbot/flows/${row.id}/`, { is_active: value })
    Object.assign(row, r)
    toast.add({ title: value ? 'Bot activado' : 'Bot desactivado', color: value ? 'green' : 'gray' })
  } catch (e: any) {
    toast.add({ title: 'No se pudo cambiar', description: http.errorMessage(e), color: 'red' })
  }
}

const settings = reactive({ open: false, saving: false, flow: null as any, channels: [] as number[], description: '', timeout: 30 })
function openSettings(row: any) {
  Object.assign(settings, { open: true, flow: row, channels: [...row.channels], description: row.description, timeout: row.session_timeout_minutes })
}
async function saveSettings() {
  settings.saving = true
  try {
    await http.patch(`/chatbot/flows/${settings.flow.id}/`, {
      channels: settings.channels, description: settings.description, session_timeout_minutes: settings.timeout,
    })
    settings.open = false
    await load()
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar', description: http.errorMessage(e), color: 'red' })
  } finally { settings.saving = false }
}

const stats = reactive({ open: false, flow: null as any, data: null as any })
async function openStats(row: any) {
  Object.assign(stats, { open: true, flow: row, data: null })
  stats.data = await http.get(`/chatbot/flows/${row.id}/stats/`)
}

async function remove(row: any) {
  if (!confirm(`¿Eliminar el bot "${row.name}" y todas sus versiones?`)) return
  try {
    await http.del(`/chatbot/flows/${row.id}/`)
    await load()
  } catch (e: any) {
    toast.add({ title: 'No se pudo eliminar', description: http.errorMessage(e), color: 'red' })
  }
}

onMounted(load)
</script>
