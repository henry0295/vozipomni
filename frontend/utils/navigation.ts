/**
 * Fuente única de verdad para el menú lateral y los permisos por ruta.
 *
 * - El layout usa NAVIGATION para pintar el menú filtrado por rol.
 * - El middleware global access.global.ts usa canAccessRoute() para
 *   impedir el acceso directo por URL a módulos no permitidos.
 *
 * Roles: admin | supervisor | analyst | agent
 * `roles` ausente = cualquier usuario autenticado (salvo agentes, que
 * siempre van a su consola).
 */
export type Role = 'admin' | 'supervisor' | 'analyst' | 'agent'

export interface NavLink {
  label: string
  icon: string
  to: string
  roles?: Role[]
}

export interface NavGroup {
  id: string
  label: string
  icon: string
  roles?: Role[]
  children: NavLink[]
}

export type NavItem = NavLink | NavGroup

const ADMIN: Role[] = ['admin']
const ADMIN_SUP: Role[] = ['admin', 'supervisor']
const ADMIN_SUP_ANALYST: Role[] = ['admin', 'supervisor', 'analyst']

export const NAVIGATION: NavItem[] = [
  { label: 'Dashboard', icon: 'i-heroicons-home', to: '/dashboard', roles: ADMIN_SUP_ANALYST },

  {
    id: 'supervision',
    label: 'Supervisión',
    icon: 'i-heroicons-presentation-chart-line',
    roles: ADMIN_SUP,
    children: [
      { label: 'Monitor en vivo', icon: 'i-heroicons-signal', to: '/supervisor', roles: ADMIN_SUP },
      { label: 'Bandeja omnicanal', icon: 'i-heroicons-chat-bubble-left-right', to: '/messaging', roles: ADMIN_SUP },
      { label: 'Auditoría de gestiones', icon: 'i-heroicons-clipboard-document-check', to: '/audit', roles: ADMIN_SUP },
    ],
  },

  {
    id: 'operation',
    label: 'Operación',
    icon: 'i-heroicons-briefcase',
    roles: ADMIN_SUP_ANALYST,
    children: [
      { label: 'Agentes', icon: 'i-heroicons-user-group', to: '/agents', roles: ADMIN_SUP },
      { label: 'Campañas', icon: 'i-heroicons-megaphone', to: '/campaigns', roles: ADMIN_SUP_ANALYST },
      { label: 'Formularios de campaña', icon: 'i-heroicons-document-text', to: '/campaign-forms', roles: ADMIN_SUP },
      { label: 'Contactos', icon: 'i-heroicons-users', to: '/contacts', roles: ADMIN_SUP },
      { label: 'Lista negra (DNC)', icon: 'i-heroicons-no-symbol', to: '/contacts/blacklist', roles: ADMIN_SUP },
      { label: 'Callbacks', icon: 'i-heroicons-phone-arrow-down-left', to: '/callbacks', roles: ADMIN_SUP },
      { label: 'Llamadas', icon: 'i-heroicons-phone-arrow-up-right', to: '/calls', roles: ADMIN_SUP_ANALYST },
    ],
  },

  {
    id: 'quality',
    label: 'Calidad',
    icon: 'i-heroicons-star',
    roles: ADMIN_SUP_ANALYST,
    children: [
      { label: 'Evaluaciones', icon: 'i-heroicons-star', to: '/quality', roles: ADMIN_SUP_ANALYST },
      { label: 'Plantillas de evaluación', icon: 'i-heroicons-clipboard-document-list', to: '/quality/templates', roles: ADMIN_SUP },
      { label: 'Grabaciones', icon: 'i-heroicons-microphone', to: '/recordings', roles: ADMIN_SUP_ANALYST },
    ],
  },

  {
    id: 'reports',
    label: 'Reportes',
    icon: 'i-heroicons-chart-bar',
    roles: ADMIN_SUP_ANALYST,
    children: [
      { label: 'KPIs y métricas', icon: 'i-heroicons-chart-pie', to: '/reports', roles: ADMIN_SUP_ANALYST },
      { label: 'Exportar / programados', icon: 'i-heroicons-arrow-down-tray', to: '/reports/saved', roles: ADMIN_SUP_ANALYST },
    ],
  },

  {
    id: 'telephony',
    label: 'Telefonía',
    icon: 'i-heroicons-phone',
    roles: ADMIN_SUP,
    children: [
      { label: 'Colas', icon: 'i-heroicons-queue-list', to: '/queues', roles: ADMIN_SUP },
      { label: 'Troncales SIP', icon: 'i-heroicons-server', to: '/trunks', roles: ADMIN },
      { label: 'Rutas Entrantes (DIDs)', icon: 'i-heroicons-arrow-down-left', to: '/inbound-routes', roles: ADMIN },
      { label: 'Rutas Salientes', icon: 'i-heroicons-arrow-up-right', to: '/outbound-routes', roles: ADMIN },
      { label: 'IVR Menus', icon: 'i-heroicons-microphone', to: '/ivr', roles: ADMIN },
      { label: 'Extensiones', icon: 'i-heroicons-hashtag', to: '/extensions', roles: ADMIN },
      { label: 'Buzones de Voz', icon: 'i-heroicons-inbox', to: '/voicemail', roles: ADMIN },
      { label: 'Condiciones Horario', icon: 'i-heroicons-clock', to: '/time-conditions', roles: ADMIN },
      { label: 'Destinos Personalizados', icon: 'i-heroicons-map-pin', to: '/custom-destinations', roles: ADMIN },
    ],
  },

  {
    id: 'admin',
    label: 'Administración',
    icon: 'i-heroicons-cog-6-tooth',
    roles: ADMIN_SUP,
    children: [
      { label: 'Usuarios y roles', icon: 'i-heroicons-identification', to: '/users', roles: ADMIN },
      { label: 'WhatsApp Business', icon: 'i-heroicons-chat-bubble-oval-left-ellipsis', to: '/settings/whatsapp', roles: ADMIN },
      { label: 'Grupos y pausas', icon: 'i-heroicons-adjustments-horizontal', to: '/settings/advanced', roles: ADMIN_SUP },
      { label: 'Webhooks', icon: 'i-heroicons-link', to: '/webhooks', roles: ADMIN_SUP },
      { label: 'Configuración', icon: 'i-heroicons-cog-6-tooth', to: '/settings', roles: ADMIN },
    ],
  },
]

export const isGroup = (item: NavItem): item is NavGroup => 'children' in item

const allowed = (roles: Role[] | undefined, role: string | undefined) =>
  !roles || (!!role && roles.includes(role as Role))

/** Menú filtrado para un rol (grupos vacíos se ocultan). */
export const navigationForRole = (role: string | undefined): NavItem[] =>
  NAVIGATION.flatMap((item): NavItem[] => {
    if (!allowed(item.roles, role)) return []
    if (isGroup(item)) {
      const children = item.children.filter((c) => allowed(c.roles, role))
      return children.length ? [{ ...item, children }] : []
    }
    return [item]
  })

/** Todas las rutas con sus roles (planas). */
const ROUTE_RULES: NavLink[] = NAVIGATION.flatMap((i) => (isGroup(i) ? i.children : [i]))

const matches = (path: string, to: string) => path === to || path.startsWith(to + '/')

/** Regla más específica (prefijo más largo) que aplica a una ruta. */
export const ruleForPath = (path: string): NavLink | undefined =>
  ROUTE_RULES.filter((r) => matches(path, r.to)).sort((a, b) => b.to.length - a.to.length)[0]

/** ¿El rol puede entrar a esta ruta? Rutas sin regla = libres para autenticados. */
export const canAccessRoute = (path: string, role: string | undefined): boolean => {
  const rule = ruleForPath(path)
  return !rule || allowed(rule.roles, role)
}

/** Ruta de inicio según rol. */
export const homeForRole = (role: string | undefined): string => {
  if (role === 'agent') return '/agent/console'
  if (role === 'supervisor') return '/supervisor'
  return '/dashboard'
}

/** Rutas públicas (sin sesión). */
export const PUBLIC_ROUTES = ['/', '/login', '/forgot-password', '/reset-password']
