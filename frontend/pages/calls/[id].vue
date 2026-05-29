<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center gap-4">
      <UButton icon="i-heroicons-arrow-left" color="gray" variant="ghost" @click="navigateTo('/calls')">
        Volver
      </UButton>
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Detalle de Llamada</h1>
        <p class="text-sm text-gray-500 mt-0.5">{{ call?.call_id || `#${route.params.id}` }}</p>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin text-gray-400" />
    </div>

    <UAlert v-else-if="error" color="red" icon="i-heroicons-exclamation-triangle">
      {{ error }}
    </UAlert>

    <template v-else-if="call">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Info principal -->
        <UCard class="lg:col-span-2">
          <template #header>
            <div class="flex items-center justify-between">
              <h2 class="font-semibold text-gray-800">Información de la llamada</h2>
              <UBadge :color="statusColor(call.status)">{{ statusLabel(call.status) }}</UBadge>
            </div>
          </template>

          <dl class="grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
            <div>
              <dt class="text-gray-500">ID de llamada</dt>
              <dd class="font-mono font-medium">{{ call.call_id || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Dirección</dt>
              <dd class="flex items-center gap-1">
                <UIcon
                  :name="call.direction === 'inbound' ? 'i-heroicons-phone-arrow-down-left' : 'i-heroicons-phone-arrow-up-right'"
                  class="h-4 w-4"
                  :class="call.direction === 'inbound' ? 'text-blue-500' : 'text-green-500'"
                />
                {{ call.direction === 'inbound' ? 'Entrante' : 'Saliente' }}
              </dd>
            </div>
            <div>
              <dt class="text-gray-500">Número origen</dt>
              <dd class="font-medium">{{ call.caller_id || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Número destino</dt>
              <dd class="font-medium">{{ call.called_number || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Inicio</dt>
              <dd>{{ formatDateTime(call.start_time) }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Fin</dt>
              <dd>{{ call.end_time ? formatDateTime(call.end_time) : '—' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Duración total</dt>
              <dd class="font-mono">{{ formatDuration(call.duration) }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Tiempo en conversación</dt>
              <dd class="font-mono">{{ formatDuration(call.talk_time) }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Tiempo de espera</dt>
              <dd class="font-mono">{{ formatDuration(call.wait_time) }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Agente</dt>
              <dd>{{ call.agent_name || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Extensión SIP</dt>
              <dd class="font-mono">{{ call.sip_extension || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Cola</dt>
              <dd>{{ call.queue_name || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Campaña</dt>
              <dd>{{ call.campaign_name || '-' }}</dd>
            </div>
            <div>
              <dt class="text-gray-500">Disposición</dt>
              <dd>{{ call.disposition || '-' }}</dd>
            </div>
          </dl>
        </UCard>

        <!-- Grabación -->
        <div class="space-y-4">
          <UCard v-if="call.recording_path || call.recording_url">
            <template #header>
              <h2 class="font-semibold text-gray-800 flex items-center gap-2">
                <UIcon name="i-heroicons-microphone" />
                Grabación
              </h2>
            </template>
            <div class="space-y-3">
              <audio controls class="w-full">
                <source :src="call.recording_url || call.recording_path" type="audio/wav">
                Tu navegador no soporta el elemento de audio.
              </audio>
              <UButton
                icon="i-heroicons-arrow-down-tray"
                color="gray"
                variant="outline"
                block
                size="sm"
                :href="call.recording_url || call.recording_path"
                target="_blank"
              >
                Descargar grabación
              </UButton>
            </div>
          </UCard>
          <UCard v-else>
            <div class="text-center py-4 text-gray-400">
              <UIcon name="i-heroicons-microphone-slash" class="h-8 w-8 mx-auto mb-2" />
              <p class="text-sm">Sin grabación disponible</p>
            </div>
          </UCard>

          <!-- Notas/Disposición -->
          <UCard>
            <template #header>
              <h2 class="font-semibold text-gray-800">Notas</h2>
            </template>
            <p v-if="call.notes" class="text-sm text-gray-700 whitespace-pre-wrap">{{ call.notes }}</p>
            <p v-else class="text-sm text-gray-400">Sin notas</p>
          </UCard>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'] })

const route = useRoute()
const toast = useToast()
const loading = ref(true)
const error = ref<string | null>(null)
const call = ref<any>(null)

function authHeaders() {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const formatDuration = (seconds: number) => {
  if (!seconds || seconds < 0) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const formatDateTime = (dt: string) => {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('es-CO')
}

const statusLabel = (s: string) => {
  const m: Record<string, string> = {
    completed: 'Completada', answered: 'Contestada', no_answer: 'No contestada',
    busy: 'Ocupado', failed: 'Fallida', cancelled: 'Cancelada',
    initiated: 'Iniciada', ringing: 'Timbrando',
  }
  return m[s] || s
}

const statusColor = (s: string) => {
  const m: Record<string, string> = {
    completed: 'green', answered: 'green', no_answer: 'orange',
    busy: 'yellow', failed: 'red', cancelled: 'gray',
    initiated: 'blue', ringing: 'blue',
  }
  return m[s] || 'gray'
}

onMounted(async () => {
  try {
    const data = await $fetch<any>(`/api/calls/${route.params.id}/`, {
      headers: authHeaders(),
    })
    call.value = data
  } catch (err: any) {
    error.value = err?.data?.detail ?? 'No se pudo cargar la llamada'
    toast.add({ title: error.value!, color: 'red' })
  } finally {
    loading.value = false
  }
})
</script>
