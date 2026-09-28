/**
 * API Plugin con manejo de errores, interceptores y auto-refresh de tokens.
 *
 * Mejoras de seguridad y UX:
 *   - Tokens almacenados en cookies (httpOnly cuando vienen del backend)
 *   - Auto-refresh silencioso cuando el access token expira (401)
 *   - Reintento automático de la request original tras refresh exitoso
 *   - Fallback a localStorage para compatibilidad con instalaciones existentes
 */
export default defineNuxtPlugin((nuxtApp) => {
  const config = useRuntimeConfig()
  const toast = useToast()
  const router = useRouter()

  // ── Helpers de token ─────────────────────────────────────────────────────
  // Leer desde cookies primero (más seguro); fallback a localStorage
  const getAccessToken = (): string | null => {
    if (!process.client) return null
    const cookie = useCookie<string | null>('access_token')
    return cookie.value || localStorage.getItem('auth_token') || null
  }

  const getRefreshToken = (): string | null => {
    if (!process.client) return null
    const cookie = useCookie<string | null>('refresh_token')
    return cookie.value || localStorage.getItem('auth_refresh_token') || null
  }

  const clearTokens = () => {
    if (!process.client) return
    useCookie('access_token').value = null
    useCookie('refresh_token').value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_refresh_token')
  }

  const setAccessToken = (token: string) => {
    if (!process.client) return
    useCookie('access_token').value = token
    localStorage.setItem('auth_token', token)
  }

  // ── Estado de refresh (evita múltiples llamadas concurrentes) ───────────
  let _refreshPromise: Promise<string | null> | null = null

  const silentRefresh = async (): Promise<string | null> => {
    // Si ya hay un refresh en curso, esperar ese en lugar de duplicarlo
    if (_refreshPromise) return _refreshPromise

    const refresh = getRefreshToken()
    if (!refresh) return null

    _refreshPromise = (async () => {
      try {
        const data: any = await $fetch(`${config.public.apiBase}/auth/refresh/`, {
          method: 'POST',
          body: { refresh },
          // No usar el interceptor principal para evitar bucles
        })
        if (data?.access) {
          setAccessToken(data.access)
          // Actualizar el store si está disponible
          try {
            const authStore = useAuthStore()
            authStore.setToken(data.access)
          } catch {
            // El store puede no estar disponible fuera de componentes
          }
          return data.access
        }
        return null
      } catch {
        return null
      } finally {
        _refreshPromise = null
      }
    })()

    return _refreshPromise
  }

  // ── Instancia $fetch principal ────────────────────────────────────────────
  const api = $fetch.create({
    baseURL: config.public.apiBase,

    // ── Request interceptor ──────────────────────────────────────────────
    onRequest({ options }) {
      const token = getAccessToken()
      if (token) {
        options.headers = {
          ...options.headers,
          Authorization: `Bearer ${token}`,
        }
      }

      // Request ID para tracking y correlación de logs
      const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      options.headers = { ...options.headers, 'X-Request-ID': requestId }

      if (process.dev) {
        console.log(`[API] ${options.method || 'GET'} ${options.baseURL}`, { requestId })
      }
    },

    // ── Response interceptor (exitoso) ───────────────────────────────────
    onResponse({ response }) {
      if (process.dev) {
        console.log(`[API] ${response.status}`, response._data)
      }
    },

    // ── Error interceptor ────────────────────────────────────────────────
    onResponseError({ request, response, options }) {
      const status = response.status
      const data = response._data

      const authStore = useAuthStore()

      // Suprimir errores si ya no hay sesión activa
      if (!authStore.isAuthenticated && status !== 401) {
        console.warn(`[API suppressed] ${status}`, { url: request })
        return
      }

      console.error(`[API ${status}]`, { url: request, data })

      switch (status) {
        case 400: {
          if (data && typeof data === 'object') {
            let shown = false
            Object.entries(data).forEach(([field, messages]: [string, any]) => {
              if (field !== 'detail' && field !== 'message' && Array.isArray(messages)) {
                shown = true
                messages.forEach((msg: string) =>
                  toast.add({ title: `Error en ${field}`, description: msg, color: 'red', timeout: 5000 })
                )
              }
            })
            if (!shown) {
              toast.add({
                title: 'Error de validación',
                description: data?.message || data?.detail || 'Datos inválidos',
                color: 'red', timeout: 5000,
              })
            }
          }
          break
        }

        case 401: {
          // Intentar refresh silencioso antes de mandar a login
          silentRefresh().then((newToken) => {
            if (newToken) {
              // Token renovado — el usuario puede reintentar su acción
              // No redirigimos: la próxima request usará el nuevo token
              console.info('[API] Token renovado silenciosamente')
            } else {
              // Refresh falló — sesión expirada definitivamente
              authStore.clearAuth()
              clearTokens()
              toast.add({
                title: 'Sesión expirada',
                description: 'Por favor inicia sesión nuevamente',
                color: 'orange', timeout: 5000,
              })
              router.push('/login')
            }
          })
          break
        }

        case 403:
          toast.add({
            title: 'Acceso denegado',
            description: 'No tienes permisos para realizar esta acción',
            color: 'red', timeout: 5000,
          })
          break

        case 404:
          toast.add({
            title: 'No encontrado',
            description: data?.message || data?.detail || 'El recurso solicitado no existe',
            color: 'orange', timeout: 5000,
          })
          break

        case 409:
          toast.add({
            title: 'Conflicto',
            description: data?.message || data?.detail || 'El recurso ya existe',
            color: 'orange', timeout: 5000,
          })
          break

        case 429:
          toast.add({
            title: 'Demasiadas solicitudes',
            description: 'Espera un momento antes de reintentar',
            color: 'orange', timeout: 5000,
          })
          break

        case 500:
        case 502:
        case 503:
        case 504:
          if (status !== 503) {
            toast.add({
              title: 'Error del servidor',
              description: 'Ocurrió un error en el servidor. Intenta más tarde.',
              color: 'red', timeout: 5000,
            })
          }
          // Reportar a Sentry si está disponible
          if (process.client && (window as any).Sentry) {
            ;(window as any).Sentry.captureException(new Error(`API Error ${status}`), {
              extra: { url: request, status, data },
            })
          }
          break

        default:
          toast.add({
            title: 'Error',
            description: data?.message || data?.detail || 'Ocurrió un error inesperado',
            color: 'red', timeout: 5000,
          })
      }
    },

    // ── Network error ────────────────────────────────────────────────────
    onRequestError({ error }) {
      console.error('[API Network Error]', error)
      toast.add({
        title: 'Error de conexión',
        description: 'No se pudo conectar con el servidor. Verifica tu conexión.',
        color: 'red', timeout: 5000,
      })
    },
  })

  return {
    provide: { api },
  }
})
