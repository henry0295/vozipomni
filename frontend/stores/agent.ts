import { defineStore } from 'pinia'
import type { Agent } from '~/types'

export type AgentStatus = 'offline' | 'available' | 'busy' | 'oncall' | 'break' | 'wrapup'

export interface Break {
  id: string
  name: string
  duration?: number
}

export interface CurrentCall {
  callId: string
  direction: 'inbound' | 'outbound' | 'internal'
  remoteNumber: string
  remoteName?: string
  startTime: Date
  campaignId?: number
  contactId?: number
  queueName?: string
}

export interface AgentState {
  agent: Agent | null
  status: AgentStatus
  currentCall: CurrentCall | null
  pauseReason: string | null
  sessionStartTime: Date | null
  webSocket: WebSocket | null
  stats: {
    callsToday: number
    talkTimeToday: number
    availableTimeToday: number
    breakTimeToday: number
    wrapupTimeToday: number
  }
}

export const useAgentStore = defineStore('agent', {
  state: (): AgentState => ({
    agent: null,
    status: 'offline',
    currentCall: null,
    pauseReason: null,
    sessionStartTime: null,
    webSocket: null,
    stats: {
      callsToday: 0,
      talkTimeToday: 0,
      availableTimeToday: 0,
      breakTimeToday: 0,
      wrapupTimeToday: 0
    }
  }),

  getters: {
    isLoggedIn: (state) => state.status !== 'offline' && state.agent !== null,
    isOnCall: (state) => state.status === 'oncall' && state.currentCall !== null,
    isAvailable: (state) => state.status === 'available',
    isOnBreak: (state) => state.status === 'break',
    canReceiveCalls: (state) => state.status === 'available',
    
    sessionDuration: (state) => {
      if (!state.sessionStartTime) return 0
      return Math.floor((Date.now() - state.sessionStartTime.getTime()) / 1000)
    },

    callDuration: (state) => {
      if (!state.currentCall) return 0
      return Math.floor((Date.now() - state.currentCall.startTime.getTime()) / 1000)
    }
  },

  actions: {
    // Login del agente
    async login(agentData: Agent) {
      const { loginAgent } = useAgents()
      
      try {
        const { error } = await loginAgent(agentData.id)
        if (error) throw error

        this.agent = agentData
        this.status = 'available'
        this.sessionStartTime = new Date()
        
        // Conectar WebSocket
        this.connectWebSocket()
        
        return { success: true }
      } catch (err: any) {
        return { success: false, error: err.message }
      }
    },

    // Logout del agente
    async logout() {
      const { logoutAgent } = useAgents()
      
      if (!this.agent) return

      try {
        await logoutAgent(this.agent.id)
        
        // Desconectar WebSocket
        this.disconnectWebSocket()
        
        // Reset state
        this.agent = null
        this.status = 'offline'
        this.currentCall = null
        this.sessionStartTime = null
        this.pauseReason = null
        
        return { success: true }
      } catch (err: any) {
        return { success: false, error: err.message }
      }
    },

    // Cambiar estado del agente
    async changeStatus(newStatus: AgentStatus, reason?: string) {
      const { changeAgentStatus } = useAgents()
      
      if (!this.agent) return { success: false, error: 'No agent logged in' }

      // No permitir cambios durante llamada
      if (this.status === 'oncall' && newStatus !== 'wrapup') {
        return { success: false, error: 'Cannot change status during call' }
      }

      try {
        const { error } = await changeAgentStatus(this.agent.id, newStatus)
        if (error) throw error

        this.status = newStatus
        
        if (newStatus === 'break') {
          this.pauseReason = reason || 'Pausa'
        } else {
          this.pauseReason = null
        }
        
        return { success: true }
      } catch (err: any) {
        return { success: false, error: err.message }
      }
    },

    // Iniciar pausa
    async startBreak(reason: string) {
      return await this.changeStatus('break', reason)
    },

    // Terminar pausa
    async endBreak() {
      return await this.changeStatus('available')
    },

    // Iniciar llamada
    startCall(callData: Omit<CurrentCall, 'startTime'>) {
      this.currentCall = {
        ...callData,
        startTime: new Date()
      }
      this.status = 'oncall'
    },

    // Finalizar llamada
    endCall() {
      this.currentCall = null
      this.status = 'wrapup'
      
      // Auto-volver a disponible después de 10 segundos
      setTimeout(() => {
        if (this.status === 'wrapup') {
          this.changeStatus('available')
        }
      }, 10000)
    },

    // Actualizar estadísticas
    updateStats(stats: Partial<AgentState['stats']>) {
      this.stats = { ...this.stats, ...stats }
    },

    // WebSocket
    connectWebSocket() {
      if (!this.agent || this.webSocket) return

      const config = useRuntimeConfig()
      const wsUrl = `${config.public.wsBase}/agent/${this.agent.id}/`
      
      this.webSocket = new WebSocket(wsUrl)
      
      this.webSocket.onopen = () => {
        console.log('Agent WebSocket connected')
      }
      
      this.webSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleWebSocketMessage(data)
        } catch (err) {
          console.error('WebSocket message error:', err)
        }
      }
      
      this.webSocket.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
      
      this.webSocket.onclose = () => {
        console.log('Agent WebSocket disconnected')
        this.webSocket = null
      }
    },

    disconnectWebSocket() {
      if (this.webSocket) {
        this.webSocket.close()
        this.webSocket = null
      }
    },

    handleWebSocketMessage(data: any) {
      switch (data.type) {
        case 'call_incoming':
          // La llamada se maneja desde el componente WebRTC
          break
          
        case 'call_ended':
          this.endCall()
          break
          
        case 'status_changed':
          this.status = data.status
          break
          
        case 'stats_update':
          this.updateStats(data.stats)
          break
          
        default:
          console.log('Unknown WebSocket message type:', data.type)
      }
    }
  }
})
