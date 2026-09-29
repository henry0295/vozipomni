<template>
  <div v-if="items.length" class="space-y-2" role="list">
    <div v-for="item in items" :key="item.label" class="space-y-1" role="listitem">
      <div class="flex items-center justify-between gap-2 text-sm">
        <span class="text-gray-700 dark:text-gray-200 truncate" :title="item.label">{{ item.label }}</span>
        <span class="text-gray-500 dark:text-gray-400 whitespace-nowrap">
          {{ item.display ?? item.value }}<span v-if="item.sub" class="text-xs text-gray-400"> · {{ item.sub }}</span>
        </span>
      </div>
      <div class="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2 overflow-hidden">
        <div class="h-2 rounded-full transition-all" :class="item.color || color"
             :style="{ width: width(item.value) }" />
      </div>
    </div>
  </div>
  <p v-else class="py-6 text-center text-sm text-gray-400">{{ empty }}</p>
</template>

<script setup lang="ts">
/** Lista de barras horizontales proporcionales (sin librería de gráficos). */
const props = withDefaults(defineProps<{
  items: { label: string; value: number; display?: string | number; sub?: string; color?: string }[]
  color?: string
  max?: number
  empty?: string
}>(), { color: 'bg-primary-500', empty: 'Sin datos para el período' })

const top = computed(() => props.max || Math.max(1, ...props.items.map(i => i.value || 0)))
const width = (v: number) => (v > 0 ? `${Math.max(2, (v / top.value) * 100)}%` : '0%')
</script>
