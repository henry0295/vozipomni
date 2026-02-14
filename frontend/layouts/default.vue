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
      <ClientOnly>
        <aside class="w-64 bg-white border-r border-gray-200 overflow-y-auto">
          <nav class="p-4 space-y-1">
            <template v-for="item in navigation" :key="item.label">
              <!-- Item sin submenu -->
              <NuxtLink
                v-if="!item.children"
                :to="item.to"
                class="flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors"
                :class="{ 'bg-sky-50 text-sky-700 font-medium': isActive(item.to) }"
              >
                <UIcon :name="item.icon" class="h-5 w-5" />
                <span>{{ item.label }}</span>
              </NuxtLink>

              <!-- Item con submenu -->
              <div v-else class="space-y-1">
                <!-- Botón para expandir/contraer -->
                <button
                  @click="toggleMenu(item.id)"
                  class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-gray-700 hover:bg-gray-100 hover:text-gray-900 transition-colors"
                  :class="{ 
                    'bg-sky-50 text-sky-700 font-medium': isChildActive(item.children),
                    'bg-gray-100': isMenuExpanded(item.id) && !isChildActive(item.children)
                  }"
                >
                  <div class="flex items-center space-x-3">
                    <UIcon :name="item.icon" class="h-5 w-5" />
                    <span>{{ item.label }}</span>
                  </div>
                  <UIcon 
                    name="i-heroicons-chevron-right" 
                    class="h-4 w-4 transition-transform"
                    :class="{ 'rotate-90': isMenuExpanded(item.id) }"
                  />
                </button>

                <!-- Submenu desplegable -->
                <transition
                  enter-active-class="transition ease-out duration-200"
                  enter-from-class="opacity-0 -translate-y-1"
                  enter-to-class="opacity-100 translate-y-0"
                  leave-active-class="transition ease-in duration-150"
                  leave-from-class="opacity-100 translate-y-0"
                  leave-to-class="opacity-0 -translate-y-1"
                >
                  <div v-if="isMenuExpanded(item.id)" class="space-y-1 pl-4">
                    <NuxtLink
                      v-for="child in item.children"
                      :key="child.label"
                      :to="child.to"
                      class="flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors text-sm"
                      :class="{ 'bg-sky-50 text-sky-700 font-medium': isActive(child.to) }"
                    >
                      <UIcon :name="child.icon" class="h-4 w-4" />
                      <span>{{ child.label }}</span>
                    </NuxtLink>
                  </div>
                </transition>
              </div>
            </template>
          </nav>
        </aside>
      </ClientOnly>

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

// Estados para submenús - usar localStorage con useLocalStorage de @vueuse
const expandedMenus = useLocalStorage<string[]>('sidebar-expanded-menus', [])

// Navegación del sidebar con submenu para Telefonía
const navigation = [
  { label: 'Dashboard', icon: 'i-heroicons-home', to: '/dashboard' },
  { label: 'Agentes', icon: 'i-heroicons-user-group', to: '/agents' },
  { label: 'Campañas', icon: 'i-heroicons-megaphone', to: '/campaigns' },
  { label: 'Contactos', icon: 'i-heroicons-users', to: '/contacts' },
  { label: 'Llamadas', icon: 'i-heroicons-phone-arrow-up-right', to: '/calls' },
  { label: 'Reportes', icon: 'i-heroicons-chart-bar', to: '/reports' },
  
  // Menú desplegable de Telefonía - Contact Center
  {
    label: 'Telefonía',
    icon: 'i-heroicons-phone',
    id: 'telephony',
    children: [
      { label: 'Colas', icon: 'i-heroicons-queue-list', to: '/queues' },
      { label: 'Troncales SIP', icon: 'i-heroicons-server', to: '/trunks' },
      { label: 'Rutas Entrantes (DIDs)', icon: 'i-heroicons-arrow-down-left', to: '/inbound-routes' },
      { label: 'Rutas Salientes', icon: 'i-heroicons-arrow-up-right', to: '/outbound-routes' },
      { label: 'IVR Menus', icon: 'i-heroicons-microphone', to: '/ivr' },
      { label: 'Extensiones', icon: 'i-heroicons-hashtag', to: '/extensions' },
      { label: 'Buzones de Voz', icon: 'i-heroicons-inbox', to: '/voicemail' },
      { label: 'Condiciones Horario', icon: 'i-heroicons-clock', to: '/time-conditions' },
      { label: 'Grabaciones', icon: 'i-heroicons-video-camera', to: '/recordings' },
      { label: 'Configuración', icon: 'i-heroicons-cog-6-tooth', to: '/settings' }
    ]
  }
]

// Funciones para manejar el menú desplegable
const toggleMenu = (menuId: string) => {
  const index = expandedMenus.value.indexOf(menuId)
  if (index > -1) {
    expandedMenus.value.splice(index, 1)
  } else {
    expandedMenus.value.push(menuId)
  }
}

const isMenuExpanded = (menuId: string) => {
  return expandedMenus.value.includes(menuId)
}

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

// Verificar si algún hijo del menú está activo
const isChildActive = (children: any[]) => {
  return children.some(child => isActive(child.to))
}

// Auto-expandir menú solo en primera carga si un hijo está activo
let hasInitialized = false
watch(
  () => route.path,
  () => {
    // Solo auto-expandir en la primera carga si no hay estado guardado
    if (!hasInitialized) {
      // Si el array está vacío (no hay estado guardado), auto-expandir basado en ruta activa
      if (expandedMenus.value.length === 0) {
        navigation.forEach(item => {
          if (item.children && isChildActive(item.children)) {
            if (!isMenuExpanded(item.id)) {
              expandedMenus.value.push(item.id)
            }
          }
        })
      }
      
      hasInitialized = true
    }
  },
  { immediate: true }
)
</script>
