<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Formularios y calificaciones</h1>
      <p class="text-sm text-gray-500 mt-1">
        Diseña los formularios que el agente llena durante la gestión y define las calificaciones (tipificaciones) de cada campaña.
      </p>
    </div>

    <UTabs :items="tabs">
      <!-- ── Formularios ─────────────────────────────────────────────── -->
      <template #forms>
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4">
          <UCard class="lg:col-span-1">
            <template #header>
              <div class="flex items-center justify-between">
                <h3 class="font-semibold">Formularios</h3>
                <UButton size="xs" icon="i-heroicons-plus" @click="newForm">Nuevo</UButton>
              </div>
            </template>
            <div v-if="!forms.length" class="text-sm text-gray-400 text-center py-6">Sin formularios</div>
            <div v-else class="space-y-1">
              <button
                v-for="f in forms" :key="f.id"
                class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-50 flex items-center justify-between"
                :class="{ 'bg-sky-50 text-sky-700': editor.id === f.id }"
                @click="editForm(f)"
              >
                <span class="truncate">{{ f.name }}</span>
                <span class="text-xs text-gray-400">{{ f.fields_schema?.length || 0 }} campos</span>
              </button>
            </div>
          </UCard>

          <UCard class="lg:col-span-2">
            <template #header>
              <div class="flex items-center justify-between">
                <h3 class="font-semibold">{{ editor.id ? 'Editar formulario' : 'Nuevo formulario' }}</h3>
                <div class="flex gap-2">
                  <UButton v-if="editor.id" size="xs" color="red" variant="ghost" icon="i-heroicons-trash" @click="deleteForm">Eliminar</UButton>
                  <UButton size="sm" :loading="editor.saving" @click="saveForm">Guardar</UButton>
                </div>
              </div>
            </template>

            <div class="space-y-4">
              <div class="grid grid-cols-2 gap-3">
                <UFormGroup label="Nombre" required><UInput v-model="editor.name" placeholder="Ej: Venta de seguros" /></UFormGroup>
                <UFormGroup label="Estado"><UCheckbox v-model="editor.is_active" label="Activo" /></UFormGroup>
              </div>
              <UFormGroup label="Descripción"><UInput v-model="editor.description" /></UFormGroup>

              <div class="flex items-center justify-between">
                <p class="text-sm font-medium">Campos</p>
                <UButton size="xs" variant="soft" icon="i-heroicons-plus" @click="addField">Agregar campo</UButton>
              </div>

              <div v-if="!editor.fields.length" class="text-sm text-gray-400 text-center py-6 border border-dashed rounded-lg">
                Agrega el primer campo del formulario
              </div>

              <div v-for="(field, i) in editor.fields" :key="i" class="border rounded-lg p-3 space-y-2 bg-white">
                <div class="grid grid-cols-12 gap-2 items-end">
                  <UFormGroup label="Etiqueta" class="col-span-4">
                    <UInput v-model="field.label" @blur="autoName(field)" />
                  </UFormGroup>
                  <UFormGroup label="Nombre interno" class="col-span-3">
                    <UInput v-model="field.name" placeholder="sin_espacios" />
                  </UFormGroup>
                  <UFormGroup label="Tipo" class="col-span-3">
                    <USelect v-model="field.type" :options="fieldTypes" />
                  </UFormGroup>
                  <div class="col-span-2 flex justify-end gap-1 pb-1">
                    <UButton icon="i-heroicons-arrow-up" size="xs" color="gray" variant="ghost" :disabled="i === 0" @click="move(i, -1)" />
                    <UButton icon="i-heroicons-arrow-down" size="xs" color="gray" variant="ghost" :disabled="i === editor.fields.length - 1" @click="move(i, 1)" />
                    <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost" @click="editor.fields.splice(i, 1)" />
                  </div>
                </div>
                <div class="grid grid-cols-12 gap-2 items-center">
                  <UInput v-model="field.placeholder" placeholder="Texto de ayuda (opcional)" class="col-span-6" />
                  <UInput v-if="['select','multiselect'].includes(field.type)" v-model="field.optionsText"
                          placeholder="Opciones separadas por coma" class="col-span-4" />
                  <div v-else class="col-span-4" />
                  <UCheckbox v-model="field.required" label="Obligatorio" class="col-span-2" />
                </div>
              </div>

              <!-- Vista previa -->
              <div v-if="editor.fields.length" class="border-t pt-4">
                <p class="text-sm font-medium mb-3 text-gray-500">Vista previa (como lo verá el agente)</p>
                <div class="grid grid-cols-2 gap-3 opacity-90 pointer-events-none">
                  <UFormGroup v-for="(f, i) in editor.fields" :key="'p' + i" :label="f.label || '(sin etiqueta)'" :required="f.required"
                              :class="{ 'col-span-2': f.type === 'textarea' }">
                    <UTextarea v-if="f.type === 'textarea'" :placeholder="f.placeholder" :rows="2" />
                    <USelect v-else-if="f.type === 'select' || f.type === 'multiselect'" :options="parseOptions(f.optionsText)" />
                    <UCheckbox v-else-if="f.type === 'checkbox'" :label="f.placeholder || 'Sí'" />
                    <UInput v-else :type="inputType(f.type)" :placeholder="f.placeholder" />
                  </UFormGroup>
                </div>
              </div>
            </div>
          </UCard>
        </div>
      </template>

      <!-- ── Calificaciones por campaña ─────────────────────────────── -->
      <template #dispositions>
        <div class="space-y-4 pt-4">
          <UCard>
            <div class="flex flex-wrap gap-4 items-end">
              <UFormGroup label="Campaña" class="w-80">
                <USelect v-model="campaignId" :options="campaignOptions" placeholder="Selecciona una campaña" @change="loadDispositions" />
              </UFormGroup>
              <UFormGroup v-if="campaignId" label="Formulario de gestión de la campaña" class="w-80">
                <USelect v-model="campaignFormId" :options="formOptions" @change="assignForm" />
              </UFormGroup>
            </div>
          </UCard>

          <UCard v-if="campaignId">
            <template #header>
              <div class="flex items-center justify-between">
                <h3 class="font-semibold">Calificaciones</h3>
                <UButton size="xs" icon="i-heroicons-plus" @click="openDisp()">Nueva calificación</UButton>
              </div>
            </template>
            <UTable :rows="dispositions" :columns="dispColumns"
                    :empty-state="{ icon: 'i-heroicons-tag', label: 'Esta campaña no tiene calificaciones' }">
              <template #is_success-data="{ row }">
                <UBadge :color="row.is_success ? 'green' : 'gray'" variant="soft">{{ row.is_success ? 'Éxito' : 'No éxito' }}</UBadge>
              </template>
              <template #requires_callback-data="{ row }">{{ row.requires_callback ? 'Sí' : 'No' }}</template>
              <template #form-data="{ row }">{{ row.form?.name || '—' }}</template>
              <template #actions-data="{ row }">
                <UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost" @click="openDisp(row)" />
                <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost" @click="deleteDisp(row)" />
              </template>
            </UTable>
          </UCard>
        </div>
      </template>
    </UTabs>

    <UModal v-model="disp.open">
      <UCard>
        <template #header><h3 class="font-semibold">{{ disp.id ? 'Editar calificación' : 'Nueva calificación' }}</h3></template>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Código" required><UInput v-model="disp.code" placeholder="VENTA" /></UFormGroup>
            <UFormGroup label="Orden"><UInput v-model.number="disp.order" type="number" /></UFormGroup>
          </div>
          <UFormGroup label="Nombre" required><UInput v-model="disp.name" placeholder="Venta concretada" /></UFormGroup>
          <UFormGroup label="Descripción"><UInput v-model="disp.description" /></UFormGroup>
          <UFormGroup label="Formulario específico (opcional)" hint="Reemplaza el formulario de la campaña para esta calificación">
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
  </div>
</template>

<script setup lang="ts">
const http = useHttp()
const toast = useToast()

const tabs = [
  { label: 'Formularios', slot: 'forms', icon: 'i-heroicons-document-text' },
  { label: 'Calificaciones por campaña', slot: 'dispositions', icon: 'i-heroicons-tag' },
]
const fieldTypes = [
  { label: 'Texto', value: 'text' }, { label: 'Texto largo', value: 'textarea' },
  { label: 'Número', value: 'number' }, { label: 'Lista', value: 'select' },
  { label: 'Selección múltiple', value: 'multiselect' }, { label: 'Casilla', value: 'checkbox' },
  { label: 'Fecha', value: 'date' }, { label: 'Teléfono', value: 'phone' }, { label: 'Correo', value: 'email' },
]
const dispColumns = [
  { key: 'order', label: '#' }, { key: 'code', label: 'Código' }, { key: 'name', label: 'Nombre' },
  { key: 'is_success', label: 'Resultado' }, { key: 'requires_callback', label: 'Rellamada' },
  { key: 'form', label: 'Formulario' }, { key: 'actions', label: '' },
]

const forms = ref<any[]>([])
const campaigns = ref<any[]>([])
const dispositions = ref<any[]>([])
const campaignId = ref<string | number>('')
const campaignFormId = ref<string | number>('')

const blankEditor = () => ({ id: null as number | null, name: '', description: '', is_active: true, fields: [] as any[], saving: false })
const editor = reactive(blankEditor())
const disp = reactive({ open: false, saving: false, id: null as number | null, code: '', name: '', description: '',
  order: 0, is_success: false, requires_callback: false, form_id: '' as string | number })

const formOptions = computed(() => [{ label: '— Sin formulario —', value: '' }, ...forms.value.map(f => ({ label: f.name, value: f.id }))])
const campaignOptions = computed(() => campaigns.value.map(c => ({ label: c.name, value: c.id })))

const slug = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')
const parseOptions = (text: string) => (text || '').split(',').map(s => s.trim()).filter(Boolean)
const inputType = (t: string) => ({ number: 'number', date: 'date', email: 'email', phone: 'tel' } as any)[t] || 'text'

function autoName(field: any) { if (!field.name && field.label) field.name = slug(field.label) }
function move(i: number, dir: number) {
  const f = editor.fields.splice(i, 1)[0]
  editor.fields.splice(i + dir, 0, f)
}
function addField() {
  editor.fields.push({ label: '', name: '', type: 'text', required: false, placeholder: '', optionsText: '' })
}
function newForm() { Object.assign(editor, blankEditor()) }
function editForm(f: any) {
  Object.assign(editor, blankEditor(), {
    id: f.id, name: f.name, description: f.description, is_active: f.is_active,
    fields: (f.fields_schema || []).map((x: any) => ({ ...x, optionsText: (x.options || []).join(', ') })),
  })
}

async function loadForms() { forms.value = http.results(await http.get('/campaign-forms/')) }

async function saveForm() {
  if (!editor.name.trim()) return toast.add({ title: 'El nombre es obligatorio', color: 'orange' })
  editor.saving = true
  const fields_schema = editor.fields.map((f, i) => {
    const out: any = { name: f.name || slug(f.label), label: f.label, type: f.type, required: !!f.required, placeholder: f.placeholder || '', order: i + 1 }
    if (['select', 'multiselect'].includes(f.type)) out.options = parseOptions(f.optionsText)
    return out
  })
  try {
    const body = { name: editor.name, description: editor.description, is_active: editor.is_active, fields_schema }
    const saved: any = editor.id ? await http.patch(`/campaign-forms/${editor.id}/`, body) : await http.post('/campaign-forms/', body)
    toast.add({ title: 'Formulario guardado', color: 'green' })
    await loadForms()
    editForm(saved)
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { editor.saving = false }
}

async function deleteForm() {
  if (!editor.id || !confirm('¿Eliminar este formulario?')) return
  await http.del(`/campaign-forms/${editor.id}/`)
  newForm()
  await loadForms()
}

async function loadCampaigns() { campaigns.value = http.results(await http.get('/campaigns/', { page_size: 200 })) }

async function loadDispositions() {
  if (!campaignId.value) return
  const c = campaigns.value.find(x => String(x.id) === String(campaignId.value))
  campaignFormId.value = c?.form?.id ?? ''
  dispositions.value = await http.get<any[]>(`/campaigns/${campaignId.value}/dispositions/`)
}

async function assignForm() {
  try {
    await http.patch(`/campaigns/${campaignId.value}/`, { form_id: campaignFormId.value || null })
    toast.add({ title: 'Formulario asignado a la campaña', color: 'green' })
    await loadCampaigns()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  }
}

function openDisp(d?: any) {
  Object.assign(disp, {
    open: true, saving: false, id: d?.id ?? null, code: d?.code ?? '', name: d?.name ?? '',
    description: d?.description ?? '', order: d?.order ?? dispositions.value.length + 1,
    is_success: d?.is_success ?? false, requires_callback: d?.requires_callback ?? false, form_id: d?.form?.id ?? '',
  })
}

async function saveDisp() {
  disp.saving = true
  const body = { code: disp.code, name: disp.name, description: disp.description, order: disp.order,
    is_success: disp.is_success, requires_callback: disp.requires_callback, form_id: disp.form_id || null }
  try {
    if (disp.id) await http.patch(`/campaigns/${campaignId.value}/dispositions/${disp.id}/`, body)
    else await http.post(`/campaigns/${campaignId.value}/dispositions/`, body)
    disp.open = false
    await loadDispositions()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { disp.saving = false }
}

async function deleteDisp(d: any) {
  if (!confirm(`¿Eliminar la calificación "${d.name}"?`)) return
  await http.del(`/campaigns/${campaignId.value}/dispositions/${d.id}/`)
  await loadDispositions()
}

onMounted(async () => { await Promise.all([loadForms(), loadCampaigns()]) })
</script>
