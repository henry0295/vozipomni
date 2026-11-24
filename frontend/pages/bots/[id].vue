<template>
  <div class="flex flex-col h-[calc(100vh-6rem)] -m-2">
    <!-- Barra superior -->
    <div class="flex flex-wrap items-center gap-3 px-3 py-2 bg-white border-b">
      <UButton icon="i-heroicons-arrow-left" color="gray" variant="ghost" to="/bots" />
      <UInput v-model="flow.name" class="w-64" size="sm" />
      <UBadge v-if="flow.published_number" color="green" variant="soft">Publicado v{{ flow.published_number }}</UBadge>
      <UBadge v-else color="gray" variant="soft">Sin publicar</UBadge>
      <UBadge v-if="dirty" color="orange" variant="soft">Cambios sin guardar</UBadge>
      <div class="flex-1" />
      <UButton size="sm" color="gray" variant="outline" icon="i-heroicons-play" @click="showSim = !showSim">
        Simulador
      </UButton>
      <UButton size="sm" color="gray" variant="outline" icon="i-heroicons-clock" @click="openVersions">Versiones</UButton>
      <UButton size="sm" color="gray" variant="outline" icon="i-heroicons-check-badge" :loading="validating" @click="validate">
        Validar
      </UButton>
      <UButton size="sm" color="gray" icon="i-heroicons-cloud-arrow-up" :loading="saving" @click="save()">Guardar</UButton>
      <UButton size="sm" icon="i-heroicons-rocket-launch" :loading="publishing" @click="publish">Publicar</UButton>
    </div>

    <UAlert
      v-if="errors.length"
      color="red"
      icon="i-heroicons-exclamation-triangle"
      class="rounded-none"
      :title="`${errors.length} problema(s) en el flujo`"
      :close-button="{ icon: 'i-heroicons-x-mark', color: 'red', variant: 'link' }"
      @close="errors = []"
    >
      <template #description>
        <ul class="list-disc pl-5 text-xs">
          <li v-for="e in errors.slice(0, 8)" :key="e">{{ e }}</li>
        </ul>
      </template>
    </UAlert>

    <div class="flex flex-1 min-h-0">
      <!-- Paleta -->
      <aside class="w-48 shrink-0 bg-white border-r overflow-y-auto p-2 space-y-3">
        <div v-for="g in PALETTE" :key="g.group">
          <p class="text-[11px] font-semibold uppercase text-gray-400 px-1 mb-1">{{ g.group }}</p>
          <button
            v-for="k in g.items"
            :key="k"
            type="button"
            draggable="true"
            class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm hover:bg-gray-100 text-left"
            :title="BLOCKS[k].help"
            @dragstart="onDragStart($event, k)"
            @click="addBlock(k)"
          >
            <UIcon :name="BLOCKS[k].icon" class="w-4 h-4 text-gray-500" />
            {{ BLOCKS[k].label }}
          </button>
        </div>
        <p class="text-[11px] text-gray-400 px-1">Arrastre un bloque al lienzo o haga clic para agregarlo.
          Conecte la salida de un bloque (derecha) con la entrada de otro (izquierda). Supr borra lo seleccionado.</p>
      </aside>

      <!-- Lienzo -->
      <div class="flex-1 relative" @drop="onDrop" @dragover.prevent>
        <VueFlow
          id="bot-designer"
          v-model:nodes="nodes"
          v-model:edges="edges"
          :default-edge-options="{ type: 'smoothstep', markerEnd: 'arrowclosed' }"
          :delete-key-code="'Delete'"
          :min-zoom="0.2"
          fit-view-on-init
          @connect="onConnect"
          @node-click="(e: any) => select(e.node.id)"
          @pane-click="selectedId = ''"
          @nodes-change="markDirty"
          @edges-change="markDirty"
        >
          <template #node-bot="p">
            <BotNode :id="p.id" :data="{ ...p.data, isStart: p.id === start }" :selected="p.id === selectedId" />
          </template>
          <Background pattern-color="#e5e7eb" :gap="16" />
          <Controls />
          <MiniMap pannable zoomable />
        </VueFlow>
      </div>

      <!-- Propiedades -->
      <aside v-if="selected" class="w-80 shrink-0 bg-white border-l overflow-y-auto p-3 space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="font-semibold text-sm">{{ BLOCKS[selected.data.kind]?.label }}</h3>
          <div class="flex gap-1">
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-document-duplicate" title="Duplicar" @click="duplicate" />
            <UButton size="xs" color="red" variant="ghost" icon="i-heroicons-trash" title="Eliminar" @click="removeSelected" />
          </div>
        </div>
        <UButton
          v-if="start !== selected.id"
          size="xs"
          color="green"
          variant="soft"
          icon="i-heroicons-flag"
          block
          @click="setStart"
        >
          Marcar como inicio
        </UButton>

        <UFormGroup label="Nombre del bloque"><UInput v-model="d.title" size="sm" /></UFormGroup>

        <!-- Texto -->
        <UFormGroup
          v-if="['message','buttons','list','question','dynamic_list','handoff','end','connector'].includes(kind)"
          :label="kind === 'connector' ? 'Mensaje de espera (opcional)' : 'Texto'"
          :hint="`${(d.text || '').length}/1024`"
        >
          <UTextarea v-model="d.text" :rows="kind === 'connector' ? 2 : 4" size="sm" />
        </UFormGroup>

        <!-- Opciones -->
        <template v-if="kind === 'buttons' || kind === 'list'">
          <UFormGroup v-if="kind === 'list'" label="Texto del botón de la lista"><UInput v-model="d.button_label" size="sm" maxlength="20" /></UFormGroup>
          <div>
            <p class="text-sm font-medium mb-1">Opciones ({{ d.options.length }}/{{ kind === 'buttons' ? 3 : 10 }})</p>
            <div v-for="(o, i) in d.options" :key="o.id" class="flex gap-1 mb-1">
              <div class="flex-1 space-y-1">
                <UInput v-model="o.label" size="xs" :maxlength="kind === 'buttons' ? 20 : 24" placeholder="Texto" />
                <UInput v-if="kind === 'list'" v-model="o.description" size="xs" maxlength="72" placeholder="Descripción (opcional)" />
              </div>
              <UButton size="xs" color="red" variant="ghost" icon="i-heroicons-x-mark" @click="removeOption(i)" />
            </div>
            <UButton
              size="xs"
              variant="soft"
              icon="i-heroicons-plus"
              :disabled="d.options.length >= (kind === 'buttons' ? 3 : 10)"
              @click="d.options.push({ id: uid('o'), label: '', description: '' })"
            >
              Agregar opción
            </UButton>
          </div>
          <UFormGroup label="Guardar la opción elegida en (opcional)"><UInput v-model="d.variable" size="sm" placeholder="opcion" /></UFormGroup>
        </template>

        <!-- Pregunta -->
        <template v-if="kind === 'question'">
          <UFormGroup label="Guardar respuesta en" required><UInput v-model="d.variable" size="sm" /></UFormGroup>
          <UFormGroup label="Validación"><USelect v-model="d.validation" :options="VALIDATIONS" size="sm" /></UFormGroup>
          <UFormGroup v-if="d.validation === 'regex'" label="Expresión regular"><UInput v-model="d.pattern" size="sm" placeholder="^[0-9]{6,10}$" /></UFormGroup>
          <UFormGroup label="Mensaje si no es válido"><UInput v-model="d.error_text" size="sm" /></UFormGroup>
          <UFormGroup label="Intentos"><UInput v-model.number="d.max_retries" type="number" min="1" max="10" size="sm" /></UFormGroup>
        </template>

        <!-- Condición -->
        <template v-if="kind === 'condition'">
          <UFormGroup label="Se cumple si">
            <USelect v-model="d.match" :options="[{ label: 'Todas las reglas', value: 'all' }, { label: 'Alguna regla', value: 'any' }]" size="sm" />
          </UFormGroup>
          <div v-for="(r, i) in d.rules" :key="i" class="border rounded p-2 space-y-1">
            <UInput v-model="r.variable" size="xs" placeholder="variable (ej. solicitante.id)" />
            <USelect v-model="r.operator" :options="OPERATORS" size="xs" />
            <UInput v-if="!['empty','not_empty'].includes(r.operator)" v-model="r.value" size="xs" placeholder="valor" />
            <UButton size="xs" color="red" variant="link" @click="d.rules.splice(i, 1)">Quitar regla</UButton>
          </div>
          <UButton size="xs" variant="soft" icon="i-heroicons-plus" @click="d.rules.push({ variable: '', operator: 'equals', value: '' })">Agregar regla</UButton>
        </template>

        <!-- Horario -->
        <UFormGroup v-if="kind === 'business_hours'" label="Condición horaria" hint="Vacío: la del canal">
          <USelect v-model="d.time_condition_id" :options="timeConditionOptions" size="sm" />
        </UFormGroup>

        <!-- Asignar variable -->
        <template v-if="kind === 'set_variable'">
          <UFormGroup label="Variable"><UInput v-model="d.variable" size="sm" /></UFormGroup>
          <UFormGroup label="Valor" hint="Acepta {{variables}}"><UInput v-model="d.value" size="sm" /></UFormGroup>
        </template>

        <!-- Conector -->
        <template v-if="kind === 'connector'">
          <UFormGroup label="Conector" required>
            <USelect v-model="d.connector_id" :options="connectorOptions" size="sm" placeholder="Seleccione" />
          </UFormGroup>
          <UFormGroup label="Acción" required>
            <USelect v-model="d.action" :options="actionOptions" size="sm" placeholder="Seleccione" />
          </UFormGroup>
          <div v-if="currentAction">
            <p class="text-xs text-gray-500 mb-1">Parámetros (puede usar <code v-pre>{{variable}}</code>)</p>
            <UFormGroup v-for="inp in currentAction.inputs" :key="inp.name" :label="inp.label + (inp.required ? ' *' : '')" class="mb-1">
              <UInput v-model="d.inputs[inp.name]" size="xs" :placeholder="wrapVar(inp.name)" />
            </UFormGroup>
            <p v-if="currentAction.outputs" class="text-[11px] text-gray-400">Devuelve: {{ currentAction.outputs }}</p>
          </div>
          <UFormGroup label="Guardar resultado en"><UInput v-model="d.output_variable" size="sm" /></UFormGroup>
          <UFormGroup label="Resultado simulado (JSON)" hint="Solo para el simulador sin conexión">
            <UTextarea v-model="mockText" :rows="3" size="xs" class="font-mono" @blur="applyMock" />
          </UFormGroup>
        </template>

        <!-- Lista dinámica -->
        <template v-if="kind === 'dynamic_list'">
          <UFormGroup label="Variable con la lista" required><UInput v-model="d.source_variable" size="sm" placeholder="tickets" /></UFormGroup>
          <UFormGroup label="Texto de cada opción" hint="Campo o plantilla"><UInput v-model="d.label_field" size="sm" placeholder="#{{id}} {{title}}" /></UFormGroup>
          <UFormGroup label="Descripción (opcional)"><UInput v-model="d.description_field" size="sm" placeholder="{{status}}" /></UFormGroup>
          <UFormGroup label="Guardar el elemento elegido en" required><UInput v-model="d.variable" size="sm" /></UFormGroup>
          <UFormGroup label="Texto del botón"><UInput v-model="d.button_label" size="sm" maxlength="20" /></UFormGroup>
        </template>

        <!-- Asesor -->
        <template v-if="kind === 'handoff'">
          <UFormGroup label="Campaña / cola de destino" hint="Vacío: la del canal">
            <USelect v-model="d.campaign_id" :options="campaignOptions" size="sm" />
          </UFormGroup>
          <UFormGroup label="Nota para el asesor" hint="Acepta {{variables}}"><UTextarea v-model="d.note" :rows="2" size="sm" /></UFormGroup>
        </template>

        <div class="border-t pt-2">
          <p class="text-[11px] font-semibold text-gray-500 mb-1">Variables disponibles</p>
          <div class="flex flex-wrap gap-1">
            <UBadge v-for="v in variables" :key="v" color="gray" variant="soft" size="xs" class="cursor-pointer" @click="copyVar(v)">
              {{ wrapVar(v) }}
            </UBadge>
          </div>
        </div>
      </aside>

      <!-- Simulador -->
      <aside v-if="showSim" class="w-80 shrink-0 bg-gray-50 border-l flex flex-col">
        <div class="flex items-center justify-between px-3 py-2 border-b bg-white">
          <span class="font-semibold text-sm">Simulador</span>
          <div class="flex items-center gap-2">
            <UCheckbox v-if="isAdmin" v-model="sim.live" label="Conectores reales" />
            <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-arrow-path" title="Reiniciar" @click="restartSim" />
          </div>
        </div>
        <div ref="simBox" class="flex-1 overflow-y-auto p-3 space-y-2">
          <template v-for="(turn, ti) in sim.turns" :key="ti">
            <div v-if="turn.input !== null" class="flex justify-end">
              <span class="bg-primary-500 text-white text-sm rounded-lg px-3 py-1.5 max-w-[85%]">{{ turn.input }}</span>
            </div>
            <div v-for="(r, ri) in turn.replies" :key="ri" class="flex" :class="r.type === 'system' ? 'justify-center' : 'justify-start'">
              <span v-if="r.type === 'system'" class="text-[11px] text-gray-500 italic">{{ r.text }}</span>
              <div v-else class="bg-white border text-sm rounded-lg px-3 py-1.5 max-w-[85%] whitespace-pre-line">
                {{ r.text }}
                <div v-if="r.options" class="mt-2 space-y-1">
                  <div v-for="o in r.options" :key="o.id" class="text-xs text-primary-600 border-t pt-1">{{ o.label }}</div>
                </div>
              </div>
            </div>
          </template>
          <p v-if="sim.status === 'handed_off' || sim.status === 'completed'" class="text-center text-xs text-gray-500">
            Fin de la simulación
          </p>
        </div>
        <div class="border-t bg-white p-2 space-y-2">
          <div v-if="sim.options.length" class="flex flex-wrap gap-1">
            <UButton v-for="o in sim.options" :key="o.id" size="xs" variant="soft" @click="sendSim(o.label, o.id)">{{ o.label }}</UButton>
          </div>
          <form class="flex gap-1" @submit.prevent="sendSim(sim.text)">
            <UInput v-model="sim.text" size="sm" class="flex-1" placeholder="Escriba como el cliente…" :disabled="sim.loading" />
            <UButton type="submit" size="sm" icon="i-heroicons-paper-airplane" :loading="sim.loading" />
          </form>
          <details v-if="Object.keys(sim.variables).length" class="text-[11px]">
            <summary class="cursor-pointer text-gray-500">Variables</summary>
            <pre class="bg-gray-100 rounded p-1 overflow-x-auto">{{ JSON.stringify(sim.variables, null, 1) }}</pre>
          </details>
        </div>
      </aside>
    </div>

    <!-- Versiones -->
    <UModal v-model="versions.open">
      <UCard>
        <template #header><h3 class="font-semibold">Versiones publicadas</h3></template>
        <div v-if="!versions.items.length" class="text-sm text-gray-500">Aún no hay versiones publicadas.</div>
        <div v-for="v in versions.items" :key="v.id" class="flex items-center justify-between py-1 border-b text-sm">
          <div>
            <span class="font-medium">v{{ v.number }}</span>
            <span class="text-gray-500 ml-2">{{ new Date(v.created_at).toLocaleString() }}</span>
            <span v-if="v.created_by_name" class="text-gray-500"> · {{ v.created_by_name }}</span>
            <p v-if="v.notes" class="text-xs text-gray-500">{{ v.notes }}</p>
          </div>
          <UButton size="xs" color="gray" variant="outline" @click="restore(v.number)">Cargar en borrador</UButton>
        </div>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import BotNode from '~/components/bot/BotNode.vue'
import { BLOCKS, OPERATORS, PALETTE, VALIDATIONS, defaultData, flowVariables, fromFlow, toFlow, uid } from '~/utils/botBlocks'

definePageMeta({ middleware: ['auth'] })

const route = useRoute()
const http = useHttp()
const toast = useToast()
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'admin')
const { screenToFlowCoordinate, fitView } = useVueFlow('bot-designer')
// Devuelve "{{nombre}}" (armado por partes para no chocar con la sintaxis de plantillas de Vue)
const wrapVar = (v: string) => '{' + '{' + v + '}' + '}'

const flow = ref<any>({ name: '' })
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const start = ref('')
const selectedId = ref('')
const dirty = ref(false)
const loaded = ref(false)
const saving = ref(false)
const validating = ref(false)
const publishing = ref(false)
const errors = ref<string[]>([])
const catalog = ref<any>({ connectors: [] })
const campaigns = ref<any[]>([])
const timeConditions = ref<any[]>([])
const showSim = ref(false)

const selected = computed(() => nodes.value.find(n => n.id === selectedId.value))
const d = computed(() => selected.value?.data || {})
const kind = computed(() => d.value.kind)
const variables = computed(() => flowVariables(nodes.value))

const connectorOptions = computed(() => catalog.value.connectors.map((c: any) => ({ label: c.name, value: c.id })))
const currentConnector = computed(() => catalog.value.connectors.find((c: any) => c.id === Number(d.value.connector_id)))
const actionOptions = computed(() => (currentConnector.value?.actions || []).map((a: any) => ({ label: a.label, value: a.name })))
const currentAction = computed(() => currentConnector.value?.actions.find((a: any) => a.name === d.value.action))
const campaignOptions = computed(() => [{ label: '— La del canal —', value: null }, ...campaigns.value.map(c => ({ label: c.name, value: c.id }))])
const timeConditionOptions = computed(() => [{ label: '— Horario del canal —', value: null }, ...timeConditions.value.map(t => ({ label: t.name, value: t.id }))])

const markDirty = () => { if (loaded.value) dirty.value = true }
watch(() => nodes.value.map(n => n.data), markDirty, { deep: true })

// Resultado simulado del conector (editable como JSON)
const mockText = ref('')
watch(selectedId, () => { mockText.value = d.value.kind === 'connector' ? JSON.stringify(d.value.mock_result || {}, null, 1) : '' })
function applyMock() {
  try { d.value.mock_result = mockText.value.trim() ? JSON.parse(mockText.value) : {} } catch { toast.add({ title: 'JSON inválido', color: 'orange' }) }
}

function select(id: string) { selectedId.value = id }
function setStart() { start.value = selectedId.value; markDirty() }

function addBlock(k: string, position?: { x: number, y: number }) {
  const id = uid()
  const pos = position || { x: 80 + (nodes.value.length % 6) * 40, y: 80 + (nodes.value.length % 6) * 40 }
  nodes.value = [...nodes.value, { id, type: 'bot', position: pos, data: { kind: k, ...defaultData(k) } }]
  if (!start.value) start.value = id
  selectedId.value = id
  markDirty()
}
function onDragStart(e: DragEvent, k: string) { e.dataTransfer?.setData('application/bot-block', k) }
function onDrop(e: DragEvent) {
  const k = e.dataTransfer?.getData('application/bot-block')
  if (!k) return
  addBlock(k, screenToFlowCoordinate({ x: e.clientX, y: e.clientY }))
}
function onConnect(c: any) {
  // Cada salida va a un solo bloque: reemplaza la conexión anterior de esa salida
  edges.value = [
    ...edges.value.filter(e => !(e.source === c.source && (e.sourceHandle || 'next') === (c.sourceHandle || 'next'))),
    { id: uid('e'), source: c.source, target: c.target, sourceHandle: c.sourceHandle || 'next' },
  ]
  markDirty()
}
function removeSelected() {
  const id = selectedId.value
  nodes.value = nodes.value.filter(n => n.id !== id)
  edges.value = edges.value.filter(e => e.source !== id && e.target !== id)
  if (start.value === id) start.value = nodes.value[0]?.id || ''
  selectedId.value = ''
  markDirty()
}
function duplicate() {
  const n = selected.value
  if (!n) return
  const copy = JSON.parse(JSON.stringify(n.data))
  if (copy.options) copy.options = copy.options.map((o: any) => ({ ...o, id: uid('o') }))
  copy.title = `${copy.title} (copia)`
  const id = uid()
  nodes.value = [...nodes.value, { id, type: 'bot', position: { x: n.position.x + 40, y: n.position.y + 60 }, data: copy }]
  selectedId.value = id
}
function removeOption(i: number) {
  const opt = d.value.options[i]
  d.value.options.splice(i, 1)
  edges.value = edges.value.filter(e => !(e.source === selectedId.value && e.sourceHandle === `opt:${opt.id}`))
}
function copyVar(v: string) {
  navigator.clipboard?.writeText(wrapVar(v))
  toast.add({ title: `Copiado: ${wrapVar(v)}`, color: 'gray', timeout: 1500 })
}

const definition = () => fromFlow(nodes.value, edges.value, start.value)

async function load() {
  const data: any = await http.get(`/chatbot/flows/${route.params.id}/`)
  flow.value = data
  const f = toFlow(data.draft || {})
  nodes.value = f.nodes
  edges.value = f.edges
  start.value = f.start
  await nextTick()
  loaded.value = true
  dirty.value = false
  setTimeout(() => fitView(), 50)
}

async function save(silent = false) {
  saving.value = true
  try {
    flow.value = await http.patch(`/chatbot/flows/${route.params.id}/`, { name: flow.value.name, draft: definition() })
    dirty.value = false
    if (!silent) toast.add({ title: 'Borrador guardado', color: 'green' })
    return true
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar', description: http.errorMessage(e), color: 'red' })
    return false
  } finally { saving.value = false }
}

async function validate() {
  validating.value = true
  try {
    const r: any = await http.post(`/chatbot/flows/${route.params.id}/validate/`, { definition: definition() })
    errors.value = r.errors || []
    if (r.valid) toast.add({ title: 'El flujo es válido', color: 'green' })
  } finally { validating.value = false }
}

async function publish() {
  if (!(await save(true))) return
  const notes = prompt('Notas de esta versión (opcional):') ?? ''
  publishing.value = true
  try {
    const r: any = await http.post(`/chatbot/flows/${route.params.id}/publish/`, { notes })
    flow.value = r.flow
    errors.value = []
    toast.add({ title: `Versión ${r.version} publicada`, description: 'Las conversaciones nuevas usarán esta versión.', color: 'green' })
  } catch (e: any) {
    errors.value = e?.data?.errors || [http.errorMessage(e)]
  } finally { publishing.value = false }
}

const versions = reactive({ open: false, items: [] as any[] })
async function openVersions() {
  versions.items = await http.get(`/chatbot/flows/${route.params.id}/versions/`)
  versions.open = true
}
async function restore(n: number) {
  if (dirty.value && !confirm('Hay cambios sin guardar que se perderán. ¿Continuar?')) return
  await http.post(`/chatbot/flows/${route.params.id}/versions/${n}/restore/`)
  versions.open = false
  loaded.value = false
  await load()
  toast.add({ title: `Versión ${n} cargada en el borrador`, color: 'green' })
}

// ── Simulador ──
const simBox = ref<HTMLElement>()
const sim = reactive({ inputs: [] as any[], turns: [] as any[], options: [] as any[], variables: {} as any,
  status: '', text: '', loading: false, live: false })
async function runSim() {
  sim.loading = true
  try {
    const r: any = await http.post(`/chatbot/flows/${route.params.id}/simulate/`, {
      definition: definition(), inputs: sim.inputs, live: sim.live,
    })
    sim.turns = r.turns
    sim.options = r.options || []
    sim.variables = r.variables || {}
    sim.status = r.status
    await nextTick()
    simBox.value?.scrollTo({ top: simBox.value.scrollHeight })
  } catch (e: any) {
    toast.add({ title: 'Simulación', description: (e?.data?.errors || [http.errorMessage(e)]).join(' · '), color: 'red' })
  } finally { sim.loading = false }
}
function sendSim(text: string, replyId = '') {
  if (!text && !replyId) return
  sim.inputs.push(replyId ? { text, reply_id: replyId } : text)
  sim.text = ''
  runSim()
}
function restartSim() { sim.inputs = []; runSim() }
watch(showSim, (v) => { if (v) restartSim() })

onBeforeRouteLeave(() => {
  if (dirty.value && !confirm('Hay cambios sin guardar. ¿Salir de todas formas?')) return false
})

onMounted(async () => {
  const [cat, camps, tcs] = await Promise.allSettled([
    http.get('/chatbot/flows/catalog/'), http.get('/campaigns/', { page_size: 200 }), http.get('/telephony/time-conditions/'),
  ])
  if (cat.status === 'fulfilled') catalog.value = cat.value
  if (camps.status === 'fulfilled') campaigns.value = http.results(camps.value)
  if (tcs.status === 'fulfilled') timeConditions.value = http.results(tcs.value)
  await load()
})
</script>
