<template>
  <UForm :state="formData" @submit="onSubmit" class="space-y-4">
    <!-- Name -->
    <UFormGroup 
      label="Nombre" 
      name="name"
      :error="getFieldError('name')"
      required
    >
      <UInput 
        v-model="formData.name" 
        @blur="validateField('name', formData.name)"
        placeholder="Nombre de la campaña"
      />
    </UFormGroup>

    <!-- Description -->
    <UFormGroup label="Descripción" name="description">
      <UTextarea 
        v-model="formData.description" 
        placeholder="Descripción de la campaña"
        :rows="3"
      />
    </UFormGroup>

    <!-- Campaign Type -->
    <UFormGroup 
      label="Tipo de Campaña" 
      name="campaign_type"
      :error="getFieldError('campaign_type')"
      required
    >
      <USelect 
        v-model="formData.campaign_type"
        :options="campaignTypes"
        @change="validateField('campaign_type', formData.campaign_type)"
      />
    </UFormGroup>

    <!-- Dialer Type -->
    <UFormGroup 
      label="Tipo de Marcador" 
      name="dialer_type"
      :error="getFieldError('dialer_type')"
    >
      <USelect 
        v-model="formData.dialer_type"
        :options="dialerTypes"
      />
    </UFormGroup>

    <!-- Dates -->
    <div class="grid grid-cols-2 gap-4">
      <UFormGroup 
        label="Fecha Inicio" 
        name="start_date"
        :error="getFieldError('start_date')"
        required
      >
        <UInput 
          v-model="formData.start_date" 
          type="datetime-local"
          @blur="validateField('start_date', formData.start_date)"
        />
      </UFormGroup>

      <UFormGroup 
        label="Fecha Fin" 
        name="end_date"
        :error="getFieldError('end_date')"
      >
        <UInput 
          v-model="formData.end_date" 
          type="datetime-local"
          @blur="validate(formData)"
        />
      </UFormGroup>
    </div>

    <!-- Configuration -->
    <div class="grid grid-cols-3 gap-4">
      <UFormGroup 
        label="Reintentos Máx." 
        name="max_retries"
        :error="getFieldError('max_retries')"
      >
        <UInput 
          v-model.number="formData.max_retries" 
          type="number"
          min="0"
          max="10"
          @blur="validateField('max_retries', formData.max_retries)"
        />
      </UFormGroup>

      <UFormGroup 
        label="Timeout (seg)" 
        name="call_timeout"
        :error="getFieldError('call_timeout')"
      >
        <UInput 
          v-model.number="formData.call_timeout" 
          type="number"
          min="10"
          max="300"
          @blur="validateField('call_timeout', formData.call_timeout)"
        />
      </UFormGroup>

      <UFormGroup 
        label="Llamadas/Agente" 
        name="max_calls_per_agent"
        :error="getFieldError('max_calls_per_agent')"
      >
        <UInput 
          v-model.number="formData.max_calls_per_agent" 
          type="number"
          min="1"
          max="5"
          @blur="validateField('max_calls_per_agent', formData.max_calls_per_agent)"
        />
      </UFormGroup>
    </div>

    <!-- Actions -->
    <div class="flex justify-end gap-3">
      <UButton 
        color="gray" 
        variant="ghost" 
        @click="$emit('cancel')"
      >
        Cancelar
      </UButton>
      <UButton 
        type="submit" 
        :loading="loading"
        :disabled="!isValid"
      >
        {{ campaign ? 'Actualizar' : 'Crear' }} Campaña
      </UButton>
    </div>
  </UForm>
</template>

<script setup lang="ts">
import { campaignSchema } from '~/composables/useFormValidation'

const props = defineProps<{
  campaign?: any
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [data: any]
  cancel: []
}>()

// Form validation
const { 
  errors, 
  isValid, 
  validate, 
  validateField, 
  getFieldError 
} = useFormValidation(campaignSchema)

// Form data
const formData = reactive({
  name: props.campaign?.name || '',
  description: props.campaign?.description || '',
  campaign_type: props.campaign?.campaign_type || 'outbound',
  dialer_type: props.campaign?.dialer_type || 'progressive',
  start_date: props.campaign?.start_date || '',
  end_date: props.campaign?.end_date || '',
  max_retries: props.campaign?.max_retries || 3,
  call_timeout: props.campaign?.call_timeout || 30,
  max_calls_per_agent: props.campaign?.max_calls_per_agent || 1,
  contact_list: props.campaign?.contact_list || null,
  queue: props.campaign?.queue || null,
})

// Options
const campaignTypes = [
  { label: 'Entrante', value: 'inbound' },
  { label: 'Saliente', value: 'outbound' },
  { label: 'Manual', value: 'manual' },
  { label: 'Preview', value: 'preview' },
]

const dialerTypes = [
  { label: 'Predictivo', value: 'predictive' },
  { label: 'Progresivo', value: 'progressive' },
  { label: 'Preview', value: 'preview' },
  { label: 'Manual', value: 'manual' },
]

// Submit handler
const onSubmit = () => {
  if (validate(formData)) {
    emit('submit', { ...formData })
  }
}
</script>
