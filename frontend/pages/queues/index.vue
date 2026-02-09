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

    <!-- Grid de colas -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth']
})

const showCreateModal = ref(false)

const queues = ref([
  {
    id: 1,
    name: 'Ventas',
    icon: 'i-heroicons-shopping-cart',
    waiting: 3,
    agents: 8,
    avgWaitTime: '1:23',
    callsToday: 156
  },
  {
    id: 2,
    name: 'Soporte Técnico',
    icon: 'i-heroicons-wrench-screwdriver',
    waiting: 5,
    agents: 12,
    avgWaitTime: '2:45',
    callsToday: 234
  },
  {
    id: 3,
    name: 'Atención al Cliente',
    icon: 'i-heroicons-user-group',
    waiting: 2,
    agents: 10,
    avgWaitTime: '0:58',
    callsToday: 189
  }
])

// TODO: Cargar colas desde la API
onMounted(() => {
  // fetchQueues()
})
</script>
