<template>
  <div>
    <!-- Botón trigger del popover -->
    <UPopover v-model:open="isOpen" :popper="{ placement: 'bottom-end', offsetDistance: 8 }">
      <button
        class="flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-colors"
        :class="[
          statusColor === 'green'  ? 'border-green-200  bg-green-50  hover:bg-green-100  dark:border-green-800  dark:bg-green-900/30  dark:hover:bg-green-900/50'  : '',
          statusColor === 'blue'   ? 'border-blue-200   bg-blue-50   hover:bg-blue-100   dark:border-blue-800   dark:bg-blue-900/30   dark:hover:bg-blue-900/50'   : '',
          statusColor === 'yellow' ? 'border-yellow-200 bg-yellow-50 hover:bg-yellow-100 dark:border-yellow-800 dark:bg-yellow-900/30 dark:hover:bg-yellow-900/50' : '',
          statusColor === 'purple' ? 'border-purple-200 bg-purple-50 hover:bg-purple-100 dark:border-purple-800 dark:bg-purple-900/30 dark:hover:bg-purple-900/50' : '',
          statusColor === 'gray'   ? 'border-gray-200   bg-gray-50   hover:bg-gray-100   dark:border-gray-700   dark:bg-gray-800      dark:hover:bg-gray-700'      : '',
        ]"
      >
        <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" :class="statusDotClass" />
        <span class="font-medium text-sm text-gray-800 dark:text-gray-200">{{ agentName }}</span>
        <span class="text-xs text-gray-500 dark:text-gray-400 hidden sm:inline">· {{ statusLabel }}</span>
        <UIcon name="i-heroicons-chevron-down" class="w-3.5 h-3.5 text-gray-400 ml-0.5" />
      </button>

      <template #panel>
        <div class="w-72">
          <!-- Encabezado con info del agente -->
          <div class="flex items-center gap-3 p-4 border-b border-gray-200 dark:border-gray-700">
            <UAvatar :alt="agentName" size="md" />
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate">{{ agentName }}</p>
              <p class="text-xs text-gray-500">Ext: {{ agentExtension }}</p>
            </div>
            <UBadge :color="statusColor" size="sm">{{ statusLabel }}</UBadge>
          </div>

          <div class="p-4 space-y-4">
            <!-- Banner de pausa activa -->
            <div
              v-if="isOnBreak"
              class="flex items-center justify-between px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800"
            >
              <div class="flex items-center gap-2">
                <UIcon name="i-heroicons-pause-circle" class="text-yellow-600 w-4 h-4 flex-shrink-0" />
                <span class="text-sm font-medium text-yellow-800 dark:text-yellow-300">{{ pauseReason }}</span>
              </div>
              <span class="text-xs text-yellow-600 dark:text-yellow-400 tabular-nums">{{ formatTime(pauseDuration) }}</span>
            </div>

            <!-- Cambiar Estado -->
            <div>
              <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Cambiar Estado</p>
              <div class="space-y-1">
                <button
                  v-for="opt in statusOptions"
                  :key="opt.value"
                  :disabled="isOnCall || isChangingStatus"
                  class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  :class="agentStore.status === opt.value
                    ? 'bg-gray-100 dark:bg-gray-700 font-semibold cursor-default'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer text-gray-700 dark:text-gray-300'"
                  @click="handleStatusChange(opt.value)"
                >
                  <span class="w-2 h-2 rounded-full flex-shrink-0" :class="opt.dot" />
                  {{ opt.label }}
                  <UIcon
                    v-if="agentStore.status === opt.value"
                    name="i-heroicons-check"
                    class="ml-auto w-3.5 h-3.5 text-gray-500"
                  />
                </button>
              </div>
            </div>

            <!-- Botones de pausa -->
            <div class="border-t border-gray-100 dark:border-gray-700 pt-3">
              <UButton
                v-if="isOnBreak"
                block
                color="green"
                size="sm"
                icon="i-heroicons-play-circle"
                :loading="isChangingStatus"
                @click="endBreak"
              >
                Terminar Pausa
              </UButton>
              <UButton
                v-else-if="!isOnCall"
                block
                color="yellow"
                variant="soft"
                size="sm"
                icon="i-heroicons-pause-circle"
                :disabled="isChangingStatus"
                @click="openBreakModal"
              >
                Iniciar Pausa
              </UButton>
            </div>

            <!-- Estadísticas del día -->
            <div class="border-t border-gray-100 dark:border-gray-700 pt-3">
              <p class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Estadísticas de Hoy</p>
              <div class="grid grid-cols-2 gap-2">
                <div class="text-center p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <p class="text-xl font-bold text-blue-700 dark:text-blue-300">{{ stats.callsToday }}</p>
                  <p class="text-xs text-blue-600 dark:text-blue-400">Llamadas</p>
                </div>
                <div class="text-center p-2 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <p class="text-base font-bold text-green-700 dark:text-green-300 tabular-nums">{{ formatTime(stats.talkTimeToday) }}</p>
                  <p class="text-xs text-green-600 dark:text-green-400">Hablando</p>
                </div>
                <div class="text-center p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <p class="text-base font-bold text-purple-700 dark:text-purple-300 tabular-nums">{{ formatTime(stats.availableTimeToday) }}</p>
                  <p class="text-xs text-purple-600 dark:text-purple-400">Disponible</p>
                </div>
                <div class="text-center p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                  <p class="text-base font-bold text-yellow-700 dark:text-yellow-300 tabular-nums">{{ formatTime(stats.breakTimeToday) }}</p>
                  <p class="text-xs text-yellow-600 dark:text-yellow-400">En Pausa</p>
                </div>
              </div>
            </div>

            <!-- Tiempo de sesión -->
            <div class="border-t border-gray-100 dark:border-gray-700 pt-3 flex items-center justify-between">
              <span class="text-xs text-gray-500">Sesión activa:</span>
              <span class="text-xs font-semibold text-gray-700 dark:text-gray-300 tabular-nums">{{ formatTime(sessionDuration) }}</span>
            </div>
          </div>
        </div>
      </template>
    </UPopover>

    <!-- Modal de pausa (fuera del popover para evitar conflictos de z-index) -->
    <UModal v-model="showBreakModal">
      <UCard>
        <template #header>
          <h3 class="text-base font-semibold">Seleccionar Motivo de Pausa</h3>
        </template>

        <div class="space-y-2">
          <UButton
            v-for="breakOption in breakOptions"
            :key="breakOption.id"
            block
            variant="soft"
            color="gray"
            :loading="isChangingStatus"
            @click="startBreak(breakOption)"
          >
            {{ breakOption.name }}
          </UButton>
        </div>

        <template #footer>
          <div class="flex justify-end">
            <UButton color="gray" variant="ghost" @click="showBreakModal = false">
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
const isOpen = ref(false)
const showBreakModal = ref(false)
const isChangingStatus = ref(false)

// Opciones de estado (solo strings como value)
const statusOptions = [
  { value: 'available', label: 'Disponible', dot: 'bg-green-500' },
  { value: 'busy',      label: 'Ocupado',     dot: 'bg-yellow-500' },
  { value: 'wrapup',    label: 'Post-llamada', dot: 'bg-purple-500' }
]

// Opciones de pausa (se cargan desde la API)
const breakOptions = ref<Array<{ id: string, name: string }>>([])

const loadBreakReasons = async () => {
  try {
    const { $api } = useNuxtApp()
    const data = await $api('/break-reasons/')
    const results = data.results || data
    breakOptions.value = (Array.isArray(results) ? results : []).map((r: any) => ({
      id: r.code || r.id.toString(),
      name: r.name
    }))
  } catch {
    breakOptions.value = [
      { id: 'bathroom',  name: 'Baño' },
      { id: 'meal',      name: 'Comida' },
      { id: 'training',  name: 'Capacitación' },
      { id: 'meeting',   name: 'Reunión' },
      { id: 'personal',  name: 'Personal' },
      { id: 'technical', name: 'Problemas Técnicos' }
    ]
  }
}

// Computed
const agentName = computed(() => {
  if (!agentStore.agent?.user_details) return 'Agente'
  const user = agentStore.agent.user_details
  return user.first_name || user.username
})

const agentExtension = computed(() => agentStore.agent?.sip_extension || 'N/A')

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    offline:   'Desconectado',
    available: 'Disponible',
    busy:      'Ocupado',
    oncall:    'En Llamada',
    break:     'En Pausa',
    wrapup:    'Post-llamada'
  }
  return labels[agentStore.status] || agentStore.status
})

const statusColor = computed(() => {
  const colors: Record<string, string> = {
    offline:   'gray',
    available: 'green',
    busy:      'yellow',
    oncall:    'blue',
    break:     'yellow',
    wrapup:    'purple'
  }
  return colors[agentStore.status] || 'gray'
})

const statusDotClass = computed(() => {
  const classes: Record<string, string> = {
    offline:   'bg-gray-400',
    available: 'bg-green-500',
    busy:      'bg-yellow-500',
    oncall:    'bg-blue-500 animate-pulse',
    break:     'bg-yellow-500',
    wrapup:    'bg-purple-500'
  }
  return classes[agentStore.status] || 'bg-gray-400'
})

const isOnCall  = computed(() => agentStore.status === 'oncall')
const isOnBreak = computed(() => agentStore.status === 'break')
const pauseReason    = computed(() => agentStore.pauseReason || 'Pausa')
const stats          = computed(() => agentStore.stats)
const sessionDuration = computed(() => agentStore.sessionDuration)

const pauseDuration = ref(0)
let pauseTimer: ReturnType<typeof setInterval> | null = null

// Métodos
const handleStatusChange = async (newStatus: string) => {
  if (newStatus === agentStore.status || isChangingStatus.value) return
  isChangingStatus.value = true
  const result = await agentStore.changeStatus(newStatus as any)
  isChangingStatus.value = false
  if (!result.success) {
    alert(result.error)
  } else {
    isOpen.value = false
  }
}

const openBreakModal = () => {
  isOpen.value = false
  // pequeño delay para que el popover cierre antes de abrir el modal
  setTimeout(() => { showBreakModal.value = true }, 150)
}

const startBreak = async (breakOption: { id: string, name: string }) => {
  showBreakModal.value = false
  isChangingStatus.value = true
  const result = await agentStore.startBreak(breakOption.name)
  isChangingStatus.value = false
  if (result.success) {
    pauseDuration.value = 0
    pauseTimer = setInterval(() => { pauseDuration.value++ }, 1000)
  } else {
    alert(result.error)
  }
}

const endBreak = async () => {
  if (pauseTimer) { clearInterval(pauseTimer); pauseTimer = null }
  pauseDuration.value = 0
  isChangingStatus.value = true
  const result = await agentStore.endBreak()
  isChangingStatus.value = false
  if (!result.success) alert(result.error)
}

const formatTime = (seconds: number) => {
  const hrs  = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  if (hrs  > 0) return `${hrs}h ${mins}m`
  if (mins > 0) return `${mins}m ${secs}s`
  return `${secs}s`
}

onMounted(loadBreakReasons)
onUnmounted(() => { if (pauseTimer) clearInterval(pauseTimer) })
</script>
