<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Extensiones</h1>
      <div class="flex gap-2">
        <UButton
          v-if="error"
          icon="i-heroicons-arrow-path"
          @click="loadExtensions"
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
          Agregar Extensión
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
        <p class="text-gray-500">Cargando extensiones...</p>
      </div>
    </UCard>

    <!-- Filtros -->
    <UCard v-if="!loading" class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por extensión o nombre..."
            icon="i-heroicons-magnifying-glass"
          />
          <USelect
            v-model="extensionFilter"
            :options="[
              { label: 'Todos', value: null },
              { label: 'SIP', value: 'SIP' },
              { label: 'IAX2', value: 'IAX2' },
              { label: 'PJSIP', value: 'PJSIP' }
            ]"
            option-attribute="label"
            value-attribute="value"
            placeholder="Filtrar por tipo"
          />
          <USelect
            v-model="statusFilter"
            :options="[
              { label: 'Todos', value: null },
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
              <th class="px-4 py-3 text-left font-semibold">Extensión</th>
              <th class="px-4 py-3 text-left font-semibold">Nombre</th>
              <th class="px-4 py-3 text-left font-semibold">Tipo</th>
              <th class="px-4 py-3 text-left font-semibold">Email</th>
              <th class="px-4 py-3 text-left font-semibold">Buzón</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="ext in filteredExtensions" :key="ext.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3 font-mono font-semibold">{{ ext.extension }}</td>
              <td class="px-4 py-3">{{ ext.name }}</td>
              <td class="px-4 py-3">
                <UBadge color="blue" variant="subtle">{{ ext.extension_type }}</UBadge>
              </td>
              <td class="px-4 py-3 text-xs">{{ ext.email || '-' }}</td>
              <td class="px-4 py-3">
                <UBadge v-if="ext.voicemail_enabled" color="green" variant="subtle">Habilitado</UBadge>
                <span v-else class="text-gray-500">-</span>
              </td>
              <td class="px-4 py-3">
                <UBadge :color="ext.is_active ? 'green' : 'gray'" variant="subtle">
                  {{ ext.is_active ? 'Activa' : 'Inactiva' }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editExtension(ext)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteExtension(ext.id)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- Modal crear/editar -->
    <USlideover v-model="isModalOpen" title="Extensión" @close="resetForm">
      <div class="p-4 space-y-4">
        <UFormGroup label="Extensión">
          <UInput v-model="form.extension" placeholder="Ej: 100" />
        </UFormGroup>

        <UFormGroup label="Nombre">
          <UInput v-model="form.name" placeholder="Ej: Juan Pérez" />
        </UFormGroup>

        <UFormGroup label="Tipo de Extensión">
          <USelect
            v-model="form.extension_type"
            :options="['SIP', 'IAX2', 'PJSIP']"
          />
        </UFormGroup>

        <UFormGroup label="Contraseña">
          <UInput v-model="form.secret" type="password" placeholder="Contraseña segura" />
        </UFormGroup>

        <UFormGroup label="Contexto">
          <USelect
            v-model="form.context"
            :options="[
              { label: 'from-internal', value: 'from-internal' },
              { label: 'from-external', value: 'from-external' },
              { label: 'custom', value: 'custom' }
            ]"
            option-attribute="label"
            value-attribute="value"
          />
        </UFormGroup>

        <UFormGroup label="Caller ID">
          <UInput v-model="form.callerid" placeholder="Ej: 100 <2001234567>" />
        </UFormGroup>

        <UFormGroup label="Email">
          <UInput v-model="form.email" type="email" placeholder="usuario@example.com" />
        </UFormGroup>

        <UFormGroup>
          <UCheckbox v-model="form.voicemail_enabled" label="Habilitar Buzón de Voz" />
        </UFormGroup>

        <UFormGroup>
          <UCheckbox v-model="form.is_active" label="Activada" />
        </UFormGroup>

        <div class="flex gap-2 pt-4">
          <UButton color="primary" @click="saveExtension" :loading="isSaving">
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

interface Extension {
  id: number
  extension: string
  name: string
  extension_type: string
  secret: string
  context: string
  callerid: string
  email: string
  voicemail_enabled: boolean
  is_active: boolean
}

const extensions = ref<Extension[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const extensionFilter = ref<string | null>(null)
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  extension: '',
  name: '',
  extension_type: 'SIP',
  secret: '',
  context: 'from-internal',
  callerid: '',
  email: '',
  voicemail_enabled: false,
  is_active: true
})

const filteredExtensions = computed(() => {
  return extensions.value.filter(ext => {
    const matchesSearch =
      ext.extension.includes(searchQuery.value) ||
      ext.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesType = extensionFilter.value === null || ext.extension_type === extensionFilter.value
    const matchesStatus = statusFilter.value === null || ext.is_active === statusFilter.value
    return matchesSearch && matchesType && matchesStatus
  })
})

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
}

const editExtension = (ext: Extension) => {
  form.value = { ...ext }
  editingId.value = ext.id
  isModalOpen.value = true
}

const loadExtensions = async () => {
  loading.value = true
  error.value = null
  try {
    const data = await $fetch('/api/extensions/')
    extensions.value = data
  } catch (err) {
    error.value = 'Error al cargar las extensiones'
    console.error('Error loading extensions:', err)
  } finally {
    loading.value = false
  }
}

const saveExtension = async () => {
  isSaving.value = true
  error.value = null
  try {
    if (editingId.value) {
      await $fetch(`/api/extensions/${editingId.value}/`, {
        method: 'PUT',
        body: form.value
      })
    } else {
      await $fetch('/api/extensions/', {
        method: 'POST',
        body: form.value
      })
    }
    await loadExtensions()
    isModalOpen.value = false
  } catch (err) {
    error.value = 'Error al guardar la extensión'
    console.error('Error saving extension:', err)
  } finally {
    isSaving.value = false
  }
}

const deleteExtension = async (id: number) => {
  if (confirm('¿Estás seguro de que deseas eliminar esta extensión?')) {
    try {
      await $fetch(`/api/extensions/${id}/`, { method: 'DELETE' })
      await loadExtensions()
    } catch (err) {
      error.value = 'Error al eliminar la extensión'
      console.error('Error deleting extension:', err)
    }
  }
}

const resetForm = () => {
  form.value = {
    extension: '',
    name: '',
    extension_type: 'SIP',
    secret: '',
    context: 'from-internal',
    callerid: '',
    email: '',
    voicemail_enabled: false,
    is_active: true
  }
  editingId.value = null
}
</script>
