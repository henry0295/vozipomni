<template>
  <div>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
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
