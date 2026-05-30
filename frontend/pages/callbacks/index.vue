<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Callbacks</h1>
        <p class="text-sm text-gray-500 mt-1">Gestión de rellamadas programadas</p>
      </div>
      <UButton icon="i-heroicons-plus" color="primary" @click="openCreate">
        Nuevo Callback
      </UButton>
    </div>

    <!-- Filtros -->
    <div class="flex flex-wrap gap-3">
      <USelectMenu
        v-model="filterStatus"
        :options="statusOptions"
        value-attribute="value"
        option-attribute="label"
        placeholder="Estado"
        class="w-40"
        @change="loadCallbacks"
      />
      <UInput v-model="filterPhone" placeholder="Buscar por teléfono" icon="i-heroicons-magnifying-glass" @input="loadCallbacks" />
      <UButton icon="i-heroicons-arrow-path" color="gray" variant="ghost" :loading="loading" @click="loadCallbacks">
        Actualizar
      </UButton>
    </div>

    <!-- Tabla -->
    <UCard>
      <UTable
        :rows="callbacks"
        :columns="columns"
        :loading="loading"
        empty-state-label="No hay callbacks registrados"
      >
        <template #status-data="{ row }">
          <UBadge :color="statusColor(row.status)" size="sm">{{ row.status }}</UBadge>
        </template>
        <template #scheduled_at-data="{ row }">
          <span class="text-sm">{{ formatDate(row.scheduled_at) }}</span>
        </template>
        <template #attempts-data="{ row }">
          <span>{{ row.attempts }} / {{ row.max_attempts }}</span>
        </template>
        <template #actions-data="{ row }">
          <div class="flex gap-2">
            <UButton
              v-if="row.status === 'pending' || row.status === 'scheduled'"
              size="xs"
              color="yellow"
              variant="soft"
              icon="i-heroicons-clock"
              @click="openReschedule(row)"
            >
              Reprogramar
            </UButton>
            <UButton
              v-if="row.status !== 'cancelled' && row.status !== 'completed'"
              size="xs"
              color="red"
              variant="soft"
              icon="i-heroicons-x-circle"
              @click="cancelCallback(row.id)"
            >
              Cancelar
            </UButton>
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Modal: Crear callback -->
    <UModal v-model="showCreate">
      <UCard>
        <template #header>
          <h3 class="font-semibold">Programar Callback</h3>
        </template>
        <div class="space-y-4">
          <UFormGroup label="Teléfono" required>
            <UInput v-model="form.phone" placeholder="+57300..." />
          </UFormGroup>
          <UFormGroup label="Nombre del contacto">
            <UInput v-model="form.contact_name" placeholder="Nombre" />
          </UFormGroup>
          <UFormGroup label="Fecha y hora programada">
            <UInput v-model="form.scheduled_at" type="datetime-local" />
          </UFormGroup>
          <UFormGroup label="Prioridad (1-10)">
            <UInput v-model="form.priority" type="number" min="1" max="10" />
          </UFormGroup>
          <UFormGroup label="Intentos máximos">
            <UInput v-model="form.max_attempts" type="number" min="1" max="10" />
          </UFormGroup>
          <UFormGroup label="Notas">
            <UTextarea v-model="form.notes" rows="2" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" @click="showCreate = false">Cancelar</UButton>
            <UButton color="primary" :loading="saving" @click="saveCallback">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal: Reprogramar -->
    <UModal v-model="showReschedule">
      <UCard>
        <template #header>
          <h3 class="font-semibold">Reprogramar Callback</h3>
        </template>
        <UFormGroup label="Nueva fecha y hora">
          <UInput v-model="rescheduleDate" type="datetime-local" />
        </UFormGroup>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" @click="showReschedule = false">Cancelar</UButton>
            <UButton color="primary" :loading="saving" @click="saveReschedule">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const callbacks = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const filterStatus = ref('')
const filterPhone = ref('')
const showCreate = ref(false)
const showReschedule = ref(false)
const rescheduleId = ref<number | null>(null)
const rescheduleDate = ref('')

const form = ref({
  phone: '',
  contact_name: '',
  scheduled_at: '',
  priority: 5,
  max_attempts: 3,
  notes: '',
})

const statusOptions = [
  { value: '', label: 'Todos' },
  { value: 'pending', label: 'Pendiente' },
  { value: 'scheduled', label: 'Programado' },
  { value: 'completed', label: 'Completado' },
  { value: 'cancelled', label: 'Cancelado' },
]

const columns = [
  { key: 'phone', label: 'Teléfono' },
  { key: 'contact_name', label: 'Contacto' },
  { key: 'status', label: 'Estado' },
  { key: 'scheduled_at', label: 'Fecha programada' },
  { key: 'attempts', label: 'Intentos' },
  { key: 'actions', label: 'Acciones' },
]

const authHeaders = () => ({ Authorization: 'Bearer ' + localStorage.getItem('auth_token') })

const loadCallbacks = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filterStatus.value) params.set('status', filterStatus.value)
    if (filterPhone.value) params.set('search', filterPhone.value)
    const data = await $fetch(`/api/callbacks/?${params}`, { headers: authHeaders() })
    callbacks.value = (data as any).results || data
  } catch { callbacks.value = [] }
  finally { loading.value = false }
}

const openCreate = () => {
  form.value = { phone: (route.query.phone as string) || '', contact_name: '', scheduled_at: '', priority: 5, max_attempts: 3, notes: '' }
  showCreate.value = true
}

const saveCallback = async () => {
  saving.value = true
  try {
    await $fetch('/api/callbacks/', {
      method: 'POST',
      headers: authHeaders(),
      body: form.value,
    })
    showCreate.value = false
    await loadCallbacks()
  } catch (e: any) {
    alert('Error: ' + (e?.data?.detail || JSON.stringify(e?.data) || e.message))
  } finally { saving.value = false }
}

const cancelCallback = async (id: number) => {
  if (!confirm('¿Cancelar este callback?')) return
  await $fetch(`/api/callbacks/${id}/cancel/`, { method: 'POST', headers: authHeaders() })
  await loadCallbacks()
}

const openReschedule = (row: any) => {
  rescheduleId.value = row.id
  rescheduleDate.value = row.scheduled_at ? row.scheduled_at.slice(0, 16) : ''
  showReschedule.value = true
}

const saveReschedule = async () => {
  if (!rescheduleId.value) return
  saving.value = true
  try {
    await $fetch(`/api/callbacks/${rescheduleId.value}/reschedule/`, {
      method: 'POST',
      headers: authHeaders(),
      body: { scheduled_at: rescheduleDate.value },
    })
    showReschedule.value = false
    await loadCallbacks()
  } catch (e: any) {
    alert('Error: ' + (e?.data?.detail || e.message))
  } finally { saving.value = false }
}

const statusColor = (s: string) => ({ pending: 'yellow', scheduled: 'blue', completed: 'green', cancelled: 'red', failed: 'red' }[s] || 'gray')

const formatDate = (iso: string) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
}

onMounted(loadCallbacks)
</script>
