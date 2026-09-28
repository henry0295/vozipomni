/**
 * Bandeja de conversaciones (WhatsApp / omnicanal) con tiempo real.
 *
 *   const inbox = useMessaging(() => ({ active: 'true', mine: 'true' }))
 *   inbox.onEvent((evt) => chatRef.value?.handleEvent(evt))
 *   await inbox.start()
 *
 * - Carga /messaging/conversations/ con los filtros que devuelva `query()`
 * - Escucha /ws/messaging/ y recarga la lista (debounce) ante cada evento
 * - Si el socket cae, hace polling cada 30 s como respaldo
 * - Notificación del navegador + sonido en mensajes entrantes (si hay permiso)
 */
export const useMessaging = (query: () => Record<string, any> = () => ({})) => {
  const http = useHttp()
  const ws = useWebSocket()

  const conversations = ref<any[]>([])
  const stats = ref<any>({ open: 0, waiting: 0, unassigned: 0, mine: 0, closed_today: 0, unread: 0 })
  const total = ref(0)
  const loading = ref(false)
  const handlers = new Set<(evt: any) => void>()

  let debounce: ReturnType<typeof setTimeout> | null = null
  let poll: ReturnType<typeof setInterval> | null = null

  async function load() {
    loading.value = true
    try {
      const params = Object.fromEntries(Object.entries(query()).filter(([, v]) => v !== '' && v != null))
      const [list, st] = await Promise.all([
        http.get('/messaging/conversations/', params),
        http.get('/messaging/conversations/stats/'),
      ])
      conversations.value = http.results(list)
      total.value = (list as any)?.count ?? conversations.value.length
      stats.value = st
    } catch (e) {
      console.warn('[Messaging] Error cargando conversaciones', e)
    } finally {
      loading.value = false
    }
  }

  function scheduleLoad(delay = 400) {
    if (debounce) clearTimeout(debounce)
    debounce = setTimeout(load, delay)
  }

  function notify(evt: any) {
    if (evt.event !== 'message.new' || evt.direction !== 'inbound') return
    if (document.visibilityState === 'visible' && document.hasFocus()) return
    try {
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Nuevo mensaje de WhatsApp', { body: evt.preview || '', tag: `conv-${evt.conversation_id}` })
      }
    } catch { /* ignore */ }
  }

  ws.onMessage((data) => {
    if (data?.type !== 'messaging') return
    handlers.forEach(h => { try { h(data) } catch (e) { console.error(e) } })
    notify(data)
    // Los cambios de estado de entrega no alteran el orden de la lista
    if (data.event !== 'message.status') scheduleLoad()
  })

  watch(ws.isConnected, (up) => {
    if (up) {
      if (poll) { clearInterval(poll); poll = null }
    } else if (!poll) {
      poll = setInterval(load, 30000)
    }
  })

  async function start() {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission().catch(() => {})
    }
    ws.connect('/ws/messaging/')
    poll = setInterval(load, 30000)
    await load()
  }

  function onEvent(cb: (evt: any) => void) {
    handlers.add(cb)
    return () => handlers.delete(cb)
  }

  if (getCurrentInstance()) {
    onUnmounted(() => {
      if (debounce) clearTimeout(debounce)
      if (poll) clearInterval(poll)
    })
  }

  return {
    conversations, stats, total, loading,
    isConnected: ws.isConnected,
    load, reload: () => scheduleLoad(0), start, onEvent,
  }
}
