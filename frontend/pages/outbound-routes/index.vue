<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Rutas Salientes</h1>
      <UButton
        icon="i-heroicons-plus"
        color="primary"
        @click="openCreateModal"
      >
        Agregar Ruta
      </UButton>
    </div>

    <!-- Filtros -->
    <UCard class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por nombre o patrón..."
            icon="i-heroicons-magnifying-glass"
          />
          <USelect
            v-model="statusFilter"
            :options="[
              { label: 'Todas', value: null },
              { label: 'Activas', value: true },
              { label: 'Inactivas', value: false }
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
              <th class="px-4 py-3 text-left font-semibold">Patrón</th>
              <th class="px-4 py-3 text-left font-semibold">Troncal</th>
              <th class="px-4 py-3 text-left font-semibold">Prefijo</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="route in filteredRoutes" :key="route.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3 font-semibold">{{ route.name }}</td>
              <td class="px-4 py-3 font-mono">{{ route.pattern }}</td>
              <td class="px-4 py-3">{{ route.trunk }}</td>
              <td class="px-4 py-3">{{ route.prepend || '-' }}</td>
              <td class="px-4 py-3">
                <UBadge :color="route.is_active ? 'green' : 'gray'" variant="subtle">
                  {{ route.is_active ? 'Activa' : 'Inactiva' }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editRoute(route)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteRoute(route.id)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- Modal crear/editar -->
    <USlideover v-model="isModalOpen" title="Ruta Saliente" @close="resetForm">
      <div class="p-4 space-y-4">
        <UFormGroup label="Nombre">
          <UInput v-model="form.name" placeholder="Ej: Colombia Nacional" />
        </UFormGroup>

        <UFormGroup label="Patrón de Discado" help="Patrón regex para coincidir. Ej: ^2[0-9]{9}$">
          <UInput v-model="form.pattern" placeholder="Ej: ^[0-9]{7,}$" />
        </UFormGroup>

        <UFormGroup label="Troncal">
          <USelect
            v-model="form.trunk"
            :options="['Claro', 'Movistar', 'DigiTel', 'Voz IP']"
            placeholder="Seleccione una troncal"
          />
        </UFormGroup>

        <UFormGroup label="Prefijo a Agregar (Opcional)" help="Dígitos a agregar al inicio">
          <UInput v-model="form.prepend" placeholder="Ej: 57" />
        </UFormGroup>

        <UFormGroup label="Dígitos a Eliminar (Opcional)" help="Dígitos a eliminar del inicio">
          <UInput v-model="form.prefix" placeholder="Ej: 1" />
        </UFormGroup>

        <UFormGroup label="Prefijo Caller ID (Opcional)">
          <UInput v-model="form.callerid_prefix" placeholder="Ej: 300" />
        </UFormGroup>

        <UFormGroup>
          <UCheckbox v-model="form.is_active" label="Activada" />
        </UFormGroup>

        <div class="flex gap-2 pt-4">
          <UButton color="primary" @click="saveRoute" :loading="isSaving">
            Guardar
          </UButton>
          <UButton color="gray" @click="isModalOpen = false">
            Cancelar
          </UButton>
        </div>
      </div>
    </USlideover>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface OutboundRoute {
  id: number
  name: string
  pattern: string
  trunk: string
  prepend: string
  prefix: string
  callerid_prefix: string
  is_active: boolean
}

const routes = ref<OutboundRoute[]>([
  {
    id: 1,
    name: 'Colombia Nacional',
    pattern: '^2[0-9]{9}$',
    trunk: 'Claro',
    prepend: '57',
    prefix: '',
    callerid_prefix: '300',
    is_active: true
  },
  {
    id: 2,
    name: 'Internacional',
    pattern: '^\\+?[0-9]{10,}$',
    trunk: 'DigiTel',
    prepend: '00',
    prefix: '',
    callerid_prefix: '',
    is_active: true
  }
])

const searchQuery = ref('')
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  name: '',
  pattern: '',
  trunk: '',
  prepend: '',
  prefix: '',
  callerid_prefix: '',
  is_active: true
})

const filteredRoutes = computed(() => {
  return routes.value.filter(route => {
    const matchesSearch =
      route.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      route.pattern.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesStatus = statusFilter.value === null || route.is_active === statusFilter.value
    return matchesSearch && matchesStatus
  })
})

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
}

const editRoute = (route: OutboundRoute) => {
  form.value = { ...route }
  editingId.value = route.id
  isModalOpen.value = true
}

const saveRoute = async () => {
  isSaving.value = true
  await new Promise(resolve => setTimeout(resolve, 500))
  
  if (editingId.value) {
    const index = routes.value.findIndex(r => r.id === editingId.value)
    if (index > -1) {
      routes.value[index] = { ...form.value, id: editingId.value } as OutboundRoute
    }
  } else {
    const newRoute: OutboundRoute = {
      ...form.value,
      id: Math.max(...routes.value.map(r => r.id), 0) + 1
    } as OutboundRoute
    routes.value.push(newRoute)
  }
  
  isSaving.value = false
  isModalOpen.value = false
}

const deleteRoute = (id: number) => {
  routes.value = routes.value.filter(r => r.id !== id)
}

const resetForm = () => {
  form.value = {
    name: '',
    pattern: '',
    trunk: '',
    prepend: '',
    prefix: '',
    callerid_prefix: '',
    is_active: true
  }
  editingId.value = null
}
</script>
