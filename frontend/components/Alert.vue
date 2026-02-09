<template>
  <div
    class="rounded-lg p-4 flex items-start space-x-3"
    :class="bgClass"
  >
    <UIcon
      :name="iconName"
      class="h-5 w-5 flex-shrink-0"
      :class="iconClass"
    />
    <div class="flex-1">
      <h4 v-if="title" class="font-medium" :class="textClass">
        {{ title }}
      </h4>
      <p class="text-sm" :class="textClass">
        <slot />
      </p>
    </div>
    <button
      v-if="dismissible"
      @click="$emit('dismiss')"
      class="flex-shrink-0"
      :class="textClass"
    >
      <UIcon name="i-heroicons-x-mark" class="h-5 w-5" />
    </button>
  </div>
</template>

<script setup lang="ts">
interface Props {
  type?: 'info' | 'success' | 'warning' | 'error'
  title?: string
  dismissible?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'info',
  dismissible: false
})

defineEmits(['dismiss'])

const bgClass = computed(() => {
  const classes = {
    info: 'bg-blue-50 border border-blue-200',
    success: 'bg-green-50 border border-green-200',
    warning: 'bg-orange-50 border border-orange-200',
    error: 'bg-red-50 border border-red-200'
  }
  return classes[props.type]
})

const textClass = computed(() => {
  const classes = {
    info: 'text-blue-900',
    success: 'text-green-900',
    warning: 'text-orange-900',
    error: 'text-red-900'
  }
  return classes[props.type]
})

const iconClass = computed(() => {
  const classes = {
    info: 'text-blue-600',
    success: 'text-green-600',
    warning: 'text-orange-600',
    error: 'text-red-600'
  }
  return classes[props.type]
})

const iconName = computed(() => {
  const icons = {
    info: 'i-heroicons-information-circle',
    success: 'i-heroicons-check-circle',
    warning: 'i-heroicons-exclamation-triangle',
    error: 'i-heroicons-x-circle'
  }
  return icons[props.type]
})
</script>
