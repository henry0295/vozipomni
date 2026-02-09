/**
 * Formatea un número de teléfono
 */
export const formatPhoneNumber = (phone: string): string => {
  // Eliminar caracteres no numéricos
  const cleaned = phone.replace(/\D/g, '')
  
  // Formatear según longitud
  if (cleaned.length === 10) {
    return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`
  }
  
  return phone
}

/**
 * Formatea una duración en segundos a formato MM:SS
 */
export const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * Formatea una fecha relativa (hace X tiempo)
 */
export const formatRelativeTime = (date: Date | string): string => {
  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) return `hace ${days} día${days > 1 ? 's' : ''}`
  if (hours > 0) return `hace ${hours} hora${hours > 1 ? 's' : ''}`
  if (minutes > 0) return `hace ${minutes} minuto${minutes > 1 ? 's' : ''}`
  return 'hace un momento'
}

/**
 * Formatea un número con separadores de miles
 */
export const formatNumber = (num: number): string => {
  return new Intl.NumberFormat('es-CO').format(num)
}

/**
 * Formatea moneda COP
 */
export const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    minimumFractionDigits: 0
  }).format(amount)
}

/**
 * Formatea porcentaje
 */
export const formatPercent = (value: number, decimals: number = 1): string => {
  return `${value.toFixed(decimals)}%`
}

/**
 * Formatea fecha
 */
export const formatDate = (date: Date | string, format: 'short' | 'long' | 'datetime' = 'short'): string => {
  const d = typeof date === 'string' ? new Date(date) : date
  
  if (format === 'short') {
    return new Intl.DateTimeFormat('es-CO', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }).format(d)
  }
  
  if (format === 'long') {
    return new Intl.DateTimeFormat('es-CO', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    }).format(d)
  }
  
  // datetime
  return new Intl.DateTimeFormat('es-CO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(d)
}
