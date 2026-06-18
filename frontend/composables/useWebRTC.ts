import { computed, markRaw } from 'vue'
import JsSIP from 'jssip'

// Construye la lista de ICE servers: STUN público + TURN propio si está configurado.
// STUN: permite al browser descubrir su IP pública.
// TURN: relay de último recurso cuando UDP directo está bloqueado (NAT simétrica, firewall corporativo).
function buildIceServers(): RTCIceServer[] {
  const config = useRuntimeConfig()
  const servers: RTCIceServer[] = [
    { urls: ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302'] }
  ]
  const turn = config.public.turnServer
  if (turn) {
    servers.push({
      urls: [
        `turn:${turn}:3478?transport=udp`,
        `turn:${turn}:3478?transport=tcp`,
        `turns:${turn}:5349`
      ],
      username: config.public.turnUser as string,
      credential: config.public.turnPassword as string
    })
  }
  return servers
}

export interface WebRTCConfig {
  sipServer: string
  sipPort: number
  sipUser: string
  sipPassword: string
  sipExtension: string
  displayName?: string
  wsUrl?: string
}

export interface CallSession {
  session: any
  remoteIdentity: string
  direction: 'incoming' | 'outgoing'
  isEstablished: boolean
  isMuted: boolean
  isOnHold: boolean
}

// ─── Singleton state via Nuxt useState ─────────────────────────────────────
// Usar useState garantiza que TODOS los componentes que llamen useWebRTC()
// compartan la misma instancia de UA y currentSession.
// Sin esto, AgentSoftphone y console.vue crean UAs independientes →
// el evento 'ended' solo llega a la instancia que originó la llamada,
// y el otro componente queda con currentSession != null (llamada "fantasma").
// ────────────────────────────────────────────────────────────────────────────

let _ua: any = null             // JsSIP UA — no puede ser useState (no serializable)
let _callTimer: any = null
let _remoteAudio: HTMLAudioElement | null = null

export const useWebRTC = () => {
  // useState comparte estado entre todos los componentes en el mismo proceso SSR/client
  const currentSession = useState<CallSession | null>('webrtc_session', () => null)
  const isRegistered = useState<boolean>('webrtc_registered', () => false)
  const isConnecting = useState<boolean>('webrtc_connecting', () => false)
  const registrationStatus = useState<string>('webrtc_status', () => 'disconnected')
  const lastError = useState<string | null>('webrtc_last_error', () => null)
  const lastCallError = useState<string | null>('webrtc_last_call_error', () => null)
  const callDuration = useState<number>('webrtc_call_duration', () => 0)

  const agentStore = useAgentStore()

  // Computed
  const hasActiveCall = computed(() => currentSession.value !== null)
  const canMakeCall = computed(() => isRegistered.value && !hasActiveCall.value)
  

  // UA accessor (singleton module-level variable)
  const ua = { get value() { return _ua } }


  // Configurar y registrar UA
  const register = (config: WebRTCConfig) => {
    if (_ua) {
      console.warn('UA already exists, unregistering first')
      unregister()
    }

    try {
      const wsEndpoint = config.wsUrl || `wss://${config.sipServer}:${config.sipPort}/ws`
      const socket = new JsSIP.WebSocketInterface(wsEndpoint)
      
      const configuration = {
        sockets: [socket],
        uri: `sip:${config.sipExtension}@${config.sipServer}`,
        password: config.sipPassword,
        display_name: config.displayName || config.sipUser,
        register: true,
        session_timers: false,
        use_preloaded_route: false
      }

      _ua = markRaw(new JsSIP.UA(configuration))

      setupUAEventListeners()

      _ua.start()
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
    if (!_ua) return

    _ua.on('connecting', () => {
      console.log('WebRTC: Connecting...')
      registrationStatus.value = 'connecting'
    })

    _ua.on('connected', () => {
      console.log('WebRTC: Connected')
      registrationStatus.value = 'connected'
    })

    _ua.on('disconnected', () => {
      console.log('WebRTC: Disconnected')
      isRegistered.value = false
      registrationStatus.value = 'disconnected'
    })

    _ua.on('registered', () => {
      console.log('WebRTC: Registered')
      isRegistered.value = true
      isConnecting.value = false
      registrationStatus.value = 'registered'
      lastError.value = null
    })

    _ua.on('unregistered', () => {
      console.log('WebRTC: Unregistered')
      isRegistered.value = false
      registrationStatus.value = 'unregistered'
    })

    _ua.on('registrationFailed', (data: any) => {
      console.error('WebRTC: Registration failed', data)
      isRegistered.value = false
      isConnecting.value = false
      lastError.value = data.cause || 'Registration failed'
      registrationStatus.value = 'failed'
    })

    _ua.on('newRTCSession', (data: any) => {
      console.log('WebRTC: New RTC Session', data)
      
      const session = data.session
      
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
      session: markRaw(session),  // markRaw evita que Vue proxie la sesión JsSIP
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
        // Reemplazar el objeto completo para garantizar que Vue detecte el cambio
        currentSession.value = { ...currentSession.value, isEstablished: true }
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
      const statusCode = data.message?.status_code
      const reasonPhrase = data.message?.reason_phrase || ''
      const cause = data.cause || 'Unknown'
      console.error(`WebRTC: Call failed — SIP ${statusCode} ${reasonPhrase} | cause: ${cause}`, data)
      lastCallError.value = statusCode
        ? `Llamada rechazada (${statusCode} ${reasonPhrase})`
        : `Llamada fallida: ${cause}`
      handleCallEnded()
    })

    session.on('peerconnection', (data: any) => {
      console.log('WebRTC: Peer connection')
      const pc = data.peerconnection

      if (_remoteAudio) {
        _remoteAudio.pause()
        _remoteAudio.srcObject = null
        _remoteAudio.remove()
        _remoteAudio = null
      }

      _remoteAudio = document.createElement('audio')
      _remoteAudio.autoplay = true
      _remoteAudio.setAttribute('playsinline', '')
      _remoteAudio.style.display = 'none'
      document.body.appendChild(_remoteAudio)

      pc.addEventListener('track', (event: RTCTrackEvent) => {
        if (event.track.kind !== 'audio') return
        console.log('WebRTC: Remote audio track received')
        const stream = event.streams[0] ?? new MediaStream([event.track])
        _remoteAudio!.srcObject = stream
        _remoteAudio!.play().catch((err: any) => {
          console.warn('WebRTC: Audio autoplay bloqueado:', err)
        })
      })
    })
  }

  // Hacer llamada
  const call = (number: string) => {
    if (!_ua || !isRegistered.value) {
      return { success: false, error: 'Not registered' }
    }

    if (currentSession.value) {
      return { success: false, error: 'Call already in progress' }
    }

    try {
      const options = {
        mediaConstraints: { audio: true, video: false },
        pcConfig: {
          iceServers: buildIceServers(),
          iceTransportPolicy: 'all' as RTCIceTransportPolicy
        }
      }

      _ua.call(`sip:${number}@${_ua.configuration.uri.host}`, options)
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
          iceServers: buildIceServers(),
          iceTransportPolicy: 'all' as RTCIceTransportPolicy
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
      const host = _ua?.configuration?.uri?.host || ''
      currentSession.value.session.refer(`sip:${targetNumber}@${host}`)
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
    if (_ua) {
      _ua.stop()
      _ua = null
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
    _callTimer = setInterval(() => {
      callDuration.value++
    }, 1000)
  }

  const stopCallTimer = () => {
    if (_callTimer) {
      clearInterval(_callTimer)
      _callTimer = null
    }
    callDuration.value = 0
  }

  // Manejar fin de llamada
  const handleCallEnded = () => {
    // Limpiar audio remoto y remover del DOM
    if (_remoteAudio) {
      _remoteAudio.pause()
      _remoteAudio.srcObject = null
      _remoteAudio.remove()
      _remoteAudio = null
    }
    
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
    lastCallError,
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
