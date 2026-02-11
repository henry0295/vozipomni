import { ref } from 'vue'
import { useApi } from './useApi'

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
  const { get, post, put, delete: del } = useApi()
  const extensions = ref<Extension[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getExtensions = async () => {
    loading.value = true
    try {
      const data = await get('/api/extensions/')
      extensions.value = data
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener extensiones'
    } finally {
      loading.value = false
    }
  }

  const createExtension = async (ext: Omit<Extension, 'id'>) => {
    try {
      const data = await post('/api/extensions/', ext)
      extensions.value.push(data)
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al crear extensión')
    }
  }

  const updateExtension = async (id: number, ext: Partial<Extension>) => {
    try {
      const data = await put(`/api/extensions/${id}/`, ext)
      const index = extensions.value.findIndex(e => e.id === id)
      if (index > -1) {
        extensions.value[index] = data
      }
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al actualizar extensión')
    }
  }

  const deleteExtension = async (id: number) => {
    try {
      await del(`/api/extensions/${id}/`)
      extensions.value = extensions.value.filter(e => e.id !== id)
    } catch (err: any) {
      throw new Error(err.message || 'Error al eliminar extensión')
    }
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
