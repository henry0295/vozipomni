// Types para la aplicación

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  name?: string
  avatar?: string
  role: 'admin' | 'supervisor' | 'agent'
  phone?: string
  department?: string
  is_active_agent: boolean
  last_activity?: string
  permissions?: string[]
}

export interface Agent {
  id: number
  user: number
  user_details?: User
  agent_id: string
  sip_extension: string
  status: 'available' | 'busy' | 'oncall' | 'break' | 'offline' | 'wrapup'
  webrtc_enabled: boolean
  max_concurrent_calls: number
  auto_answer: boolean
  recording_enabled: boolean
  current_calls: number
  last_call_time?: string
  logged_in_at?: string
  calls_today: number
  talk_time_today: number
  available_time_today: number
  break_time_today: number
  is_available?: boolean
  created_at: string
  updated_at: string
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
  call_id: string
  channel: string
  unique_id: string
  direction: 'inbound' | 'outbound'
  status: 'initiated' | 'ringing' | 'answered' | 'completed' | 'busy' | 'no_answer' | 'failed' | 'cancelled'
  caller_id: string
  called_number: string
  agent?: number
  agent_name?: string
  campaign?: number
  campaign_name?: string
  contact?: number
  queue?: number
  start_time: string
  answer_time?: string
  end_time?: string
  wait_time: number
  talk_time: number
  hold_time: number
  duration?: number
  recording_file?: string
  is_recorded: boolean
  transferred: boolean
  transfer_to?: string
  notes?: string
  metadata?: any
}

export interface Recording {
  id: number
  call: number
  call_details?: Call
  filename: string
  file_path: string
  file_size: number
  file_size_mb?: number
  format: string
  duration: number
  codec?: string
  status: 'recording' | 'completed' | 'failed' | 'archived'
  agent?: number
  campaign?: number
  transcription?: string
  transcription_status?: string
  is_public: boolean
  access_count: number
  created_at: string
  updated_at: string
  archived_at?: string
}

export interface SipTrunk {
  id: number
  name: string
  description?: string
  trunk_type: string
  host: string
  port: number
  protocol: string
  outbound_auth_username?: string
  outbound_auth_password?: string
  from_user?: string
  from_domain?: string
  inbound_auth_username?: string
  inbound_auth_password?: string
  sends_registration: boolean
  registration_server_uri?: string
  registration_client_uri?: string
  sends_auth: boolean
  accepts_auth: boolean
  accepts_registrations: boolean
  rtp_symmetric: boolean
  force_rport: boolean
  rewrite_contact: boolean
  direct_media: boolean
  codec: string
  dtmf_mode: string
  context: string
  custom_context?: string
  max_channels: number
  caller_id?: string
  caller_id_name?: string
  is_active: boolean
  is_registered: boolean
  last_registration_time?: string
  calls_total: number
  calls_active: number
  calls_successful: number
  calls_failed: number
  concurrent_calls?: number
  status?: string
  username?: string
  password?: string
  created_at: string
  updated_at: string
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
