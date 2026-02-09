<template>
  <UModal v-model="isOpen" :title="title">
    <template #default>
      <slot />
    </template>

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
          @click="handleConfirm"
          :loading="loading"
          :disabled="loading"
        >
          {{ confirmText }}
        </UButton>
      </div>
    </template>
  </UModal>
</template>

<script setup lang="ts">
interface Props {
  modelValue: boolean
  title: string
  confirmText?: string
  cancelText?: string
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  confirmText: 'Confirmar',
  cancelText: 'Cancelar',
  loading: false
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const handleConfirm = () => {
  emit('confirm')
}

const handleCancel = () => {
  emit('cancel')
  isOpen.value = false
}
</script>
