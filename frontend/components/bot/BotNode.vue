<template>
  <div
    class="rounded-lg border-2 bg-white shadow-sm w-64 text-left"
    :class="selected ? 'border-primary-500 ring-2 ring-primary-200' : palette.border"
  >
    <Handle type="target" :position="Position.Left" class="!w-3 !h-3 !bg-gray-400" />

    <div class="flex items-center gap-2 px-3 py-2 rounded-t-md" :class="palette.head">
      <UIcon :name="meta.icon" class="w-4 h-4 shrink-0" :class="palette.icon" />
      <span class="text-sm font-semibold truncate flex-1">{{ data.title || meta.label }}</span>
      <UBadge v-if="data.isStart" color="green" size="xs" variant="solid">Inicio</UBadge>
    </div>

    <div v-if="preview" class="px-3 py-2 text-xs text-gray-600 whitespace-pre-line line-clamp-3 border-b">
      {{ preview }}
    </div>
    <div v-else class="px-3 py-1 text-[11px] text-gray-400 border-b">{{ meta.label }}</div>

    <div v-if="outputs.length" class="py-1">
      <div
        v-for="o in outputs"
        :key="o.id"
        class="relative flex items-center justify-end pr-4 pl-3 py-1 text-[11px] text-gray-600"
      >
        <span class="truncate">{{ o.label }}</span>
        <Handle
          :id="o.id"
          type="source"
          :position="Position.Right"
          class="!w-3 !h-3"
          :class="handleColor(o.id)"
        />
      </div>
    </div>
    <div v-else class="px-3 py-1 text-[11px] text-gray-400 italic">Termina aquí</div>
  </div>
</template>

<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import { BLOCKS, blockOutputs } from '~/utils/botBlocks'

const props = defineProps<{ id: string, data: any, selected?: boolean }>()

const meta = computed(() => BLOCKS[props.data.kind] || { label: props.data.kind, icon: 'i-heroicons-cube', color: 'gray', help: '' })
const outputs = computed(() => blockOutputs(props.data))
// Clases completas (Tailwind no genera clases armadas dinámicamente)
const PALETTES: Record<string, { border: string, head: string, icon: string }> = {
  sky: { border: 'border-sky-300', head: 'bg-sky-50', icon: 'text-sky-600' },
  violet: { border: 'border-violet-300', head: 'bg-violet-50', icon: 'text-violet-600' },
  amber: { border: 'border-amber-300', head: 'bg-amber-50', icon: 'text-amber-600' },
  orange: { border: 'border-orange-300', head: 'bg-orange-50', icon: 'text-orange-600' },
  emerald: { border: 'border-emerald-300', head: 'bg-emerald-50', icon: 'text-emerald-600' },
  rose: { border: 'border-rose-300', head: 'bg-rose-50', icon: 'text-rose-600' },
  fuchsia: { border: 'border-fuchsia-300', head: 'bg-fuchsia-50', icon: 'text-fuchsia-600' },
  gray: { border: 'border-gray-300', head: 'bg-gray-50', icon: 'text-gray-600' },
}
const palette = computed(() => PALETTES[meta.value.color] || PALETTES.gray)
const preview = computed(() => {
  const d = props.data
  if (d.kind === 'connector') return d.action ? `${d.action} → {{${d.output_variable || 'resultado'}}}` : 'Sin acción'
  if (d.kind === 'condition') return (d.rules || []).map((r: any) => `${r.variable} ${r.operator} ${r.value ?? ''}`).join('\n')
  if (d.kind === 'set_variable') return `${d.variable} = ${d.value}`
  return (d.text || '').slice(0, 140)
})
const handleColor = (id: string) => (
  id === 'error' || id === 'false' || id === 'closed' || id === 'invalid' ? '!bg-red-400'
    : id === 'empty' ? '!bg-amber-400' : '!bg-primary-500'
)
</script>
