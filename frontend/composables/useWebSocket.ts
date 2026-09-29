/**
 * WebSocket autenticado y con reconexión.
 *
 * - Añade ?token=<JWT> (requerido por JwtAuthMiddleware del backend)
 * - Reconexión con backoff exponencial (máx 30s), relee el token en cada intento
 *   para usar el token renovado por el auto-refresh
 * - Los handlers registrados con onMessage sobreviven a las reconexiones
 *
 * Uso:
 *   const ws = useWebSocket()
 *   ws.onMessage((data) => { ... })
 *   ws.connect('/ws/dashboard/')
 */
export const buildWsUrl = (endpoint: string): string => {
  const config = useRuntimeConfig()
  let base = String(config.public.wsBase || '').replace(/\/$/, '')

  // wsBase relativo (ej: '/ws') → construir desde el host actual
  if (!base || base.startsWith('/')) {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
    base = `${proto}//${location.host}`
  } else if (base.endsWith('/ws') && endpoint.startsWith('/ws/')) {
    // Evitar /ws/ws/ cuando wsBase ya incluye /ws
    base = base.slice(0, -3)
  }

  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const token = localStorage.getItem('auth_token') || ''
  const sep = path.includes('?') ? '&' : '?'
  return `${base}${path}${token ? `${sep}token=${encodeURIComponent(token)}` : ''}`
}

export const useWebSocket = (options: { autoCleanup?: boolean } = {}) => {
  const { autoCleanup = true } = options

  let socket: WebSocket | null = null
  let endpoint = ''
  let manualClose = false
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  const handlers = new Set<(data: any) => void>()

  const isConnected = ref(false)
  const reconnectAttempts = ref(0)

  const scheduleReconnect = () => {
    if (manualClose || !endpoint) return
    // 4401/4403 = sin permiso; no insistir si no hay token
    if (!localStorage.getItem('auth_token')) return
    const delay = Math.min(30000, 1000 * 2 ** reconnectAttempts.value)
    reconnectAttempts.value++
    reconnectTimer = setTimeout(() => open(), delay)
  }

  const open = () => {
    if (!process.client || !endpoint) return
    try {
      socket = new WebSocket(buildWsUrl(endpoint))
    } catch (e) {
      console.error('[WS] No se pudo crear el socket', e)
      scheduleReconnect()
      return
    }

    socket.onopen = () => {
      isConnected.value = true
      reconnectAttempts.value = 0
    }
    socket.onmessage = (event) => {
      let data: any
      try { data = JSON.parse(event.data) } catch { return }
      handlers.forEach((h) => {
        try { h(data) } catch (e) { console.error('[WS] handler error', e) }
      })
    }
    socket.onerror = () => { /* onclose se encarga */ }
    socket.onclose = (ev) => {
      isConnected.value = false
      socket = null
      if (ev.code === 4403 || ev.code === 4404) return // sin permiso / ruta inexistente: no reintentar
      scheduleReconnect()
    }
  }

  const connect = (ep: string) => {
    disconnect()
    endpoint = ep
    manualClose = false
    reconnectAttempts.value = 0
    open()
  }

  const disconnect = () => {
    manualClose = true
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = null
    if (socket) {
      socket.close()
      socket = null
    }
    isConnected.value = false
  }

  const send = (data: any) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(data))
      return true
    }
    return false
  }

  const onMessage = (callback: (data: any) => void) => {
    handlers.add(callback)
    return () => handlers.delete(callback)
  }

  if (autoCleanup && getCurrentInstance()) {
    onUnmounted(disconnect)
  }

  return {
    isConnected: readonly(isConnected),
    connect,
    disconnect,
    send,
    onMessage,
  }
}
