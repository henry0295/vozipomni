<template>
  <UModal v-model="isOpen">
    <UCard>
      <template #header>
        <div class="flex items-center space-x-2">
          <UIcon v-if="icon" :name="icon" :class="iconColorClass" class="w-5 h-5" />
          <h3 class="text-lg font-semibold">{{ title }}</h3>
        </div>
      </template>

      <div v-if="message" class="text-sm text-gray-600">{{ message }}</div>
      <slot />

      <template #footer>
        <div class="flex justify-end space-x-3">
          <UButton
            color="gray"
            variant="outline"
            @click="handleCancel"
            :disabled="loading"
          >
            {{ cancelText }}
          </UButton>
          <UButton
            :color="confirmColor"
            @click="handleConfirm"
            :loading="loading"
            :disabled="loading"
          >
            {{ confirmText }}
          </UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
interface Props {
  modelValue: boolean
  title: string
  message?: string
  confirmText?: string
  cancelText?: string
  confirmColor?: string
  icon?: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  confirmText: 'Confirmar',
  cancelText: 'Cancelar',
  confirmColor: 'primary',
  loading: false
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const iconColorClass = computed(() => {
  const map: Record<string, string> = {
    red: 'text-red-500',
    green: 'text-green-500',
    yellow: 'text-yellow-500',
    blue: 'text-blue-500',
    primary: 'text-sky-500'
  }
  return map[props.confirmColor] || 'text-gray-500'
})

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  emit('cancel')
  isOpen.value = false
}
</script>
