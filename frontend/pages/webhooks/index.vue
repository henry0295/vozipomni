<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Webhooks</h1>
        <p class="text-sm text-gray-500 mt-1">Integración de eventos en tiempo real</p>
      </div>
      <UButton icon="i-heroicons-plus" color="primary" @click="openCreate">
        Nuevo Webhook
      </UButton>
    </div>

    <!-- Lista de endpoints -->
    <div class="grid gap-4">
      <UCard v-for="wh in webhooks" :key="wh.id">
        <div class="flex items-start justify-between">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <h3 class="font-semibold text-gray-900">{{ wh.name }}</h3>
              <UBadge :color="wh.is_active ? 'green' : 'gray'" size="xs">
                {{ wh.is_active ? 'Activo' : 'Inactivo' }}
              </UBadge>
            </div>
            <p class="text-sm text-gray-500 truncate font-mono">{{ wh.url }}</p>
            <div class="flex gap-2 mt-2 flex-wrap">
              <UBadge
                v-for="evt in (wh.events || []).slice(0, 5)"
                :key="evt"
                color="blue"
                size="xs"
                variant="soft"
              >{{ evt }}</UBadge>
              <span v-if="(wh.events || []).length > 5" class="text-xs text-gray-400">
                +{{ wh.events.length - 5 }} más
              </span>
            </div>
          </div>
          <div class="flex gap-2 ml-4 shrink-0">
            <UButton
              size="xs"
              color="blue"
              variant="soft"
              icon="i-heroicons-play"
              :loading="testingId === wh.id"
              @click="testWebhook(wh)"
            >
              Probar
            </UButton>
            <UButton
              size="xs"
              color="gray"
              variant="soft"
              icon="i-heroicons-clock"
              @click="viewDeliveries(wh)"
            >
              Historial
            </UButton>
            <UButton
              size="xs"
              color="yellow"
              variant="soft"
              icon="i-heroicons-pencil"
              @click="openEdit(wh)"
            />
            <UButton
              size="xs"
              color="red"
              variant="soft"
              icon="i-heroicons-trash"
              @click="deleteWebhook(wh.id)"
            />
          </div>
        </div>
        <!-- Stats -->
        <div class="grid grid-cols-3 gap-3 mt-4 pt-3 border-t text-center text-xs">
          <div>
            <p class="font-semibold text-gray-700">{{ wh.total_deliveries || 0 }}</p>
            <p class="text-gray-400">Total envíos</p>
          </div>
          <div>
            <p class="font-semibold text-green-600">{{ wh.successful_deliveries || 0 }}</p>
            <p class="text-gray-400">Exitosos</p>
          </div>
          <div>
            <p class="font-semibold text-red-500">{{ wh.failed_deliveries || 0 }}</p>
            <p class="text-gray-400">Fallidos</p>
          </div>
        </div>
      </UCard>
      <div v-if="!loading && webhooks.length === 0" class="text-center py-12 text-gray-400">
        <UIcon name="i-heroicons-link" class="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>No hay webhooks configurados</p>
      </div>
    </div>

    <!-- Modal: Crear/Editar -->
    <UModal v-model="showForm" :ui="{ width: 'sm:max-w-4xl' }">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">{{ editId ? 'Editar Webhook' : 'Nuevo Webhook' }}</h3>
        </template>

        <div class="space-y-4">
          <UAlert
            icon="i-heroicons-information-circle"
            color="blue"
            variant="soft"
            title="Recomendaciones"
            description="Configure el secret HMAC para validar la autenticidad de las peticiones. Habilite reintentos para mejorar la fiabilidad."
          />

          <UTabs v-model="activeTabWebhook" :items="tabItemsWebhook">
            <template #default="{ item }">
              <div v-if="item.slot === 'basic'" class="space-y-4 pt-4">
                <div class="border rounded-lg p-4 space-y-4">
                  <h4 class="font-semibold text-sm text-gray-700 dark:text-gray-300">Información Básica</h4>
                  <div class="grid grid-cols-2 gap-4">
                    <UFormGroup label="Nombre" required class="col-span-2">
                      <UInput v-model="form.name" placeholder="Mi webhook" />
                    </UFormGroup>
                    <UFormGroup label="URL" required class="col-span-2">
                      <UInput v-model="form.url" placeholder="https://mi-sistema.com/webhook" />
                    </UFormGroup>
                  </div>
                  <UFormGroup label="Eventos a notificar">
                    <div class="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto border rounded-lg p-3">
                      <label
                        v-for="evt in availableEvents"
                        :key="evt.value"
                        class="flex items-center gap-2 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          :value="evt.value"
                          :checked="form.events.includes(evt.value)"
                          class="rounded"
                          @change="toggleEvent(evt.value)"
                        />
                        <span class="text-xs">{{ evt.value }}</span>
                      </label>
                    </div>
                  </UFormGroup>
                </div>
              </div>

              <div v-if="item.slot === 'security'" class="space-y-4 pt-4">
                <div class="border rounded-lg p-4 space-y-4">
                  <h4 class="font-semibold text-sm text-gray-700 dark:text-gray-300">Seguridad</h4>
                  <UFormGroup label="Secret (HMAC)" help="Clave secreta para firma HMAC de peticiones">
                    <UInput v-model="form.secret" type="password" placeholder="Opcional pero recomendado" />
                  </UFormGroup>
                </div>
              </div>

              <div v-if="item.slot === 'config'" class="space-y-4 pt-4">
                <div class="border rounded-lg p-4 space-y-4">
                  <h4 class="font-semibold text-sm text-gray-700 dark:text-gray-300">Configuración Avanzada</h4>
                  <div class="grid grid-cols-2 gap-4">
                    <UFormGroup label="Timeout (segundos)">
                      <UInput v-model="form.timeout_seconds" type="number" min="1" max="30" />
                    </UFormGroup>
                  </div>
                  <div class="flex items-center gap-3">
                    <UToggle v-model="form.is_active" />
                    <span class="text-sm">Webhook Activo</span>
                  </div>
                  <div class="flex items-center gap-3">
                    <UToggle v-model="form.retry_on_failure" />
                    <span class="text-sm">Reintentar en fallos</span>
                  </div>
                </div>
              </div>
            </template>
          </UTabs>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" @click="showForm = false">Cancelar</UButton>
            <UButton color="sky" :loading="saving" @click="saveWebhook">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal: Historial de entregas -->
    <UModal v-model="showDeliveries" :ui="{ width: 'sm:max-w-3xl' }">
      <UCard>
        <template #header>
          <h3 class="font-semibold">Historial de entregas — {{ selectedWh?.name }}</h3>
        </template>
        <UTable
          :rows="deliveries"
          :columns="deliveryColumns"
          :loading="loadingDeliveries"
          empty-state-label="Sin entregas registradas"
        >
          <template #success-data="{ row }">
            <UIcon
              :name="row.success ? 'i-heroicons-check-circle' : 'i-heroicons-x-circle'"
              :class="row.success ? 'text-green-500' : 'text-red-500'"
              class="w-4 h-4"
            />
          </template>
          <template #created_at-data="{ row }">
            <span class="text-xs">{{ formatDate(row.created_at) }}</span>
          </template>
        </UTable>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const webhooks = ref<any[]>([])
const loading = ref(false)
const saving = ref(false)
const showForm = ref(false)
const editId = ref<number | null>(null)
const testingId = ref<number | null>(null)
const showDeliveries = ref(false)
const selectedWh = ref<any>(null)
const deliveries = ref<any[]>([])
const loadingDeliveries = ref(false)
const availableEvents = ref<any[]>([])
const activeTabWebhook = ref(0)

const tabItemsWebhook = [
  { slot: 'basic', label: 'Básica', icon: 'i-heroicons-identification' },
  { slot: 'security', label: 'Seguridad', icon: 'i-heroicons-lock-closed' },
  { slot: 'config', label: 'Configuración', icon: 'i-heroicons-cog-6-tooth' }
]

const form = ref({
  name: '', url: '', secret: '', events: [] as string[],
  is_active: true, retry_on_failure: true, timeout_seconds: 10,
})

const deliveryColumns = [
  { key: 'event_type', label: 'Evento' },
  { key: 'status_code', label: 'HTTP' },
  { key: 'success', label: 'OK' },
  { key: 'duration_ms', label: 'ms' },
  { key: 'attempt', label: 'Intento' },
  { key: 'created_at', label: 'Fecha' },
]

const authHeaders = () => ({ Authorization: 'Bearer ' + localStorage.getItem('auth_token') })

const loadWebhooks = async () => {
  loading.value = true
  try {
    const data = await $fetch('/api/webhooks/', { headers: authHeaders() })
    webhooks.value = (data as any).results || data
  } catch { webhooks.value = [] }
  finally { loading.value = false }
}

const loadAvailableEvents = async () => {
  try {
    const data = await $fetch('/api/webhooks/available_events/', { headers: authHeaders() })
    availableEvents.value = (data as any).events || []
  } catch { availableEvents.value = [] }
}

const openCreate = async () => {
  editId.value = null
  form.value = { name: '', url: '', secret: '', events: [], is_active: true, retry_on_failure: true, timeout_seconds: 10 }
  await loadAvailableEvents()
  showForm.value = true
}

const openEdit = async (wh: any) => {
  editId.value = wh.id
  form.value = { ...wh, secret: '' }
  await loadAvailableEvents()
  showForm.value = true
}

const toggleEvent = (evt: string) => {
  const idx = form.value.events.indexOf(evt)
  if (idx >= 0) form.value.events.splice(idx, 1)
  else form.value.events.push(evt)
}

const saveWebhook = async () => {
  saving.value = true
  try {
    const body = { ...form.value }
    if (!body.secret) delete (body as any).secret
    if (editId.value) {
      await $fetch(`/api/webhooks/${editId.value}/`, { method: 'PATCH', headers: authHeaders(), body })
    } else {
      await $fetch('/api/webhooks/', { method: 'POST', headers: authHeaders(), body })
    }
    showForm.value = false
    await loadWebhooks()
  } catch (e: any) {
    alert('Error: ' + (e?.data?.detail || JSON.stringify(e?.data)))
  } finally { saving.value = false }
}

const deleteWebhook = async (id: number) => {
  if (!confirm('¿Eliminar este webhook?')) return
  await $fetch(`/api/webhooks/${id}/`, { method: 'DELETE', headers: authHeaders() })
  await loadWebhooks()
}

const testWebhook = async (wh: any) => {
  testingId.value = wh.id
  try {
    const result = await $fetch(`/api/webhooks/${wh.id}/test/`, { method: 'POST', headers: authHeaders() })
    alert((result as any).message || 'Prueba enviada')
  } catch (e: any) {
    alert('Error: ' + (e?.data?.detail || e.message))
  } finally { testingId.value = null }
}

const viewDeliveries = async (wh: any) => {
  selectedWh.value = wh
  showDeliveries.value = true
  loadingDeliveries.value = true
  try {
    const data = await $fetch(`/api/webhooks/${wh.id}/deliveries/`, { headers: authHeaders() })
    deliveries.value = (data as any).results || data
  } catch { deliveries.value = [] }
  finally { loadingDeliveries.value = false }
}

const formatDate = (iso: string) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
}

onMounted(loadWebhooks)
</script>
