<template>
  <div>
    <UCard class="shadow-xl">
      <template #header>
        <div class="text-center">
          <UIcon name="i-heroicons-phone" class="h-12 w-12 text-sky-500 mx-auto mb-4" />
          <h1 class="text-2xl font-bold text-gray-900">VozipOmni</h1>
          <p class="text-gray-600 mt-2">Inicia sesión en tu cuenta</p>
        </div>
      </template>

      <UForm 
        :state="form" 
        @submit="handleLogin"
        class="space-y-4"
      >
        <UFormGroup label="Usuario" name="username" required>
          <UInput
            v-model="form.username"
            icon="i-heroicons-user"
            placeholder="Ingresa tu usuario"
            size="lg"
          />
        </UFormGroup>

        <UFormGroup label="Contraseña" name="password" required>
          <UInput
            v-model="form.password"
            type="password"
            icon="i-heroicons-lock-closed"
            placeholder="Ingresa tu contraseña"
            size="lg"
          />
        </UFormGroup>

        <UButton
          type="submit"
          block
          size="lg"
          :loading="loading"
          :disabled="loading"
        >
          Iniciar sesión
        </UButton>
      </UForm>

      <template #footer>
        <div class="text-center text-sm text-gray-600">
          <p>¿Olvidaste tu contraseña? <NuxtLink to="/forgot-password" class="text-sky-600 hover:text-sky-700">Recuperar</NuxtLink></p>
        </div>
      </template>
    </UCard>

    <!-- Notificaciones -->
    <UNotifications />
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'auth',
  middleware: ['guest']
})

const { login } = useAuth()
const toast = useToast()

const form = reactive({
  username: '',
  password: ''
})

const loading = ref(false)

const handleLogin = async () => {
  loading.value = true
  
  try {
    const result = await login(form)

    if (result.success) {
      toast.add({
        title: '¡Bienvenido!',
        description: 'Inicio de sesión exitoso',
        color: 'green'
      })
      
      await navigateTo('/dashboard')
    } else {
      toast.add({
        title: 'Error',
        description: result.error || 'Usuario o contraseña incorrectos',
        color: 'red'
      })
    }
  } catch (error: any) {
    toast.add({
      title: 'Error',
      description: error.message || 'Error al iniciar sesión',
      color: 'red'
    })
  } finally {
    loading.value = false
  }
}
</script>
