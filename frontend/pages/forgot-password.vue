<template>
  <div>
    <UCard class="shadow-xl">
      <template #header>
        <div class="text-center">
          <UIcon name="i-heroicons-key" class="h-12 w-12 text-sky-500 mx-auto mb-4" />
          <h1 class="text-2xl font-bold text-gray-900">Recuperar contraseña</h1>
          <p class="text-gray-600 mt-2">Te enviaremos un enlace para crear una nueva contraseña.</p>
        </div>
      </template>

      <UAlert v-if="sent" icon="i-heroicons-envelope" color="green" variant="soft"
              title="Revisa tu correo"
              :description="message" />

      <UForm v-else :state="form" class="space-y-4" @submit="submit">
        <UFormGroup label="Correo o usuario" name="email" required>
          <UInput v-model="form.email" icon="i-heroicons-at-symbol" placeholder="tu@empresa.com" size="lg" autofocus />
        </UFormGroup>
        <UButton type="submit" block size="lg" :loading="loading" :disabled="!form.email.trim()">
          Enviar enlace
        </UButton>
      </UForm>

      <template #footer>
        <div class="text-center text-sm text-gray-600">
          <NuxtLink to="/login" class="text-sky-600 hover:text-sky-700">← Volver a iniciar sesión</NuxtLink>
        </div>
      </template>
    </UCard>
    <UNotifications />
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'auth', middleware: ['guest'] })
useHead({ title: 'Recuperar contraseña - VozipOmni' })

const http = useHttp()
const toast = useToast()

const form = reactive({ email: '' })
const loading = ref(false)
const sent = ref(false)
const message = ref('')

async function submit() {
  loading.value = true
  try {
    const res: any = await http.post('/auth/password-reset/', { email: form.email.trim() })
    message.value = res?.message || 'Si la cuenta existe, recibirás un correo con instrucciones.'
    sent.value = true
  } catch (e: any) {
    const tooMany = e?.response?.status === 429 || e?.statusCode === 429
    toast.add({
      title: 'No se pudo enviar',
      description: tooMany ? 'Demasiados intentos. Espera un momento e inténtalo de nuevo.' : http.errorMessage(e),
      color: 'red',
    })
  } finally {
    loading.value = false
  }
}
</script>
