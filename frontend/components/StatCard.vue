<template>
  <UCard>
    <div class="flex items-center space-x-4">
      <div
        class="flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center"
        :class="iconBgClass"
      >
        <UIcon :name="icon" class="h-6 w-6" :class="iconColorClass" />
      </div>
      <div class="flex-1">
        <p class="text-sm text-gray-600">{{ label }}</p>
        <p class="text-2xl font-bold text-gray-900 mt-1">{{ value }}</p>
      </div>
    </div>
    <div v-if="trend" class="mt-4">
      <span
        class="text-sm"
        :class="trendClass"
      >
        {{ trendIcon }} {{ trend }}
      </span>
    </div>
  </UCard>
</template>

<script setup lang="ts">
interface Props {
  label: string
  value: string | number
  icon: string
  color?: 'green' | 'blue' | 'purple' | 'orange' | 'red' | 'sky'
  trend?: string
  trendDirection?: 'up' | 'down' | 'neutral'
}

const props = withDefaults(defineProps<Props>(), {
  color: 'sky',
  trendDirection: 'neutral'
})

const iconBgClass = computed(() => {
  const colors = {
    green: 'bg-green-100',
    blue: 'bg-blue-100',
    purple: 'bg-purple-100',
    orange: 'bg-orange-100',
    red: 'bg-red-100',
    sky: 'bg-sky-100'
  }
  return colors[props.color]
})

const iconColorClass = computed(() => {
  const colors = {
    green: 'text-green-600',
    blue: 'text-blue-600',
    purple: 'text-purple-600',
    orange: 'text-orange-600',
    red: 'text-red-600',
    sky: 'text-sky-600'
  }
  return colors[props.color]
})

const trendClass = computed(() => {
  const classes = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-600'
  }
  return classes[props.trendDirection]
})

const trendIcon = computed(() => {
  const icons = {
    up: '↑',
    down: '↓',
    neutral: '→'
  }
  return icons[props.trendDirection]
})
</script>
