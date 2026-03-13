/**
 * API Plugin with error handling and interceptors
 */
export default defineNuxtPlugin((nuxtApp) => {
  const config = useRuntimeConfig()
  const toast = useToast()
  const router = useRouter()
  
  // Create custom $fetch instance
  const api = $fetch.create({
    baseURL: config.public.apiBase,
    
    // Request interceptor
    onRequest({ options }) {
      // Add auth token from localStorage (managed by auth store)
      if (process.client) {
        const token = localStorage.getItem('auth_token')
        if (token) {
          options.headers = {
            ...options.headers,
            Authorization: `Bearer ${token}`
          }
        }
      }
      
      // Add request ID for tracking
      const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      options.headers = {
        ...options.headers,
        'X-Request-ID': requestId
      }
      
      // Log request in development
      if (process.dev) {
        console.log(`[API Request] ${options.method || 'GET'} ${options.baseURL}${typeof options === 'string' ? options : ''}`, {
          requestId,
          body: options.body
        })
      }
    },
    
    // Response interceptor
    onResponse({ response }) {
      // Log response in development
      if (process.dev) {
        console.log(`[API Response] ${response.status}`, response._data)
      }
    },
    
    // Error interceptor
    onResponseError({ request, response, options }) {
      const status = response.status
      const data = response._data
      
      // Log error
      console.error(`[API Error] ${status}`, {
        url: request,
        data,
        requestId: options.headers?.['X-Request-ID']
      })
      
      // Handle specific error codes
      switch (status) {
        case 400:
          // Bad Request - validation errors
          if (data?.errors) {
            // Show validation errors
            Object.entries(data.errors).forEach(([field, messages]) => {
              const errorMessages = Array.isArray(messages) ? messages : [messages]
              errorMessages.forEach((message: string) => {
                toast.add({
                  title: `Error en ${field}`,
                  description: message,
                  color: 'red',
                  timeout: 5000
                })
              })
            })
          } else {
            toast.add({
              title: 'Error de validación',
              description: data?.message || data?.detail || 'Datos inválidos',
              color: 'red',
              timeout: 5000
            })
          }
          break
        
        case 401:
          // Unauthorized - token expired or invalid
          toast.add({
            title: 'Sesión expirada',
            description: 'Por favor inicia sesión nuevamente',
            color: 'orange',
            timeout: 5000
          })
          
          // Clear tokens
          const accessToken = useCookie('access_token')
          const refreshToken = useCookie('refresh_token')
          accessToken.value = null
          refreshToken.value = null
          
          // Redirect to login
          router.push('/login')
          break
        
        case 403:
          // Forbidden - insufficient permissions
          toast.add({
            title: 'Acceso denegado',
            description: 'No tienes permisos para realizar esta acción',
            color: 'red',
            timeout: 5000
          })
          break
        
        case 404:
          // Not Found
          toast.add({
            title: 'No encontrado',
            description: data?.message || data?.detail || 'El recurso solicitado no existe',
            color: 'orange',
            timeout: 5000
          })
          break
        
        case 409:
          // Conflict - duplicate or constraint violation
          toast.add({
            title: 'Conflicto',
            description: data?.message || data?.detail || 'El recurso ya existe',
            color: 'orange',
            timeout: 5000
          })
          break
        
        case 422:
          // Unprocessable Entity - semantic errors
          toast.add({
            title: 'Error de procesamiento',
            description: data?.message || data?.detail || 'No se pudo procesar la solicitud',
            color: 'red',
            timeout: 5000
          })
          break
        
        case 429:
          // Too Many Requests - rate limiting
          toast.add({
            title: 'Demasiadas solicitudes',
            description: 'Por favor espera un momento antes de intentar nuevamente',
            color: 'orange',
            timeout: 5000
          })
          break
        
        case 500:
        case 502:
        case 503:
        case 504:
          // Server errors
          toast.add({
            title: 'Error del servidor',
            description: 'Ocurrió un error en el servidor. Por favor intenta más tarde.',
            color: 'red',
            timeout: 5000
          })
          
          // Report to error tracking service (e.g., Sentry)
          if (process.client && window.Sentry) {
            window.Sentry.captureException(new Error(`API Error ${status}`), {
              extra: {
                url: request,
                status,
                data
              }
            })
          }
          break
        
        default:
          // Generic error
          toast.add({
            title: 'Error',
            description: data?.message || data?.detail || 'Ocurrió un error inesperado',
            color: 'red',
            timeout: 5000
          })
      }
    },
    
    // Network error handler
    onRequestError({ error }) {
      console.error('[API Network Error]', error)
      
      toast.add({
        title: 'Error de conexión',
        description: 'No se pudo conectar con el servidor. Verifica tu conexión a internet.',
        color: 'red',
        timeout: 5000
      })
    }
  })
  
  // Provide to app
  return {
    provide: {
      api
    }
  }
})
