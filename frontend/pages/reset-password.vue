<template>
  <div>
    <UCard class="shadow-xl">
      <template #header>
        <div class="text-center">
          <UIcon name="i-heroicons-lock-closed" class="h-12 w-12 text-sky-500 mx-auto mb-4" />
          <h1 class="text-2xl font-bold text-gray-900">Nueva contraseña</h1>
          <p class="text-gray-600 mt-2">Elige una contraseña segura para tu cuenta.</p>
        </div>
      </template>

      <UAlert v-if="!uid || !token" icon="i-heroicons-exclamation-triangle" color="red" variant="soft"
              title="Enlace incompleto"
              description="Abre el enlace completo que recibiste por correo o solicita uno nuevo." />

      <UAlert v-else-if="done" icon="i-heroicons-check-circle" color="green" variant="soft"
              title="Contraseña actualizada"
              description="Ya puedes iniciar sesión con tu nueva contraseña." />

      <UForm v-else :state="form" class="space-y-4" @submit="submit">
        <UFormGroup label="Nueva contraseña" name="password" required
                    hint="Mínimo 8 caracteres, no solo números">
          <UInput v-model="form.password" type="password" icon="i-heroicons-lock-closed" size="lg" autocomplete="new-password" />
        </UFormGroup>
        <UFormGroup label="Confirmar contraseña" name="confirm" required
                    :error="form.confirm && form.confirm !== form.password ? 'No coincide' : undefined">
          <UInput v-model="form.confirm" type="password" icon="i-heroicons-lock-closed" size="lg" autocomplete="new-password" />
        </UFormGroup>
        <UAlert v-if="error" color="red" variant="soft" :description="error" />
        <UButton type="submit" block size="lg" :loading="loading"
                 :disabled="!form.password || form.password !== form.confirm">
          Guardar contraseña
        </UButton>
      </UForm>

      <template #footer>
        <div class="flex justify-between text-sm">
          <NuxtLink to="/forgot-password" class="text-gray-600 hover:text-gray-800">Solicitar otro enlace</NuxtLink>
          <NuxtLink to="/login" class="text-sky-600 hover:text-sky-700">Iniciar sesión →</NuxtLink>
        </div>
      </template>
    </UCard>
  </div>
</template>

<script setup lang="ts">
// Sin middleware guest: el enlace del correo debe funcionar aunque haya una sesión abierta
definePageMeta({ layout: 'auth' })
useHead({ title: 'Nueva contraseña - VozipOmni' })

const route = useRoute()
const http = useHttp()

const uid = computed(() => String(route.query.uid || ''))
const token = computed(() => String(route.query.token || ''))

const form = reactive({ password: '', confirm: '' })
const loading = ref(false)
const done = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await http.post('/auth/password-reset/confirm/', {
      uid: uid.value,
      token: token.value,
      password: form.password,
    })
    done.value = true
    // La sesión anterior (si existía) quedó invalidada en el backend
    try { useAuthStore().clearAuth() } catch { /* ignore */ }
    setTimeout(() => navigateTo('/login'), 2500)
  } catch (e: any) {
    const d = e?.data
    error.value = Array.isArray(d?.password) ? d.password.join(' ') : http.errorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>
