<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Plantillas de evaluación</h1>
        <p class="text-sm text-gray-500 mt-1">Define los criterios con los que se califican las llamadas. El puntaje final se normaliza a 0-100.</p>
      </div>
      <UButton icon="i-heroicons-plus" @click="openForm()">Nueva plantilla</UButton>
    </div>

    <div v-if="loading" class="text-center py-10"><UIcon name="i-heroicons-arrow-path" class="animate-spin w-6 h-6" /></div>

    <div v-else-if="!templates.length" class="text-center py-12 text-gray-500">
      <UIcon name="i-heroicons-clipboard-document-list" class="w-12 h-12 mx-auto text-gray-300" />
      <p class="mt-2">Aún no hay plantillas. Mientras tanto se usa la plantilla estándar de 5 criterios.</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      <UCard v-for="t in templates" :key="t.id" :class="{ 'opacity-60': !t.is_active }">
        <template #header>
          <div class="flex items-start justify-between gap-2">
            <div>
              <h3 class="font-semibold">{{ t.name }}</h3>
              <p class="text-xs text-gray-500">{{ t.criteria.length }} criterios · máx {{ t.max_total_score }} pts · {{ t.evaluations_count }} evaluaciones</p>
            </div>
            <div class="flex gap-1">
              <UBadge v-if="t.is_default" color="green" variant="soft" size="xs">Por defecto</UBadge>
              <UBadge v-if="!t.is_active" color="gray" variant="soft" size="xs">Inactiva</UBadge>
            </div>
          </div>
        </template>
        <p v-if="t.description" class="text-sm text-gray-600 mb-3">{{ t.description }}</p>
        <ul class="space-y-1 text-sm">
          <li v-for="c in t.criteria" :key="c.name" class="flex justify-between">
            <span>{{ c.label }}</span><span class="text-gray-400">0 – {{ c.max_score }}</span>
          </li>
        </ul>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton v-if="!t.is_default && t.is_active" size="xs" color="gray" variant="ghost" @click="setDefault(t)">Usar por defecto</UButton>
            <UButton size="xs" icon="i-heroicons-pencil" color="gray" variant="ghost" @click="openForm(t)" />
            <UButton size="xs" icon="i-heroicons-trash" color="red" variant="ghost" @click="remove(t)" />
          </div>
        </template>
      </UCard>
    </div>

    <UModal v-model="form.open" :ui="{ width: 'sm:max-w-2xl' }">
      <UCard>
        <template #header><h3 class="font-semibold">{{ form.id ? 'Editar plantilla' : 'Nueva plantilla' }}</h3></template>
        <div class="space-y-4">
          <UFormGroup label="Nombre" required><UInput v-model="form.name" placeholder="Ej: Ventas outbound" /></UFormGroup>
          <UFormGroup label="Descripción"><UTextarea v-model="form.description" :rows="2" /></UFormGroup>

          <div>
            <div class="flex items-center justify-between mb-2">
              <p class="text-sm font-medium">Criterios</p>
              <UButton size="xs" icon="i-heroicons-plus" variant="soft" @click="addCriterion">Agregar criterio</UButton>
            </div>
            <div class="space-y-2">
              <div v-for="(c, i) in form.criteria" :key="i" class="grid grid-cols-12 gap-2 items-start">
                <UInput v-model="c.label" placeholder="Criterio (ej: Saludo)" class="col-span-4" />
                <UInput v-model="c.description" placeholder="Guía para el evaluador (opcional)" class="col-span-5" />
                <UInput v-model.number="c.max_score" type="number" :min="1" :max="100" class="col-span-2" />
                <UButton icon="i-heroicons-x-mark" color="red" variant="ghost" class="col-span-1" @click="form.criteria.splice(i, 1)" />
              </div>
              <p class="text-xs text-gray-400">Columna numérica = puntaje máximo del criterio. Total: {{ totalMax }} pts.</p>
            </div>
          </div>

          <div class="flex gap-6">
            <UCheckbox v-model="form.is_active" label="Activa" />
            <UCheckbox v-model="form.is_default" label="Plantilla por defecto" />
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <UButton color="gray" variant="ghost" @click="form.open = false">Cancelar</UButton>
            <UButton :loading="form.saving" @click="save">Guardar</UButton>
          </div>
        </template>
      </UCard>
    </UModal>
  </div>
</template>

<script setup lang="ts">
const http = useHttp()
const toast = useToast()

const templates = ref<any[]>([])
const loading = ref(false)

const emptyCriteria = () => [
  { label: 'Saludo', description: '', max_score: 5 },
  { label: 'Claridad', description: '', max_score: 5 },
  { label: 'Resolución', description: '', max_score: 5 },
]

const form = reactive({
  open: false, saving: false, id: null as number | null,
  name: '', description: '', is_active: true, is_default: false,
  criteria: emptyCriteria() as any[],
})

const totalMax = computed(() => form.criteria.reduce((s, c) => s + Number(c.max_score || 0), 0))

async function load() {
  loading.value = true
  try { templates.value = http.results(await http.get('/evaluation-templates/')) }
  finally { loading.value = false }
}

function openForm(t?: any) {
  Object.assign(form, {
    open: true, saving: false, id: t?.id ?? null,
    name: t?.name ?? '', description: t?.description ?? '',
    is_active: t?.is_active ?? true, is_default: t?.is_default ?? false,
    criteria: t ? t.criteria.map((c: any) => ({ ...c })) : emptyCriteria(),
  })
}

function addCriterion() {
  form.criteria.push({ label: '', description: '', max_score: 5 })
}

async function save() {
  form.saving = true
  const body = {
    name: form.name, description: form.description,
    is_active: form.is_active, is_default: form.is_default,
    criteria: form.criteria.filter(c => c.label?.trim()),
  }
  try {
    if (form.id) await http.patch(`/evaluation-templates/${form.id}/`, body)
    else await http.post('/evaluation-templates/', body)
    toast.add({ title: 'Plantilla guardada', color: 'green' })
    form.open = false
    await load()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  } finally { form.saving = false }
}

async function setDefault(t: any) {
  await http.patch(`/evaluation-templates/${t.id}/`, { is_default: true })
  await load()
}

async function remove(t: any) {
  if (!confirm(`¿Eliminar la plantilla "${t.name}"?`)) return
  try {
    const res: any = await http.del(`/evaluation-templates/${t.id}/`)
    toast.add({
      title: res?.status === 'deactivated' ? 'Plantilla desactivada (tiene evaluaciones)' : 'Plantilla eliminada',
      color: 'green',
    })
    await load()
  } catch (e: any) {
    toast.add({ title: 'Error', description: http.errorMessage(e), color: 'red' })
  }
}

onMounted(load)
</script>
