import { ref, computed } from 'vue'
import JsSIP from 'jssip'

export interface WebRTCConfig {
  sipServer: string
  sipPort: number
  sipUser: string
  sipPassword: string
  sipExtension: string
  displayName?: string
}

export interface CallSession {
  session: any
  remoteIdentity: string
  direction: 'incoming' | 'outgoing'
  isEstablished: boolean
  isMuted: boolean
  isOnHold: boolean
}

export const useWebRTC = () => {
  const ua = ref<any>(null)
  const currentSession = ref<CallSession | null>(null)
  const isRegistered = ref(false)
  const isConnecting = ref(false)
  const registrationStatus = ref('disconnected')
  const lastError = ref<string | null>(null)
  
  const callDuration = ref(0)
  let callTimer: any = null
  
  const agentStore = useAgentStore()

  // Computed
  const hasActiveCall = computed(() => currentSession.value !== null)
  const canMakeCall = computed(() => isRegistered.value && !hasActiveCall.value)

  // Configurar y registrar UA
  const register = (config: WebRTCConfig) => {
    if (ua.value) {
      console.warn('UA already exists, unregistering first')
      unregister()
    }

    try {
      // Configuración del socket WebSocket
      const socket = new JsSIP.WebSocketInterface(`wss://${config.sipServer}:${config.sipPort}/ws`)
      
      const configuration = {
        sockets: [socket],
        uri: `sip:${config.sipExtension}@${config.sipServer}`,
        password: config.sipPassword,
        display_name: config.displayName || config.sipUser,
        register: true,
        session_timers: false,
        use_preloaded_route: false
      }

      ua.value = new JsSIP.UA(configuration)

      // Event listeners
      setupUAEventListeners()

      ua.value.start()
      isConnecting.value = true
      registrationStatus.value = 'connecting'

      return { success: true }
    } catch (err: any) {
      lastError.value = err.message
      return { success: false, error: err.message }
    }
  }

  // Configurar listeners del UA
  const setupUAEventListeners = () => {
    if (!ua.value) return

    ua.value.on('connecting', () => {
      console.log('WebRTC: Connecting...')
      registrationStatus.value = 'connecting'
    })

    ua.value.on('connected', () => {
      console.log('WebRTC: Connected')
      registrationStatus.value = 'connected'
    })

    ua.value.on('disconnected', () => {
      console.log('WebRTC: Disconnected')
      isRegistered.value = false
      registrationStatus.value = 'disconnected'
    })

    ua.value.on('registered', () => {
      console.log('WebRTC: Registered')
      isRegistered.value = true
      isConnecting.value = false
      registrationStatus.value = 'registered'
      lastError.value = null
    })

    ua.value.on('unregistered', () => {
      console.log('WebRTC: Unregistered')
      isRegistered.value = false
      registrationStatus.value = 'unregistered'
    })

    ua.value.on('registrationFailed', (data: any) => {
      console.error('WebRTC: Registration failed', data)
      isRegistered.value = false
      isConnecting.value = false
      lastError.value = data.cause || 'Registration failed'
      registrationStatus.value = 'failed'
    })

    ua.value.on('newRTCSession', (data: any) => {
      console.log('WebRTC: New RTC Session', data)
      
      const session = data.session
      
      // Si ya hay una llamada activa, rechazar
      if (currentSession.value) {
        session.terminate()
        return
      }

      handleNewSession(session, data.originator === 'local' ? 'outgoing' : 'incoming')
    })
  }

  // Manejar nueva sesión
  const handleNewSession = (session: any, direction: 'incoming' | 'outgoing') => {
    const remoteIdentity = session.remote_identity.uri.user || 'Unknown'

    currentSession.value = {
      session,
      remoteIdentity,
      direction,
      isEstablished: false,
      isMuted: false,
      isOnHold: false
    }

    // Event listeners de la sesión
    session.on('progress', () => {
      console.log('WebRTC: Call progress')
    })

    session.on('accepted', () => {
      console.log('WebRTC: Call accepted')
    })

    session.on('confirmed', () => {
      console.log('WebRTC: Call confirmed')
      if (currentSession.value) {
        currentSession.value.isEstablished = true
      }
      
      // Iniciar timer
      startCallTimer()
      
      // Actualizar estado del agente
      agentStore.startCall({
        callId: session.id,
        direction,
        remoteNumber: remoteIdentity
      })
    })

    session.on('ended', () => {
      console.log('WebRTC: Call ended')
      handleCallEnded()
    })

    session.on('failed', (data: any) => {
      console.error('WebRTC: Call failed', data)
      handleCallEnded()
    })

    session.on('peerconnection', (data: any) => {
      console.log('WebRTC: Peer connection')
      
      // Agregar stream de audio remoto
      const remoteStream = new MediaStream()
      const receivers = data.peerconnection.getReceivers()
      
      receivers.forEach((receiver: any) => {
        if (receiver.track) {
          remoteStream.addTrack(receiver.track)
        }
      })

      // Reproducir audio remoto
      const remoteAudio = new Audio()
      remoteAudio.srcObject = remoteStream
      remoteAudio.play().catch((err: any) => {
        console.error('Error playing remote audio:', err)
      })
    })
  }

  // Hacer llamada
  const call = (number: string) => {
    if (!ua.value || !isRegistered.value) {
      return { success: false, error: 'Not registered' }
    }

    if (currentSession.value) {
      return { success: false, error: 'Call already in progress' }
    }

    try {
      const eventHandlers = {
        progress: () => console.log('Call is in progress'),
        failed: (data: any) => console.error('Call failed:', data),
        ended: () => console.log('Call ended'),
        confirmed: () => console.log('Call confirmed')
      }

      const options = {
        eventHandlers,
        mediaConstraints: {
          audio: true,
          video: false
        },
        pcConfig: {
          iceServers: [
            { urls: ['stun:stun.l.google.com:19302'] }
          ]
        }
      }

      ua.value.call(`sip:${number}@${ua.value.configuration.uri.host}`, options)
      
      return { success: true }
    } catch (err: any) {
      lastError.value = err.message
      return { success: false, error: err.message }
    }
  }

  // Contestar llamada
  const answer = () => {
    if (!currentSession.value) {
      return { success: false, error: 'No incoming call' }
    }

    try {
      const options = {
        mediaConstraints: {
          audio: true,
          video: false
        },
        pcConfig: {
          iceServers: [
            { urls: ['stun:stun.l.google.com:19302'] }
          ]
        }
      }

      currentSession.value.session.answer(options)
      return { success: true }
    } catch (err: any) {
      lastError.value = err.message
      return { success: false, error: err.message }
    }
  }

  // Colgar llamada
  const hangup = () => {
    if (!currentSession.value) {
      return { success: false, error: 'No active call' }
    }

    try {
      currentSession.value.session.terminate()
      return { success: true }
    } catch (err: any) {
      lastError.value = err.message
      return { success: false, error: err.message }
    }
  }

  // Rechazar llamada
  const reject = () => {
    if (!currentSession.value || currentSession.value.direction !== 'incoming') {
      return { success: false, error: 'No incoming call to reject' }
    }

    try {
      currentSession.value.session.terminate()
      return { success: true }
    } catch (err: any) {
      lastError.value = err.message
      return { success: false, error: err.message }
    }
  }

  // Mutear/Desmutear
  const toggleMute = () => {
    if (!currentSession.value || !currentSession.value.isEstablished) {
      return { success: false, error: 'No established call' }
    }

    try {
      if (currentSession.value.isMuted) {
        currentSession.value.session.unmute()
        currentSession.value.isMuted = false
      } else {
        currentSession.value.session.mute()
        currentSession.value.isMuted = true
      }
      return { success: true, isMuted: currentSession.value.isMuted }
    } catch (err: any) {
      lastError.value = err.message
      return { success: false, error: err.message }
    }
  }

  // Hold/Unhold
  const toggleHold = () => {
    if (!currentSession.value || !currentSession.value.isEstablished) {
      return { success: false, error: 'No established call' }
    }

    try {
      if (currentSession.value.isOnHold) {
        currentSession.value.session.unhold()
        currentSession.value.isOnHold = false
      } else {
        currentSession.value.session.hold()
        currentSession.value.isOnHold = true
      }
      return { success: true, isOnHold: currentSession.value.isOnHold }
    } catch (err: any) {
      lastError.value = err.message
      return { success: false, error: err.message }
    }
  }

  // Transferir llamada
  const transfer = (targetNumber: string) => {
    if (!currentSession.value || !currentSession.value.isEstablished) {
      return { success: false, error: 'No established call' }
    }

    try {
      currentSession.value.session.refer(`sip:${targetNumber}@${ua.value.configuration.uri.host}`)
      return { success: true }
    } catch (err: any) {
      lastError.value = err.message
      return { success: false, error: err.message }
    }
  }

  // Enviar DTMF
  const sendDTMF = (digit: string) => {
    if (!currentSession.value || !currentSession.value.isEstablished) {
      return { success: false, error: 'No established call' }
    }

    try {
      currentSession.value.session.sendDTMF(digit)
      return { success: true }
    } catch (err: any) {
      lastError.value = err.message
      return { success: false, error: err.message }
    }
  }

  // Desregistrar
  const unregister = () => {
    if (ua.value) {
      ua.value.stop()
      ua.value = null
    }
    isRegistered.value = false
    isConnecting.value = false
    registrationStatus.value = 'disconnected'
    currentSession.value = null
    stopCallTimer()
  }

  // Timer de llamada
  const startCallTimer = () => {
    callDuration.value = 0
    callTimer = setInterval(() => {
      callDuration.value++
    }, 1000)
  }

  const stopCallTimer = () => {
    if (callTimer) {
      clearInterval(callTimer)
      callTimer = null
    }
    callDuration.value = 0
  }

  // Manejar fin de llamada
  const handleCallEnded = () => {
    stopCallTimer()
    currentSession.value = null
    
    // Actualizar estado del agente
    agentStore.endCall()
  }

  // Formato de duración
  const formatDuration = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    
    if (hrs > 0) {
      return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return {
    // State
    ua,
    currentSession,
    isRegistered,
    isConnecting,
    registrationStatus,
    lastError,
    callDuration,
    hasActiveCall,
    canMakeCall,

    // Methods
    register,
    unregister,
    call,
    answer,
    hangup,
    reject,
    toggleMute,
    toggleHold,
    transfer,
    sendDTMF,
    formatDuration
  }
}
