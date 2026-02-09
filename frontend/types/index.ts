// Types para la aplicación

export interface User {
  id: number
  username: string
  email: string
  name: string
  avatar?: string
  role: 'admin' | 'supervisor' | 'agent'
  permissions?: string[]
  extension?: string
}

export interface Agent {
  id: number
  name: string
  email: string
  extension: string
  queue: string
  status: 'available' | 'busy' | 'break' | 'offline'
  statusLabel: string
  callsToday: number
  avgTime: string
}

export interface Queue {
  id: number
  name: string
  icon: string
  waiting: number
  agents: number
  avgWaitTime: string
  callsToday: number
  maxWaitTime?: number
  strategy?: 'ringall' | 'leastrecent' | 'fewestcalls' | 'random'
}

export interface Call {
  id: number
  number: string
  duration: string
  type: 'inbound' | 'outbound' | 'internal'
  typeLabel: string
  status: 'ringing' | 'connected' | 'hold' | 'ended' | 'missed'
  agent?: string
  queue?: string
  startTime: string
  endTime?: string
  recording?: string
}

export interface Campaign {
  id: number
  name: string
  description: string
  type: 'preview' | 'progressive' | 'predictive' | 'manual'
  status: 'active' | 'paused' | 'completed'
  contactsTotal: number
  contactsCalled: number
  successRate: number
  startDate: string
  endDate?: string
}

export interface Contact {
  id: number
  firstName: string
  lastName: string
  phone: string
  email?: string
  company?: string
  status: 'new' | 'contacted' | 'qualified' | 'converted'
  lastContact?: string
  notes?: string
}

export interface Trunk {
  id: number
  name: string
  host: string
  port: number
  protocol: 'sip' | 'iax2' | 'pjsip'
  status: 'active' | 'inactive' | 'error'
  callsActive: number
  callsTotal: number
}

export interface Recording {
  id: number
  callId: number
  filename: string
  duration: number
  date: string
  agent: string
  customer: string
  url: string
}

export interface DashboardStats {
  activeAgents: number
  queuedCalls: number
  callsToday: number
  avgTime: string
  answeredCalls?: number
  missedCalls?: number
  abandonedCalls?: number
}

export interface ApiResponse<T> {
  data: T
  message?: string
  status: number
}

export interface PaginatedResponse<T> {
  results: T[]
  count: number
  next: string | null
  previous: string | null
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
}

export type AgentStatus = 'available' | 'busy' | 'break' | 'offline'
export type CallType = 'inbound' | 'outbound' | 'internal'
export type CampaignType = 'preview' | 'progressive' | 'predictive' | 'manual'
export type UserRole = 'admin' | 'supervisor' | 'agent'
