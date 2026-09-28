<template>
  <div class="space-y-3">
    <UFormGroup label="Plantilla aprobada" required>
      <USelect v-model="templateId" :options="options" :loading="loading"
               :placeholder="loading ? 'Cargando…' : (options.length ? 'Selecciona una plantilla' : 'No hay plantillas aprobadas')" />
    </UFormGroup>
    <p v-if="!loading && !options.length" class="text-xs text-amber-600">
      Esta línea no tiene plantillas aprobadas. Un administrador puede sincronizarlas o crearlas en Configuración → WhatsApp Business.
    </p>

    <template v-if="selected">
      <div v-if="selected.header_param_count" class="space-y-2">
        <p class="text-xs text-gray-500">Variables del encabezado</p>
        <UInput v-for="i in selected.header_param_count" :key="`h${i}`" v-model="headerParams[i - 1]" size="sm" :placeholder="`Encabezado {{${i}}}`" />
      </div>
      <div v-if="selected.body_param_count" class="space-y-2">
        <p class="text-xs text-gray-500">Variables del mensaje</p>
        <UInput v-for="i in selected.body_param_count" :key="`b${i}`" v-model="bodyParams[i - 1]" size="sm" :placeholder="`Variable {{${i}}}`" />
      </div>
      <div class="rounded-lg p-3 bg-[#e5ddd5]">
        <div class="bg-white rounded-lg shadow p-3 max-w-[95%] space-y-1">
          <p v-if="selected.header_text" class="font-semibold text-sm">{{ fill(selected.header_text, headerParams) }}</p>
          <p class="text-sm whitespace-pre-line">{{ fill(selected.body_text, bodyParams) }}</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * Selector de plantilla de WhatsApp + variables + vista previa.
 * v-model = { template_id, body_params, header_params, valid }
 */
const props = defineProps<{ lineId: number | string | null, modelValue?: any }>()
const emit = defineEmits(['update:modelValue'])

const http = useHttp()
const templates = ref<any[]>([])
const loading = ref(false)
const templateId = ref<string>('')
const bodyParams = ref<string[]>([])
const headerParams = ref<string[]>([])

const options = computed(() => templates.value.map(t => ({
  label: `${t.name} (${t.language})${t.category ? ' · ' + t.category : ''}`, value: String(t.id),
})))
const selected = computed(() => templates.value.find(t => String(t.id) === templateId.value) || null)

const fill = (text: string, params: string[]) =>
  (text || '').replace(/\{\{(\d+)\}\}/g, (m, n) => params[Number(n) - 1] || m)

async function load() {
  templates.value = []
  templateId.value = ''
  if (!props.lineId) return
  loading.value = true
  try {
    const data = await http.get('/messaging/whatsapp/templates/', { line: props.lineId, status: 'APPROVED' })
    templates.value = http.results(data)
    if (templates.value.length === 1) templateId.value = String(templates.value[0].id)
  } catch { templates.value = [] }
  finally { loading.value = false }
}

watch(() => props.lineId, load, { immediate: true })
watch(templateId, () => { bodyParams.value = []; headerParams.value = [] })

watch([templateId, bodyParams, headerParams], () => {
  const t = selected.value
  const bp = t ? Array.from({ length: t.body_param_count || 0 }, (_, i) => (bodyParams.value[i] || '').trim()) : []
  const hp = t ? Array.from({ length: t.header_param_count || 0 }, (_, i) => (headerParams.value[i] || '').trim()) : []
  emit('update:modelValue', {
    template_id: t ? t.id : null,
    body_params: bp,
    header_params: hp,
    valid: !!t && bp.every(Boolean) && hp.every(Boolean),
  })
}, { deep: true, immediate: true })
</script>
