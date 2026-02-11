<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-gray-900">Mi Perfil</h1>
      <UButton
        label="Cambiar Contraseña"
        icon="i-heroicons-key"
        color="gray"
        @click="showPasswordModal = true"
      />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Información Personal -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Datos básicos -->
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold">Información Personal</h3>
          </template>

          <div class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <UFormGroup label="Nombre Completo" required>
                <UInput v-model="profile.name" />
              </UFormGroup>
              
              <UFormGroup label="Email" required>
                <UInput v-model="profile.email" type="email" />
              </UFormGroup>
              
              <UFormGroup label="Teléfono">
                <UInput v-model="profile.phone" type="tel" />
              </UFormGroup>
              
              <UFormGroup label="Cargo">
                <UInput v-model="profile.position" />
              </UFormGroup>
              
              <UFormGroup label="Departamento">
                <USelect 
                  v-model="profile.department"
                  :options="departmentOptions"
                />
              </UFormGroup>
              
              <UFormGroup label="Zona Horaria">
                <USelect 
                  v-model="profile.timezone"
                  :options="timezoneOptions"
                />
              </UFormGroup>
            </div>

            <div class="flex justify-end">
              <UButton 
                @click="saveProfile"
                :loading="saving"
              >
                Guardar Cambios
              </UButton>
            </div>
          </div>
        </UCard>

        <!-- Configuración de agente -->
        <UCard v-if="user?.role === 'agent'">
          <template #header>
            <h3 class="text-lg font-semibold">Configuración de Agente</h3>
          </template>

          <div class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <UFormGroup label="Extensión SIP">
                <UInput v-model="agentConfig.extension" disabled />
              </UFormGroup>
              
              <UFormGroup label="Estado por Defecto">
                <USelect 
                  v-model="agentConfig.default_status"
                  :options="statusOptions"
                />
              </UFormGroup>
              
              <UFormGroup label="Auto-Login">
                <UToggle v-model="agentConfig.auto_login" />
              </UFormGroup>
              
              <UFormGroup label="WebRTC Habilitado">
                <UToggle v-model="agentConfig.webrtc_enabled" />
              </UFormGroup>
            </div>
          </div>
        </UCard>

        <!-- Notificaciones -->
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold">Preferencias de Notificaciones</h3>
          </template>

          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <div class="font-medium">Notificaciones de Email</div>
                <div class="text-sm text-gray-500">Recibir alertas importantes por email</div>
              </div>
              <UToggle v-model="notifications.email" />
            </div>

            <div class="flex items-center justify-between">
              <div>
                <div class="font-medium">Notificaciones del Sistema</div>
                <div class="text-sm text-gray-500">Mostrar notificaciones en el navegador</div>
              </div>
              <UToggle v-model="notifications.browser" />
            </div>

            <div class="flex items-center justify-between">
              <div>
                <div class="font-medium">Sonidos de Alerta</div>
                <div class="text-sm text-gray-500">Reproducir sonidos para nuevas llamadas</div>
              </div>
              <UToggle v-model="notifications.sounds" />
            </div>

            <div class="flex items-center justify-between">
              <div>
                <div class="font-medium">Reportes Semanales</div>
                <div class="text-sm text-gray-500">Recibir resumen semanal de actividad</div>
              </div>
              <UToggle v-model="notifications.weekly_reports" />
            </div>
          </div>
        </UCard>
      </div>

      <!-- Sidebar -->
      <div class="space-y-6">
        <!-- Avatar y info básica -->
        <UCard>
          <div class="text-center space-y-4">
            <div class="flex justify-center">
              <UAvatar
                :src="user?.avatar"
                :alt="user?.name"
                size="xl"
              />
            </div>
            
            <div>
              <h3 class="text-lg font-semibold">{{ user?.name }}</h3>
              <p class="text-gray-600">{{ user?.email }}</p>
              <UBadge 
                :label="user?.role" 
                color="sky" 
                class="mt-2"
              />
            </div>

            <UButton
              label="Cambiar Avatar"
              icon="i-heroicons-camera"
              color="gray"
              variant="outline"
              @click="changeAvatar"
            />
          </div>
        </UCard>

        <!-- Estadísticas -->
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold">Estadísticas</h3>
          </template>

          <div class="space-y-4">
            <div class="flex justify-between items-center">
              <span class="text-gray-600">Último Login</span>
              <span class="font-medium">{{ formatDate(stats.last_login) }}</span>
            </div>
            
            <div class="flex justify-between items-center">
              <span class="text-gray-600">Días Activo</span>
              <span class="font-medium">{{ stats.active_days }} días</span>
            </div>
            
            <div v-if="user?.role === 'agent'" class="space-y-2">
              <div class="flex justify-between items-center">
                <span class="text-gray-600">Llamadas Hoy</span>
                <span class="font-medium">{{ stats.calls_today }}</span>
              </div>
              
              <div class="flex justify-between items-center">
                <span class="text-gray-600">Tiempo Total</span>
                <span class="font-medium">{{ stats.total_time }}</span>
              </div>
            </div>
          </div>
        </UCard>

        <!-- Seguridad -->
        <UCard>
          <template #header>
            <h3 class="text-lg font-semibold">Seguridad</h3>
          </template>

          <div class="space-y-3">
            <UButton
              label="Cambiar Contraseña"
              icon="i-heroicons-key"
              color="gray"
              variant="outline"
              block
              @click="showPasswordModal = true"
            />
            
            <UButton
              label="Activar 2FA"
              icon="i-heroicons-shield-check"
              color="green"
              variant="outline"
              block
            />
            
            <UButton
              label="Ver Sesiones Activas"
              icon="i-heroicons-computer-desktop"
              color="gray"
              variant="outline"
              block
            />
          </div>
        </UCard>
      </div>
    </div>

    <!-- Modal cambio de contraseña -->
    <UModal v-model="showPasswordModal">
      <UCard>
        <template #header>
          <h3 class="text-lg font-semibold">Cambiar Contraseña</h3>
        </template>

        <div class="space-y-4">
          <UFormGroup label="Contraseña Actual" required>
            <UInput 
              v-model="passwordForm.current" 
              type="password"
            />
          </UFormGroup>
          
          <UFormGroup label="Nueva Contraseña" required>
            <UInput 
              v-model="passwordForm.new" 
              type="password"
            />
          </UFormGroup>
          
          <UFormGroup label="Confirmar Nueva Contraseña" required>
            <UInput 
              v-model="passwordForm.confirm" 
              type="password"
            />
          </UFormGroup>
        </div>

        <template #footer>
          <div class="flex justify-end space-x-2">
            <UButton 
              color="gray" 
              @click="showPasswordModal = false"
            >
              Cancelar
            </UButton>
            <UButton 
              @click="changePassword"
              :loading="changingPassword"
            >
              Cambiar Contraseña
            </UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default',  
  middleware: 'auth'
})

const { user } = useAuth()

// Estados reactivos
const saving = ref(false)
const changingPassword = ref(false)
const showPasswordModal = ref(false)

// Datos del perfil
const profile = reactive({
  name: user.value?.name || '',
  email: user.value?.email || '',
  phone: '+57 300 123 4567',
  position: 'Agente de Contact Center',
  department: 'operaciones',
  timezone: 'America/Bogota'
})

// Configuración de agente
const agentConfig = reactive({
  extension: '1001',
  default_status: 'available',
  auto_login: true,
  webrtc_enabled: true
})

// Notificaciones
const notifications = reactive({
  email: true,
  browser: true,
  sounds: true,
  weekly_reports: false
})

// Formulario de contraseña
const passwordForm = reactive({
  current: '',
  new: '',
  confirm: ''
})

// Estadísticas
const stats = reactive({
  last_login: '2026-02-11T09:00:00Z',
  active_days: 45,
  calls_today: 23,
  total_time: '6h 42m'
})

// Opciones
const departmentOptions = [
  { label: 'Operaciones', value: 'operaciones' },
  { label: 'Supervisión', value: 'supervision' },
  { label: 'Administración', value: 'admin' }
]

const timezoneOptions = [
  { label: 'Bogotá (GMT-5)', value: 'America/Bogota' },
  { label: 'México (GMT-6)', value: 'America/Mexico_City' },
  { label: 'Buenos Aires (GMT-3)', value: 'America/Argentina/Buenos_Aires' }
]

const statusOptions = [
  { label: 'Disponible', value: 'available' },
  { label: 'En Llamada', value: 'busy' },
  { label: 'Descanso', value: 'break' }
]

// Funciones
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('es-CO', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const saveProfile = async () => {
  saving.value = true
  
  // Simular guardado
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // Aquí iría la llamada a la API
  console.log('Guardando perfil:', profile)
  
  saving.value = false
  
  // Mostrar notificación de éxito
}

const changePassword = async () => {
  if (passwordForm.new !== passwordForm.confirm) {
    // Mostrar error de contraseñas no coinciden
    return
  }
  
  changingPassword.value = true
  
  // Simular cambio
  await new Promise(resolve => setTimeout(resolve, 1000))
  
  // Aquí iría la llamada a la API
  console.log('Cambiando contraseña')
  
  changingPassword.value = false
  showPasswordModal.value = false
  
  // Limpiar formulario
  Object.keys(passwordForm).forEach(key => {
    passwordForm[key] = ''
  })
}

const changeAvatar = () => {
  // Implementar cambio de avatar
  console.log('Cambiar avatar')
}

// Metadata de la página
useHead({
  title: 'Mi Perfil - VozipOmni'
})
</script>