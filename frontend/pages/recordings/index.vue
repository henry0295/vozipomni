<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-900">Grabaciones</h1>
      <UButton
        icon="i-heroicons-arrow-down-tray"
        label="Descargar Seleccionadas"
        color="sky"
      />
    </div>

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle">
      {{ error }}
    </UAlert>

    <!-- Filtros -->
    <UCard>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <UFormGroup label="Fecha Desde">
          <UInput 
            type="date" 
            v-model="filters.dateFrom"
            icon="i-heroicons-calendar-days"
          />
        </UFormGroup>
        
        <UFormGroup label="Fecha Hasta">
          <UInput 
            type="date" 
            v-model="filters.dateTo"
            icon="i-heroicons-calendar-days"
          />
        </UFormGroup>
        
        <UFormGroup label="Agente">
          <USelect 
            v-model="filters.agent"
            :options="agentOptions"
            placeholder="Todos los agentes"
          />
        </UFormGroup>
        
        <UFormGroup label="Búsqueda">
          <UInput 
            v-model="filters.search"
            placeholder="Número, cliente..."
            icon="i-heroicons-magnifying-glass"
          />
        </UFormGroup>
      </div>
    </UCard>

    <!-- Tabla de grabaciones -->
    <UCard>
      <UTable 
        :rows="recordings" 
        :columns="columns"
        :loading="loading"
        :empty-state="{ icon: 'i-heroicons-circle-stack-20-solid', label: 'No hay grabaciones disponibles' }"
      >
        <template #duration-data="{ row }">
          <span class="font-mono text-sm">{{ formatDuration(row.duration) }}</span>
        </template>
        
        <template #status-data="{ row }">
          <UBadge 
            :color="getStatusColor(row.status)" 
            :label="row.status" 
          />
        </template>
        
        <template #actions-data="{ row }">
          <div class="flex items-center space-x-2">
            <UButton
              icon="i-heroicons-play"
              size="xs"
              color="sky"
              variant="ghost"
              @click="playRecording(row)"
            />
            <UButton
              icon="i-heroicons-arrow-down-tray"
              size="xs"
              color="gray"
              variant="ghost"
              @click="downloadRecording(row)"
            />
            <UButton
              icon="i-heroicons-trash"
              size="xs"
              color="red"
              variant="ghost"
              @click="deleteRecording(row)"
            />
          </div>
        </template>
      </UTable>

      <!-- Paginación -->
      <div class="flex justify-center mt-4">
        <UPagination 
          v-model="page" 
          :page-count="10" 
          :total="totalRecordings" 
        />
      </div>
    </UCard>

    <!-- Modal de reproducción -->
    <UModal v-model="showPlayer">
      <div class="p-6">
        <h3 class="text-lg font-semibold mb-4">Reproducir Grabación</h3>
        <div class="space-y-4">
          <div>
            <p><strong>Llamada:</strong> {{ selectedRecording?.call_id }}</p>
            <p><strong>Fecha:</strong> {{ formatDate(selectedRecording?.created_at) }}</p>
            <p><strong>Duración:</strong> {{ formatDuration(selectedRecording?.duration) }}</p>
          </div>
          
          <div v-if="audioLoading" class="text-sm text-gray-500">Cargando audio…</div>
          <UAlert v-else-if="audioError" color="red" icon="i-heroicons-exclamation-triangle" :title="audioError" />
          <audio v-else-if="audioUrl" :src="audioUrl" controls autoplay class="w-full" aria-label="Reproductor de la grabación">
            Tu navegador no soporta el elemento de audio.
          </audio>
        </div>
        
        <div class="flex justify-end mt-6 space-x-2">
          <UButton color="gray" @click="showPlayer = false">Cerrar</UButton>
          <UButton 
            icon="i-heroicons-arrow-down-tray" 
            @click="downloadRecording(selectedRecording)"
          >
            Descargar
          </UButton>
        </div>
      </div>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default',
  middleware: 'auth'
})

const http = useHttp()
const toast = useToast()

// Estados reactivos
const loading = ref(false)
const error = ref<string | null>(null)
const page = ref(1)
const showPlayer = ref(false)
const selectedRecording = ref<any>(null)
// El audio se pide autenticado (Bearer) y se reproduce desde un blob: <audio src> no envía el token
const audioUrl = ref('')
const audioLoading = ref(false)
const audioError = ref('')

// Filtros
const filters = reactive({
  dateFrom: '',
  dateTo: '',
  agent: '',
  search: ''
})

const recordings = ref<any[]>([])

const totalRecordings = ref(0)

const agentOptions = computed(() => {
  const agents = new Map<string, string>()
  recordings.value.forEach(recording => {
    const name = recording.agent_name
    if (name) agents.set(name, name)
  })

  return [
    { label: 'Todos los agentes', value: '' },
    ...Array.from(agents.keys()).map(name => ({ label: name, value: name }))
  ]
})

// Columnas de la tabla
const columns = [
  { key: 'call_id', label: 'ID Llamada' },
  { key: 'caller', label: 'Cliente' },
  { key: 'agent', label: 'Agente' },
  { key: 'duration', label: 'Duración' },
  { key: 'created_at', label: 'Fecha' },
  { key: 'status', label: 'Estado' },
  { key: 'actions', label: 'Acciones' }
]

// Funciones utilitarias
const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('es-CO', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed': return 'green'
    case 'recording': return 'yellow'
    case 'failed': return 'red'
    case 'archived': return 'gray'
    default: return 'gray'
  }
}

// Acciones
const releaseAudio = () => {
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
  audioUrl.value = ''
}

const playRecording = async (recording: any) => {
  selectedRecording.value = recording
  showPlayer.value = true
  releaseAudio()
  audioError.value = ''
  audioLoading.value = true
  try {
    const { data } = await http.blob(`/recordings/${recording.id}/download/`, { inline: 1 })
    audioUrl.value = URL.createObjectURL(data)
  } catch (err: any) {
    audioError.value = await http.blobErrorMessage(err, 'No se pudo cargar el audio')
  } finally {
    audioLoading.value = false
  }
}

watch(showPlayer, (open) => { if (!open) releaseAudio() })
onBeforeUnmount(releaseAudio)

const downloadRecording = async (recording: any) => {
  if (!recording) return
  try {
    await http.download(`/recordings/${recording.id}/download/`, undefined, recording.filename || `grabacion-${recording.id}.wav`)
  } catch (err: any) {
    toast.add({ title: 'No se pudo descargar', description: await http.blobErrorMessage(err), color: 'red' })
  }
}

const deleteRecording = async (recording: any) => {
  if (!confirm('¿Estás seguro de eliminar esta grabación?')) return
  const { deleteRecording: deleteRecordingApi } = useRecordings()
  const result = await deleteRecordingApi(recording.id)
  if (!result.error) {
    await loadRecordings()
  }
}

const loadRecordings = async () => {
  loading.value = true
  error.value = null
  try {
    const query: Record<string, any> = { page: page.value }
    if (filters.dateFrom) query.date_from = filters.dateFrom
    if (filters.dateTo) query.date_to = filters.dateTo
    if (filters.search) query.search = filters.search
    const data: any = await http.get('/recordings/', query)
    const rows = http.results<any>(data)
    recordings.value = rows
      .map((recording: any) => {
        const call = recording.call_details || {}
        return {
          id: recording.id,
          filename: recording.filename,
          call_id: call.call_id || `CALL-${recording.call}`,
          // Saliente: el cliente es el número marcado; entrante: quien llama
          caller: (call.direction === 'outbound' ? call.called_number : call.caller_id) || call.caller_id || '-',
          agent: call.agent_name || '-',
          agent_name: call.agent_name || '',
          duration: recording.duration || call.talk_time || 0,
          created_at: recording.created_at,
          status: recording.status,
          file_size: `${recording.file_size_mb || 0} MB`
        }
      })
      .filter((r: any) => !filters.agent || r.agent_name === filters.agent)
    totalRecordings.value = data?.count ?? rows.length
  } catch (err: any) {
    error.value = http.errorMessage(err, 'Error al cargar grabaciones')
    recordings.value = []
    totalRecordings.value = 0
  } finally {
    loading.value = false
  }
}

watch(page, loadRecordings)
let searchTimer: any = null
watch(() => [filters.dateFrom, filters.dateTo, filters.search, filters.agent], () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value === 1 ? loadRecordings() : (page.value = 1) }, 400)
})

// Metadata de la página
useHead({
  title: 'Grabaciones - VozipOmni'
})

onMounted(() => {
  loadRecordings()
})
</script>