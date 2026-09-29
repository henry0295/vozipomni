<template>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
    <UFormGroup label="Campaña por defecto" hint="Define tipificaciones y respuestas rápidas">
      <USelect v-model="model.default_campaign" :options="[{ label: 'Ninguna', value: '' }, ...campaigns]" />
    </UFormGroup>
    <UFormGroup label="Máx. chats simultáneos por agente">
      <UInput v-model.number="model.max_chats_per_agent" type="number" min="1" max="50" />
    </UFormGroup>
    <div class="md:col-span-2 flex flex-wrap gap-6">
      <UCheckbox v-model="model.auto_assign" label="Asignar automáticamente al agente disponible con menos chats" />
      <UCheckbox v-model="model.is_active" label="Activo" />
    </div>
    <UFormGroup label="Mensaje de bienvenida (opcional)" class="md:col-span-2" hint="Se envía al primer mensaje de una conversación nueva dentro del horario">
      <UTextarea v-model="model.welcome_message" :rows="2" />
    </UFormGroup>
    <UFormGroup label="Horario de atención" hint="Condiciones horarias de telefonía">
      <USelect v-model="model.time_condition" :options="[{ label: 'Siempre abierto', value: '' }, ...timeConditions]" />
    </UFormGroup>
    <div class="flex items-end">
      <NuxtLink to="/time-conditions" class="text-xs text-sky-600 hover:underline">Gestionar horarios →</NuxtLink>
    </div>
    <UFormGroup v-if="model.time_condition" label="Mensaje fuera de horario" class="md:col-span-2"
                hint="Se responde automáticamente (máximo una vez cada 4 h por conversación)">
      <UTextarea v-model="model.after_hours_message" :rows="2"
                 placeholder="Gracias por escribirnos. Nuestro horario es de lunes a viernes de 8:00 a 18:00; te responderemos apenas abramos." />
    </UFormGroup>
  </div>
</template>

<script setup lang="ts">
/** Campos comunes de enrutamiento y horario de un canal (email, chat web, Messenger/Instagram, WhatsApp). */
defineProps<{ campaigns: { label: string, value: string }[], timeConditions: { label: string, value: string }[] }>()
const model = defineModel<any>({ required: true })
</script>
