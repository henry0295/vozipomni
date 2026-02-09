<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
      <div class="mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex h-16 items-center justify-between">
          <!-- Logo y título -->
          <div class="flex items-center space-x-4">
            <NuxtLink to="/dashboard" class="flex items-center space-x-2">
              <UIcon name="i-heroicons-phone" class="h-8 w-8 text-sky-500" />
              <span class="text-xl font-bold text-gray-900">VozipOmni</span>
            </NuxtLink>
          </div>

          <!-- Breadcrumb -->
          <nav class="hidden md:flex items-center space-x-2 text-sm">
            <template v-for="(item, index) in breadcrumbs" :key="index">
              <UIcon 
                v-if="index > 0" 
                name="i-heroicons-chevron-right" 
                class="h-4 w-4 text-gray-400" 
              />
              <NuxtLink
                v-if="item.to"
                :to="item.to"
                class="text-gray-600 hover:text-gray-900 transition-colors"
              >
                {{ item.label }}
              </NuxtLink>
              <span v-else class="text-gray-900 font-medium">
                {{ item.label }}
              </span>
            </template>
          </nav>

          <!-- Usuario y acciones -->
          <div class="flex items-center space-x-4">
            <!-- Notificaciones -->
            <UButton
              icon="i-heroicons-bell"
              color="gray"
              variant="ghost"
              size="lg"
              :ui="{ rounded: 'rounded-full' }"
            />

            <!-- Menú de usuario -->
            <UDropdown
              :items="userMenuItems"
              :popper="{ placement: 'bottom-end' }"
            >
              <UButton
                color="white"
                :label="user?.name || 'Usuario'"
                trailing-icon="i-heroicons-chevron-down-20-solid"
              >
                <template #leading>
                  <UAvatar
                    :alt="user?.name"
                    size="xs"
                    :src="user?.avatar"
                  />
                </template>
              </UButton>
            </UDropdown>
          </div>
        </div>
      </div>
    </header>

    <!-- Sidebar y contenido principal -->
    <div class="flex h-[calc(100vh-4rem)]">
      <!-- Sidebar -->
      <aside class="w-64 bg-white border-r border-gray-200 overflow-y-auto">
        <nav class="p-4 space-y-1">
          <template v-for="item in navigation" :key="item.label">
            <NuxtLink
              :to="item.to"
              class="flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors"
              :class="{ 'bg-sky-50 text-sky-700 font-medium': isActive(item.to) }"
            >
              <UIcon :name="item.icon" class="h-5 w-5" />
              <span>{{ item.label }}</span>
            </NuxtLink>
          </template>
        </nav>
      </aside>

      <!-- Contenido principal -->
      <main class="flex-1 overflow-y-auto">
        <div class="p-6">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { user, logout } = useAuth()

// Navegación del sidebar
const navigation = [
  { label: 'Dashboard', icon: 'i-heroicons-home', to: '/dashboard' },
  { label: 'Agentes', icon: 'i-heroicons-user-group', to: '/agents' },
  { label: 'Colas', icon: 'i-heroicons-queue-list', to: '/queues' },
  { label: 'Campañas', icon: 'i-heroicons-megaphone', to: '/campaigns' },
  { label: 'Contactos', icon: 'i-heroicons-users', to: '/contacts' },
  { label: 'Llamadas', icon: 'i-heroicons-phone-arrow-up-right', to: '/calls' },
  { label: 'Grabaciones', icon: 'i-heroicons-microphone', to: '/recordings' },
  { label: 'Reportes', icon: 'i-heroicons-chart-bar', to: '/reports' },
  { label: 'Troncales', icon: 'i-heroicons-server', to: '/trunks' },
  { label: 'Configuración', icon: 'i-heroicons-cog-6-tooth', to: '/settings' }
]

// Menú de usuario
const userMenuItems = [
  [{
    label: 'Perfil',
    icon: 'i-heroicons-user',
    to: '/profile'
  }],
  [{
    label: 'Configuración',
    icon: 'i-heroicons-cog-6-tooth',
    to: '/settings'
  }],
  [{
    label: 'Cerrar sesión',
    icon: 'i-heroicons-arrow-right-on-rectangle',
    click: async () => {
      await logout()
      navigateTo('/login')
    }
  }]
]

// Breadcrumbs dinámicos
const breadcrumbs = computed(() => {
  const paths = route.path.split('/').filter(Boolean)
  const crumbs: Array<{ label: string; to?: string }> = [
    { label: 'Inicio', to: '/dashboard' }
  ]

  let currentPath = ''
  paths.forEach((path, index) => {
    currentPath += `/${path}`
    const isLast = index === paths.length - 1
    
    crumbs.push({
      label: path.charAt(0).toUpperCase() + path.slice(1),
      to: isLast ? undefined : currentPath
    })
  })

  return crumbs
})

// Verificar si una ruta está activa
const isActive = (path: string) => {
  return route.path.startsWith(path)
}
</script>
