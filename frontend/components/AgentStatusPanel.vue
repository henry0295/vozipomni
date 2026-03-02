<template>
  <div class="agent-status-panel">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">Estado del Agente</h3>
          <UBadge :color="statusColor" size="lg">
            {{ statusLabel }}
          </UBadge>
        </div>
      </template>

      <!-- Información del agente -->
      <div class="space-y-4">
        <div class="flex items-center gap-3 pb-4 border-b border-gray-200">
          <UAvatar
            :alt="agentName"
            size="xl"
          />
          <div class="flex-1">
            <p class="font-semibold text-lg">{{ agentName }}</p>
            <p class="text-sm text-gray-600">Ext: {{ agentExtension }}</p>
          </div>
        </div>

        <!-- Selector de estado -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-gray-700">Cambiar Estado</label>
          <USelectMenu
            v-model="selectedStatus"
            :options="statusOptions"
            :disabled="isOnCall"
            @change="handleStatusChange"
          >
            <template #leading>
              <div :class="`w-2 h-2 rounded-full ${statusColor === 'green' ? 'bg-green-500' : statusColor === 'red' ? 'bg-red-500' : statusColor === 'yellow' ? 'bg-yellow-500' : 'bg-gray-500'}`" />
            </template>
          </USelectMenu>
        </div>

        <!-- Botón de pausa -->
        <div v-if="!isOnCall && !isOnBreak" class="pt-2">
          <UButton
            block
            color="yellow"
            variant="soft"
            icon="i-heroicons-pause-circle"
            @click="showBreakModal = true"
          >
            Iniciar Pausa
          </UButton>
        </div>

        <!-- En pausa - mostrar razón y botón para terminar -->
        <div v-if="isOnBreak" class="pt-2 space-y-2">
          <div class="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
            <div class="flex items-center gap-2">
              <UIcon name="i-heroicons-pause-circle" class="text-yellow-600" />
              <span class="text-sm font-medium text-yellow-800">{{ pauseReason }}</span>
            </div>
            <span class="text-xs text-yellow-600">{{ formatTime(pauseDuration) }}</span>
          </div>
          <UButton
            block
            color="green"
            icon="i-heroicons-play-circle"
            @click="endBreak"
          >
            Terminar Pausa
          </UButton>
        </div>

        <!-- Estadísticas del día -->
        <div class="pt-4 border-t border-gray-200">
          <p class="text-sm font-medium text-gray-700 mb-3">Estadísticas de Hoy</p>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-blue-50 p-3 rounded-lg">
              <p class="text-xs text-blue-600 mb-1">Llamadas</p>
              <p class="text-2xl font-bold text-blue-700">{{ stats.callsToday }}</p>
            </div>
            <div class="bg-green-50 p-3 rounded-lg">
              <p class="text-xs text-green-600 mb-1">Tiempo hablando</p>
              <p class="text-lg font-bold text-green-700">{{ formatTime(stats.talkTimeToday) }}</p>
            </div>
            <div class="bg-purple-50 p-3 rounded-lg">
              <p class="text-xs text-purple-600 mb-1">Disponible</p>
              <p class="text-lg font-bold text-purple-700">{{ formatTime(stats.availableTimeToday) }}</p>
            </div>
            <div class="bg-yellow-50 p-3 rounded-lg">
              <p class="text-xs text-yellow-600 mb-1">En pausa</p>
              <p class="text-lg font-bold text-yellow-700">{{ formatTime(stats.breakTimeToday) }}</p>
            </div>
          </div>
        </div>

        <!-- Tiempo de sesión -->
        <div class="pt-4 border-t border-gray-200">
          <div class="flex items-center justify-between">
            <span class="text-sm text-gray-600">Sesión iniciada:</span>
            <span class="text-sm font-medium">{{ formatTime(sessionDuration) }}</span>
          </div>
        </div>
      </div>
    </UCard>

    <!-- Modal de pausa -->
    <UModal v-model="showBreakModal">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Seleccionar Motivo de Pausa</h3>
        </template>

        <div class="space-y-3">
          <UButton
            v-for="breakOption in breakOptions"
            :key="breakOption.id"
            block
            variant="soft"
            color="gray"
            @click="startBreak(breakOption)"
          >
            {{ breakOption.name }}
          </UButton>
        </div>

        <template #footer>
          <div class="flex justify-end">
            <UButton
              color="gray"
              variant="ghost"
              @click="showBreakModal = false"
            >
              Cancelar
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useAgentStore } from '~/stores/agent'

const agentStore = useAgentStore()
const showBreakModal = ref(false)

// Estado seleccionado
const selectedStatus = ref('available')

// Opciones de estado
const statusOptions = [
  { value: 'available', label: 'Disponible' },
  { value: 'busy', label: 'Ocupado' },
  { value: 'wrapup', label: 'Post-llamada' }
]

// Opciones de pausa
const breakOptions = [
  { id: 'bathroom', name: 'Baño' },
  { id: 'meal', name: 'Comida' },
  { id: 'training', name: 'Capacitación' },
  { id: 'meeting', name: 'Reunión' },
  { id: 'personal', name: 'Personal' },
  { id: 'technical', name: 'Problemas Técnicos' }
]

// Computed
const agentName = computed(() => {
  if (!agentStore.agent?.user_details) return 'Agente'
  const user = agentStore.agent.user_details
  return user.first_name || user.username
})

const agentExtension = computed(() => agentStore.agent?.sip_extension || 'N/A')

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    offline: 'Desconectado',
    available: 'Disponible',
    busy: 'Ocupado',
    oncall: 'En Llamada',
    break: 'En Pausa',
    wrapup: 'Post-llamada'
  }
  return labels[agentStore.status] || agentStore.status
})

const statusColor = computed(() => {
  const colors: Record<string, string> = {
    offline: 'gray',
    available: 'green',
    busy: 'yellow',
    oncall: 'blue',
    break: 'yellow',
    wrapup: 'purple'
  }
  return colors[agentStore.status] || 'gray'
})

const isOnCall = computed(() => agentStore.status === 'oncall')
const isOnBreak = computed(() => agentStore.status === 'break')
const pauseReason = computed(() => agentStore.pauseReason || 'Pausa')
const stats = computed(() => agentStore.stats)
const sessionDuration = computed(() => agentStore.sessionDuration)

// Duración de pausa
const pauseDuration = ref(0)
let pauseTimer: any = null

// Métodos
const handleStatusChange = async () => {
  if (selectedStatus.value === agentStore.status) return
  
  const result = await agentStore.changeStatus(selectedStatus.value as any)
  if (!result.success) {
    // Revertir selección
    selectedStatus.value = agentStore.status
    alert(result.error)
  }
}

const startBreak = async (breakOption: any) => {
  showBreakModal.value = false
  const result = await agentStore.startBreak(breakOption.name)
  
  if (result.success) {
    pauseDuration.value = 0
    pauseTimer = setInterval(() => {
      pauseDuration.value++
    }, 1000)
  } else {
    alert(result.error)
  }
}

const endBreak = async () => {
  if (pauseTimer) {
    clearInterval(pauseTimer)
    pauseTimer = null
  }
  pauseDuration.value = 0
  
  const result = await agentStore.endBreak()
  if (!result.success) {
    alert(result.error)
  }
}

const formatTime = (seconds: number) => {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (hrs > 0) {
    return `${hrs}h ${mins}m`
  }
  if (mins > 0) {
    return `${mins}m ${secs}s`
  }
  return `${secs}s`
}

// Lifecycle
onMounted(() => {
  selectedStatus.value = agentStore.status
})

onUnmounted(() => {
  if (pauseTimer) {
    clearInterval(pauseTimer)
  }
})
</script>

<style scoped>
.agent-status-panel {
  height: 100%;
}
</style>
