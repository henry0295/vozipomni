export const useWebSocket = () => {
  const config = useRuntimeConfig()
  const authStore = useAuthStore()
  
  let socket: WebSocket | null = null
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000

  const connect = (endpoint: string) => {
    const token = authStore.token
    if (!token) {
      console.error('No auth token available for WebSocket connection')
      return
    }

    const wsUrl = `${config.public.wsBase}${endpoint}?token=${token}`
    
    try {
      socket = new WebSocket(wsUrl)

      socket.onopen = () => {
        console.log('WebSocket connected')
        isConnected.value = true
        reconnectAttempts.value = 0
      }

      socket.onclose = () => {
        console.log('WebSocket disconnected')
        isConnected.value = false
        
        // Intentar reconectar
        if (reconnectAttempts.value < maxReconnectAttempts) {
          setTimeout(() => {
            reconnectAttempts.value++
            connect(endpoint)
          }, reconnectDelay)
        }
      }

      socket.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }

  const disconnect = () => {
    if (socket) {
      socket.close()
      socket = null
      isConnected.value = false
    }
  }

  const send = (data: any) => {
    if (socket && isConnected.value) {
      socket.send(JSON.stringify(data))
    } else {
      console.error('WebSocket is not connected')
    }
  }

  const onMessage = (callback: (data: any) => void) => {
    if (socket) {
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          callback(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
    }
  }

  // Limpiar al desmontar el componente
  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected: readonly(isConnected),
    connect,
    disconnect,
    send,
    onMessage
  }
}
