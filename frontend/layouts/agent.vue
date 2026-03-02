<template>
  <div class="agent-layout">
    <slot />
  </div>
</template>

<script setup lang="ts">
// Layout minimalista para la consola de agente
// Sin sidebar ni navegación extra
</script>

<style scoped>
.agent-layout {
  @apply w-full min-h-screen;
}
</style>
