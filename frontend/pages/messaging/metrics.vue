<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Métricas de chat</h1>
        <p class="text-sm text-gray-500 mt-1">Tiempo de primera respuesta, tiempo de atención y productividad por agente en todos los canales.</p>
      </div>
      <div class="flex gap-2">
        <UButton icon="i-heroicons-arrow-down-tray" color="gray" variant="outline" :loading="exporting" @click="exportXlsx">Exportar detalle</UButton>
        <UButton icon="i-heroicons-arrow-left" color="gray" variant="ghost" to="/messaging">Bandeja</UButton>
      </div>
    </div>

    <UCard>
      <div class="flex flex-wrap items-end gap-3">
        <UFormGroup label="Desde"><UInput v-model="f.date_from" type="date" /></UFormGroup>
        <UFormGroup label="Hasta"><UInput v-model="f.date_to" type="date" /></UFormGroup>
        <UFormGroup label="Canal"><USelect v-model="f.channel_type" :options="channelOptions" class="w-44" /></UFormGroup>
        <UFormGroup label="Campaña"><USelect v-model="f.campaign" :options="[{ label: 'Todas', value: '' }, ...campaignOptions]" class="w-52" /></UFormGroup>
        <UFormGroup label="SLA primera respuesta" hint="minutos"><UInput v-model.number="f.sla_minutes" type="number" min="1" class="w-24" /></UFormGroup>
        <UButton icon="i-heroicons-funnel" :loading="loading" @click="load">Aplicar</UButton>
      </div>
    </UCard>

    <div v-if="data" class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
      <UCard v-for="k in kpis" :key="k.label" :ui="{ body: { padding: 'p-3 sm:p-3' } }">
        <p class="text-xs text-gray-500">{{ k.label }}</p>
        <p class="text-xl font-bold" :class="k.color">{{ k.value }}</p>
      </UCard>
    </div>

    <div v-if="data" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <UCard class="lg:col-span-2">
        <template #header><h3 class="font-semibold">Por agente</h3></template>
        <UTable :rows="data.by_agent" :columns="agentColumns" :empty-state="{ icon: 'i-heroicons-user-group', label: 'Sin conversaciones asignadas' }">
          <template #avg_first_response-data="{ row }">
            <span :class="slaClass(row.avg_first_response)">{{ formatSeconds(row.avg_first_response) }}</span>
          </template>
          <template #avg_handle_time-data="{ row }">{{ formatSeconds(row.avg_handle_time) }}</template>
          <template #closed-data="{ row }">{{ row.closed }} <span class="text-xs text-gray-400">({{ pct(row.closed, row.conversations) }})</span></template>
        </UTable>
      </UCard>

      <div class="space-y-6">
        <UCard>
          <template #header><h3 class="font-semibold">Por canal</h3></template>
          <div class="space-y-2">
            <div v-for="c in data.by_channel" :key="c.channel_type" class="flex items-center gap-2 text-sm">
              <UIcon :name="channelMeta(c.channel_type).icon" class="w-4 h-4" :class="channelMeta(c.channel_type).color" />
              <span class="flex-1">{{ channelMeta(c.channel_type).label }}</span>
              <span class="font-semibold">{{ c.conversations }}</span>
            </div>
            <p v-if="!data.by_channel.length" class="text-sm text-gray-400">Sin datos</p>
          </div>
        </UCard>
        <UCard>
          <template #header><h3 class="font-semibold">Tipificaciones</h3></template>
          <div class="space-y-2">
            <div v-for="d in data.by_disposition" :key="d.disposition" class="text-sm">
              <div class="flex justify-between"><span>{{ d.disposition }} <UBadge v-if="d.is_success" size="xs" color="green" variant="soft">Éxito</UBadge></span><span class="font-semibold">{{ d.count }}</span></div>
              <UProgress :value="d.count" :max="maxDisposition" size="xs" :color="d.is_success ? 'green' : 'gray'" />
            </div>
            <p v-if="!data.by_disposition.length" class="text-sm text-gray-400">Sin conversaciones tipificadas</p>
          </div>
        </UCard>
        <UCard>
          <template #header><h3 class="font-semibold">Etiquetas</h3></template>
          <div class="flex flex-wrap gap-2">
            <UBadge v-for="t in data.by_tag" :key="t.tag" :color="t.color || 'gray'" variant="soft">{{ t.tag }} · {{ t.count }}</UBadge>
            <p v-if="!data.by_tag.length" class="text-sm text-gray-400">Sin etiquetas</p>
          </div>
        </UCard>
      </div>
    </div>

    <UCard v-if="data">
      <template #header><h3 class="font-semibold">Evolución diaria</h3></template>
      <div v-if="data.daily.length" class="flex items-end gap-1 h-40" role="img" aria-label="Conversaciones por día">
        <div v-for="d in data.daily" :key="d.date" class="flex-1 flex flex-col items-center justify-end h-full group"
             :title="`${d.date}: ${d.conversations} conversaciones, ${d.closed} cerradas, 1ª respuesta ${formatSeconds(d.avg_first_response)}`">
          <span class="text-[10px] text-gray-500 opacity-0 group-hover:opacity-100">{{ d.conversations }}</span>
          <div class="w-full rounded-t bg-primary-500" :style="{ height: `${Math.max(2, d.conversations / maxDaily * 100)}%` }" />
          <span class="text-[10px] text-gray-400 mt-1">{{ d.date.slice(5) }}</span>
        </div>
      </div>
      <p v-else class="text-sm text-gray-400">Sin datos en el período</p>
    </UCard>
  </div>
</template>

<script setup lang="ts">
import { CHANNEL_FILTER_OPTIONS, channelMeta, formatSeconds } from '~/utils/channels'

useHead({ title: 'Métricas de chat - VozipOmni' })

const http = useHttp()
const toast = useToast()
const channelOptions = CHANNEL_FILTER_OPTIONS
const iso = (d: Date) => d.toISOString().slice(0, 10)

const f = reactive({
  date_from: iso(new Date(Date.now() - 6 * 86400000)), date_to: iso(new Date()),
  channel_type: '', campaign: '', sla_minutes: 5,
})
const data = ref<any>(null)
const loading = ref(false)
const exporting = ref(false)
const campaignOptions = ref<any[]>([])

const agentColumns = [
  { key: 'name', label: 'Agente' }, { key: 'conversations', label: 'Conversaciones' },
  { key: 'closed', label: 'Cerradas' }, { key: 'avg_first_response', label: '1ª respuesta prom.' },
  { key: 'avg_handle_time', label: 'Atención prom.' }, { key: 'messages_sent', label: 'Mensajes enviados' },
]

const pct = (a: number, b: number) => b ? `${Math.round(a / b * 100)}%` : '0%'
const slaClass = (s: number | null) => s == null ? '' : (s <= f.sla_minutes * 60 ? 'text-green-600' : 'text-red-600')
const maxDaily = computed(() => Math.max(1, ...(data.value?.daily || []).map((d: any) => d.conversations)))
const maxDisposition = computed(() => Math.max(1, ...(data.value?.by_disposition || []).map((d: any) => d.count)))

const kpis = computed(() => {
  const d = data.value
  if (!d) return []
  return [
    { label: 'Conversaciones', value: d.total_conversations, color: 'text-gray-900' },
    { label: 'Cerradas', value: d.closed_conversations, color: 'text-green-600' },
    { label: 'Abiertas', value: d.open_conversations, color: 'text-amber-600' },
    { label: 'Sin asignar', value: d.unassigned, color: d.unassigned ? 'text-red-600' : 'text-gray-500' },
    { label: '1ª respuesta prom.', value: formatSeconds(d.avg_first_response), color: slaClass(d.avg_first_response) || 'text-gray-900' },
    { label: `En SLA (≤ ${d.sla_minutes} min)`, value: d.sla_pct == null ? '—' : `${d.sla_pct}%`, color: 'text-sky-600' },
    { label: 'Atención prom.', value: formatSeconds(d.avg_handle_time), color: 'text-gray-900' },
    { label: 'Mensajes in / out', value: `${d.messages_inbound} / ${d.messages_outbound}`, color: 'text-gray-700' },
  ]
})

function query() {
  const q: Record<string, any> = { date_from: f.date_from, date_to: f.date_to, sla_minutes: f.sla_minutes || 5 }
  if (f.channel_type) q.channel_type = f.channel_type
  if (f.campaign) q.campaign = f.campaign
  return q
}

async function load() {
  loading.value = true
  try { data.value = await http.get('/messaging/metrics/', query()) }
  catch (e: any) { toast.add({ title: 'Error cargando métricas', description: http.errorMessage(e), color: 'red' }) }
  finally { loading.value = false }
}

async function exportXlsx() {
  exporting.value = true
  try {
    const q: Record<string, any> = { dataset: 'chats', format: 'xlsx', period: 'custom', start_date: f.date_from, end_date: f.date_to }
    if (f.channel_type) q.channel_type = f.channel_type
    if (f.campaign) q.campaign = f.campaign
    await http.download('/reports/export/', q, `conversaciones_${f.date_from}_${f.date_to}.xlsx`)
  } catch (e: any) {
    toast.add({ title: 'No se pudo exportar', description: await http.blobErrorMessage(e), color: 'red' })
  } finally { exporting.value = false }
}

onMounted(async () => {
  load()
  try {
    campaignOptions.value = http.results(await http.get('/campaigns/')).map((c: any) => ({ label: c.name, value: String(c.id) }))
  } catch { /* opcional */ }
})
</script>
