/** Metadatos visuales de los canales de mensajería. */
export const CHANNEL_META: Record<string, { label: string, icon: string, color: string }> = {
  whatsapp: { label: 'WhatsApp', icon: 'i-heroicons-chat-bubble-oval-left-ellipsis', color: 'text-green-600' },
  email: { label: 'Email', icon: 'i-heroicons-envelope', color: 'text-sky-600' },
  webchat: { label: 'Chat web', icon: 'i-heroicons-globe-alt', color: 'text-violet-600' },
  messenger: { label: 'Messenger', icon: 'i-heroicons-chat-bubble-left-right', color: 'text-blue-600' },
  instagram: { label: 'Instagram', icon: 'i-heroicons-camera', color: 'text-pink-600' },
}

export const channelMeta = (type: string) =>
  CHANNEL_META[type] || { label: type || 'Canal', icon: 'i-heroicons-chat-bubble-left', color: 'text-gray-500' }

export const CHANNEL_FILTER_OPTIONS = [
  { label: 'Todos los canales', value: '' },
  ...Object.entries(CHANNEL_META).map(([value, m]) => ({ label: m.label, value })),
]

/** Formatea segundos como "45 s", "3 min 20 s", "1 h 5 min". */
export const formatSeconds = (s: number | null | undefined) => {
  if (s == null || isNaN(Number(s))) return '—'
  const v = Number(s)
  if (v < 60) return `${Math.round(v)} s`
  if (v < 3600) return `${Math.floor(v / 60)} min ${Math.round(v % 60)} s`
  return `${Math.floor(v / 3600)} h ${Math.floor((v % 3600) / 60)} min`
}
