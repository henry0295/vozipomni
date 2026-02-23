import { ref } from 'vue'

interface Extension {
  id: number
  extension: string
  name: string
  extension_type: string
  secret: string
  context: string
  callerid: string
  email: string
  voicemail_enabled: boolean
  is_active: boolean
}

export const useExtensions = () => {
  const { apiFetch } = useApi()
  const extensions = ref<Extension[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getExtensions = async () => {
    loading.value = true
    try {
      const { data, error: fetchError } = await apiFetch<any>('/telephony/extensions/')
      if (fetchError.value) throw new Error('Error al obtener extensiones')
      const raw = data.value
      extensions.value = Array.isArray(raw) ? raw : (raw?.results || [])
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener extensiones'
    } finally {
      loading.value = false
    }
  }

  const createExtension = async (ext: Omit<Extension, 'id'>) => {
    const { data, error: fetchError } = await apiFetch<any>('/telephony/extensions/', {
      method: 'POST',
      body: ext
    })
    if (fetchError.value) throw new Error('Error al crear extensión')
    const created = data.value
    extensions.value.push(created)
    return created
  }

  const updateExtension = async (id: number, ext: Partial<Extension>) => {
    const { data, error: fetchError } = await apiFetch<any>(`/telephony/extensions/${id}/`, {
      method: 'PUT',
      body: ext
    })
    if (fetchError.value) throw new Error('Error al actualizar extensión')
    const updated = data.value
    const index = extensions.value.findIndex(e => e.id === id)
    if (index > -1) extensions.value[index] = updated
    return updated
  }

  const deleteExtension = async (id: number) => {
    const { error: fetchError } = await apiFetch(`/telephony/extensions/${id}/`, {
      method: 'DELETE'
    })
    if (fetchError.value) throw new Error('Error al eliminar extensión')
    extensions.value = extensions.value.filter(e => e.id !== id)
  }

  return {
    extensions,
    loading,
    error,
    getExtensions,
    createExtension,
    updateExtension,
    deleteExtension
  }
}
