<template>
  <div>
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Contactos</h1>
        <p class="text-gray-600 mt-2">Base de datos de contactos</p>
      </div>
      <div class="flex gap-3">
        <UButton
          icon="i-heroicons-arrow-up-tray"
          color="gray"
          variant="outline"
          size="lg"
          @click="showBulkImport = true"
        >
          Importar
        </UButton>
        <UButton
          icon="i-heroicons-plus"
          size="lg"
          @click="showCreateModal = true"
        >
          Nuevo Contacto
        </UButton>
      </div>
    </div>

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle" class="mb-6">
      {{ error }}
    </UAlert>

    <!-- Filtros y búsqueda -->
    <UCard class="mb-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <UInput
          v-model="filters.search"
          icon="i-heroicons-magnifying-glass"
          placeholder="Buscar contacto..."
          class="md:col-span-2"
        />
        <USelectMenu
          v-model="filters.status"
          :options="statusOptions"
          placeholder="Estado"
        />
        <UButton
          color="gray"
          variant="outline"
          @click="clearFilters"
        >
          Limpiar
        </UButton>
      </div>
    </UCard>

    <!-- Tabla de contactos -->
    <UCard>
      <UTable
        :rows="contacts"
        :columns="columns"
        :loading="loading"
        :empty-state="{ icon: 'i-heroicons-circle-stack-20-solid', label: 'No hay contactos registrados' }"
      >
        <template #name-data="{ row }">
          <div>
            <p class="font-medium text-gray-900">{{ row.firstName }} {{ row.lastName }}</p>
            <p class="text-sm text-gray-600">{{ row.company || 'Sin empresa' }}</p>
          </div>
        </template>

        <template #contact-data="{ row }">
          <div class="space-y-1">
            <div class="flex items-center space-x-2">
              <UIcon name="i-heroicons-phone" class="h-4 w-4 text-gray-400" />
              <span class="text-sm text-gray-900">{{ row.phone }}</span>
            </div>
            <div v-if="row.email" class="flex items-center space-x-2">
              <UIcon name="i-heroicons-envelope" class="h-4 w-4 text-gray-400" />
              <span class="text-sm text-gray-600">{{ row.email }}</span>
            </div>
          </div>
        </template>

        <template #status-data="{ row }">
          <UBadge :color="getStatusColor(row.status)">
            {{ row.statusLabel }}
          </UBadge>
        </template>

        <template #lastContact-data="{ row }">
          <span class="text-sm text-gray-600">
            {{ row.lastContact || 'Sin contacto' }}
          </span>
        </template>

        <template #actions-data="{ row }">
          <div class="flex gap-2">
            <UButton
              icon="i-heroicons-phone"
              color="green"
              variant="ghost"
              size="sm"
              @click="makeCall(row)"
            />
            <UDropdown :items="getActions(row)">
              <UButton
                icon="i-heroicons-ellipsis-vertical"
                color="gray"
                variant="ghost"
                size="sm"
              />
            </UDropdown>
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Modal: Importación masiva -->
    <UModal v-model="showBulkImport">
      <UCard>
        <template #header>
          <h3 class="font-semibold">Importar contactos (CSV / Excel)</h3>
        </template>
        <div class="space-y-4">
          <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <UIcon name="i-heroicons-document-arrow-up" class="w-10 h-10 mx-auto text-gray-400 mb-3" />
            <p class="text-sm text-gray-600 mb-2">Selecciona un archivo CSV o Excel (.xlsx)</p>
            <input type="file" accept=".csv,.xlsx,.xls" class="hidden" id="bulk-file-input" @change="onFileChange" />
            <label for="bulk-file-input" class="cursor-pointer">
              <UButton color="gray" variant="outline" as="span">Seleccionar archivo</UButton>
            </label>
            <p v-if="importFile" class="mt-2 text-sm text-green-600 font-medium">{{ importFile.name }}</p>
          </div>

          <!-- Resultado -->
          <div v-if="importResult" class="rounded-lg p-4" :class="importResult.error ? 'bg-red-50' : 'bg-green-50'">
            <p v-if="importResult.error" class="text-red-700 text-sm">{{ importResult.error }}</p>
            <div v-else class="text-sm space-y-1">
              <p class="text-green-700 font-medium">✓ Importación completada</p>
              <p class="text-gray-600">Importados: <strong>{{ importResult.imported }}</strong></p>
              <p class="text-gray-600">Omitidos: <strong>{{ importResult.skipped }}</strong></p>
              <p v-if="importResult.total_errors" class="text-red-600">Errores: {{ importResult.total_errors }}</p>
            </div>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" @click="showBulkImport = false">Cerrar</UButton>
            <UButton
              color="primary"
              icon="i-heroicons-arrow-up-tray"
              :disabled="!importFile"
              :loading="importLoading"
              @click="runBulkImport"
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
definePageMeta({
  middleware: ['auth']
})

const showCreateModal = ref(false)
const showBulkImport = ref(false)
const importFile = ref<File | null>(null)
const importListId = ref<number | null>(null)
const importLoading = ref(false)
const importResult = ref<any>(null)

const authHeaders = () => ({ Authorization: 'Bearer ' + localStorage.getItem('auth_token') })

const onFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  importFile.value = input.files?.[0] || null
  importResult.value = null
}

const runBulkImport = async () => {
  if (!importFile.value) return
  importLoading.value = true
  importResult.value = null
  try {
    const fd = new FormData()
    fd.append('file', importFile.value)
    if (importListId.value) fd.append('contact_list_id', String(importListId.value))
    const result = await $fetch('/api/cc/bulk-import/', {
      method: 'POST',
      headers: authHeaders(),
      body: fd,
    })
    importResult.value = result
  } catch (e: any) {
    importResult.value = { error: e?.data?.error || e.message }
  } finally { importLoading.value = false }
}
const loading = ref(false)
const error = ref<string | null>(null)

const filters = reactive({
  search: '',
  status: null
})

const statusOptions = [
  { label: 'Nuevo', value: 'new' },
  { label: 'Contactado', value: 'contacted' },
  { label: 'Calificado', value: 'qualified' },
  { label: 'Convertido', value: 'converted' }
]

const columns = [
  { key: 'name', label: 'Nombre' },
  { key: 'contact', label: 'Contacto' },
  { key: 'status', label: 'Estado' },
  { key: 'lastContact', label: 'Último Contacto' },
  { key: 'actions', label: '' }
]

const contacts = ref<any[]>([])

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    new: 'blue',
    contacted: 'yellow',
    qualified: 'purple',
    converted: 'green'
  }
  return colors[status] || 'gray'
}

const makeCall = (contact: any) => {
  // TODO: Iniciar llamada
  console.log('Llamando a:', contact.phone)
}

const getActions = (row: any) => [
  [{
    label: 'Ver detalles',
    icon: 'i-heroicons-eye',
    click: () => navigateTo(`/contacts/${row.id}`)
  }],
  [{
    label: 'Editar',
    icon: 'i-heroicons-pencil',
    click: () => console.log('Edit', row.id)
  }],
  [{
    label: 'Eliminar',
    icon: 'i-heroicons-trash',
    click: () => deleteContact(row.id)
  }]
]

const clearFilters = () => {
  filters.search = ''
  filters.status = null
}

const { apiFetch } = useApi()

const loadContacts = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<any>('/contacts/')
  if (fetchError.value) {
    error.value = 'Error al cargar contactos'
    contacts.value = []
  } else {
    const raw = data.value
    const list = Array.isArray(raw) ? raw : (raw?.results || [])
    contacts.value = list.map((contact: any) => ({
      id: contact.id,
      firstName: contact.first_name,
      lastName: contact.last_name,
      phone: contact.phone,
      email: contact.email,
      company: contact.company,
      status: contact.status,
      statusLabel: contact.status,
      lastContact: null
    }))
  }
  loading.value = false
}

const deleteContact = async (id: number) => {
  if (!confirm('¿Estás seguro de eliminar este contacto?')) return
  const { error: deleteError } = await apiFetch(`/contacts/${id}/`, { method: 'DELETE' })
  if (!deleteError.value) {
    await loadContacts()
  }
}

onMounted(() => {
  loadContacts()
})
</script>
