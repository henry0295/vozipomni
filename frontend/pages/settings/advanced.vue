<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Configuración Avanzada</h1>
      <p class="text-sm text-gray-500 mt-1">Razones de pausa y grupos de agentes</p>
    </div>

    <!-- Tabs -->
    <UTabs :items="tabs" v-model="activeTab">
      <!-- Razones de Pausa -->
      <template #pause-reasons>
        <div class="space-y-4 pt-4">
          <div class="flex justify-between items-center">
            <h2 class="text-lg font-semibold text-gray-800">Razones de Pausa</h2>
            <UButton icon="i-heroicons-plus" @click="openBreakModal()">Nueva razón</UButton>
          </div>

          <UTable
            :rows="breakReasons"
            :columns="breakColumns"
            :loading="loadingBreak"
            :empty-state="{ icon: 'i-heroicons-pause-circle', label: 'Sin razones de pausa configuradas' }"
          >
            <template #is_paid-data="{ row }">
              <UBadge :color="row.is_paid ? 'green' : 'gray'" variant="soft" size="xs">
                {{ row.is_paid ? 'Pagada' : 'No pagada' }}
              </UBadge>
            </template>
            <template #max_duration-data="{ row }">
              {{ row.max_duration ? `${row.max_duration} min` : '∞' }}
            </template>
            <template #is_active-data="{ row }">
              <UToggle :model-value="row.is_active" @update:model-value="toggleBreak(row)" />
            </template>
            <template #actions-data="{ row }">
              <div class="flex gap-1">
                <UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost" @click="openBreakModal(row)" />
                <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost" @click="deleteBreak(row)" />
              </div>
            </template>
          </UTable>
        </div>
      </template>

      <!-- Grupos de Agentes -->
      <template #agent-groups>
        <div class="space-y-4 pt-4">
          <div class="flex justify-between items-center">
            <h2 class="text-lg font-semibold text-gray-800">Grupos de Agentes</h2>
            <UButton icon="i-heroicons-plus" @click="openGroupModal()">Nuevo grupo</UButton>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <UCard v-for="group in agentGroups" :key="group.id"
                   :class="{ 'opacity-50': !group.is_active }">
              <template #header>
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <UIcon name="i-heroicons-user-group" class="text-blue-500" />
                    <span class="font-semibold text-gray-800">{{ group.name }}</span>
                  </div>
                  <UBadge :color="group.is_active ? 'green' : 'gray'" variant="soft" size="xs">
                    {{ group.is_active ? 'Activo' : 'Inactivo' }}
                  </UBadge>
                </div>
              </template>
              <div class="space-y-3">
                <p v-if="group.description" class="text-sm text-gray-500">{{ group.description }}</p>
                <p class="text-2xl font-bold text-blue-600">
                  {{ group.agent_count }} <span class="text-sm font-normal text-gray-500">agentes</span>
                </p>
              </div>
              <template #footer>
                <div class="flex gap-2">
                  <UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="outline"
                           class="flex-1" @click="openGroupModal(group)">
                    Editar
                  </UButton>
                  <UButton icon="i-heroicons-users" size="xs" color="blue" variant="outline"
                           class="flex-1" @click="openGroupAgentsModal(group)">
                    Agentes
                  </UButton>
                  <UButton icon="i-heroicons-trash" size="xs" color="red" variant="ghost"
                           @click="deleteGroup(group)" />
                </div>
              </template>
            </UCard>
            <UCard v-if="!loadingGroups && !agentGroups.length"
                   class="col-span-full text-center py-10 text-gray-400">
              <UIcon name="i-heroicons-user-group" class="text-4xl mb-2" />
              <p>Sin grupos configurados</p>
            </UCard>
          </div>
        </div>
      </template>
    </UTabs>

    <!-- Modal Razón de Pausa -->
    <UModal v-model="breakModal.open">
      <UCard>
        <template #header>
          <h3 class="font-semibold">{{ breakModal.editing ? 'Editar' : 'Nueva' }} Razón de Pausa</h3>
        </template>
        <div class="space-y-4">
          <UFormGroup label="Nombre *">
            <UInput v-model="breakForm.name" placeholder="ej: Almuerzo" />
          </UFormGroup>
          <UFormGroup label="Código (para Asterisk)">
            <UInput v-model="breakForm.code" placeholder="ej: LUNCH" />
          </UFormGroup>
          <div class="grid grid-cols-2 gap-4">
            <UFormGroup label="Duración máx. (min)">
              <UInput v-model.number="breakForm.max_duration" type="number" min="0" placeholder="Sin límite" />
            </UFormGroup>
            <UFormGroup label="Orden">
              <UInput v-model.number="breakForm.order" type="number" min="0" />
            </UFormGroup>
          </div>
          <div class="flex gap-6">
            <UFormGroup label="¿Es pagada?">
              <UToggle v-model="breakForm.is_paid" />
            </UFormGroup>
            <UFormGroup label="¿Activa?">
              <UToggle v-model="breakForm.is_active" />
            </UFormGroup>
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="breakModal.open = false">Cancelar</UButton>
            <UButton :loading="breakModal.loading" @click="saveBreakReason">
              {{ breakModal.editing ? 'Guardar' : 'Crear' }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal Grupo -->
    <UModal v-model="groupModal.open">
      <UCard>
        <template #header>
          <h3 class="font-semibold">{{ groupModal.editing ? 'Editar' : 'Nuevo' }} Grupo</h3>
        </template>
        <div class="space-y-4">
          <UFormGroup label="Nombre *">
            <UInput v-model="groupForm.name" placeholder="ej: Equipo Ventas" />
          </UFormGroup>
          <UFormGroup label="Descripción">
            <UTextarea v-model="groupForm.description" rows="2" />
          </UFormGroup>
          <UFormGroup label="¿Activo?">
            <UToggle v-model="groupForm.is_active" />
          </UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="groupModal.open = false">Cancelar</UButton>
            <UButton :loading="groupModal.loading" @click="saveGroup">
              {{ groupModal.editing ? 'Guardar' : 'Crear' }}
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Modal agentes del grupo -->
    <UModal v-model="groupAgentsModal.open" :ui="{ width: 'max-w-2xl' }">
      <UCard>
        <template #header>
          <h3 class="font-semibold">Agentes — {{ groupAgentsModal.group?.name }}</h3>
        </template>
        <div class="grid grid-cols-2 gap-4">
          <!-- Agentes en el grupo -->
          <div>
            <p class="text-sm font-medium text-gray-500 mb-2">En el grupo</p>
            <div class="space-y-1 max-h-64 overflow-y-auto">
              <div v-for="a in groupAgentsModal.inGroup" :key="a.id"
                   class="flex items-center justify-between p-2 bg-green-50 rounded-lg text-sm">
                <span>{{ a.user?.username ?? `Agente ${a.agent_id}` }}</span>
                <UButton icon="i-heroicons-minus" size="xs" color="red" variant="ghost"
                         @click="removeFromGroup(a)" />
              </div>
              <p v-if="!groupAgentsModal.inGroup.length" class="text-xs text-gray-400 text-center py-3">Sin agentes</p>
            </div>
          </div>
          <!-- Agentes disponibles -->
          <div>
            <p class="text-sm font-medium text-gray-500 mb-2">Disponibles</p>
            <div class="space-y-1 max-h-64 overflow-y-auto">
              <div v-for="a in groupAgentsModal.available" :key="a.id"
                   class="flex items-center justify-between p-2 bg-gray-50 rounded-lg text-sm">
                <span>{{ a.user?.username ?? `Agente ${a.agent_id}` }}</span>
                <UButton icon="i-heroicons-plus" size="xs" color="green" variant="ghost"
                         @click="addToGroup(a)" />
              </div>
              <p v-if="!groupAgentsModal.available.length" class="text-xs text-gray-400 text-center py-3">Sin más agentes</p>
            </div>
          </div>
        </div>
        <template #footer>
          <UButton color="gray" variant="ghost" @click="groupAgentsModal.open = false">Cerrar</UButton>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ middleware: ['auth'], layout: 'default' })

const activeTab = ref(0)
const tabs = [
  { label: 'Razones de Pausa', slot: 'pause-reasons', icon: 'i-heroicons-pause-circle' },
  { label: 'Grupos de Agentes', slot: 'agent-groups', icon: 'i-heroicons-user-group' },
]

// ── Break Reasons ───────────────────────────────────
const breakReasons = ref<any[]>([])
const loadingBreak = ref(false)
const breakModal = ref({ open: false, editing: false, id: null as number | null, loading: false })
const breakForm = ref({ name: '', code: '', max_duration: null as number | null, order: 0, is_paid: false, is_active: true })
const breakColumns = [
  { key: 'order', label: '#' },
  { key: 'name', label: 'Nombre' },
  { key: 'code', label: 'Código' },
  { key: 'is_paid', label: 'Tipo' },
  { key: 'max_duration', label: 'Duración' },
  { key: 'is_active', label: 'Activa' },
  { key: 'actions', label: '' },
]

async function loadBreakReasons() {
  loadingBreak.value = true
  try {
    const res = await $fetch('/api/break-reasons/?ordering=order', { headers: authHeaders() }) as any
    breakReasons.value = res.results ?? res
  } finally {
    loadingBreak.value = false }
}

function openBreakModal(reason?: any) {
  breakModal.value.editing = !!reason
  breakModal.value.id = reason?.id ?? null
  breakForm.value = reason
    ? { name: reason.name, code: reason.code, max_duration: reason.max_duration, order: reason.order, is_paid: reason.is_paid, is_active: reason.is_active }
    : { name: '', code: '', max_duration: null, order: 0, is_paid: false, is_active: true }
  breakModal.value.open = true
}

async function saveBreakReason() {
  breakModal.value.loading = true
  try {
    const url = breakModal.value.editing ? `/api/break-reasons/${breakModal.value.id}/` : '/api/break-reasons/'
    await $fetch(url, { method: breakModal.value.editing ? 'PATCH' : 'POST', headers: authHeaders(), body: breakForm.value })
    useToast().add({ title: breakModal.value.editing ? 'Razón actualizada' : 'Razón creada', color: 'green' })
    breakModal.value.open = false
    await loadBreakReasons()
  } catch { useToast().add({ title: 'Error al guardar', color: 'red' }) }
  finally { breakModal.value.loading = false }
}

async function toggleBreak(reason: any) {
  await $fetch(`/api/break-reasons/${reason.id}/`, { method: 'PATCH', headers: authHeaders(), body: { is_active: !reason.is_active } })
  await loadBreakReasons()
}

async function deleteBreak(reason: any) {
  if (!confirm(`¿Eliminar razón "${reason.name}"?`)) return
  await $fetch(`/api/break-reasons/${reason.id}/`, { method: 'DELETE', headers: authHeaders() })
  await loadBreakReasons()
}

// ── Agent Groups ────────────────────────────────────
const agentGroups = ref<any[]>([])
const loadingGroups = ref(false)
const groupModal = ref({ open: false, editing: false, id: null as number | null, loading: false })
const groupForm = ref({ name: '', description: '', is_active: true })

const groupAgentsModal = ref({ open: false, group: null as any, inGroup: [] as any[], available: [] as any[] })
const allAgents = ref<any[]>([])

async function loadGroups() {
  loadingGroups.value = true
  try {
    const res = await $fetch('/api/agent-groups/', { headers: authHeaders() }) as any
    agentGroups.value = res.results ?? res
  } finally { loadingGroups.value = false }
}

function openGroupModal(group?: any) {
  groupModal.value.editing = !!group
  groupModal.value.id = group?.id ?? null
  groupForm.value = group
    ? { name: group.name, description: group.description ?? '', is_active: group.is_active }
    : { name: '', description: '', is_active: true }
  groupModal.value.open = true
}

async function saveGroup() {
  groupModal.value.loading = true
  try {
    const url = groupModal.value.editing ? `/api/agent-groups/${groupModal.value.id}/` : '/api/agent-groups/'
    await $fetch(url, { method: groupModal.value.editing ? 'PATCH' : 'POST', headers: authHeaders(), body: groupForm.value })
    useToast().add({ title: groupModal.value.editing ? 'Grupo actualizado' : 'Grupo creado', color: 'green' })
    groupModal.value.open = false
    await loadGroups()
  } catch { useToast().add({ title: 'Error al guardar grupo', color: 'red' }) }
  finally { groupModal.value.loading = false }
}

async function deleteGroup(group: any) {
  if (!confirm(`¿Eliminar grupo "${group.name}"?`)) return
  await $fetch(`/api/agent-groups/${group.id}/`, { method: 'DELETE', headers: authHeaders() })
  await loadGroups()
}

async function openGroupAgentsModal(group: any) {
  if (!allAgents.value.length) {
    const res = await $fetch('/api/agents/', { headers: authHeaders() }) as any
    allAgents.value = res.results ?? res
  }
  const inGroupIds = new Set((group.agents ?? []) as number[])
  groupAgentsModal.value = {
    open: true,
    group,
    inGroup: allAgents.value.filter(a => inGroupIds.has(a.id)),
    available: allAgents.value.filter(a => !inGroupIds.has(a.id)),
  }
}

async function addToGroup(agent: any) {
  await $fetch(`/api/agent-groups/${groupAgentsModal.value.group.id}/add_agent/`, {
    method: 'POST', headers: authHeaders(), body: { agent_id: agent.id },
  })
  groupAgentsModal.value.inGroup.push(agent)
  groupAgentsModal.value.available = groupAgentsModal.value.available.filter(a => a.id !== agent.id)
  await loadGroups()
}

async function removeFromGroup(agent: any) {
  await $fetch(`/api/agent-groups/${groupAgentsModal.value.group.id}/remove_agent/`, {
    method: 'POST', headers: authHeaders(), body: { agent_id: agent.id },
  })
  groupAgentsModal.value.available.push(agent)
  groupAgentsModal.value.inGroup = groupAgentsModal.value.inGroup.filter(a => a.id !== agent.id)
  await loadGroups()
}

function authHeaders() {
  const token = process.client ? localStorage.getItem('auth_token') : null
  return token ? { Authorization: `Bearer ${token}` } : {}
}

onMounted(() => {
  loadBreakReasons()
  loadGroups()
})
</script>
