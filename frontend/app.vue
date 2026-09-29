<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <!-- Un único contenedor de notificaciones para toda la app: si solo existe en algunas páginas,
         los toasts del resto se acumulan y aparecen todos juntos al volver a esas páginas (p. ej. /login). -->
    <UNotifications />
  </div>
</template>

<script setup lang="ts">
// Global app setup
useHead({
  titleTemplate: (titleChunk) => {
    return titleChunk ? `${titleChunk} - VozipOmni` : 'VozipOmni - Contact Center'
  }
})
</script>
