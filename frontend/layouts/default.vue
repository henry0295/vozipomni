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
                v-if="!('children' in item)"
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

    <!-- Screen Pop global (llamadas entrantes) -->
    <ScreenPop />
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { user, logout } = useAuth()

// Estados para submenús - usar localStorage con useLocalStorage de @vueuse (SSR-safe)
const expandedMenus = process.client ? useLocalStorage<string[]>('sidebar-expanded-menus', []) : ref<string[]>([])

// Menú y permisos centralizados en utils/navigation.ts
import { navigationForRole, ruleForPath } from '~/utils/navigation'

// Filtrar navegación según el rol del usuario (grupos vacíos se ocultan)
const navigation = computed<any[]>(() => navigationForRole(user.value?.role))

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

// Ruta activa = regla más específica que coincide (evita marcar /settings
// y /settings/whatsapp a la vez)
const activeTo = computed(() => ruleForPath(route.path)?.to)
const isActive = (path: string) => activeTo.value === path

// Verificar si algún hijo del menú está activo
const isChildActive = (children: any[]) => {
  return children.some(child => isActive(child.to))
}

// Auto-expandir menú solo en primera carga si un hijo está activo
let hasInitialized = false
watch(
  () => route.path,
  () => {
    if (!hasInitialized && process.client) {
      // Si el array está vacío (no hay estado guardado), auto-expandir basado en ruta activa
      const expandedRef = expandedMenus as any
      if (expandedRef.value?.length === 0) {
        navigation.value.forEach(item => {
          if (item.children && isChildActive(item.children)) {
            if (!isMenuExpanded(item.id)) {
              expandedRef.value?.push(item.id)
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
