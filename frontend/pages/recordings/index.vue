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

// Datos demo 
const recordings = ref([
  {
    id: 1,
    call_id: 'CALL-001-2026',
    caller: '+57 300 123 4567',
    agent: 'Juan Pérez',
    duration: 185, // segundos
    created_at: '2026-02-11T10:30:00Z',
    status: 'Completada',
    file_url: '/media/recordings/call-001.wav',
    file_size: '2.1 MB'
  },
  {
    id: 2,
    call_id: 'CALL-002-2026',
    caller: '+57 301 987 6543',
    agent: 'María García',
    duration: 92,
    created_at: '2026-02-11T11:15:00Z',
    status: 'Completada',
    file_url: '/media/recordings/call-002.wav',
    file_size: '1.3 MB'
  },
  {
    id: 3,
    call_id: 'CALL-003-2026',
    caller: '+57 302 555 7890',
    agent: 'Carlos Rodríguez',
    duration: 245,
    created_at: '2026-02-11T12:45:00Z',
    status: 'Procesando',
    file_url: '/media/recordings/call-003.wav',
    file_size: '3.2 MB'
  }
])

const totalRecordings = ref(25)

// Opciones de agentes
const agentOptions = [
  { label: 'Todos los agentes', value: '' },
  { label: 'Juan Pérez', value: 'juan' },
  { label: 'María García', value: 'maria' },
  { label: 'Carlos Rodríguez', value: 'carlos' }
]

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
    case 'Completada': return 'green'
    case 'Procesando': return 'yellow'
    case 'Error': return 'red'
    default: return 'gray'
  }
}

// Acciones
const playRecording = (recording: any) => {
  selectedRecording.value = recording
  showPlayer.value = true
}

const downloadRecording = (recording: any) => {
  // Implementar descarga
  window.open(recording.file_url, '_blank')
}

const deleteRecording = (recording: any) => {
  // Implementar confirmación y eliminación
  console.log('Eliminar grabación:', recording.id)
}

// Metadata de la página
useHead({
  title: 'Grabaciones - VozipOmni'
})
</script>