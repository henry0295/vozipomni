<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold">Buzones de Voz</h1>
      <UButton
        icon="i-heroicons-plus"
        color="primary"
        @click="openCreateModal"
      >
        Crear Buzón
      </UButton>
    </div>

    <!-- Filtros -->
    <UCard class="divide-y">
      <template #header>
        <div class="flex gap-2">
          <UInput
            v-model="searchQuery"
            placeholder="Buscar por buzón o nombre..."
            icon="i-heroicons-magnifying-glass"
          />
          <USelect
            v-model="statusFilter"
            :options="[
              { label: 'Todos', value: null },
              { label: 'Activos', value: true },
              { label: 'Inactivos', value: false }
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
              <th class="px-4 py-3 text-left font-semibold">Buzón</th>
              <th class="px-4 py-3 text-left font-semibold">Nombre</th>
              <th class="px-4 py-3 text-left font-semibold">Email</th>
              <th class="px-4 py-3 text-left font-semibold">Notificaciones</th>
              <th class="px-4 py-3 text-left font-semibold">Mensajes Máx</th>
              <th class="px-4 py-3 text-left font-semibold">Estado</th>
              <th class="px-4 py-3 text-center font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="voicemail in filteredVoicemails" :key="voicemail.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="px-4 py-3 font-mono font-semibold">{{ voicemail.mailbox }}</td>
              <td class="px-4 py-3">{{ voicemail.name }}</td>
              <td class="px-4 py-3 text-xs">{{ voicemail.email }}</td>
              <td class="px-4 py-3">
                <div class="flex gap-1">
                  <UBadge v-if="voicemail.email_attach" color="green" variant="subtle" size="xs">Adjuntar</UBadge>
                  <UBadge v-if="voicemail.email_delete" color="yellow" variant="subtle" size="xs">Eliminar</UBadge>
                </div>
              </td>
              <td class="px-4 py-3">{{ voicemail.max_messages }}</td>
              <td class="px-4 py-3">
                <UBadge :color="voicemail.is_active ? 'green' : 'gray'" variant="subtle">
                  {{ voicemail.is_active ? 'Activo' : 'Inactivo' }}
                </UBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <UButton
                  variant="ghost"
                  icon="i-heroicons-pencil"
                  size="sm"
                  @click="editVoicemail(voicemail)"
                />
                <UButton
                  variant="ghost"
                  icon="i-heroicons-trash"
                  color="red"
                  size="sm"
                  @click="deleteVoicemail(voicemail.id)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <!-- Modal crear/editar -->
    <USlideover v-model="isModalOpen" title="Buzón de Voz" @close="resetForm">
      <div class="p-4 space-y-4">
        <UFormGroup label="Número de Buzón">
          <UInput v-model="form.mailbox" placeholder="Ej: 100" />
        </UFormGroup>

        <UFormGroup label="Nombre del Propietario">
          <UInput v-model="form.name" placeholder="Ej: Recepción" />
        </UFormGroup>

        <UFormGroup label="Email">
          <UInput v-model="form.email" type="email" placeholder="buzón@example.com" />
        </UFormGroup>

        <UFormGroup label="Contraseña de Acceso">
          <UInput v-model="form.password" type="password" placeholder="Contraseña" />
        </UFormGroup>

        <UFormGroup label="Mensajes Máximos">
          <UInput v-model.number="form.max_messages" type="number" min="1" max="200" />
        </UFormGroup>

        <div class="space-y-3 border-t pt-4">
          <h3 class="font-semibold">Configuración de Notificaciones</h3>
          <UFormGroup>
            <UCheckbox v-model="form.email_attach" label="Adjuntar audio a notificaciones de email" />
          </UFormGroup>
          <UFormGroup>
            <UCheckbox v-model="form.email_delete" label="Eliminar mensaje después de enviar por email" />
          </UFormGroup>
        </div>

        <UFormGroup>
          <UCheckbox v-model="form.is_active" label="Activado" />
        </UFormGroup>

        <div class="flex gap-2 pt-4">
          <UButton color="primary" @click="saveVoicemail" :loading="isSaving">
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

interface Voicemail {
  id: number
  mailbox: string
  name: string
  email: string
  password: string
  max_messages: number
  email_attach: boolean
  email_delete: boolean
  is_active: boolean
}

const voicemails = ref<Voicemail[]>([
  {
    id: 1,
    mailbox: '100',
    name: 'Recepción',
    email: 'recepcion@example.com',
    password: 'pass123',
    max_messages: 100,
    email_attach: true,
    email_delete: false,
    is_active: true
  }
])

const searchQuery = ref('')
const statusFilter = ref<boolean | null>(null)
const isModalOpen = ref(false)
const isSaving = ref(false)
const editingId = ref<number | null>(null)

const form = ref({
  mailbox: '',
  name: '',
  email: '',
  password: '',
  max_messages: 100,
  email_attach: true,
  email_delete: false,
  is_active: true
})

const filteredVoicemails = computed(() => {
  return voicemails.value.filter(vm => {
    const matchesSearch =
      vm.mailbox.includes(searchQuery.value) ||
      vm.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesStatus = statusFilter.value === null || vm.is_active === statusFilter.value
    return matchesSearch && matchesStatus
  })
})

const openCreateModal = () => {
  resetForm()
  isModalOpen.value = true
}

const editVoicemail = (voicemail: Voicemail) => {
  form.value = { ...voicemail }
  editingId.value = voicemail.id
  isModalOpen.value = true
}

const saveVoicemail = async () => {
  isSaving.value = true
  await new Promise(resolve => setTimeout(resolve, 500))
  
  if (editingId.value) {
    const index = voicemails.value.findIndex(vm => vm.id === editingId.value)
    if (index > -1) {
      voicemails.value[index] = { ...form.value, id: editingId.value } as Voicemail
    }
  } else {
    const newVoicemail: Voicemail = {
      ...form.value,
      id: Math.max(...voicemails.value.map(vm => vm.id), 0) + 1
    } as Voicemail
    voicemails.value.push(newVoicemail)
  }
  
  isSaving.value = false
  isModalOpen.value = false
}

const deleteVoicemail = (id: number) => {
  voicemails.value = voicemails.value.filter(vm => vm.id !== id)
}

const resetForm = () => {
  form.value = {
    mailbox: '',
    name: '',
    email: '',
    password: '',
    max_messages: 100,
    email_attach: true,
    email_delete: false,
    is_active: true
  }
  editingId.value = null
}
</script>
