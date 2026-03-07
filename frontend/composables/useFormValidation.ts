/**
 * Form validation composable with Zod
 */
import { z } from 'zod'

export const useFormValidation = <T extends z.ZodType>(schema: T) => {
  const errors = ref<Record<string, string>>({})
  const isValid = ref(true)
  
  /**
   * Validate form data against schema
   */
  const validate = (data: any): boolean => {
    try {
      schema.parse(data)
      errors.value = {}
      isValid.value = true
      return true
    } catch (error) {
      if (error instanceof z.ZodError) {
        errors.value = {}
        error.errors.forEach((err) => {
          const path = err.path.join('.')
          errors.value[path] = err.message
        })
        isValid.value = false
      }
      return false
    }
  }
  
  /**
   * Validate single field
   */
  const validateField = (fieldName: string, value: any): boolean => {
    try {
      // Get field schema
      const fieldSchema = (schema as any).shape[fieldName]
      if (!fieldSchema) return true
      
      fieldSchema.parse(value)
      delete errors.value[fieldName]
      return true
    } catch (error) {
      if (error instanceof z.ZodError) {
        errors.value[fieldName] = error.errors[0].message
      }
      return false
    }
  }
  
  /**
   * Clear all errors
   */
  const clearErrors = () => {
    errors.value = {}
    isValid.value = true
  }
  
  /**
   * Clear specific field error
   */
  const clearFieldError = (fieldName: string) => {
    delete errors.value[fieldName]
  }
  
  /**
   * Get error for specific field
   */
  const getFieldError = (fieldName: string): string | undefined => {
    return errors.value[fieldName]
  }
  
  /**
   * Check if field has error
   */
  const hasFieldError = (fieldName: string): boolean => {
    return !!errors.value[fieldName]
  }
  
  return {
    errors: readonly(errors),
    isValid: readonly(isValid),
    validate,
    validateField,
    clearErrors,
    clearFieldError,
    getFieldError,
    hasFieldError
  }
}


// ============= VALIDATION SCHEMAS =============

/**
 * Campaign validation schema
 */
export const campaignSchema = z.object({
  name: z.string().min(3, 'El nombre debe tener al menos 3 caracteres'),
  description: z.string().optional(),
  campaign_type: z.enum(['inbound', 'outbound', 'manual', 'preview']),
  dialer_type: z.enum(['predictive', 'progressive', 'preview', 'manual']).optional(),
  start_date: z.date(),
  end_date: z.date().optional(),
  schedule_start_time: z.string().optional(),
  schedule_end_time: z.string().optional(),
  max_retries: z.number().min(0).max(10, 'Máximo 10 reintentos'),
  call_timeout: z.number().min(10).max(300, 'Timeout debe estar entre 10 y 300 segundos'),
  max_calls_per_agent: z.number().min(1).max(5, 'Debe estar entre 1 y 5'),
  contact_list: z.number().optional(),
  queue: z.number().optional(),
}).refine(data => {
  if (data.end_date && data.start_date) {
    return data.end_date > data.start_date
  }
  return true
}, {
  message: 'La fecha de fin debe ser posterior a la fecha de inicio',
  path: ['end_date']
})

/**
 * Contact validation schema
 */
export const contactSchema = z.object({
  first_name: z.string().min(2, 'El nombre debe tener al menos 2 caracteres'),
  last_name: z.string().optional(),
  email: z.string().email('Email inválido').optional().or(z.literal('')),
  phone: z.string().regex(/^\+?[1-9]\d{6,14}$/, 'Formato de teléfono inválido'),
  phone2: z.string().regex(/^\+?[1-9]\d{6,14}$/, 'Formato de teléfono inválido').optional().or(z.literal('')),
  phone3: z.string().regex(/^\+?[1-9]\d{6,14}$/, 'Formato de teléfono inválido').optional().or(z.literal('')),
  company: z.string().optional(),
  position: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
  country: z.string().length(2, 'Código de país debe ser de 2 letras').optional(),
  priority: z.number().min(0).max(10, 'Prioridad debe estar entre 0 y 10').optional(),
  contact_list: z.number(),
})

/**
 * Agent validation schema
 */
export const agentSchema = z.object({
  agent_id: z.string().min(3, 'ID de agente debe tener al menos 3 caracteres'),
  sip_extension: z.string().regex(/^\d{3,6}$/, 'Extensión debe ser numérica de 3-6 dígitos'),
  username: z.string().min(3, 'Usuario debe tener al menos 3 caracteres').optional(),
  password: z.string().min(8, 'Contraseña debe tener al menos 8 caracteres').optional(),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  email: z.string().email('Email inválido').optional(),
  sip_password: z.string().min(8, 'Contraseña SIP debe tener al menos 8 caracteres').optional(),
  webrtc_enabled: z.boolean().optional(),
  max_concurrent_calls: z.number().min(1).max(5).optional(),
  auto_answer: z.boolean().optional(),
  recording_enabled: z.boolean().optional(),
})

/**
 * SIP Trunk validation schema
 */
export const sipTrunkSchema = z.object({
  name: z.string().min(3, 'El nombre debe tener al menos 3 caracteres'),
  description: z.string().optional(),
  trunk_type: z.enum(['nat_provider', 'no_nat_provider', 'pbx_lan', 'corporate', 'custom']),
  host: z.string().min(1, 'Host es requerido'),
  port: z.number().min(1).max(65535, 'Puerto debe estar entre 1 y 65535'),
  protocol: z.enum(['udp', 'tcp', 'tls']),
  outbound_auth_username: z.string().optional(),
  outbound_auth_password: z.string().optional(),
  sends_registration: z.boolean().optional(),
  registration_server_uri: z.string().optional(),
  max_channels: z.number().min(1).max(1000).optional(),
  is_active: z.boolean().optional(),
}).refine(data => {
  if (data.sends_registration && !data.registration_server_uri) {
    return false
  }
  return true
}, {
  message: 'Server URI es requerido cuando el registro está habilitado',
  path: ['registration_server_uri']
})

/**
 * Queue validation schema
 */
export const queueSchema = z.object({
  name: z.string().min(3, 'El nombre debe tener al menos 3 caracteres'),
  extension: z.string().regex(/^\d{3,6}$/, 'Extensión debe ser numérica de 3-6 dígitos'),
  description: z.string().optional(),
  strategy: z.enum(['ringall', 'leastrecent', 'fewestcalls', 'random', 'rrmemory', 'linear']),
  timeout: z.number().min(5).max(300, 'Timeout debe estar entre 5 y 300 segundos'),
  max_wait_time: z.number().min(30).max(3600, 'Tiempo máximo debe estar entre 30 y 3600 segundos'),
  max_callers: z.number().min(0).max(1000).optional(),
  is_active: z.boolean().optional(),
})
