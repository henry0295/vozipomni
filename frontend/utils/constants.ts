/**
 * Constantes de la aplicación
 */

// Estados de agente
export const AGENT_STATUS = {
  AVAILABLE: 'available',
  BUSY: 'busy',
  BREAK: 'break',
  OFFLINE: 'offline'
} as const

export const AGENT_STATUS_LABELS = {
  [AGENT_STATUS.AVAILABLE]: 'Disponible',
  [AGENT_STATUS.BUSY]: 'En llamada',
  [AGENT_STATUS.BREAK]: 'En descanso',
  [AGENT_STATUS.OFFLINE]: 'Desconectado'
} as const

// Tipos de llamada
export const CALL_TYPES = {
  INBOUND: 'inbound',
  OUTBOUND: 'outbound',
  INTERNAL: 'internal'
} as const

export const CALL_TYPE_LABELS = {
  [CALL_TYPES.INBOUND]: 'Entrante',
  [CALL_TYPES.OUTBOUND]: 'Saliente',
  [CALL_TYPES.INTERNAL]: 'Interna'
} as const

// Estados de llamada
export const CALL_STATUS = {
  RINGING: 'ringing',
  CONNECTED: 'connected',
  HOLD: 'hold',
  ENDED: 'ended',
  MISSED: 'missed'
} as const

// Tipos de campaña
export const CAMPAIGN_TYPES = {
  PREVIEW: 'preview',
  PROGRESSIVE: 'progressive',
  PREDICTIVE: 'predictive',
  MANUAL: 'manual'
} as const

export const CAMPAIGN_TYPE_LABELS = {
  [CAMPAIGN_TYPES.PREVIEW]: 'Preview',
  [CAMPAIGN_TYPES.PROGRESSIVE]: 'Progresivo',
  [CAMPAIGN_TYPES.PREDICTIVE]: 'Predictivo',
  [CAMPAIGN_TYPES.MANUAL]: 'Manual'
} as const

// Roles de usuario
export const USER_ROLES = {
  ADMIN: 'admin',
  SUPERVISOR: 'supervisor',
  AGENT: 'agent'
} as const

export const USER_ROLE_LABELS = {
  [USER_ROLES.ADMIN]: 'Administrador',
  [USER_ROLES.SUPERVISOR]: 'Supervisor',
  [USER_ROLES.AGENT]: 'Agente'
} as const

// Períodos de tiempo para reportes
export const TIME_PERIODS = {
  TODAY: 'today',
  YESTERDAY: 'yesterday',
  LAST_7_DAYS: 'last7days',
  LAST_30_DAYS: 'last30days',
  THIS_MONTH: 'thismonth',
  LAST_MONTH: 'lastmonth',
  CUSTOM: 'custom'
} as const

// Configuración de paginación
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 25,
  PAGE_SIZE_OPTIONS: [10, 25, 50, 100]
} as const

// Tiempos de refresco (ms)
export const REFRESH_INTERVALS = {
  DASHBOARD: 5000,
  QUEUE: 3000,
  AGENTS: 5000,
  CALLS: 2000
} as const

// API endpoints
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login/',
    LOGOUT: '/auth/logout/',
    REFRESH: '/auth/refresh/',
    ME: '/auth/me/'
  },
  AGENTS: '/agents/',
  QUEUES: '/queues/',
  CAMPAIGNS: '/campaigns/',
  CONTACTS: '/contacts/',
  CALLS: '/calls/',
  RECORDINGS: '/recordings/',
  REPORTS: '/reports/',
  TRUNKS: '/telephony/trunks/'
} as const
