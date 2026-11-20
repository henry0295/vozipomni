<template>
  <div>
    <div class="mb-8 flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Contactos</h1>
        <p class="text-gray-600 mt-2">Listas de contactos y base de datos para campañas</p>
      </div>
      <div class="flex gap-3">
        <UButton icon="i-heroicons-queue-list" color="gray" variant="outline" size="lg" @click="openList()">
          Nueva lista
        </UButton>
        <UButton icon="i-heroicons-arrow-up-tray" color="gray" variant="outline" size="lg" @click="openImport">
          Importar
        </UButton>
        <UButton icon="i-heroicons-plus" size="lg" @click="openContact()">
          Nuevo contacto
        </UButton>
      </div>
    </div>

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle" class="mb-6" :title="error" />

    <UTabs :items="tabs" class="w-full">
      <!-- ── Contactos ─────────────────────────────────────────────── -->
      <template #contacts>
        <div class="space-y-6 pt-4">
          <UCard>
            <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
              <UInput
                v-model="filters.search"
                icon="i-heroicons-magnifying-glass"
                placeholder="Buscar por nombre, teléfono, email o empresa"
                class="md:col-span-2"
                @update:model-value="debouncedLoad"
              />
              <USelect v-model="filters.contact_list" :options="listFilterOptions" @change="loadContacts(1)" />
              <USelect v-model="filters.status" :options="statusFilterOptions" @change="loadContacts(1)" />
              <UButton color="gray" variant="outline" @click="clearFilters">Limpiar</UButton>
            </div>
          </UCard>

          <UCard>
            <UTable
              :rows="contacts"
              :columns="columns"
              :loading="loading"
              :empty-state="{ icon: 'i-heroicons-circle-stack-20-solid', label: lists.length ? 'No hay contactos con estos filtros' : 'Primero cree una lista de contactos' }"
            >
              <template #name-data="{ row }">
                <div>
                  <p class="font-medium text-gray-900">{{ row.first_name }} {{ row.last_name }}</p>
                  <p class="text-sm text-gray-600">{{ row.company || 'Sin empresa' }}</p>
                </div>
              </template>
              <template #contact-data="{ row }">
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    <UIcon name="i-heroicons-phone" class="h-4 w-4 text-gray-400" />
                    <span class="text-sm text-gray-900">{{ row.phone }}</span>
                  </div>
                  <div v-if="row.email" class="flex items-center gap-2">
                    <UIcon name="i-heroicons-envelope" class="h-4 w-4 text-gray-400" />
                    <span class="text-sm text-gray-600">{{ row.email }}</span>
                  </div>
                </div>
              </template>
              <template #list-data="{ row }">
                <span class="text-sm">{{ listName(row.contact_list) }}</span>
              </template>
              <template #status-data="{ row }">
                <UBadge :color="statusColor(row.status)" variant="soft">{{ statusLabel(row.status) }}</UBadge>
              </template>
              <template #whatsapp-data="{ row }">
                <UToggle
                  :model-value="!!row.whatsapp_opt_in"
                  aria-label="Acepta mensajes de WhatsApp"
                  @update:model-value="toggleOptIn(row)"
                />
              </template>
              <template #actions-data="{ row }">
                <div class="flex gap-1 justify-end">
                  <UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost" @click="openContact(row)" />
                  <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost" @click="deleteContact(row)" />
                </div>
              </template>
            </UTable>
            <div v-if="totalContacts > pageSize" class="flex justify-end pt-4">
              <UPagination v-model="page" :page-count="pageSize" :total="totalContacts" @update:model-value="loadContacts" />
            </div>
          </UCard>
        </div>
      </template>

      <!-- ── Listas ────────────────────────────────────────────────── -->
      <template #lists>
        <div class="pt-4">
          <UCard>
            <UTable
              :rows="lists"
              :columns="listColumns"
              :empty-state="{ icon: 'i-heroicons-queue-list', label: 'No hay listas. Cree una con «Nueva lista».' }"
            >
              <template #is_active-data="{ row }">
                <UBadge :color="row.is_active ? 'green' : 'gray'" variant="soft">{{ row.is_active ? 'Activa' : 'Inactiva' }}</UBadge>
              </template>
              <template #actions-data="{ row }">
                <div class="flex gap-1 justify-end">
                  <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-eye" @click="showListContacts(row)" />
                  <UButton size="xs" color="gray" variant="ghost" icon="i-heroicons-pencil" @click="openList(row)" />
                  <UButton size="xs" color="red" variant="ghost" icon="i-heroicons-trash" @click="deleteList(row)" />
                </div>
              </template>
            </UTable>
          </UCard>
        </div>
      </template>
    </UTabs>

    <!-- Modal: lista -->
    <UModal v-model="listForm.open">
      <UCard>
        <template #header><h3 class="font-semibold">{{ listForm.id ? 'Editar lista' : 'Nueva lista de contactos' }}</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Nombre" required><UInput v-model="listForm.name" placeholder="Base clientes octubre" /></UFormGroup>
          <UFormGroup label="Descripción"><UTextarea v-model="listForm.description" :rows="2" /></UFormGroup>
          <UCheckbox v-model="listForm.is_active" label="Activa" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="listForm.open = false">Cancelar</UButton>
            <UButton :loading="listForm.saving" @click="saveList">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal: contacto -->
    <UModal v-model="contactForm.open" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ contactForm.id ? 'Editar contacto' : 'Nuevo contacto' }}</h3></template>
        <UAlert
          v-if="!lists.length"
          color="orange"
          icon="i-heroicons-exclamation-triangle"
          title="Primero cree una lista de contactos"
          class="mb-3"
        />
        <div class="grid grid-cols-2 gap-3">
          <UFormGroup label="Lista" required class="col-span-2">
            <USelect v-model="contactForm.contact_list" :options="listOptions" placeholder="Seleccione una lista" />
          </UFormGroup>
          <UFormGroup label="Nombre" required><UInput v-model="contactForm.first_name" /></UFormGroup>
          <UFormGroup label="Apellido"><UInput v-model="contactForm.last_name" /></UFormGroup>
          <UFormGroup label="Teléfono" required hint="Con indicativo, ej. +573001234567"><UInput v-model="contactForm.phone" /></UFormGroup>
          <UFormGroup label="Teléfono 2"><UInput v-model="contactForm.phone2" /></UFormGroup>
          <UFormGroup label="Email"><UInput v-model="contactForm.email" type="email" /></UFormGroup>
          <UFormGroup label="Empresa"><UInput v-model="contactForm.company" /></UFormGroup>
          <UFormGroup label="Ciudad"><UInput v-model="contactForm.city" /></UFormGroup>
          <UFormGroup label="Estado"><USelect v-model="contactForm.status" :options="statusOptions" /></UFormGroup>
          <div class="col-span-2 flex gap-6">
            <UCheckbox v-model="contactForm.whatsapp_opt_in" label="Acepta WhatsApp" />
            <UCheckbox v-model="contactForm.is_vip" label="VIP" />
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="contactForm.open = false">Cancelar</UButton>
            <UButton :loading="contactForm.saving" :disabled="!lists.length" @click="saveContact">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal: importación -->
    <UModal v-model="importForm.open">
      <UCard>
        <template #header><h3 class="font-semibold">Importar contactos (CSV / Excel)</h3></template>
        <div class="space-y-4">
          <UFormGroup label="Lista destino" required>
            <USelect v-model="importForm.contact_list" :options="listOptions" placeholder="Seleccione una lista" />
          </UFormGroup>
          <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <UIcon name="i-heroicons-document-arrow-up" class="w-10 h-10 mx-auto text-gray-400 mb-3" />
            <p class="text-sm text-gray-600 mb-1">Archivo CSV o Excel (.xlsx)</p>
            <p class="text-xs text-gray-500 mb-3">Columnas: first_name, last_name, phone, email, company, city</p>
            <input id="bulk-file-input" type="file" accept=".csv,.xlsx,.xls" class="hidden" @change="onFileChange">
            <label for="bulk-file-input" class="cursor-pointer">
              <UButton color="gray" variant="outline" as="span">Seleccionar archivo</UButton>
            </label>
            <p v-if="importForm.file" class="mt-2 text-sm text-green-600 font-medium">{{ importForm.file.name }}</p>
          </div>
          <UCheckbox v-model="importForm.skip_duplicates" label="Omitir teléfonos repetidos en la lista" />
          <div v-if="importForm.result" class="rounded-lg p-4" :class="importForm.result.error ? 'bg-red-50' : 'bg-green-50'">
            <p v-if="importForm.result.error" class="text-red-700 text-sm">{{ importForm.result.error }}</p>
            <div v-else class="text-sm space-y-1">
              <p class="text-green-700 font-medium">Importación completada</p>
              <p>Importados: <strong>{{ importForm.result.imported ?? 0 }}</strong></p>
              <p>Omitidos: <strong>{{ importForm.result.skipped ?? 0 }}</strong></p>
              <p v-if="importForm.result.total_errors" class="text-red-600">Errores: {{ importForm.result.total_errors }}</p>
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="importForm.open = false">Cerrar</UButton>
            <UButton
              icon="i-heroicons-arrow-up-tray"
              :disabled="!importForm.file || !importForm.contact_list"
              :loading="importForm.loading"
              @click="runImport"
            >
              Importar
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })

const http = useHttp()
const toast = useToast()

const tabs = [
  { label: 'Contactos', slot: 'contacts', icon: 'i-heroicons-users' },
  { label: 'Listas', slot: 'lists', icon: 'i-heroicons-queue-list' },
]

const statusOptions = [
  { label: 'Nuevo', value: 'new' },
  { label: 'Pendiente', value: 'pending' },
  { label: 'Rellamada', value: 'callback' },
  { label: 'Contactado', value: 'contacted' },
  { label: 'Exitoso', value: 'success' },
  { label: 'Fallido', value: 'failed' },
  { label: 'Lista negra', value: 'blacklisted' },
]
const statusFilterOptions = [{ label: 'Todos los estados', value: '' }, ...statusOptions]
const statusLabel = (s: string) => statusOptions.find(o => o.value === s)?.label || s
const statusColor = (s: string) => ({
  new: 'blue', pending: 'yellow', callback: 'orange', contacted: 'purple',
  success: 'green', failed: 'red', blacklisted: 'gray',
} as Record<string, string>)[s] || 'gray'

const columns = [
  { key: 'name', label: 'Nombre' },
  { key: 'contact', label: 'Contacto' },
  { key: 'list', label: 'Lista' },
  { key: 'status', label: 'Estado' },
  { key: 'whatsapp', label: 'Acepta WhatsApp' },
  { key: 'actions', label: '' },
]
const listColumns = [
  { key: 'name', label: 'Nombre' },
  { key: 'description', label: 'Descripción' },
  { key: 'total_contacts', label: 'Contactos' },
  { key: 'is_active', label: 'Estado' },
  { key: 'actions', label: '' },
]

const contacts = ref<any[]>([])
const lists = ref<any[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const page = ref(1)
const pageSize = 50
const totalContacts = ref(0)
const filters = reactive({ search: '', status: '', contact_list: '' as string | number })

const listOptions = computed(() => lists.value.map(l => ({ label: l.name, value: l.id })))
const listFilterOptions = computed(() => [{ label: 'Todas las listas', value: '' }, ...listOptions.value])
const listName = (id: number) => lists.value.find(l => l.id === id)?.name || '—'

async function loadLists() {
  try {
    lists.value = http.results(await http.get('/contact-lists/', { page_size: 500 }))
  } catch (e: any) {
    error.value = http.errorMessage(e, 'Error al cargar las listas')
  }
}

async function loadContacts(p = page.value) {
  page.value = p
  loading.value = true
  error.value = null
  try {
    const query: Record<string, any> = { page: page.value, page_size: pageSize }
    if (filters.search) query.search = filters.search
    if (filters.status) query.status = filters.status
    if (filters.contact_list) query.contact_list = filters.contact_list
    const data: any = await http.get('/contacts/', query)
    contacts.value = http.results(data)
    totalContacts.value = data?.count ?? contacts.value.length
  } catch (e: any) {
    error.value = http.errorMessage(e, 'Error al cargar contactos')
    contacts.value = []
  } finally { loading.value = false }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined
const debouncedLoad = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadContacts(1), 350)
}
function clearFilters() {
  Object.assign(filters, { search: '', status: '', contact_list: '' })
  loadContacts(1)
}

// ── Listas ──
const listForm = reactive({ open: false, saving: false, id: null as number | null, name: '', description: '', is_active: true })
function openList(l?: any) {
  Object.assign(listForm, { open: true, saving: false, id: l?.id ?? null, name: l?.name ?? '', description: l?.description ?? '', is_active: l?.is_active ?? true })
}
async function saveList() {
  if (!listForm.name.trim()) return toast.add({ title: 'El nombre es obligatorio', color: 'orange' })
  listForm.saving = true
  try {
    const body = { name: listForm.name.trim(), description: listForm.description, is_active: listForm.is_active }
    if (listForm.id) await http.patch(`/contact-lists/${listForm.id}/`, body)
    else await http.post('/contact-lists/', body)
    toast.add({ title: 'Lista guardada', color: 'green' })
    listForm.open = false
    await loadLists()
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar la lista', description: http.errorMessage(e), color: 'red' })
  } finally { listForm.saving = false }
}
async function deleteList(l: any) {
  if (!confirm(`¿Eliminar la lista "${l.name}" y todos sus contactos?`)) return
  try {
    await http.del(`/contact-lists/${l.id}/`)
    toast.add({ title: 'Lista eliminada', color: 'green' })
    await Promise.all([loadLists(), loadContacts(1)])
  } catch (e: any) {
    toast.add({ title: 'No se pudo eliminar', description: http.errorMessage(e), color: 'red' })
  }
}
function showListContacts(l: any) {
  filters.contact_list = l.id
  loadContacts(1)
  toast.add({ title: `Mostrando contactos de "${l.name}" en la pestaña Contactos`, color: 'blue' })
}

// ── Contactos ──
const blankContact = () => ({
  open: false, saving: false, id: null as number | null, contact_list: '' as string | number,
  first_name: '', last_name: '', phone: '', phone2: '', email: '', company: '', city: '',
  status: 'new', whatsapp_opt_in: false, is_vip: false,
})
const contactForm = reactive(blankContact())
function openContact(c?: any) {
  Object.assign(contactForm, blankContact(), { open: true })
  if (c) {
    Object.assign(contactForm, {
      id: c.id, contact_list: c.contact_list, first_name: c.first_name, last_name: c.last_name || '',
      phone: c.phone, phone2: c.phone2 || '', email: c.email || '', company: c.company || '',
      city: c.city || '', status: c.status || 'new', whatsapp_opt_in: !!c.whatsapp_opt_in, is_vip: !!c.is_vip,
    })
  } else if (filters.contact_list) {
    contactForm.contact_list = filters.contact_list
  } else if (lists.value.length === 1) {
    contactForm.contact_list = lists.value[0].id
  }
}
async function saveContact() {
  if (!contactForm.contact_list) return toast.add({ title: 'Seleccione una lista', color: 'orange' })
  if (!contactForm.first_name.trim() || !contactForm.phone.trim()) {
    return toast.add({ title: 'Nombre y teléfono son obligatorios', color: 'orange' })
  }
  contactForm.saving = true
  const { open, saving, id, ...body } = contactForm
  try {
    if (id) await http.patch(`/contacts/${id}/`, body)
    else await http.post('/contacts/', body)
    toast.add({ title: 'Contacto guardado', color: 'green' })
    contactForm.open = false
    await Promise.all([loadContacts(), loadLists()])
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar el contacto', description: http.errorMessage(e), color: 'red' })
  } finally { contactForm.saving = false }
}
async function deleteContact(c: any) {
  if (!confirm(`¿Eliminar a ${c.first_name} ${c.last_name || ''}?`)) return
  try {
    await http.del(`/contacts/${c.id}/`)
    await Promise.all([loadContacts(), loadLists()])
  } catch (e: any) {
    toast.add({ title: 'No se pudo eliminar', description: http.errorMessage(e), color: 'red' })
  }
}
async function toggleOptIn(row: any) {
  const value = !row.whatsapp_opt_in
  try {
    await http.patch(`/contacts/${row.id}/`, { whatsapp_opt_in: value, whatsapp_opt_in_source: 'agente' })
    row.whatsapp_opt_in = value
  } catch (e: any) {
    toast.add({ title: 'No se pudo actualizar el consentimiento', description: http.errorMessage(e), color: 'red' })
  }
}

// ── Importación ──
const importForm = reactive({ open: false, loading: false, file: null as File | null, contact_list: '' as string | number, skip_duplicates: true, result: null as any })
function openImport() {
  Object.assign(importForm, { open: true, loading: false, file: null, result: null, contact_list: filters.contact_list || (lists.value.length === 1 ? lists.value[0].id : '') })
}
function onFileChange(e: Event) {
  importForm.file = (e.target as HTMLInputElement).files?.[0] || null
  importForm.result = null
}
async function runImport() {
  if (!importForm.file || !importForm.contact_list) return
  importForm.loading = true
  importForm.result = null
  try {
    const fd = new FormData()
    fd.append('file', importForm.file)
    fd.append('contact_list_id', String(importForm.contact_list))
    fd.append('skip_duplicates', importForm.skip_duplicates ? 'true' : 'false')
    importForm.result = await http.post('/cc/bulk-import/', fd)
    await Promise.all([loadContacts(1), loadLists()])
  } catch (e: any) {
    importForm.result = { error: e?.data?.error || http.errorMessage(e) }
  } finally { importForm.loading = false }
}

onMounted(async () => {
  await loadLists()
  await loadContacts(1)
})
</script>
