<template>
  <div class="message-media">
    <div v-if="loading" class="flex items-center gap-2 text-xs text-gray-500 py-2">
      <UIcon name="i-heroicons-arrow-path" class="w-4 h-4 animate-spin" /> Cargando adjunto…
    </div>
    <div v-else-if="error" class="flex items-center gap-2 text-xs text-gray-500 py-1">
      <UIcon name="i-heroicons-exclamation-circle" class="w-4 h-4" />
      <span>{{ error }}</span>
      <UButton size="2xs" color="gray" variant="ghost" icon="i-heroicons-arrow-path" @click="load" />
    </div>
    <template v-else-if="url">
      <img v-if="kind === 'image' || kind === 'sticker'" :src="url" :alt="message.body || 'Imagen'"
           class="rounded-lg max-w-[260px] max-h-[320px] cursor-zoom-in" @click="openFull" />
      <audio v-else-if="kind === 'audio'" controls :src="url" class="max-w-[260px]" />
      <video v-else-if="kind === 'video'" controls :src="url" class="rounded-lg max-w-[280px]" />
      <a v-else :href="url" :download="filename" class="flex items-center gap-2 p-2 bg-gray-100 rounded hover:bg-gray-200">
        <UIcon name="i-heroicons-document" class="h-6 w-6 text-gray-600" />
        <span class="text-sm font-medium truncate max-w-[200px]">{{ filename }}</span>
        <UIcon name="i-heroicons-arrow-down-tray" class="h-4 w-4 text-gray-500" />
      </a>
    </template>
  </div>
</template>

<script setup lang="ts">
/** Carga el adjunto de un mensaje desde el endpoint autenticado (no hay URL pública por privacidad). */
const props = defineProps<{ message: any, reloadKey?: number }>()

const http = useHttp()
const url = ref('')
const loading = ref(false)
const error = ref('')

const kind = computed(() => props.message.message_type)
const filename = computed(() =>
  props.message.metadata?.filename || `adjunto-${props.message.id}${props.message.metadata?.mime_type?.includes('pdf') ? '.pdf' : ''}`)

function revoke() {
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await http.blob(`/messaging/messages/${props.message.id}/media/`)
    revoke()
    url.value = URL.createObjectURL(data)
  } catch (e: any) {
    error.value = await http.blobErrorMessage(e, 'No se pudo cargar el adjunto')
  } finally {
    loading.value = false
  }
}

function openFull() {
  if (url.value) window.open(url.value, '_blank', 'noopener')
}

onMounted(load)
// El backend avisa con message.media cuando termina la descarga desde Meta
watch(() => props.reloadKey, (v, old) => { if (v !== old) load() })
onBeforeUnmount(revoke)
</script>
