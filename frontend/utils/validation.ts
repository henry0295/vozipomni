/**
 * Valida un email
 */
export const isValidEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

/**
 * Valida un número de teléfono colombiano
 */
export const isValidPhone = (phone: string): boolean => {
  const phoneRegex = /^(\+57)?[3][0-9]{9}$/
  const cleaned = phone.replace(/\D/g, '')
  return phoneRegex.test(cleaned)
}

/**
 * Valida que un string no esté vacío
 */
export const isNotEmpty = (value: string): boolean => {
  return value.trim().length > 0
}

/**
 * Valida longitud mínima
 */
export const minLength = (value: string, min: number): boolean => {
  return value.length >= min
}

/**
 * Valida longitud máxima
 */
export const maxLength = (value: string, max: number): boolean => {
  return value.length <= max
}

/**
 * Valida formato de extensión (solo números)
 */
export const isValidExtension = (extension: string): boolean => {
  return /^\d{3,5}$/.test(extension)
}

/**
 * Valida formato de IP
 */
export const isValidIP = (ip: string): boolean => {
  const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/
  if (!ipRegex.test(ip)) return false
  
  const parts = ip.split('.')
  return parts.every(part => {
    const num = parseInt(part, 10)
    return num >= 0 && num <= 255
  })
}

/**
 * Valida rango numérico
 */
export const isInRange = (value: number, min: number, max: number): boolean => {
  return value >= min && value <= max
}
