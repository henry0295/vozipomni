/**
 * Texto legible a partir de un error de la API (DRF / $fetch / useFetch).
 * Muestra el motivo real que devuelve el backend, por ejemplo
 * "contact_list: Las campañas salientes requieren una lista de contactos",
 * en lugar de un mensaje genérico.
 */
export function apiErrorMessage(err: any, fallback = 'Ocurrió un error'): string {
  const d = err?.data ?? err?.value?.data ?? err?.response?._data
  if (!d) return err?.message && !String(err.message).startsWith('[') ? `${fallback}: ${err.message}` : fallback
  if (typeof d === 'string') return d.length > 300 ? fallback : d
  if (d.error) return String(d.error)
  if (d.detail) return String(d.detail)
  if (Array.isArray(d)) return String(d[0] ?? fallback)
  const parts = Object.entries(d).slice(0, 3).map(([field, msg]) => {
    const text = Array.isArray(msg) ? msg[0] : (typeof msg === 'object' ? JSON.stringify(msg) : msg)
    return field === 'non_field_errors' ? String(text) : `${field}: ${text}`
  })
  return parts.length ? `${fallback} — ${parts.join(' · ')}` : fallback
}
