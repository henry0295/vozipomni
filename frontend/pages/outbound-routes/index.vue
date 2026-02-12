<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Rutas Salientes</h1>
      <div class="flex gap-2">
        <UButton
          v-if="error"
          icon="i-heroicons-arrow-path"
          @click="loadRoutes"
          :loading="loading"
        >
          Reintentar
        </UButton>
        <UButton
          icon="i-heroicons-plus"
          color="primary"
          @click="openCreateModal"
          :disabled="loading"
        >
          Agregar Ruta
        </UButton>
      </div>
    </div>

    <!-- Estado de carga/error -->
    <UAlert v-if="error" color="red" icon="i-heroicons-exclamation-triangle">
      {{ error }}
    </UAlert>

    <UCard v-if="loading" class="flex justify-center items-center py-12">
      <div class="text-center space-y-2">
        <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto" />
        <p class="text-gray-500">Cargando rutas salientes...</p>
      </div>
    </UCard>

    <!-- Filtros -->
    <UCard v-if="!loading" class="divide-y">
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
import { ref, computed, onMounted } from 'vue'

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

const routes = ref<OutboundRoute[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
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

const loadRoutes = async () => {
  loading.value = true
  error.value = null
  try {
    const data = await $fetch('/api/outbound-routes/')
    routes.value = data
  } catch (err) {
    error.value = 'Error al cargar las rutas salientes'
    console.error('Error loading outbound routes:', err)
  } finally {
    loading.value = false
  }
}

const saveRoute = async () => {
  isSaving.value = true
  error.value = null
  try {
    if (editingId.value) {
      await $fetch(`/api/outbound-routes/${editingId.value}/`, {
        method: 'PUT',
        body: form.value
      })
    } else {
      await $fetch('/api/outbound-routes/', {
        method: 'POST',
        body: form.value
      })
    }
    await loadRoutes()
    isModalOpen.value = false
  } catch (err) {
    error.value = 'Error al guardar la ruta'
    console.error('Error saving route:', err)
  } finally {
    isSaving.value = false
  }
}

const deleteRoute = async (id: number) => {
  if (confirm('¿Estás seguro de que deseas eliminar esta ruta?')) {
    try {
      await $fetch(`/api/outbound-routes/${id}/`, { method: 'DELETE' })
      await loadRoutes()
    } catch (err) {
      error.value = 'Error al eliminar la ruta'
      console.error('Error deleting route:', err)
    }
  }
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
