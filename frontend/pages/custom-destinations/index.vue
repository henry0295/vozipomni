<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Destinos Personalizados</h1>
        <p class="text-sm text-gray-500 mt-1">
          Nodos de dialplan Asterisk (context / extension / priority) reutilizables como destino de enrutamiento.
        </p>
      </div>
      <UButton icon="i-heroicons-plus" @click="openModal()">Nuevo destino</UButton>
    </div>

    <!-- Filtros -->
    <UCard>
      <div class="flex flex-wrap gap-4 items-center">
        <UInput
          v-model="search"
          icon="i-heroicons-magnifying-glass"
          placeholder="Buscar por nombre, contexto..."
          class="w-64"
          @input="fetchDestinations"
        />
        <USelect
          v-model="filterActive"
          :options="activeOptions"
          option-attribute="label"
          value-attribute="value"
          class="w-40"
          @change="fetchDestinations"
        />
        <UButton icon="i-heroicons-arrow-path" color="gray" variant="ghost" @click="fetchDestinations">
          Actualizar
        </UButton>
      </div>
    </UCard>

    <!-- Tabla -->
    <UCard>
      <UTable
        :rows="destinations"
        :columns="columns"
        :loading="loading"
        :empty-state="{ icon: 'i-heroicons-map-pin', label: 'Sin destinos personalizados configurados' }"
      >
        <template #context-data="{ row }">
          <span class="font-mono text-sm text-blue-700 bg-blue-50 px-2 py-0.5 rounded">{{ row.context }}</span>
        </template>
        <template #extension-data="{ row }">
          <span class="font-mono text-sm">{{ row.extension }}</span>
        </template>
        <template #priority-data="{ row }">
          <span class="font-mono text-sm text-gray-600">{{ row.priority }}</span>
        </template>
        <template #failover-data="{ row }">
          <span v-if="row.failover_context" class="text-xs text-gray-500 font-mono">
            {{ row.failover_context }}/{{ row.failover_extension }}/{{ row.failover_priority }}
          </span>
          <span v-else class="text-xs text-gray-400">—</span>
        </template>
        <template #is_active-data="{ row }">
          <UToggle :model-value="row.is_active" @update:model-value="toggleActive(row)" />
        </template>
        <template #actions-data="{ row }">
          <div class="flex gap-1">
            <UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost" @click="openModal(row)" />
            <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost" @click="deleteDestination(row)" />
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Modal Create/Edit -->
    <UModal v-model="isModalOpen" :prevent-close="saving">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">
              {{ editingDestination ? 'Editar Destino Personalizado' : 'Nuevo Destino Personalizado' }}
            </h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="closeModal" />
          </div>
        </template>

        <form class="space-y-5" @submit.prevent="saveDestination">
          <!-- Nombre y descripción -->
          <div class="grid grid-cols-1 gap-4">
            <UFormGroup label="Nombre *" required>
              <UInput v-model="form.name" placeholder="ej. Cola_Ventas" />
            </UFormGroup>
            <UFormGroup label="Descripción">
              <UTextarea v-model="form.description" placeholder="Descripción opcional" :rows="2" />
            </UFormGroup>
          </div>

          <!-- Dialplan principal -->
          <div>
            <p class="text-sm font-semibold text-gray-700 mb-2">Destino Asterisk</p>
            <div class="grid grid-cols-3 gap-3">
              <UFormGroup label="Context *" required>
                <UInput v-model="form.context" placeholder="ej. from-internal" class="font-mono" />
              </UFormGroup>
              <UFormGroup label="Extension *" required>
                <UInput v-model="form.extension" placeholder="ej. s" class="font-mono" />
              </UFormGroup>
              <UFormGroup label="Priority *" required>
                <UInput v-model.number="form.priority" type="number" min="1" placeholder="1" class="font-mono" />
              </UFormGroup>
            </div>
          </div>

          <!-- Destino de fallo -->
          <div>
            <div class="flex items-center gap-2 mb-2">
              <p class="text-sm font-semibold text-gray-700">Destino de fallo</p>
              <UBadge color="gray" variant="soft" size="xs">Opcional</UBadge>
            </div>
            <div class="grid grid-cols-3 gap-3">
              <UFormGroup label="Context (fallo)">
                <UInput v-model="form.failover_context" placeholder="ej. default" class="font-mono" />
              </UFormGroup>
              <UFormGroup label="Extension (fallo)">
                <UInput v-model="form.failover_extension" placeholder="ej. h" class="font-mono" />
              </UFormGroup>
              <UFormGroup label="Priority (fallo)">
                <UInput v-model.number="form.failover_priority" type="number" min="1" placeholder="1" class="font-mono" />
              </UFormGroup>
            </div>
          </div>

          <!-- Activo -->
          <UFormGroup label="Estado">
            <div class="flex items-center gap-3">
              <UToggle v-model="form.is_active" />
              <span class="text-sm text-gray-600">{{ form.is_active ? 'Activo' : 'Inactivo' }}</span>
            </div>
          </UFormGroup>
        </form>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="gray" variant="outline" :disabled="saving" @click="closeModal">Cancelar</UButton>
            <UButton :loading="saving" @click="saveDestination">
              {{ editingDestination ? 'Guardar cambios' : 'Crear destino' }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })

const toast = useToast()

// ── Estado ──────────────────────────────────────────────────────────────
const destinations = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const filterActive = ref('')

const isModalOpen = ref(false)
const saving = ref(false)
const editingDestination = ref<any>(null)

const emptyForm = () => ({
  name: '',
  description: '',
  context: '',
  extension: 's',
  priority: 1,
  failover_context: '',
  failover_extension: '',
  failover_priority: null as number | null,
  is_active: true,
})

const form = ref(emptyForm())

// ── Opciones ────────────────────────────────────────────────────────────
const activeOptions = [
  { label: 'Todos', value: '' },
  { label: 'Activos', value: 'true' },
  { label: 'Inactivos', value: 'false' },
]

const columns = [
  { key: 'name', label: 'Nombre', sortable: true },
  { key: 'context', label: 'Context' },
  { key: 'extension', label: 'Extension' },
  { key: 'priority', label: 'Priority' },
  { key: 'failover', label: 'Fallo (ctx/ext/prio)' },
  { key: 'is_active', label: 'Activo' },
  { key: 'actions', label: '' },
]

// ── Helpers ─────────────────────────────────────────────────────────────
const apiBase = '/api'

function authHeaders() {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// ── CRUD ─────────────────────────────────────────────────────────────────
async function fetchDestinations() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (search.value) params.search = search.value
    if (filterActive.value !== '') params.is_active = filterActive.value

    const qs = new URLSearchParams(params).toString()
    const data = await $fetch<any>(`${apiBase}/telephony/custom-destinations/${qs ? '?' + qs : ''}`, {
      headers: authHeaders(),
    })
    destinations.value = Array.isArray(data) ? data : (data.results ?? [])
  } catch {
    toast.add({ title: 'Error al cargar destinos', color: 'red' })
  } finally {
    loading.value = false
  }
}

async function saveDestination() {
  if (!form.value.name || !form.value.context || !form.value.extension) {
    toast.add({ title: 'Completa los campos requeridos (nombre, context, extension)', color: 'orange' })
    return
  }

  saving.value = true
  try {
    const payload = { ...form.value }
    // Limpiar failover si está vacío
    if (!payload.failover_context) {
      payload.failover_context = ''
      payload.failover_extension = ''
      payload.failover_priority = null
    }

    if (editingDestination.value) {
      await $fetch(`${apiBase}/telephony/custom-destinations/${editingDestination.value.id}/`, {
        method: 'PUT',
        headers: authHeaders(),
        body: payload,
      })
      toast.add({ title: 'Destino actualizado', color: 'green' })
    } else {
      await $fetch(`${apiBase}/telephony/custom-destinations/`, {
        method: 'POST',
        headers: authHeaders(),
        body: payload,
      })
      toast.add({ title: 'Destino creado', color: 'green' })
    }

    closeModal()
    await fetchDestinations()
  } catch (err: any) {
    const detail = err?.data?.name?.[0] ?? err?.data?.detail ?? 'Error al guardar'
    toast.add({ title: detail, color: 'red' })
  } finally {
    saving.value = false
  }
}

async function toggleActive(row: any) {
  try {
    await $fetch(`${apiBase}/telephony/custom-destinations/${row.id}/`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: { is_active: !row.is_active },
    })
    row.is_active = !row.is_active
  } catch {
    toast.add({ title: 'Error al cambiar estado', color: 'red' })
  }
}

async function deleteDestination(row: any) {
  if (!confirm(`¿Eliminar el destino "${row.name}"?`)) return
  try {
    await $fetch(`${apiBase}/telephony/custom-destinations/${row.id}/`, {
      method: 'DELETE',
      headers: authHeaders(),
    })
    toast.add({ title: 'Destino eliminado', color: 'green' })
    await fetchDestinations()
  } catch {
    toast.add({ title: 'Error al eliminar', color: 'red' })
  }
}

// ── Modal ────────────────────────────────────────────────────────────────
function openModal(destination?: any) {
  if (destination) {
    editingDestination.value = destination
    form.value = {
      name: destination.name,
      description: destination.description ?? '',
      context: destination.context,
      extension: destination.extension,
      priority: destination.priority,
      failover_context: destination.failover_context ?? '',
      failover_extension: destination.failover_extension ?? '',
      failover_priority: destination.failover_priority ?? null,
      is_active: destination.is_active,
    }
  } else {
    editingDestination.value = null
    form.value = emptyForm()
  }
  isModalOpen.value = true
}

function closeModal() {
  isModalOpen.value = false
  editingDestination.value = null
  form.value = emptyForm()
}

// ── Init ─────────────────────────────────────────────────────────────────
onMounted(fetchDestinations)
</script>
