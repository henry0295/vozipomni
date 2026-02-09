<template>
  <div>
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900">Configuración</h1>
      <p class="text-gray-600 mt-2">Administra las configuraciones del sistema</p>
    </div>

    <!-- Tabs de configuración -->
    <UTabs :items="tabs" v-model="activeTab">
      <!-- General -->
      <template #general>
        <UCard class="mt-6">
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">Configuración General</h2>
          </template>

          <div class="space-y-6">
            <UFormGroup label="Nombre de la Empresa" required>
              <UInput v-model="settings.companyName" placeholder="VozipOmni" />
            </UFormGroup>

            <UFormGroup label="Zona Horaria" required>
              <USelectMenu
                v-model="settings.timezone"
                :options="timezones"
                placeholder="Selecciona zona horaria"
              />
            </UFormGroup>

            <UFormGroup label="Idioma" required>
              <USelectMenu
                v-model="settings.language"
                :options="languages"
                placeholder="Selecciona idioma"
              />
            </UFormGroup>
          </div>

          <template #footer>
            <div class="flex justify-end">
              <UButton @click="saveSettings">Guardar Cambios</UButton>
            </div>
          </template>
        </UCard>
      </template>

      <!-- Asterisk -->
      <template #asterisk>
        <UCard class="mt-6">
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">Configuración de Asterisk</h2>
          </template>

          <div class="space-y-6">
            <UFormGroup label="Host AMI" required>
              <UInput v-model="asteriskSettings.amiHost" placeholder="localhost" />
            </UFormGroup>

            <UFormGroup label="Puerto AMI" required>
              <UInput v-model="asteriskSettings.amiPort" type="number" placeholder="5038" />
            </UFormGroup>

            <UFormGroup label="Usuario AMI" required>
              <UInput v-model="asteriskSettings.amiUser" placeholder="admin" />
            </UFormGroup>

            <UFormGroup label="Contraseña AMI" required>
              <UInput v-model="asteriskSettings.amiPassword" type="password" />
            </UFormGroup>

            <div class="pt-4 border-t border-gray-200">
              <UButton color="gray" variant="outline" @click="testAmiConnection">
                <template #leading>
                  <UIcon name="i-heroicons-signal" />
                </template>
                Probar Conexión AMI
              </UButton>
            </div>
          </div>

          <template #footer>
            <div class="flex justify-end">
              <UButton @click="saveAsteriskSettings">Guardar Cambios</UButton>
            </div>
          </template>
        </UCard>
      </template>

      <!-- Notificaciones -->
      <template #notifications>
        <UCard class="mt-6">
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">Notificaciones</h2>
          </template>

          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-gray-900">Notificaciones de llamadas</p>
                <p class="text-sm text-gray-600">Recibe alertas de nuevas llamadas</p>
              </div>
              <UToggle v-model="notificationSettings.calls" />
            </div>

            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-gray-900">Notificaciones de agentes</p>
                <p class="text-sm text-gray-600">Alertas de cambios de estado de agentes</p>
              </div>
              <UToggle v-model="notificationSettings.agents" />
            </div>

            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-gray-900">Notificaciones de cola</p>
                <p class="text-sm text-gray-600">Alertas cuando la cola supera el límite</p>
              </div>
              <UToggle v-model="notificationSettings.queue" />
            </div>

            <div class="flex items-center justify-between">
              <div>
                <p class="font-medium text-gray-900">Sonidos de notificación</p>
                <p class="text-sm text-gray-600">Reproducir sonido con las alertas</p>
              </div>
              <UToggle v-model="notificationSettings.sound" />
            </div>
          </div>

          <template #footer>
            <div class="flex justify-end">
              <UButton @click="saveNotificationSettings">Guardar Cambios</UButton>
            </div>
          </template>
        </UCard>
      </template>
    </UTabs>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  middleware: ['auth']
})

const toast = useToast()
const activeTab = ref(0)

const tabs = [
  { label: 'General', value: 'general', slot: 'general' },
  { label: 'Asterisk', value: 'asterisk', slot: 'asterisk' },
  { label: 'Notificaciones', value: 'notifications', slot: 'notifications' }
]

const settings = reactive({
  companyName: 'VozipOmni',
  timezone: 'America/Bogota',
  language: 'es'
})

const asteriskSettings = reactive({
  amiHost: 'localhost',
  amiPort: 5038,
  amiUser: 'admin',
  amiPassword: ''
})

const notificationSettings = reactive({
  calls: true,
  agents: true,
  queue: true,
  sound: true
})

const timezones = [
  { label: 'América/Bogotá', value: 'America/Bogota' },
  { label: 'América/México', value: 'America/Mexico_City' },
  { label: 'América/Lima', value: 'America/Lima' }
]

const languages = [
  { label: 'Español', value: 'es' },
  { label: 'English', value: 'en' }
]

const saveSettings = () => {
  toast.add({
    title: 'Configuración guardada',
    description: 'Los cambios se han guardado correctamente',
    color: 'green'
  })
}

const saveAsteriskSettings = () => {
  toast.add({
    title: 'Configuración de Asterisk guardada',
    color: 'green'
  })
}

const saveNotificationSettings = () => {
  toast.add({
    title: 'Configuración de notificaciones guardada',
    color: 'green'
  })
}

const testAmiConnection = async () => {
  // TODO: Implementar prueba de conexión AMI
  toast.add({
    title: 'Probando conexión...',
    description: 'Verificando conectividad con Asterisk AMI',
    color: 'blue'
  })
}
</script>
