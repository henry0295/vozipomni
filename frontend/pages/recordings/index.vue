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
          
          <audio controls class="w-full">
            <source :src="selectedRecording?.file_url" type="audio/wav">
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

// Estados reactivos
const loading = ref(false)
const error = ref<string | null>(null)
const page = ref(1)
const showPlayer = ref(false)
const selectedRecording = ref(null)

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
const playRecording = (recording: any) => {
  selectedRecording.value = recording
  showPlayer.value = true
}

const downloadRecording = (recording: any) => {
  if (recording.file_url) {
    window.open(recording.file_url, '_blank')
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
  const { getRecordings } = useRecordings()
  const result = await getRecordings({ page: page.value })
  if (result.error) {
    error.value = 'Error al cargar grabaciones'
    recordings.value = []
    totalRecordings.value = 0
  } else {
    recordings.value = result.data.map(recording => ({
      id: recording.id,
      call_id: recording.call_details?.call_id || `CALL-${recording.call}`,
      caller: recording.call_details?.caller_id || '-',
      agent: recording.call_details?.agent_name || '-',
      duration: recording.duration || 0,
      created_at: recording.created_at,
      status: recording.status,
      file_url: recording.file_path,
      file_size: `${recording.file_size_mb || 0} MB`
    }))
    totalRecordings.value = result.total || 0
  }
  loading.value = false
}

// Metadata de la página
useHead({
  title: 'Grabaciones - VozipOmni'
})

onMounted(() => {
  loadRecordings()
})
</script>