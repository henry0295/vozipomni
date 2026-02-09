<template>
  <div>
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
      <p class="text-gray-600 mt-2">Bienvenido al panel de control de VozipOmni</p>
    </div>

    <!-- Estadísticas principales -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Agentes Activos</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.activeAgents }}</p>
          </div>
          <UIcon name="i-heroicons-user-group" class="h-12 w-12 text-green-500" />
        </div>
        <div class="mt-4">
          <span class="text-sm text-green-600">↑ 12% vs ayer</span>
        </div>
      </UCard>

      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Llamadas en Cola</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.queuedCalls }}</p>
          </div>
          <UIcon name="i-heroicons-phone" class="h-12 w-12 text-sky-500" />
        </div>
        <div class="mt-4">
          <span class="text-sm text-gray-600">En tiempo real</span>
        </div>
      </UCard>

      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Llamadas Hoy</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.callsToday }}</p>
          </div>
          <UIcon name="i-heroicons-phone-arrow-up-right" class="h-12 w-12 text-blue-500" />
        </div>
        <div class="mt-4">
          <span class="text-sm text-green-600">↑ 8% vs ayer</span>
        </div>
      </UCard>

      <UCard>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-600">Tiempo Promedio</p>
            <p class="text-3xl font-bold text-gray-900 mt-1">{{ stats.avgTime }}</p>
          </div>
          <UIcon name="i-heroicons-clock" class="h-12 w-12 text-purple-500" />
        </div>
        <div class="mt-4">
          <span class="text-sm text-red-600">↓ 5% vs ayer</span>
        </div>
      </UCard>
    </div>

    <!-- Actividad reciente -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <UCard>
        <template #header>
          <h2 class="text-xl font-semibold text-gray-900">Agentes en Línea</h2>
        </template>
        
        <div class="space-y-3">
          <div v-for="agent in recentAgents" :key="agent.id" class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div class="flex items-center space-x-3">
              <UAvatar :alt="agent.name" size="sm" />
              <div>
                <p class="font-medium text-gray-900">{{ agent.name }}</p>
                <p class="text-sm text-gray-600">{{ agent.extension }}</p>
              </div>
            </div>
            <UBadge :color="agent.status === 'available' ? 'green' : 'yellow'">
              {{ agent.statusLabel }}
            </UBadge>
          </div>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <h2 class="text-xl font-semibold text-gray-900">Llamadas Recientes</h2>
        </template>
        
        <div class="space-y-3">
          <div v-for="call in recentCalls" :key="call.id" class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div class="flex items-center space-x-3">
              <UIcon name="i-heroicons-phone" class="h-8 w-8 text-sky-500" />
              <div>
                <p class="font-medium text-gray-900">{{ call.number }}</p>
                <p class="text-sm text-gray-600">{{ call.duration }}</p>
              </div>
            </div>
            <UBadge :color="call.type === 'inbound' ? 'blue' : 'green'">
              {{ call.typeLabel }}
            </UBadge>
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

const stats = reactive({
  activeAgents: 24,
  queuedCalls: 5,
  callsToday: 342,
  avgTime: '4:32'
})

const recentAgents = ref([
  { id: 1, name: 'Juan Pérez', extension: '1001', status: 'available', statusLabel: 'Disponible' },
  { id: 2, name: 'María García', extension: '1002', status: 'busy', statusLabel: 'En llamada' },
  { id: 3, name: 'Carlos Rodríguez', extension: '1003', status: 'available', statusLabel: 'Disponible' },
  { id: 4, name: 'Ana Martínez', extension: '1004', status: 'available', statusLabel: 'Disponible' }
])

const recentCalls = ref([
  { id: 1, number: '+57 300 123 4567', duration: '5:23', type: 'inbound', typeLabel: 'Entrante' },
  { id: 2, number: '+57 301 987 6543', duration: '3:45', type: 'outbound', typeLabel: 'Saliente' },
  { id: 3, number: '+57 302 555 7890', duration: '7:12', type: 'inbound', typeLabel: 'Entrante' },
  { id: 4, number: '+57 303 444 3210', duration: '2:30', type: 'inbound', typeLabel: 'Entrante' }
])

// TODO: Cargar datos reales desde la API
onMounted(() => {
  // fetchDashboardStats()
})
</script>
