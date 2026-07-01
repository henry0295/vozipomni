<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Colas de Llamadas</h1>
      <div class="flex gap-2">
        <UButton
          v-if="error"
          icon="i-heroicons-arrow-path"
          @click="loadQueues"
          :loading="loading"
        >
          Reintentar
        </UButton>
        <UButton
          icon="i-heroicons-plus"
          color="primary"
          @click="openCreateModal"
          :disabled="loading"
        >
          Nueva Cola
        </UButton>
      </div>
    </div>

    <!-- Estado de carga/error -->
    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle">
      {{ error }}
    </UAlert>

    <UCard v-if="loading" class="flex justify-center items-center py-12">
      <div class="text-center space-y-2">
        <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto" />
        <p class="text-gray-500">Cargando colas...</p>
      </div>
    </UCard>

    <!-- Filtros -->
    <UCard v-if="!loading" class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por nombre o extensión..."
            icon="i-heroicons-magnifying-glass"
          />
          <USelect
            v-model="strategyFilter"
            :options="[
              { label: 'Todas', value: '' },
              { label: 'Ring All', value: 'ringall' },
              { label: 'Least Recent', value: 'leastrecent' },
              { label: 'Fewest Calls', value: 'fewestcalls' },
              { label: 'Random', value: 'random' },
              { label: 'Round Robin', value: 'rrmemory' },
              { label: 'Linear', value: 'linear' }
            ]"
            option-attribute="label"
            value-attribute="value"
            placeholder="Filtrar por estrategia"
          />
          <USelect
            v-model="statusFilter"
            :options="[
              { label: 'Todas', value: '' },
              { label: 'Activas', value: 'true' },
              { label: 'Inactivas', value: 'false' }
            ]"
            option-attribute="label"
            value-attribute="value"
            placeholder="Filtrar por estado"
          />
        </div>
      </template>

      <!-- Tabla -->
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th class="px-4 py-3 text-left font-semibold">Nombre</th>
              <th class="px-4 py-3 text-left font-semibold">Extensión</th>
              <th class="px-4 py-3 text-left font-semibold">Estrategia</th>
              <th class="px-4 py-3 text-left font-semibold">Timeout</th>
              <th class="px-4 py-3 text-left font-semibold">Máx. Espera</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="queue in filteredQueues" :key="queue.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3 font-semibold">{{ queue.name }}</td>
              <td class="px-4 py-3 font-mono">{{ queue.extension }}</td>
              <td class="px-4 py-3">
                <UBadge color="blue" variant="subtle">{{ getStrategyLabel(queue.strategy) }}</UBadge>
              </td>
              <td class="px-4 py-3">{{ queue.timeout }}s</td>
              <td class="px-4 py-3">{{ queue.max_wait_time }}s</td>
              <td class="px-4 py-3">
                <UBadge :color="queue.is_active ? 'green' : 'gray'" variant="subtle">
                  {{ queue.is_active ? 'Activa' : 'Inactiva' }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editQueue(queue)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteQueue(queue.id)"
                />
              </td>
            </tr>
            <tr v-if="filteredQueues.length === 0 && !loading">
              <td colspan="7" class="px-4 py-8 text-center text-gray-500">
                No hay colas configuradas
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- ============================== -->
    <!-- MODAL CREAR/EDITAR COLA        -->
    <!-- ============================== -->
    <UModal v-model="isModalOpen" :ui="{ width: 'sm:max-w-5xl' }">
      <UCard>
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">
              {{ editingId ? 'Editar Cola' : 'Nueva Cola de Llamadas' }}
            </h3>
            <UButton icon="i-heroicons-x-mark" color="gray" variant="ghost" @click="isModalOpen = false" />
          </div>
        </template>

        <!-- Tabs de secciones -->
        <UTabs :items="queueTabs" v-model="activeQueueTab">
          <!-- ===== TAB 1: INFORMACIÓN BÁSICA ===== -->
          <template #basica="{ item }">
            <div class="space-y-5 py-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Nombre de la Cola" required help="Nombre descriptivo para la cola">
                  <UInput v-model="form.name" placeholder="Soporte General" />
                </UFormGroup>

                <UFormGroup label="Extensión" required help="Número para acceder a la cola">
                  <UInput v-model="form.extension" placeholder="500" />
                </UFormGroup>
              </div>

              <UFormGroup label="Descripción">
                <UTextarea v-model="form.description" placeholder="Descripción de la cola" :rows="3" />
              </UFormGroup>

              <!-- Estrategia de distribución -->
              <UFormGroup label="Estrategia de Distribución" required help="Cómo se distribuyen las llamadas entre agentes">
                <USelectMenu
                  v-model="form.strategy"
                  :options="strategyOptions"
                  value-attribute="value"
                  option-attribute="label"
                />
              </UFormGroup>

              <!-- Descripción de estrategias -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <UAlert 
                  icon="i-heroicons-bell-alert" 
                  color="purple" 
                  variant="subtle"
                  title="Ring All"
                  description="Timbran todos los agentes simultáneamente. El primero en contestar toma la llamada."
                />
                <UAlert 
                  icon="i-heroicons-arrow-path" 
                  color="blue" 
                  variant="subtle"
                  title="Round Robin"
                  description="Distribución circular con memoria. Recuerda el último agente que contestó."
                />
                <UAlert 
                  icon="i-heroicons-chart-bar" 
                  color="green" 
                  variant="subtle"
                  title="Fewest Calls"
                  description="Prioriza al agente con menos llamadas atendidas."
                />
                <UAlert 
                  icon="i-heroicons-clock" 
                  color="orange" 
                  variant="subtle"
                  title="Least Recent"
                  description="Llama al agente que más tiempo lleva sin atender una llamada."
                />
              </div>

              <div class="flex items-center space-x-4 pt-2">
                <UCheckbox v-model="form.is_active" label="Cola Activa" />
              </div>
            </div>
          </template>

          <!-- ===== TAB 2: TIEMPOS Y LÍMITES ===== -->
          <template #tiempos="{ item }">
            <div class="space-y-5 py-4">
              <!-- Tiempos de timbre -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-clock" class="text-blue-500" />
                  <h4 class="font-medium text-gray-800">Tiempos de Timbre</h4>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Timeout (segundos)" help="Tiempo que timbra en cada agente">
                    <UInput v-model.number="form.timeout" type="number" min="5" max="300" />
                  </UFormGroup>

                  <UFormGroup label="Reintentar (segundos)" help="Pausa antes de volver a intentar">
                    <UInput v-model.number="form.retry" type="number" min="0" max="60" />
                  </UFormGroup>
                </div>

                <UAlert 
                  icon="i-heroicons-information-circle" 
                  color="blue" 
                  variant="subtle"
                  description="Timeout: tiempo que suena en cada agente (30s recomendado). Retry: pausa entre intentos (5s recomendado)."
                />
              </div>

              <!-- Límites -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-shield-check" class="text-green-500" />
                  <h4 class="font-medium text-gray-800">Límites de Cola</h4>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Tiempo Máximo de Espera (seg)" help="0 = sin límite">
                    <UInput v-model.number="form.max_wait_time" type="number" min="0" max="3600" />
                  </UFormGroup>

                  <UFormGroup label="Máximo de Llamadas en Cola" help="0 = ilimitado">
                    <UInput v-model.number="form.max_callers" type="number" min="0" />
                  </UFormGroup>
                </div>

                <UAlert 
                  icon="i-heroicons-exclamation-triangle" 
                  color="yellow" 
                  variant="subtle"
                  description="Si se supera el tiempo o número máximo, la llamada seguirá el enrutamiento de overflow configurado."
                />
              </div>

              <!-- Service Level y Wrap-up -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <UFormGroup label="Nivel de Servicio (seg)" help="Meta de tiempo de respuesta para métricas">
                  <UInput v-model.number="form.service_level" type="number" min="0" />
                </UFormGroup>

                <UFormGroup label="Wrap-up Time (seg)" help="Tiempo post-llamada antes de recibir otra">
                  <UInput v-model.number="form.wrap_up_time" type="number" min="0" />
                </UFormGroup>
              </div>
            </div>
          </template>

          <!-- ===== TAB 3: ANUNCIOS Y MÚSICA ===== -->
          <template #anuncios="{ item }">
            <div class="space-y-5 py-4">
              <!-- Anuncios -->
              <div class="border border-blue-200 bg-blue-50 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-speaker-wave" class="text-blue-600" />
                  <h4 class="font-medium text-blue-800">Configuración de Anuncios</h4>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UFormGroup label="Frecuencia de Anuncios (seg)" help="0 = sin anuncios">
                    <UInput v-model.number="form.announce_frequency" type="number" min="0" />
                  </UFormGroup>

                  <UFormGroup label="Anuncios Periódicos (seg)" help="Frecuencia de anuncios repetitivos">
                    <UInput v-model.number="form.periodic_announce_frequency" type="number" min="0" />
                  </UFormGroup>
                </div>

                <div class="flex items-center space-x-4">
                  <UCheckbox v-model="form.announce_holdtime" label="Anunciar tiempo de espera estimado" />
                </div>

                <UAlert 
                  icon="i-heroicons-information-circle" 
                  color="blue" 
                  variant="subtle"
                  description="Los anuncios periódicos informan al cliente sobre su posición en cola y tiempo estimado de espera."
                />
              </div>

              <!-- Música en espera -->
              <div class="border border-gray-200 rounded-lg p-4 space-y-4">
                <div class="flex items-center space-x-2">
                  <UIcon name="i-heroicons-musical-note" class="text-purple-500" />
                  <h4 class="font-medium text-gray-800">Música en Espera</h4>
                </div>

                <UFormGroup label="Clase de MOH" help="Categoría de música on hold">
                  <UInput v-model="form.music_on_hold" placeholder="default" />
                </UFormGroup>

                <UAlert 
                  icon="i-heroicons-musical-note" 
                  color="purple" 
                  variant="subtle"
                  description="La música en espera se reproduce mientras el llamante aguarda a ser atendido. Puedes configurar clases personalizadas en /var/lib/asterisk/moh/"
                />
              </div>
            </div>
          </template>
        </UTabs>

        <template #footer>
          <div class="flex justify-end gap-3">
            <UButton color="gray" variant="outline" @click="isModalOpen = false" :disabled="isSaving">
              Cancelar
            </UButton>
            <UButton color="sky" @click="saveQueue" :loading="isSaving">
              {{ editingId ? 'Guardar Cambios' : 'Crear Cola' }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

definePageMeta({
  middleware: ['auth']
})

useHead({ title: 'Colas de Llamadas' })

interface QueueItem {
  id: number
  name: string
  extension: string
  description: string
  strategy: string
  timeout: number
  retry: number
  max_wait_time: number
  announce_frequency: number
  announce_holdtime: boolean
  periodic_announce_frequency: number
  music_on_hold: string
  max_callers: number
  service_level: number
  wrap_up_time: number
  is_active: boolean
}

const strategyOptions = [
  { label: 'Ring All - Timbran todos', value: 'ringall' },
  { label: 'Least Recent - Menos reciente', value: 'leastrecent' },
  { label: 'Fewest Calls - Menos llamadas', value: 'fewestcalls' },
  { label: 'Random - Aleatorio', value: 'random' },
  { label: 'Round Robin Memory', value: 'rrmemory' },
  { label: 'Linear - Lineal', value: 'linear' }
]

const queues = ref<QueueItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const strategyFilter = ref('')
const statusFilter = ref('')
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)
const activeQueueTab = ref(0)

const { apiFetch } = useApi()

// Tabs del modal
const queueTabs = [
  { slot: 'basica', label: 'Información Básica', icon: 'i-heroicons-queue-list' },
  { slot: 'tiempos', label: 'Tiempos y Límites', icon: 'i-heroicons-clock' },
  { slot: 'anuncios', label: 'Anuncios y Música', icon: 'i-heroicons-speaker-wave' }
]

const defaultForm = () => ({
  name: '',
  extension: '',
  description: '',
  strategy: 'ringall',
  timeout: 30,
  retry: 5,
  max_wait_time: 300,
  announce_frequency: 30,
  announce_holdtime: true,
  periodic_announce_frequency: 60,
  music_on_hold: 'default',
  max_callers: 0,
  service_level: 60,
  wrap_up_time: 0,
  is_active: true
})

const form = ref(defaultForm())

const filteredQueues = computed(() => {
  return queues.value.filter(queue => {
    const matchesSearch =
      queue.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      queue.extension.includes(searchQuery.value)
    const matchesStrategy = !strategyFilter.value || queue.strategy === strategyFilter.value
    const matchesStatus = !statusFilter.value || String(queue.is_active) === statusFilter.value
    return matchesSearch && matchesStrategy && matchesStatus
  })
})

const getStrategyLabel = (strategy: string) => {
  return strategyOptions.find(s => s.value === strategy)?.label?.split(' - ')[0] || strategy
}

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
}

const editQueue = (queue: QueueItem) => {
  form.value = { ...queue }
  editingId.value = queue.id
  isModalOpen.value = true
}

const loadQueues = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<any>('/queues/')
  if (fetchError.value) {
    error.value = 'Error al cargar las colas'
    console.error('Error loading queues:', fetchError.value)
  } else {
    const raw = data.value
    queues.value = Array.isArray(raw) ? raw : (raw?.results || [])
  }
  loading.value = false
}

const saveQueue = async () => {
  isSaving.value = true
  error.value = null
  try {
    if (editingId.value) {
      const { error: saveError } = await apiFetch(`/queues/${editingId.value}/`, {
        method: 'PUT',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar la cola')
    } else {
      const { error: saveError } = await apiFetch('/queues/', {
        method: 'POST',
        body: form.value
      })
      if (saveError.value) throw new Error('Error al guardar la cola')
    }
    await loadQueues()
    isModalOpen.value = false
  } catch (err) {
    error.value = 'Error al guardar la cola'
    console.error('Error saving queue:', err)
  } finally {
    isSaving.value = false
  }
}

const deleteQueue = async (id: number) => {
  if (confirm('¿Estás seguro de que deseas eliminar esta cola?')) {
    try {
      const { error: delError } = await apiFetch(`/queues/${id}/`, { method: 'DELETE' })
      if (delError.value) throw new Error('Error al eliminar la cola')
      await loadQueues()
    } catch (err) {
      error.value = 'Error al eliminar la cola'
      console.error('Error deleting queue:', err)
    }
  }
}

const resetForm = () => {
  form.value = defaultForm()
  editingId.value = null
}

onMounted(() => loadQueues())
</script>
