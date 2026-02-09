<template>
  <UCard :ui="{ body: { padding: 'p-0' } }">
    <template #header>
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
        <slot name="header-actions" />
      </div>
    </template>

    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th
              v-for="column in columns"
              :key="column.key"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              {{ column.label }}
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="(row, index) in data"
            :key="index"
            class="hover:bg-gray-50 transition-colors"
          >
            <td
              v-for="column in columns"
              :key="column.key"
              class="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
            >
              <slot :name="`cell-${column.key}`" :row="row" :value="row[column.key]">
                {{ row[column.key] }}
              </slot>
            </td>
          </tr>
          <tr v-if="!data || data.length === 0">
            <td
              :colspan="columns.length"
              class="px-6 py-8 text-center text-sm text-gray-500"
            >
              {{ emptyMessage }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <template #footer v-if="showPagination">
      <div class="flex items-center justify-between">
        <p class="text-sm text-gray-700">
          Mostrando {{ startItem }} a {{ endItem }} de {{ total }} resultados
        </p>
        <div class="flex gap-2">
          <UButton
            icon="i-heroicons-chevron-left"
            color="gray"
            variant="outline"
            :disabled="currentPage === 1"
            @click="$emit('page-change', currentPage - 1)"
          />
          <UButton
            icon="i-heroicons-chevron-right"
            color="gray"
            variant="outline"
            :disabled="currentPage === totalPages"
            @click="$emit('page-change', currentPage + 1)"
          />
        </div>
      </div>
    </template>
  </UCard>
</template>

<script setup lang="ts">
interface Column {
  key: string
  label: string
}

interface Props {
  title?: string
  columns: Column[]
  data: any[]
  showPagination?: boolean
  currentPage?: number
  pageSize?: number
  total?: number
  emptyMessage?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  showPagination: false,
  currentPage: 1,
  pageSize: 10,
  total: 0,
  emptyMessage: 'No hay datos disponibles'
})

defineEmits(['page-change'])

const startItem = computed(() => (props.currentPage - 1) * props.pageSize + 1)
const endItem = computed(() => Math.min(props.currentPage * props.pageSize, props.total))
const totalPages = computed(() => Math.ceil(props.total / props.pageSize))
</script>
