<template>
  <UCard :ui="{ body: { padding: 'px-4 py-3 sm:p-4' } }">
    <div class="flex items-start justify-between gap-2">
      <p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">{{ label }}</p>
      <UTooltip v-if="hint" :text="hint" :popper="{ placement: 'top' }">
        <UIcon name="i-heroicons-information-circle" class="w-4 h-4 text-gray-400" :aria-label="hint" />
      </UTooltip>
    </div>
    <p class="text-2xl font-bold mt-1" :class="toneClass">{{ value }}</p>
    <div class="flex items-center gap-2 mt-1 min-h-[1.25rem]">
      <span v-if="delta" class="inline-flex items-center gap-0.5 text-xs font-medium" :class="delta.class"
            :title="`Período anterior: ${previousText}`">
        <UIcon :name="delta.icon" class="w-3.5 h-3.5" aria-hidden="true" />
        {{ delta.text }}
      </span>
      <span v-if="sub" class="text-xs text-gray-400 truncate">{{ sub }}</span>
    </div>
  </UCard>
</template>

<script setup lang="ts">
/**
 * Tarjeta de KPI con variación frente al período anterior.
 *  - points: la métrica es un porcentaje → la variación se muestra en puntos (pp)
 *  - invert: un valor menor es mejor (abandono, espera, AHT…)
 *  - tone: color del valor según la meta (good | warn | bad)
 */
const props = defineProps<{
  label: string
  value: string | number
  current?: number
  previous?: number
  points?: boolean
  invert?: boolean
  tone?: 'good' | 'warn' | 'bad' | ''
  hint?: string
  sub?: string
  previousText?: string
}>()

const toneClass = computed(() => ({
  good: 'text-green-600 dark:text-green-400',
  warn: 'text-amber-600 dark:text-amber-400',
  bad: 'text-red-600 dark:text-red-400',
}[props.tone || ''] || 'text-gray-900 dark:text-white'))

const delta = computed(() => {
  const cur = props.current
  const prev = props.previous
  if (cur === undefined || prev === undefined || cur === null || prev === null) return null
  let diff: number
  let text: string
  if (props.points) {
    diff = Math.round((cur - prev) * 10) / 10
    text = `${diff > 0 ? '+' : ''}${diff} pp`
  } else if (prev === 0) {
    if (cur === 0) return null
    diff = 1
    text = 'nuevo'
  } else {
    diff = Math.round(((cur - prev) / prev) * 1000) / 10
    text = `${diff > 0 ? '+' : ''}${diff}%`
  }
  if (diff === 0) {
    return { text: 'sin cambio', icon: 'i-heroicons-minus', class: 'text-gray-400' }
  }
  const better = props.invert ? diff < 0 : diff > 0
  return {
    text,
    icon: diff > 0 ? 'i-heroicons-arrow-trending-up' : 'i-heroicons-arrow-trending-down',
    class: better ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400',
  }
})
</script>
