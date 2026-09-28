/**
 * Envoltorio global de $fetch para llamadas a la API.
 *
 * Muchas páginas usan `$fetch('/api/...', { headers: authHeaders() })` directamente,
 * saltándose el plugin $api. Este plugin intercepta TODAS esas llamadas y:
 *   1. Inyecta siempre el access token vigente (evita tokens viejos capturados en closures)
 *   2. Si la API responde 401, renueva el token con el refresh token y REINTENTA una vez
 *   3. Si la renovación falla, limpia la sesión y redirige a /login
 *
 * Así no hay que tocar cada llamada existente para obtener auto-refresh.
 */
export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()
  const original = globalThis.$fetch
  const apiBase = String(config.public.apiBase || '/api').replace(/\/$/, '')

  const urlOf = (request: any): string =>
    typeof request === 'string' ? request : (request?.url ?? '')

  const isApiUrl = (url: string) =>
    url.startsWith('/api/') || (apiBase && url.startsWith(apiBase + '/'))

  // Endpoints de auth no deben reintentarse ni recibir token viejo
  const isAuthEndpoint = (url: string) =>
    /\/auth\/(login|refresh|password-reset)/.test(url)

  const withToken = (opts: any = {}) => {
    const token = localStorage.getItem('auth_token')
    const headers = new Headers(opts.headers || {})
    if (token) headers.set('Authorization', `Bearer ${token}`)
    return { ...opts, headers }
  }

  let refreshing: Promise<string | null> | null = null

  const refreshToken = (): Promise<string | null> => {
    if (refreshing) return refreshing
    const refresh = localStorage.getItem('auth_refresh_token')
    if (!refresh) return Promise.resolve(null)

    refreshing = (async () => {
      try {
        const data: any = await original(`${apiBase}/auth/refresh/`, {
          method: 'POST',
          body: { refresh },
        })
        if (!data?.access) return null
        localStorage.setItem('auth_token', data.access)
        if (data.refresh) localStorage.setItem('auth_refresh_token', data.refresh)
        try {
          const store = useAuthStore()
          store.setToken(data.access)
          if (data.refresh) store.refreshToken = data.refresh
        } catch { /* store no disponible */ }
        return data.access as string
      } catch {
        return null
      } finally {
        refreshing = null
      }
    })()
    return refreshing
  }

  const is401 = (err: any) =>
    err?.response?.status === 401 || err?.statusCode === 401 || err?.status === 401

  const wrapped = (async (request: any, opts: any = {}) => {
    const url = urlOf(request)
    if (!isApiUrl(url) || isAuthEndpoint(url)) {
      return original(request, opts)
    }
    try {
      return await original(request, withToken(opts))
    } catch (err: any) {
      if (!is401(err)) throw err
      const newToken = await refreshToken()
      if (newToken) {
        return await original(request, withToken(opts))
      }
      // Sesión expirada definitivamente
      try { useAuthStore().clearAuth() } catch { /* ignore */ }
      if (!location.pathname.startsWith('/login')) {
        navigateTo('/login')
      }
      throw err
    }
  }) as typeof $fetch

  // Conservar la API auxiliar de ofetch
  ;(wrapped as any).raw = original.raw
  ;(wrapped as any).native = original.native
  ;(wrapped as any).create = original.create

  globalThis.$fetch = wrapped
})
