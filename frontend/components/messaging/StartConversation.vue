<template>
  <UModal :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
    <UCard>
      <template #header>
        <div class="flex items-center justify-between gap-3">
          <h3 class="font-semibold">Nueva conversación</h3>
          <div v-if="emailAccounts.length" class="flex gap-1" role="tablist">
            <UButton size="xs" :variant="mode === 'whatsapp' ? 'solid' : 'ghost'" :color="mode === 'whatsapp' ? 'green' : 'gray'"
                     icon="i-heroicons-chat-bubble-oval-left-ellipsis" role="tab" :aria-selected="mode === 'whatsapp'" @click="mode = 'whatsapp'">WhatsApp</UButton>
            <UButton size="xs" :variant="mode === 'email' ? 'solid' : 'ghost'" :color="mode === 'email' ? 'sky' : 'gray'"
                     icon="i-heroicons-envelope" role="tab" :aria-selected="mode === 'email'" @click="mode = 'email'">Email</UButton>
          </div>
        </div>
      </template>

      <!-- WhatsApp -->
      <div v-if="mode === 'whatsapp'" class="space-y-3">
        <UFormGroup label="Línea" required>
          <USelect v-model="lineId" :options="lineOptions" :placeholder="lineOptions.length ? 'Selecciona' : 'No hay líneas activas'" />
        </UFormGroup>
        <UFormGroup label="Número destino" required hint="Con indicativo de país, ej: 573001234567">
          <UInput v-model="to" icon="i-heroicons-phone" placeholder="573001234567" />
        </UFormGroup>
        <p class="text-xs text-gray-500">WhatsApp exige una plantilla aprobada para iniciar una conversación. Cuando el cliente responda podrás escribir libremente durante 24 h.</p>
        <MessagingTemplateForm v-if="lineId" v-model="tpl" :line-id="lineId" />
      </div>

      <!-- Email -->
      <div v-else class="space-y-3">
        <UFormGroup label="Desde" required>
          <USelect v-model="accountId" :options="emailOptions" />
        </UFormGroup>
        <UFormGroup label="Para" required>
          <UInput v-model="emailTo" type="email" icon="i-heroicons-at-symbol" placeholder="cliente@correo.com" />
        </UFormGroup>
        <UFormGroup label="Asunto" required>
          <UInput v-model="subject" maxlength="300" />
        </UFormGroup>
        <UFormGroup label="Mensaje" required>
          <UTextarea v-model="emailBody" :rows="6" />
        </UFormGroup>
      </div>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton color="gray" variant="ghost" @click="emit('update:modelValue', false)">Cancelar</UButton>
          <UButton v-if="mode === 'whatsapp'" icon="i-heroicons-paper-airplane" color="green" :loading="sending"
                   :disabled="!lineId || digits.length < 8 || !tpl?.valid" @click="start">Iniciar</UButton>
          <UButton v-else icon="i-heroicons-paper-airplane" color="sky" :loading="sending"
                   :disabled="!accountId || !emailValid || !subject.trim() || !emailBody.trim()" @click="startEmail">Enviar correo</UButton>
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

const mode = ref<'whatsapp' | 'email'>('whatsapp')
const lines = ref<any[]>([])
const emailAccounts = ref<any[]>([])
const lineId = ref('')
const to = ref('')
const tpl = ref<any>(null)
const sending = ref(false)
const accountId = ref('')
const emailTo = ref('')
const subject = ref('')
const emailBody = ref('')

const digits = computed(() => to.value.replace(/\D/g, ''))
const emailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailTo.value.trim()))
const lineOptions = computed(() => lines.value
  .filter(l => l.is_active)
  .map(l => ({ label: `${l.name}${l.display_phone_number ? ' · ' + l.display_phone_number : ''}`, value: String(l.id) })))
const emailOptions = computed(() => emailAccounts.value
  .filter(a => a.is_active)
  .map(a => ({ label: `${a.name} <${a.email_address}>`, value: String(a.id) })))

async function loadChannels() {
  const [l, e] = await Promise.allSettled([
    http.get('/messaging/whatsapp/lines/'),
    http.get('/messaging/email/accounts/'),
  ])
  lines.value = l.status === 'fulfilled' ? http.results(l.value) : []
  emailAccounts.value = e.status === 'fulfilled' ? http.results(e.value) : []
  if (!lineId.value && lineOptions.value.length === 1) lineId.value = lineOptions.value[0].value
  if (!accountId.value && emailOptions.value.length) accountId.value = emailOptions.value[0].value
  if (!lineOptions.value.length && emailOptions.value.length) mode.value = 'email'
}

watch(() => props.modelValue, (open) => {
  if (!open) return
  const initial = props.initialTo || ''
  if (initial.includes('@')) {
    mode.value = 'email'
    emailTo.value = initial
  } else {
    to.value = initial.replace(/\D/g, '')
  }
  tpl.value = null
  subject.value = ''
  emailBody.value = ''
  loadChannels()
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
    toast.add({ title: 'No se pudo iniciar la conversación', description: d?.message?.error_message || http.errorMessage(e), color: 'red' })
    if (d?.conversation) emit('started', d.conversation)
  } finally { sending.value = false }
}

async function startEmail() {
  sending.value = true
  try {
    const res: any = await http.post('/messaging/conversations/start-email/', {
      account_id: Number(accountId.value), to: emailTo.value.trim(),
      subject: subject.value.trim(), body: emailBody.value.trim(),
    })
    toast.add({ title: 'Correo enviado', color: 'green' })
    emit('update:modelValue', false)
    emit('started', res.conversation)
  } catch (e: any) {
    const d = e?.data
    toast.add({ title: 'No se pudo enviar el correo', description: d?.message?.error_message || http.errorMessage(e), color: 'red' })
    if (d?.conversation) emit('started', d.conversation)
  } finally { sending.value = false }
}
</script>
