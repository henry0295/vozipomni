<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Tipificaciones de llamada</h1>
        <p class="text-sm text-gray-500">
          Opciones con las que el agente califica cada llamada. Se configuran por campaña.
        </p>
      </div>
      <UButton v-if="campaignId" icon="i-heroicons-plus" @click="openDisp()">Nueva tipificación</UButton>
    </div>

    <UCard>
      <div class="flex flex-wrap gap-4 items-end">
        <UFormGroup label="Campaña" class="w-80">
          <USelect
            v-model="campaignId"
            :options="campaignOptions"
            placeholder="Selecciona una campaña"
            @change="onCampaignChange"
          />
        </UFormGroup>
        <UFormGroup v-if="campaignId" label="Buscar" class="w-64">
          <UInput v-model="search" icon="i-heroicons-magnifying-glass" placeholder="Código o nombre" />
        </UFormGroup>
        <UButton
          v-if="campaignId"
          color="gray"
          variant="outline"
          icon="i-heroicons-document-duplicate"
          @click="copy.open = true"
        >
          Copiar de otra campaña
        </UButton>
      </div>
    </UCard>

    <UCard v-if="!campaignId">
      <div class="text-center text-gray-500 py-8">
        <UIcon name="i-heroicons-tag" class="w-10 h-10 mx-auto mb-2" />
        Selecciona una campaña para ver y editar sus tipificaciones.
      </div>
    </UCard>

    <UCard v-else>
      <UTable
        :rows="filtered"
        :columns="columns"
        :loading="loading"
        :empty-state="{ icon: 'i-heroicons-tag', label: 'Esta campaña no tiene tipificaciones' }"
      >
        <template #is_success-data="{ row }">
          <UBadge :color="row.is_success ? 'green' : 'gray'" variant="soft">
            {{ row.is_success ? 'Éxito' : 'No éxito' }}
          </UBadge>
        </template>
        <template #requires_callback-data="{ row }">
          <UBadge v-if="row.requires_callback" color="orange" variant="soft">Rellamada</UBadge>
          <span v-else class="text-gray-400">—</span>
        </template>
        <template #form-data="{ row }">{{ row.form?.name || '—' }}</template>
        <template #actions-data="{ row }">
          <div class="flex gap-1 justify-end">
            <UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost" @click="openDisp(row)" />
            <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost" @click="deleteDisp(row)" />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Crear / editar -->
    <UModal v-model="disp.open">
      <UCard>
        <template #header>
          <h3 class="font-semibold">{{ disp.id ? 'Editar tipificación' : 'Nueva tipificación' }}</h3>
        </template>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Código" required hint="Único en la campaña">
              <UInput v-model="disp.code" placeholder="VENTA" @update:model-value="disp.code = String($event).toUpperCase()" />
            </UFormGroup>
            <UFormGroup label="Orden">
              <UInput v-model.number="disp.order" type="number" min="0" />
            </UFormGroup>
          </div>
          <UFormGroup label="Nombre" required>
            <UInput v-model="disp.name" placeholder="Venta concretada" />
          </UFormGroup>
          <UFormGroup label="Descripción">
            <UTextarea v-model="disp.description" :rows="2" />
          </UFormGroup>
          <UFormGroup label="Formulario específico (opcional)" hint="Reemplaza el formulario de la campaña">
            <USelect v-model="disp.form_id" :options="formOptions" />
          </UFormGroup>
          <div class="flex gap-6">
            <UCheckbox v-model="disp.is_success" label="Cuenta como éxito" />
            <UCheckbox v-model="disp.requires_callback" label="Requiere rellamada" />
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="disp.open = false">Cancelar</UButton>
            <UButton :loading="disp.saving" @click="saveDisp">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Copiar de otra campaña -->
    <UModal v-model="copy.open">
      <UCard>
        <template #header><h3 class="font-semibold">Copiar tipificaciones</h3></template>
        <div class="space-y-3">
          <p class="text-sm text-gray-500">
            Se copian a la campaña actual las tipificaciones de la campaña elegida.
            Las que ya existen con el mismo código se omiten.
          </p>
          <UFormGroup label="Copiar desde">
            <USelect v-model="copy.sourceId" :options="otherCampaignOptions" placeholder="Selecciona una campaña" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="copy.open = false">Cancelar</UButton>
            <UButton :loading="copy.saving" :disabled="!copy.sourceId" @click="copyFrom">Copiar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const http = useHttp()
const toast = useToast()
const route = useRoute()
const router = useRouter()

const columns = [
  { key: 'order', label: '#' },
  { key: 'code', label: 'Código' },
  { key: 'name', label: 'Nombre' },
  { key: 'is_success', label: 'Resultado' },
  { key: 'requires_callback', label: 'Rellamada' },
  { key: 'form', label: 'Formulario' },
  { key: 'actions', label: '' },
]

const campaigns = ref<any[]>([])
const forms = ref<any[]>([])
const dispositions = ref<any[]>([])
const campaignId = ref<string | number>((route.query.campaign as string) || '')
const search = ref('')
const loading = ref(false)

const disp = reactive({
  open: false, saving: false, id: null as number | null, code: '', name: '', description: '',
  order: 0, is_success: false, requires_callback: false, form_id: '' as string | number,
})
const copy = reactive({ open: false, saving: false, sourceId: '' as string | number })

const campaignOptions = computed(() => campaigns.value.map(c => ({ label: c.name, value: c.id })))
const otherCampaignOptions = computed(() =>
  campaignOptions.value.filter(c => String(c.value) !== String(campaignId.value)))
const formOptions = computed(() => [
  { label: '— Formulario de la campaña —', value: '' },
  ...forms.value.map(f => ({ label: f.name, value: f.id })),
])
const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return dispositions.value
  return dispositions.value.filter(d =>
    d.code?.toLowerCase().includes(q) || d.name?.toLowerCase().includes(q))
})

async function loadCampaigns() {
  campaigns.value = http.results(await http.get('/campaigns/', { page_size: 200 }))
}
async function loadForms() {
  try { forms.value = http.results(await http.get('/campaign-forms/')) } catch { forms.value = [] }
}
async function loadDispositions() {
  if (!campaignId.value) { dispositions.value = []; return }
  loading.value = true
  try {
    dispositions.value = await http.get<any[]>(`/campaigns/${campaignId.value}/dispositions/`)
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { loading.value = false }
}
function onCampaignChange() {
  router.replace({ query: campaignId.value ? { campaign: String(campaignId.value) } : {} })
  loadDispositions()
}

function openDisp(d?: any) {
  Object.assign(disp, {
    open: true, saving: false, id: d?.id ?? null, code: d?.code ?? '', name: d?.name ?? '',
    description: d?.description ?? '', order: d?.order ?? dispositions.value.length + 1,
    is_success: d?.is_success ?? false, requires_callback: d?.requires_callback ?? false,
    form_id: d?.form?.id ?? '',
  })
}

async function saveDisp() {
  if (!disp.code.trim() || !disp.name.trim()) {
    return toast.add({ title: 'Código y nombre son obligatorios', color: 'orange' })
  }
  disp.saving = true
  const body = {
    code: disp.code.trim(), name: disp.name.trim(), description: disp.description,
    order: disp.order || 0, is_success: disp.is_success, requires_callback: disp.requires_callback,
    form_id: disp.form_id || null,
  }
  try {
    if (disp.id) await http.patch(`/campaigns/${campaignId.value}/dispositions/${disp.id}/`, body)
    else await http.post(`/campaigns/${campaignId.value}/dispositions/`, body)
    toast.add({ title: 'Tipificación guardada', color: 'green' })
    disp.open = false
    await loadDispositions()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { disp.saving = false }
}

async function deleteDisp(d: any) {
  if (!confirm(`¿Eliminar la tipificación "${d.name}"? Las llamadas ya calificadas conservan su historial.`)) return
  try {
    await http.del(`/campaigns/${campaignId.value}/dispositions/${d.id}/`)
    toast.add({ title: 'Tipificación eliminada', color: 'green' })
    await loadDispositions()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  }
}

async function copyFrom() {
  copy.saving = true
  try {
    const source = await http.get<any[]>(`/campaigns/${copy.sourceId}/dispositions/`)
    const existing = new Set(dispositions.value.map(d => d.code))
    let created = 0
    for (const d of source) {
      if (existing.has(d.code)) continue
      await http.post(`/campaigns/${campaignId.value}/dispositions/`, {
        code: d.code, name: d.name, description: d.description, order: d.order,
        is_success: d.is_success, requires_callback: d.requires_callback, form_id: d.form?.id ?? null,
      })
      created++
    }
    toast.add({ title: `${created} tipificaciones copiadas`, color: 'green' })
    copy.open = false
    copy.sourceId = ''
    await loadDispositions()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { copy.saving = false }
}

onMounted(async () => {
  await Promise.all([loadCampaigns(), loadForms()])
  if (campaignId.value) await loadDispositions()
})
</script>
