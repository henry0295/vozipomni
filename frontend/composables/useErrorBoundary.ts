/**
 * Error boundary composable for catching and handling errors
 */
export const useErrorBoundary = () => {
  const error = ref<Error | null>(null)
  const hasError = computed(() => error.value !== null)
  
  /**
   * Catch and handle error
   */
  const catchError = (err: Error) => {
    error.value = err
    console.error('[Error Boundary]', err)
    
    // Report to error tracking service
    if (process.client && window.Sentry) {
      window.Sentry.captureException(err)
    }
  }
  
  /**
   * Clear error
   */
  const clearError = () => {
    error.value = null
  }
  
  /**
   * Wrap function with error boundary
   */
  const withBoundary = async <T>(fn: () => Promise<T>): Promise<T | null> => {
    try {
      return await fn()
    } catch (err) {
      catchError(err as Error)
      return null
    }
  }
  
  return {
    error: readonly(error),
    hasError,
    catchError,
    clearError,
    withBoundary
  }
}
