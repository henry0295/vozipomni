/**
 * Composable for handling API errors
 */
export const useApiError = () => {
  const toast = useToast()
  
  /**
   * Handle API error and show appropriate message
   */
  const handleError = (error: any, customMessage?: string) => {
    console.error('[API Error]', error)
    
    // Extract error message
    let message = customMessage || 'Ocurrió un error inesperado'
    
    if (error?.data) {
      message = error.data.message || error.data.detail || message
    } else if (error?.message) {
      message = error.message
    }
    
    // Show toast
    toast.add({
      title: 'Error',
      description: message,
      color: 'red',
      timeout: 5000
    })
    
    return message
  }
  
  /**
   * Handle validation errors
   */
  const handleValidationErrors = (errors: Record<string, string[]>) => {
    Object.entries(errors).forEach(([field, messages]) => {
      messages.forEach((message) => {
        toast.add({
          title: `Error en ${field}`,
          description: message,
          color: 'red',
          timeout: 5000
        })
      })
    })
  }
  
  /**
   * Wrap async function with error handling
   */
  const withErrorHandling = async <T>(
    fn: () => Promise<T>,
    errorMessage?: string
  ): Promise<T | null> => {
    try {
      return await fn()
    } catch (error) {
      handleError(error, errorMessage)
      return null
    }
  }
  
  return {
    handleError,
    handleValidationErrors,
    withErrorHandling
  }
}
