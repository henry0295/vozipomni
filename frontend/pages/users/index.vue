<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Usuarios y roles</h1>
        <p class="text-sm text-gray-500 mt-1">Administradores, supervisores, analistas y agentes con acceso al sistema.</p>
      </div>
      <UButton icon="i-heroicons-user-plus" @click="openForm()">Nuevo usuario</UButton>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <UCard v-for="r in roleCards" :key="r.value" class="cursor-pointer" :class="{ 'ring-2 ring-sky-400': filterRole === r.value }"
             @click="filterRole = filterRole === r.value ? '' : r.value; load()">
        <p class="text-xs text-gray-500 uppercase">{{ r.label }}</p>
        <p class="text-2xl font-bold" :class="r.color">{{ counts[r.value] ?? 0 }}</p>
      </UCard>
    </div>

    <UCard>
      <template #header>
        <div class="flex flex-wrap gap-2 items-center">
          <UInput v-model="search" icon="i-heroicons-magnifying-glass" placeholder="Buscar usuario, nombre o correo" class="w-72" @keyup.enter="load" />
          <USelect v-model="filterActive" :options="activeOptions" @change="load" />
          <UButton color="gray" variant="ghost" icon="i-heroicons-arrow-path" :loading="loading" @click="load" />
        </div>
      </template>

      <UTable :rows="users" :columns="columns" :loading="loading"
              :empty-state="{ icon: 'i-heroicons-users', label: 'No hay usuarios' }">
        <template #name-data="{ row }">
          <div class="flex items-center gap-2">
            <UAvatar :alt="row.name" size="xs" />
            <div>
              <p class="font-medium">{{ row.name }}</p>
              <p class="text-xs text-gray-500">@{{ row.username }}</p>
            </div>
          </div>
        </template>
        <template #role-data="{ row }">
          <UBadge :color="roleColor(row.role)" variant="soft">{{ row.role_display }}</UBadge>
          <UBadge v-if="row.has_agent_profile" color="gray" variant="soft" size="xs" class="ml-1">Perfil agente</UBadge>
        </template>
        <template #is_active-data="{ row }">
          <UBadge :color="row.is_active ? 'green' : 'gray'" variant="soft">{{ row.is_active ? 'Activo' : 'Inactivo' }}</UBadge>
        </template>
        <template #last_login-data="{ row }">
          <span class="text-sm text-gray-600">{{ row.last_login ? new Date(row.last_login).toLocaleString('es-CO') : 'Nunca' }}</span>
        </template>
        <template #actions-data="{ row }">
          <div class="flex gap-1">
            <UTooltip text="Editar"><UButton icon="i-heroicons-pencil" size="xs" color="gray" variant="ghost" @click="openForm(row)" /></UTooltip>
            <UTooltip text="Cambiar contraseña"><UButton icon="i-heroicons-key" size="xs" color="gray" variant="ghost" @click="openPassword(row)" /></UTooltip>
            <UTooltip :text="row.is_active ? 'Desactivar' : 'Activar'">
              <UButton :icon="row.is_active ? 'i-heroicons-no-symbol' : 'i-heroicons-check-circle'" size="xs"
                       :color="row.is_active ? 'red' : 'green'" variant="ghost"
                       :disabled="row.id === user?.id" @click="toggleActive(row)" />
            </UTooltip>
          </div>
        </template>
      </UTable>
    </UCard>

    <!-- Crear / editar -->
    <UModal v-model="form.open">
      <UCard>
        <template #header><h3 class="font-semibold">{{ form.id ? 'Editar usuario' : 'Nuevo usuario' }}</h3></template>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Nombre"><UInput v-model="form.first_name" /></UFormGroup>
            <UFormGroup label="Apellido"><UInput v-model="form.last_name" /></UFormGroup>
          </div>
          <UFormGroup label="Usuario" required><UInput v-model="form.username" :disabled="!!form.id" /></UFormGroup>
          <UFormGroup label="Correo" hint="Necesario para recuperar la contraseña"><UInput v-model="form.email" type="email" /></UFormGroup>
          <div class="grid grid-cols-2 gap-3">
            <UFormGroup label="Rol" required>
              <USelect v-model="form.role" :options="roleOptions" :disabled="form.id === user?.id" />
            </UFormGroup>
            <UFormGroup label="Teléfono"><UInput v-model="form.phone" /></UFormGroup>
          </div>
          <UFormGroup label="Departamento"><UInput v-model="form.department" /></UFormGroup>
          <UFormGroup v-if="!form.id" label="Contraseña" required hint="Mínimo 8 caracteres, no solo números">
            <UInput v-model="form.password" type="password" autocomplete="new-password" />
          </UFormGroup>
          <UAlert v-if="form.role === 'agent' && !form.id" icon="i-heroicons-information-circle" color="blue" variant="soft"
                  description="Para que un agente pueda atender llamadas créale además su perfil (extensión SIP) en Operación → Agentes." />
          <UCheckbox v-model="form.is_active" label="Usuario activo" :disabled="form.id === user?.id" />
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="form.open = false">Cancelar</UButton>
            <UButton :loading="form.saving" @click="save">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>

    <!-- Contraseña -->
    <UModal v-model="pwd.open">
      <UCard>
        <template #header><h3 class="font-semibold">Nueva contraseña · {{ pwd.user?.username }}</h3></template>
        <div class="space-y-3">
          <UFormGroup label="Contraseña"><UInput v-model="pwd.password" type="password" autocomplete="new-password" /></UFormGroup>
          <UFormGroup label="Confirmar"><UInput v-model="pwd.confirm" type="password" autocomplete="new-password" /></UFormGroup>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="pwd.open = false">Cancelar</UButton>
            <UButton :loading="pwd.saving" :disabled="!pwd.password || pwd.password !== pwd.confirm" @click="savePassword">Actualizar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const http = useHttp()
const toast = useToast()
const { user } = useAuth()

const users = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const filterRole = ref('')
const filterActive = ref('true')
const counts = ref<Record<string, number>>({})

const roleOptions = [
  { label: 'Administrador', value: 'admin' },
  { label: 'Supervisor', value: 'supervisor' },
  { label: 'Analista', value: 'analyst' },
  { label: 'Agente', value: 'agent' },
]
const roleCards = [
  { label: 'Administradores', value: 'admin', color: 'text-red-600' },
  { label: 'Supervisores', value: 'supervisor', color: 'text-blue-600' },
  { label: 'Analistas', value: 'analyst', color: 'text-purple-600' },
  { label: 'Agentes', value: 'agent', color: 'text-green-600' },
]
const activeOptions = [
  { label: 'Activos', value: 'true' },
  { label: 'Inactivos', value: 'false' },
  { label: 'Todos', value: '' },
]
const columns = [
  { key: 'name', label: 'Usuario' },
  { key: 'email', label: 'Correo' },
  { key: 'role', label: 'Rol' },
  { key: 'department', label: 'Departamento' },
  { key: 'is_active', label: 'Estado' },
  { key: 'last_login', label: 'Último acceso' },
  { key: 'actions', label: '' },
]

const roleColor = (r: string) => ({ admin: 'red', supervisor: 'blue', analyst: 'purple', agent: 'green' } as any)[r] ?? 'gray'

const blankForm = () => ({
  open: false, saving: false, id: null as number | null,
  username: '', email: '', first_name: '', last_name: '', role: 'agent',
  phone: '', department: '', password: '', is_active: true,
})
const form = reactive(blankForm())
const pwd = reactive({ open: false, saving: false, user: null as any, password: '', confirm: '' })

async function load() {
  loading.value = true
  try {
    const query: any = { page_size: 200 }
    if (search.value) query.search = search.value
    if (filterRole.value) query.role = filterRole.value
    if (filterActive.value) query.is_active = filterActive.value
    users.value = http.results(await http.get('/users/', query))
    // Conteo por rol (usuarios activos) usando el `count` de la paginación de DRF
    const perRole = await Promise.all(roleCards.map(r => http.get<any>('/users/', { role: r.value, is_active: 'true' })))
    counts.value = Object.fromEntries(roleCards.map((r, i) => [r.value, perRole[i]?.count ?? http.results(perRole[i]).length]))
  } catch (e: any) {
    toast.add({ title: 'Error cargando usuarios', description: http.errorMessage(e), color: 'red' })
  } finally { loading.value = false }
}

function openForm(u?: any) {
  Object.assign(form, blankForm(), u ? {
    id: u.id, username: u.username, email: u.email, first_name: u.first_name, last_name: u.last_name,
    role: u.role, phone: u.phone, department: u.department, is_active: u.is_active,
  } : {}, { open: true })
}

async function save() {
  form.saving = true
  const { open, saving, id, ...body } = form as any
  if (id) delete body.password
  try {
    if (id) await http.patch(`/users/${id}/`, body)
    else await http.post('/users/', body)
    toast.add({ title: id ? 'Usuario actualizado' : 'Usuario creado', color: 'green' })
    form.open = false
    await load()
  } catch (e: any) {
    toast.add({ title: 'No se pudo guardar', description: http.errorMessage(e), color: 'red' })
  } finally { form.saving = false }
}

function openPassword(u: any) {
  Object.assign(pwd, { open: true, saving: false, user: u, password: '', confirm: '' })
}

async function savePassword() {
  pwd.saving = true
  try {
    await http.post(`/users/${pwd.user.id}/set-password/`, { password: pwd.password })
    toast.add({ title: 'Contraseña actualizada', color: 'green' })
    pwd.open = false
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { pwd.saving = false }
}

async function toggleActive(u: any) {
  if (u.is_active && !confirm(`¿Desactivar a ${u.name}? No podrá iniciar sesión.`)) return
  try {
    await http.post(`/users/${u.id}/toggle-active/`)
    await load()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  }
}

onMounted(load)
</script>
