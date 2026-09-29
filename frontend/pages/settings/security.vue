<template>
  <div class="space-y-6">
    <section class="rounded-2xl p-6 text-white sec-hero">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="flex items-start gap-4">
          <div class="w-14 h-14 rounded-2xl bg-white/10 ring-1 ring-white/20 flex items-center justify-center">
            <UIcon name="i-heroicons-shield-check" class="w-8 h-8" />
          </div>
          <div>
            <p class="text-xs uppercase tracking-widest text-slate-300">Telefonía</p>
            <h1 class="text-2xl font-bold">Seguridad y antifraude</h1>
            <p class="text-sm text-slate-300 mt-1 max-w-2xl">
              Controla a dónde se puede llamar y cuántas llamadas simultáneas salen por cada troncal.
              Aplica a todas las llamadas salientes: agentes, click-to-call, callbacks, conferencias y marcador automático.
            </p>
          </div>
        </div>
        <UButton icon="i-heroicons-arrow-path" color="white" variant="ghost" class="text-white hover:bg-white/10" :loading="loading" @click="loadAll">Actualizar</UButton>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
        <div v-for="k in kpis" :key="k.label" class="rounded-xl bg-white/5 ring-1 ring-white/10 px-4 py-3">
          <p class="text-[11px] uppercase tracking-wide text-slate-300">{{ k.label }}</p>
          <p class="text-2xl font-bold" :class="k.color">{{ k.value }}</p>
        </div>
      </div>
    </section>

    <div v-if="form" class="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <div class="xl:col-span-2 space-y-6">
        <!-- Destinos -->
        <section class="rounded-2xl border border-gray-200 bg-white p-5 space-y-4">
          <header>
            <h2 class="font-semibold text-gray-900">Destinos permitidos</h2>
            <p class="text-xs text-gray-500">Las llamadas bloqueadas escuchan "servicio no disponible" y quedan registradas.</p>
          </header>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="rounded-xl border border-gray-200 p-3 space-y-2">
              <UToggle v-model="form.block_international" aria-label="Bloquear internacionales" />
              <p class="text-sm font-medium">Bloquear llamadas internacionales</p>
              <p class="text-xs text-gray-500">Números que empiezan por <code>00</code> o por <code>+</code> con un indicativo distinto al del país.</p>
              <UFormGroup label="Indicativo del país">
                <UInput v-model="form.home_country_code" class="w-24" placeholder="57" />
              </UFormGroup>
            </div>
            <UFormGroup label="Longitud máxima del número" hint="0 = sin límite">
              <UInput v-model.number="form.max_number_length" type="number" min="0" max="20" class="w-28" />
            </UFormGroup>
            <UFormGroup label="Prefijos bloqueados" hint="Uno por línea" help="Tarifas especiales (01900), satelitales, países de alto fraude…">
              <UTextarea v-model="form.blocked_prefixes" :rows="5" class="font-mono text-sm" />
            </UFormGroup>
            <UFormGroup label="Lista blanca (opcional)" hint="Uno por línea" help="Si la llenas, SOLO se podrá llamar a números que empiecen así (ej: 3, 60, 57, 01800).">
              <UTextarea v-model="form.allowed_prefixes" :rows="5" class="font-mono text-sm" placeholder="3&#10;60&#10;57&#10;01800" />
            </UFormGroup>
          </div>
        </section>

        <!-- Capacidad -->
        <section class="rounded-2xl border border-gray-200 bg-white p-5 space-y-4">
          <header>
            <h2 class="font-semibold text-gray-900">Límites de uso</h2>
            <p class="text-xs text-gray-500">Evitan que una cuenta comprometida o un error de configuración genere cientos de llamadas.</p>
          </header>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="rounded-xl border border-gray-200 p-3 space-y-2">
              <UToggle v-model="form.enforce_trunk_channels" aria-label="Respetar canales por troncal" />
              <p class="text-sm font-medium">Canales máximos por troncal</p>
              <p class="text-xs text-gray-500">Usa el valor "Canales" de cada troncal. Llamada extra → "todos los circuitos ocupados".</p>
            </div>
            <UFormGroup label="Llamadas salientes simultáneas (total)" hint="0 = sin límite">
              <UInput v-model.number="form.max_concurrent_outbound" type="number" min="0" />
            </UFormGroup>
            <UFormGroup label="Llamadas por extensión por hora" hint="0 = sin límite">
              <UInput v-model.number="form.max_calls_per_extension_hour" type="number" min="0" />
            </UFormGroup>
          </div>
        </section>

        <!-- Alertas -->
        <section class="rounded-2xl border border-gray-200 bg-white p-5 space-y-4">
          <header>
            <h2 class="font-semibold text-gray-900">Alertas</h2>
            <p class="text-xs text-gray-500">Se revisan cada 2 minutos. Cada tipo de alerta se envía como máximo cada 30 minutos.</p>
          </header>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <UFormGroup label="Llamadas salientes en 10 min" hint="0 = desactivada">
              <UInput v-model.number="form.alert_calls_per_10min" type="number" min="0" />
            </UFormGroup>
            <UFormGroup label="Internacionales por hora" hint="0 = desactivada">
              <UInput v-model.number="form.alert_international_per_hour" type="number" min="0" />
            </UFormGroup>
            <UFormGroup label="Intentos bloqueados en 10 min" hint="0 = desactivada">
              <UInput v-model.number="form.alert_blocked_per_10min" type="number" min="0" />
            </UFormGroup>
          </div>
          <UFormGroup label="Correos de alerta" hint="Uno por línea" help="Vacío = administradores activos con email. Requiere EMAIL_HOST configurado en el servidor.">
            <UTextarea v-model="form.alert_emails" :rows="2" placeholder="seguridad@tuempresa.com" />
          </UFormGroup>
        </section>

        <div class="flex items-center justify-between gap-3 sticky bottom-0 bg-white/90 backdrop-blur py-3">
          <p class="text-xs text-gray-500">
            Última actualización: {{ form.updated_at ? new Date(form.updated_at).toLocaleString('es-CO') : '—' }}
            <span v-if="form.updated_by_name"> · {{ form.updated_by_name }}</span>
          </p>
          <UButton icon="i-heroicons-check" :loading="saving" @click="save">Guardar y aplicar</UButton>
        </div>
      </div>

      <!-- Columna lateral -->
      <div class="space-y-6">
        <section class="rounded-2xl border border-gray-200 bg-white p-5 space-y-3">
          <h2 class="font-semibold text-gray-900">Probar un número</h2>
          <p class="text-xs text-gray-500">Verifica con la política guardada si una llamada saldría o sería bloqueada.</p>
          <div class="flex gap-2">
            <UInput v-model="testNumber" placeholder="+34912345678" class="flex-1" @keyup.enter="runTest" />
            <UButton :loading="testing" :disabled="!testNumber.trim()" @click="runTest">Probar</UButton>
          </div>
          <div v-if="testResult" class="rounded-xl p-3 text-sm flex items-center gap-2"
               :class="testResult.allowed ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800'" role="status">
            <UIcon :name="testResult.allowed ? 'i-heroicons-check-circle' : 'i-heroicons-no-symbol'" class="w-5 h-5" />
            {{ testResult.allowed ? 'Permitida' : `Bloqueada: ${testResult.reason_label}` }}
          </div>
        </section>

        <section class="rounded-2xl border border-gray-200 bg-white p-5 space-y-3">
          <h2 class="font-semibold text-gray-900">Protección de la red SIP</h2>
          <ul class="space-y-2 text-sm text-gray-600">
            <li v-for="item in networkProtections" :key="item" class="flex gap-2">
              <UIcon name="i-heroicons-check-circle" class="w-5 h-5 text-emerald-500 flex-shrink-0" />
              <span>{{ item }}</span>
            </li>
          </ul>
        </section>
      </div>
    </div>

    <!-- Eventos -->
    <section class="rounded-2xl border border-gray-200 bg-white overflow-hidden">
      <header class="flex flex-wrap items-center gap-3 px-5 py-4 border-b border-gray-100">
        <h2 class="font-semibold text-gray-900">Eventos de seguridad</h2>
        <USelect v-model="filters.event_type" size="sm" class="w-60" :options="eventTypeOptions" @change="loadEvents" />
        <USelect v-model="filters.days" size="sm" class="w-36" :options="[{ label: 'Últimas 24 h', value: 1 }, { label: '7 días', value: 7 }, { label: '30 días', value: 30 }]" @change="loadEvents" />
      </header>
      <UTable :rows="events" :columns="eventColumns" :loading="loadingEvents"
              :empty-state="{ icon: 'i-heroicons-shield-check', label: 'Sin eventos en el período' }">
        <template #created_at-data="{ row }"><span class="text-xs whitespace-nowrap">{{ new Date(row.created_at).toLocaleString('es-CO') }}</span></template>
        <template #event_type_display-data="{ row }">
          <span class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium" :class="severityClass(row.severity)">
            <span class="w-1.5 h-1.5 rounded-full" :class="severityDot(row.severity)" />{{ row.event_type_display }}
          </span>
        </template>
        <template #number-data="{ row }"><span class="font-mono text-xs">{{ row.number || '—' }}</span></template>
        <template #detail-data="{ row }"><p class="text-xs text-gray-600 max-w-md whitespace-pre-line line-clamp-2" :title="row.detail">{{ row.detail }}</p></template>
      </UTable>
      <div v-if="eventsTotal > events.length" class="flex justify-center py-3">
        <UPagination v-model="page" :page-count="50" :total="eventsTotal" @update:model-value="loadEvents" />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
useHead({ title: 'Seguridad y antifraude - VozipOmni' })

const http = useHttp()
const toast = useToast()

const form = ref<any>(null)
const summary = ref<any>(null)
const events = ref<any[]>([])
const eventsTotal = ref(0)
const page = ref(1)
const loading = ref(false)
const loadingEvents = ref(false)
const saving = ref(false)
const testNumber = ref('')
const testing = ref(false)
const testResult = ref<any>(null)
const filters = reactive({ event_type: '', days: 7 })

const eventTypeOptions = [
  { label: 'Todos los eventos', value: '' },
  { label: 'Internacional bloqueada', value: 'international' },
  { label: 'Prefijo bloqueado', value: 'blocked_prefix' },
  { label: 'Fuera de la lista blanca', value: 'not_allowed' },
  { label: 'Troncal sin canales', value: 'trunk_full' },
  { label: 'Límite total', value: 'global_limit' },
  { label: 'Límite por extensión', value: 'extension_rate' },
  { label: 'Bloqueada en el marcador', value: 'dialer_blocked' },
  { label: 'Alerta: pico de llamadas', value: 'alert_spike' },
  { label: 'Alerta: internacionales', value: 'alert_international' },
  { label: 'Alerta: muchos bloqueos', value: 'alert_blocked' },
]
const eventColumns = [
  { key: 'created_at', label: 'Fecha' }, { key: 'event_type_display', label: 'Evento' },
  { key: 'number', label: 'Número' }, { key: 'trunk', label: 'Troncal' },
  { key: 'source', label: 'Origen' }, { key: 'detail', label: 'Detalle' },
]
const networkProtections = [
  'Kamailio solo acepta llamadas y registros desde el WebSocket de la plataforma, Asterisk o este servidor; cualquier otra IP recibe 403 y queda bloqueada 1 hora.',
  'El WebSocket SIP exige un ticket firmado de una sesión activa: sin usuario en VozipOmni no se puede registrar ni marcar.',
  'Escáneres SIP conocidos (sipvicious, sipcli…) e inundaciones de peticiones se bloquean automáticamente.',
  'TURN con credenciales temporales por agente; solo retransmite audio hacia este servidor.',
]

const kpis = computed(() => {
  const s = summary.value || {}
  return [
    { label: 'Salientes 24 h', value: s.outbound_24h ?? '—', color: 'text-white' },
    { label: 'Internacionales 24 h', value: s.international_24h ?? '—', color: s.international_24h ? 'text-amber-300' : 'text-white' },
    { label: 'Eventos 24 h', value: s.events_24h ?? '—', color: 'text-white' },
    { label: 'Críticos 24 h', value: s.critical_24h ?? '—', color: s.critical_24h ? 'text-red-300' : 'text-emerald-300' },
  ]
})

const severityClass = (s: string) => ({ critical: 'bg-red-50 text-red-700', warning: 'bg-amber-50 text-amber-700' } as any)[s] || 'bg-gray-100 text-gray-600'
const severityDot = (s: string) => ({ critical: 'bg-red-500', warning: 'bg-amber-500' } as any)[s] || 'bg-gray-400'

async function loadPolicy() {
  form.value = await http.get('/telephony/security/policy/')
}
async function loadSummary() {
  try { summary.value = await http.get('/telephony/security/summary/') } catch { /* opcional */ }
}
async function loadEvents() {
  loadingEvents.value = true
  try {
    const q: any = { page: page.value, days: filters.days }
    if (filters.event_type) q.event_type = filters.event_type
    const data: any = await http.get('/telephony/security/events/', q)
    events.value = http.results(data)
    eventsTotal.value = data?.count ?? events.value.length
  } finally { loadingEvents.value = false }
}
async function loadAll() {
  loading.value = true
  try { await Promise.all([loadPolicy(), loadSummary(), loadEvents()]) }
  catch (e: any) { toast.add({ title: 'Error cargando la política', description: http.errorMessage(e), color: 'red' }) }
  finally { loading.value = false }
}

async function save() {
  saving.value = true
  try {
    const { updated_at, updated_by_name, blocked_list, allowed_list, apply_result, ...body } = form.value
    const res: any = await http.put('/telephony/security/policy/', body)
    form.value = res
    const r = res.apply_result || {}
    toast.add({
      title: r.reloaded ? 'Política aplicada' : 'Política guardada',
      description: r.reloaded ? 'Asterisk recargó el dialplan con las nuevas reglas.'
        : 'No se pudo recargar Asterisk ahora; se aplicará en la próxima sincronización.',
      color: r.reloaded ? 'green' : 'amber',
    })
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar', description: http.errorMessage(e), color: 'red' })
  } finally { saving.value = false }
}

async function runTest() {
  testing.value = true
  try { testResult.value = await http.post('/telephony/security/policy/test/', { number: testNumber.value }) }
  catch (e: any) { toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' }) }
  finally { testing.value = false }
}

onMounted(loadAll)
</script>

<style scoped>
.sec-hero {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #334155 100%);
}
</style>
