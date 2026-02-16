<template>
  <div>
    <div class="mb-8 flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-gray-900">Colas</h1>
        <p class="text-gray-600 mt-2">Gestión de colas de llamadas</p>
      </div>
      <UButton
        icon="i-heroicons-plus"
        size="lg"
        @click="showCreateModal = true"
      >
        Nueva Cola
      </UButton>
    </div>

    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle" class="mb-6">
      {{ error }}
    </UAlert>

    <UCard v-if="loading" class="flex justify-center items-center py-12 mb-6">
      <div class="text-center space-y-2">
        <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto" />
        <p class="text-gray-500">Cargando colas...</p>
      </div>
    </UCard>

    <!-- Grid de colas -->
    <div v-if="!loading && queues.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <UCard
        v-for="queue in queues"
        :key="queue.id"
        :ui="{ body: { padding: 'p-6' } }"
      >
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-xl font-semibold text-gray-900">{{ queue.name }}</h3>
            <UIcon :name="queue.icon" class="h-8 w-8 text-sky-500" />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <p class="text-sm text-gray-600">En cola</p>
              <p class="text-2xl font-bold text-gray-900">{{ queue.waiting }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-600">Agentes</p>
              <p class="text-2xl font-bold text-gray-900">{{ queue.agents }}</p>
            </div>
          </div>

          <div class="space-y-2">
            <div class="flex justify-between text-sm">
              <span class="text-gray-600">Tiempo espera</span>
              <span class="font-medium text-gray-900">{{ queue.avgWaitTime }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-gray-600">Llamadas hoy</span>
              <span class="font-medium text-gray-900">{{ queue.callsToday }}</span>
            </div>
          </div>

          <div class="pt-4 border-t border-gray-200">
            <UButton
              block
              color="gray"
              variant="outline"
              @click="navigateTo(`/queues/${queue.id}`)"
            >
              Ver detalles
            </UButton>
          </div>
        </div>
      </UCard>
    </div>

    <div v-else-if="!loading" class="text-sm text-gray-500">No hay colas configuradas</div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth']
})

const showCreateModal = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)

const { apiFetch } = useApi()

const queues = ref<any[]>([])

const loadQueues = async () => {
  loading.value = true
  error.value = null
  const { data, error: fetchError } = await apiFetch<any>('/queues/')
  if (fetchError.value) {
    error.value = 'Error al cargar las colas'
  } else {
    const raw = data.value
    const list = Array.isArray(raw) ? raw : (raw?.results || [])
    queues.value = list.map((queue: any) => ({
      id: queue.id,
      name: queue.name,
      icon: 'i-heroicons-user-group',
      waiting: 0,
      agents: 0,
      avgWaitTime: '0:00',
      callsToday: 0
    }))
  }
  loading.value = false
}

onMounted(() => {
  loadQueues()
})
</script>
