export default defineNuxtPlugin(() => {
  const authStore = useAuthStore()

  // Cargar autenticación desde localStorage al iniciar
  if (process.client) {
    authStore.loadFromStorage()
  }
})
