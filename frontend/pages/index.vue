<template>
  <div>
    <NuxtLink to="/login">Ir a Login</NuxtLink>
  </div>
</template>

<script setup lang="ts">
// Redirigir automáticamente
definePageMeta({
  middleware: ['guest']
})

onMounted(() => {
  const { isAuthenticated } = useAuth()
  if (isAuthenticated.value) {
    navigateTo('/dashboard')
  } else {
    navigateTo('/login')
  }
})
</script>
