<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Lista negra (DNC)</h1>
        <p class="text-sm text-gray-500 mt-1">Números que el marcador nunca debe llamar. Los cambios aplican al dialer en segundos.</p>
      </div>
      <div class="flex gap-2">
        <UButton icon="i-heroicons-arrow-up-tray" color="gray" variant="outline" @click="importModal.open = true">Importar</UButton>
        <UButton icon="i-heroicons-plus" @click="openForm()">Agregar número</UButton>
      </div>
    </div>

    <!-- Verificar número -->
    <UCard>
      <div class="flex flex-wrap items-end gap-3">
        <UFormGroup label="Verificar un número" class="w-72">
          <UInput v-model="checkPhone" placeholder="Ej: 3001234567" icon="i-heroicons-phone" @keyup.enter="check" />
        </UFormGroup>
        <UButton :loading="checking" @click="check">Verificar</UButton>
        <div v-if="checkResult" class="flex items-center gap-2">
          <UBadge :color="checkResult.blocked ? 'red' : 'green'" size="lg" variant="soft">
            {{ checkResult.blocked ? 'Bloqueado' : 'Permitido' }}
          </UBadge>
          <span v-if="checkResult.blocked" class="text-sm text-gray-500">
            {{ checkResult.in_blacklist ? 'Está en la lista negra' : '' }}{{ checkResult.in_blacklist && checkResult.dnc_opt_out ? ' · ' : '' }}{{ checkResult.dnc_opt_out ? 'El contacto pidió no ser llamado' : '' }}
          </span>
        </div>
      </div>
    </UCard>

    <UCard>
      <template #header>
        <div class="flex gap-2 items-center">
          <UInput v-model="search" icon="i-heroicons-magnifying-glass" placeholder="Buscar número o motivo" class="w-72" @keyup.enter="load" />
          <USelect v-model="filterActive" :options="[{label:'Activos',value:'true'},{label:'Inactivos',value:'false'},{label:'Todos',value:''}]" @change="load" />
          <span class="text-sm text-gray-500 ml-auto">{{ total }} números</span>
        </div>
      </template>
      <UTable :rows="rows" :columns="columns" :loading="loading"
              :empty-state="{ icon: 'i-heroicons-no-symbol', label: 'La lista negra está vacía' }">
        <template #is_active-data="{ row }">
          <UToggle :model-value="row.is_active" @update:model-value="toggle(row)" />
        </template>
        <template #added_at-data="{ row }">{{ new Date(row.added_at).toLocaleString('es-CO') }}</template>
        <template #actions-data="{ row }">
          <UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost" @click="openForm(row)" />
          <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost" @click="remove(row)" />
        </template>
      </UTable>
      <div v-if="total > rows.length" class="flex justify-center pt-4">
        <UPagination v-model="page" :page-count="50" :total="total" @update:model-value="load" />
      </div>
    </UCard>

    <UModal v-model="form.open">
      <UCard>
        <template #header><h3 class="font-semibold">{{ form.id ? 'Editar número' : 'Agregar a la lista negra' }}</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Teléfono" required><UInput v-model="form.phone" placeholder="+573001234567" /></UFormGroup>
          <UFormGroup label="Motivo"><UInput v-model="form.reason" placeholder="Ej: Solicitud del cliente, Ley de Habeas Data" /></UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="form.open = false">Cancelar</UButton>
            <UButton :loading="form.saving" @click="save">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <UModal v-model="importModal.open">
      <UCard>
        <template #header><h3 class="font-semibold">Importación masiva</h3></template>
        <div class="space-y-4">
          <UFormGroup label="Archivo CSV / Excel" hint="Columna 1: teléfono · Columna 2 (opcional): motivo">
            <input type="file" accept=".csv,.xlsx,.xls" class="text-sm" @change="onFile" />
          </UFormGroup>
          <UDivider label="o pega los números" />
          <UTextarea v-model="importModal.numbers" :rows="6" placeholder="Un número por línea" />
          <UFormGroup label="Motivo para todos"><UInput v-model="importModal.reason" placeholder="Importación masiva" /></UFormGroup>
          <UAlert v-if="importModal.result" color="green" variant="soft"
                  :title="`${importModal.result.imported} importados`"
                  :description="`${importModal.result.skipped} ya existían · ${importModal.result.invalid} inválidos`" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="importModal.open = false">Cerrar</UButton>
            <UButton :loading="importModal.saving" :disabled="!importModal.file && !importModal.numbers.trim()" @click="doImport">Importar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const http = useHttp()
const toast = useToast()

const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const search = ref('')
const filterActive = ref('true')
const checkPhone = ref('')
const checking = ref(false)
const checkResult = ref<any>(null)

const columns = [
  { key: 'phone', label: 'Teléfono' },
  { key: 'reason', label: 'Motivo' },
  { key: 'added_by_name', label: 'Agregado por' },
  { key: 'added_at', label: 'Fecha' },
  { key: 'is_active', label: 'Activo' },
  { key: 'actions', label: '' },
]

const form = reactive({ open: false, saving: false, id: null as number | null, phone: '', reason: '' })
const importModal = reactive({ open: false, saving: false, file: null as File | null, numbers: '', reason: '', result: null as any })

async function load() {
  loading.value = true
  try {
    const query: any = { page: page.value }
    if (search.value) query.search = search.value
    if (filterActive.value) query.is_active = filterActive.value
    const data: any = await http.get('/blacklist/', query)
    rows.value = http.results(data)
    total.value = data?.count ?? rows.value.length
  } finally { loading.value = false }
}

function openForm(r?: any) {
  Object.assign(form, { open: true, saving: false, id: r?.id ?? null, phone: r?.phone ?? '', reason: r?.reason ?? '' })
}

async function save() {
  form.saving = true
  try {
    const body = { phone: form.phone, reason: form.reason }
    if (form.id) await http.patch(`/blacklist/${form.id}/`, body)
    else await http.post('/blacklist/', body)
    toast.add({ title: 'Guardado', color: 'green' })
    form.open = false
    await load()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { form.saving = false }
}

async function toggle(r: any) {
  await http.patch(`/blacklist/${r.id}/`, { is_active: !r.is_active })
  r.is_active = !r.is_active
}

async function remove(r: any) {
  if (!confirm(`¿Quitar ${r.phone} de la lista negra?`)) return
  await http.del(`/blacklist/${r.id}/`)
  await load()
}

async function check() {
  if (!checkPhone.value.trim()) return
  checking.value = true
  try { checkResult.value = await http.get('/blacklist/check/', { phone: checkPhone.value }) }
  catch (e: any) { toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' }) }
  finally { checking.value = false }
}

function onFile(e: Event) {
  importModal.file = (e.target as HTMLInputElement).files?.[0] ?? null
}

async function doImport() {
  importModal.saving = true
  importModal.result = null
  try {
    const fd = new FormData()
    if (importModal.file) fd.append('file', importModal.file)
    if (importModal.numbers.trim()) fd.append('numbers', importModal.numbers)
    if (importModal.reason) fd.append('reason', importModal.reason)
    importModal.result = await http.post('/blacklist/bulk-import/', fd)
    await load()
  } catch (e: any) {
    toast.add({ title: 'Error importando', description: http.errorMessage(e), color: 'red' })
  } finally { importModal.saving = false }
}

onMounted(load)
</script>
