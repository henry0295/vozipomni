<template>
  <UModal :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
    <UCard>
      <template #header><h3 class="font-semibold">Nueva conversación de WhatsApp</h3></template>
      <div class="space-y-3">
        <UFormGroup label="Línea" required>
          <USelect v-model="lineId" :options="lineOptions" :placeholder="lineOptions.length ? 'Selecciona' : 'No hay líneas activas'" />
        </UFormGroup>
        <UFormGroup label="Número destino" required hint="Con indicativo de país, ej: 573001234567">
          <UInput v-model="to" icon="i-heroicons-phone" placeholder="573001234567" />
        </UFormGroup>
        <p class="text-xs text-gray-500">WhatsApp exige una plantilla aprobada para iniciar una conversación. Cuando el cliente responda podrás escribir libremente durante 24 h.</p>
        <MessagingTemplateForm v-if="lineId" v-model="tpl" :line-id="lineId" />
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" @click="emit('update:modelValue', false)">Cancelar</UButton>
          <UButton icon="i-heroicons-paper-airplane" color="green" :loading="sending"
                   :disabled="!lineId || digits.length < 8 || !tpl?.valid" @click="start">Iniciar</UButton>
        </div>
      </template>
    </UCard>
  </UModal>
</template>

<script setup lang="ts">
const props = defineProps<{ modelValue: boolean, initialTo?: string, contactId?: number | null }>()
const emit = defineEmits(['update:modelValue', 'started'])

const http = useHttp()
const toast = useToast()

const lines = ref<any[]>([])
const lineId = ref('')
const to = ref('')
const tpl = ref<any>(null)
const sending = ref(false)

const digits = computed(() => to.value.replace(/\D/g, ''))
const lineOptions = computed(() => lines.value
  .filter(l => l.is_active)
  .map(l => ({ label: `${l.name}${l.display_phone_number ? ' · ' + l.display_phone_number : ''}`, value: String(l.id) })))

async function loadLines() {
  try {
    lines.value = http.results(await http.get('/messaging/whatsapp/lines/'))
    if (!lineId.value && lineOptions.value.length === 1) lineId.value = lineOptions.value[0].value
  } catch { lines.value = [] }
}

watch(() => props.modelValue, (open) => {
  if (!open) return
  to.value = (props.initialTo || '').replace(/\D/g, '')
  tpl.value = null
  loadLines()
}, { immediate: true })

async function start() {
  sending.value = true
  try {
    const res: any = await http.post('/messaging/conversations/start/', {
      line_id: Number(lineId.value),
      to: digits.value,
      template_id: tpl.value.template_id,
      body_params: tpl.value.body_params,
      header_params: tpl.value.header_params,
      contact_id: props.contactId || undefined,
    })
    toast.add({ title: 'Plantilla enviada', color: 'green' })
    emit('update:modelValue', false)
    emit('started', res.conversation)
  } catch (e: any) {
    const d = e?.data
    toast.add({
      title: 'No se pudo iniciar la conversación',
      description: d?.message?.error_message || http.errorMessage(e),
      color: 'red',
    })
    if (d?.conversation) emit('started', d.conversation)
  } finally { sending.value = false }
}
</script>
