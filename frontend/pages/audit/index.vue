<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Auditoría de Gestiones</h1>
        <p class="text-sm text-gray-500 mt-1">Revisión de calificaciones de llamadas por agentes</p>
      </div>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <UCard v-for="card in summaryCards" :key="card.label">
        <div class="text-center">
          <p class="text-xs text-gray-500 uppercase tracking-wide">{{ card.label }}</p>
          <p class="text-3xl font-bold mt-1" :class="card.color">{{ card.value }}</p>
        </div>
      </UCard>
    </div>

    <!-- Filtros -->
    <UCard>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <UFormGroup label="Estado">
          <USelect v-model="filters.status" :options="statusOptions" placeholder="Todos" />
        </UFormGroup>
        <UFormGroup label="Agente">
          <USelect v-model="filters.agent" :options="agentOptions" placeholder="Todos" />
        </UFormGroup>
        <UFormGroup label="Campaña">
          <USelect v-model="filters.campaign" :options="campaignOptions" placeholder="Todas" />
        </UFormGroup>
        <UFormGroup label="&nbsp;">
          <UButton block @click="loadAudits">Filtrar</UButton>
        </UFormGroup>
      </div>
    </UCard>

    <!-- Tabla de auditorías -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h2 class="font-semibold text-gray-800">Registros</h2>
          <UBadge color="blue" variant="soft">{{ total }} registros</UBadge>
        </div>
      </template>
      <UTable
        :rows="audits"
        :columns="columns"
        :loading="loading"
        :empty-state="{ icon: 'i-heroicons-clipboard-document-check', label: 'Sin auditorías pendientes' }"
      >
        <template #status-data="{ row }">
          <UBadge :color="statusColor(row.status)" variant="soft" size="xs">
            {{ statusLabelText(row.status) }}
          </UBadge>
        </template>
        <template #quality_score-data="{ row }">
          <span v-if="row.quality_score !== null" class="font-semibold"
                :class="row.quality_score >= 80 ? 'text-green-600' : row.quality_score >= 60 ? 'text-yellow-600' : 'text-red-600'">
            {{ row.quality_score }}
          </span>
          <span v-else class="text-gray-400">—</span>
        </template>
        <template #created_at-data="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
        <template #actions-data="{ row }">
          <div class="flex gap-1">
            <UTooltip text="Ver detalle">
              <UButton icon="i-heroicons-eye" size="xs" color="gray" variant="ghost" @click="openDetail(row)" />
            </UTooltip>
            <UTooltip text="Aprobar">
              <UButton icon="i-heroicons-check" size="xs" color="green" variant="ghost"
                       :disabled="row.status !== 'pending'"
                       @click="approveAudit(row)" />
            </UTooltip>
            <UTooltip text="Rechazar">
              <UButton icon="i-heroicons-x-mark" size="xs" color="red" variant="ghost"
                       :disabled="row.status !== 'pending'"
                       @click="openRejectModal(row)" />
            </UTooltip>
            <UTooltip text="Corregir">
              <UButton icon="i-heroicons-pencil-square" size="xs" color="orange" variant="ghost"
                       :disabled="row.status !== 'pending'"
                       @click="openCorrectModal(row)" />
            </UTooltip>
          </div>
        </template>
      </UTable>

      <!-- Paginación -->
      <div class="flex justify-center mt-4">
        <UPagination v-model="page" :total="total" :page-count="pageSize" @change="loadAudits" />
      </div>
    </UCard>

    <!-- Modal rechazo -->
    <UModal v-model="rejectModal.open">
      <UCard>
        <template #header><h3 class="font-semibold">Rechazar gestión</h3></template>
        <div class="space-y-3">
          <p class="text-sm text-gray-600">Llamada <strong>{{ rejectModal.audit?.call_id }}</strong> — Agente: <strong>{{ rejectModal.audit?.agent_name }}</strong></p>
          <UFormGroup label="Motivo de rechazo *">
            <UTextarea v-model="rejectModal.notes" placeholder="Explica por qué se rechaza esta gestión..." rows="3" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="rejectModal.open = false">Cancelar</UButton>
            <UButton color="red" :loading="actionLoading" @click="submitReject">Rechazar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal corrección -->
    <UModal v-model="correctModal.open">
      <UCard>
        <template #header><h3 class="font-semibold">Corregir gestión</h3></template>
        <div class="space-y-3">
          <p class="text-sm text-gray-600">
            Calificación original: <strong>{{ correctModal.audit?.original_disposition_name }}</strong>
          </p>
          <UFormGroup label="Nueva calificación *">
            <USelect v-model="correctModal.dispositionId" :options="dispositionOptions" placeholder="Selecciona calificación" />
          </UFormGroup>
          <UFormGroup label="Puntuación de calidad (0-100)">
            <UInput v-model.number="correctModal.score" type="number" min="0" max="100" placeholder="85" />
          </UFormGroup>
          <UFormGroup label="Notas del supervisor">
            <UTextarea v-model="correctModal.notes" rows="2" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="correctModal.open = false">Cancelar</UButton>
            <UButton color="orange" :loading="actionLoading" @click="submitCorrect">Aplicar corrección</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal detalle (solo lectura) -->
    <UModal v-model="detailModal.open" :ui="{ width: 'max-w-2xl' }">
      <UCard v-if="detailModal.audit">
        <template #header><h3 class="font-semibold">Detalle de Auditoría</h3></template>
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div><span class="text-gray-500">ID Llamada</span><p class="font-medium">{{ detailModal.audit.call_id }}</p></div>
          <div><span class="text-gray-500">Agente</span><p class="font-medium">{{ detailModal.audit.agent_name }}</p></div>
          <div><span class="text-gray-500">Campaña</span><p class="font-medium">{{ detailModal.audit.campaign }}</p></div>
          <div><span class="text-gray-500">Estado</span>
            <UBadge :color="statusColor(detailModal.audit.status)" variant="soft" size="xs">
              {{ statusLabelText(detailModal.audit.status) }}
            </UBadge>
          </div>
          <div><span class="text-gray-500">Calificación original</span><p class="font-medium">{{ detailModal.audit.original_disposition_name }}</p></div>
          <div v-if="detailModal.audit.corrected_disposition_name">
            <span class="text-gray-500">Calificación corregida</span>
            <p class="font-medium text-orange-600">{{ detailModal.audit.corrected_disposition_name }}</p>
          </div>
          <div><span class="text-gray-500">Puntuación</span>
            <p class="font-semibold" :class="detailModal.audit.quality_score >= 80 ? 'text-green-600' : 'text-yellow-600'">
              {{ detailModal.audit.quality_score ?? '—' }}
            </p>
          </div>
          <div v-if="detailModal.audit.audited_by_name">
            <span class="text-gray-500">Auditado por</span><p class="font-medium">{{ detailModal.audit.audited_by_name }}</p>
          </div>
          <div class="col-span-2" v-if="detailModal.audit.agent_notes">
            <span class="text-gray-500">Notas del agente</span><p class="mt-1">{{ detailModal.audit.agent_notes }}</p>
          </div>
          <div class="col-span-2" v-if="detailModal.audit.supervisor_notes">
            <span class="text-gray-500">Notas del supervisor</span>
            <p class="mt-1 text-orange-700">{{ detailModal.audit.supervisor_notes }}</p>
          </div>
        </div>
        <template #footer>
          <UButton color="gray" variant="ghost" @click="detailModal.open = false">Cerrar</UButton>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'], layout: 'default' })

const loading = ref(false)
const actionLoading = ref(false)
const audits = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const summary = ref<any>({})

const filters = ref({ status: '', agent: '', campaign: '' })
const rejectModal = ref({ open: false, audit: null as any, notes: '' })
const correctModal = ref({ open: false, audit: null as any, dispositionId: '', score: null as number | null, notes: '' })
const detailModal = ref({ open: false, audit: null as any })

const agentOptions = ref<any[]>([])
const campaignOptions = ref<any[]>([])
const dispositionOptions = ref<any[]>([])

const statusOptions = [
  { label: 'Todos', value: '' },
  { label: 'Pendientes', value: 'pending' },
  { label: 'Aprobados', value: 'approved' },
  { label: 'Rechazados', value: 'rejected' },
  { label: 'Corregidos', value: 'corrected' },
]

const columns = [
  { key: 'call_id', label: 'Llamada' },
  { key: 'agent_name', label: 'Agente' },
  { key: 'original_disposition_name', label: 'Calificación' },
  { key: 'status', label: 'Estado' },
  { key: 'quality_score', label: 'Puntuación' },
  { key: 'created_at', label: 'Fecha' },
  { key: 'actions', label: '' },
]

const summaryCards = computed(() => [
  { label: 'Total', value: summary.value.total ?? 0, color: 'text-gray-900' },
  { label: 'Pendientes', value: summary.value.pending ?? 0, color: 'text-yellow-600' },
  { label: 'Aprobadas', value: summary.value.by_status?.approved ?? 0, color: 'text-green-600' },
  { label: 'Puntuación media', value: summary.value.avg_quality_score ? `${summary.value.avg_quality_score}` : '—', color: 'text-blue-600' },
])

const statusColor = (s: string) => ({ pending: 'yellow', approved: 'green', rejected: 'red', corrected: 'orange' })[s] ?? 'gray'
const statusLabelText = (s: string) => ({ pending: 'Pendiente', approved: 'Aprobado', rejected: 'Rechazado', corrected: 'Corregido' })[s] ?? s
const formatDate = (d: string) => new Date(d).toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' })

function authHeaders() {
  const token = process.client ? localStorage.getItem('auth_token') : null
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function loadAudits() {
  loading.value = true
  try {
    const params = new URLSearchParams({ page: String(page.value), page_size: String(pageSize) })
    if (filters.value.status) params.set('status', filters.value.status)
    if (filters.value.agent) params.set('agent', filters.value.agent)
    if (filters.value.campaign) params.set('campaign', filters.value.campaign)

    const [res, sum] = await Promise.all([
      $fetch(`/api/audits/?${params}`, { headers: authHeaders() }) as any,
      $fetch('/api/audits/summary/', { headers: authHeaders() }) as any,
    ])
    audits.value = res.results ?? res
    total.value = res.count ?? audits.value.length
    summary.value = sum
  } catch {
    useToast().add({ title: 'Error cargando auditorías', color: 'red' })
  } finally {
    loading.value = false
  }
}

async function approveAudit(audit: any) {
  try {
    await $fetch(`/api/audits/${audit.id}/approve/`, { method: 'POST', headers: authHeaders() })
    useToast().add({ title: 'Gestión aprobada', color: 'green' })
    await loadAudits()
  } catch (e: any) {
    useToast().add({ title: e.data?.error ?? 'Error', color: 'red' })
  }
}

function openRejectModal(audit: any) {
  rejectModal.value = { open: true, audit, notes: '' }
}

async function submitReject() {
  if (!rejectModal.value.notes.trim()) return
  actionLoading.value = true
  try {
    await $fetch(`/api/audits/${rejectModal.value.audit.id}/reject/`, {
      method: 'POST', headers: authHeaders(),
      body: { notes: rejectModal.value.notes },
    })
    useToast().add({ title: 'Gestión rechazada', color: 'orange' })
    rejectModal.value.open = false
    await loadAudits()
  } catch (e: any) {
    useToast().add({ title: e.data?.error ?? 'Error', color: 'red' })
  } finally {
    actionLoading.value = false
  }
}

function openCorrectModal(audit: any) {
  correctModal.value = { open: true, audit, dispositionId: '', score: null, notes: '' }
  // Cargar calificaciones de la campaña si no están
  if (!dispositionOptions.value.length) loadDispositions(audit.campaign)
}

async function loadDispositions(campaignId: number) {
  try {
    const res = await $fetch(`/api/campaigns/${campaignId}/dispositions/`, { headers: authHeaders() }) as any[]
    dispositionOptions.value = res.map((d: any) => ({ label: d.name, value: d.id }))
  } catch {}
}

async function submitCorrect() {
  if (!correctModal.value.dispositionId) return
  actionLoading.value = true
  try {
    await $fetch(`/api/audits/${correctModal.value.audit.id}/correct/`, {
      method: 'POST', headers: authHeaders(),
      body: {
        corrected_disposition_id: correctModal.value.dispositionId,
        quality_score: correctModal.value.score,
        notes: correctModal.value.notes,
      },
    })
    useToast().add({ title: 'Gestión corregida', color: 'orange' })
    correctModal.value.open = false
    await loadAudits()
  } catch (e: any) {
    useToast().add({ title: e.data?.error ?? 'Error', color: 'red' })
  } finally {
    actionLoading.value = false
  }
}

function openDetail(audit: any) {
  detailModal.value = { open: true, audit }
}

onMounted(loadAudits)
</script>
