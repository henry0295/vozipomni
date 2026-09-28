/**
 * Cliente HTTP mínimo para páginas nuevas.
 * Usa el $fetch global (envuelto por plugins/fetch-auth.client.ts), así que
 * hereda token automático, refresh y reintento en 401.
 *
 * Uso:
 *   const http = useHttp()
 *   const users = await http.get('/users/')
 *   await http.post('/users/', { username: 'x' })
 */
export const useHttp = () => {
  const base = String(useRuntimeConfig().public.apiBase || '/api').replace(/\/$/, '')

  const request = <T = any>(url: string, opts: any = {}) =>
    $fetch<T>(`${base}${url.startsWith('/') ? url : '/' + url}`, opts)

  /** Extrae resultados de respuestas paginadas de DRF */
  const results = <T = any>(data: any): T[] =>
    Array.isArray(data) ? data : (data?.results ?? [])

  /** Mensaje legible desde un error de DRF */
  const errorMessage = (err: any, fallback = 'Ocurrió un error'): string => {
    const d = err?.data
    if (!d) return err?.message || fallback
    if (typeof d === 'string') return d
    if (d.error) return d.error
    if (d.detail) return d.detail
    const first = Object.entries(d)[0]
    if (first) {
      const [field, msg] = first as [string, any]
      return `${field}: ${Array.isArray(msg) ? msg[0] : msg}`
    }
    return fallback
  }

  /** Obtiene un archivo autenticado como Blob (+ nombre desde Content-Disposition) */
  const blob = async (url: string, query?: Record<string, any>) => {
    let filename = ''
    const data = await request<Blob>(url, {
      query,
      responseType: 'blob',
      onResponse({ response }: any) {
        const cd = response.headers.get('content-disposition') || ''
        const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i)
        if (m) filename = decodeURIComponent(m[1])
      },
    })
    return { data, filename }
  }

  /** Descarga un archivo autenticado disparando el diálogo del navegador */
  const download = async (url: string, query?: Record<string, any>, fallbackName = 'archivo') => {
    const { data, filename } = await blob(url, query)
    const href = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = href
    a.download = filename || fallbackName
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(href), 1000)
  }

  /** Mensaje de error cuando la respuesta fallida es un Blob (JSON dentro) */
  const blobErrorMessage = async (err: any, fallback = 'Ocurrió un error'): Promise<string> => {
    const d = err?.data
    if (d instanceof Blob) {
      try {
        const j = JSON.parse(await d.text())
        return j.error || j.detail || fallback
      } catch { return fallback }
    }
    return errorMessage(err, fallback)
  }

  return {
    request,
    blob,
    download,
    blobErrorMessage,
    get: <T = any>(url: string, query?: Record<string, any>) => request<T>(url, { query }),
    post: <T = any>(url: string, body?: any) => request<T>(url, { method: 'POST', body }),
    patch: <T = any>(url: string, body?: any) => request<T>(url, { method: 'PATCH', body }),
    put: <T = any>(url: string, body?: any) => request<T>(url, { method: 'PUT', body }),
    del: <T = any>(url: string) => request<T>(url, { method: 'DELETE' }),
    results,
    errorMessage,
  }
}
