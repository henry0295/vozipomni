import { ref } from 'vue'
import { useApi } from './useApi'

interface Voicemail {
  id: number
  mailbox: string
  name: string
  email: string
  password: string
  max_messages: number
  email_attach: boolean
  email_delete: boolean
  is_active: boolean
}

export const useVoicemail = () => {
  const { get, post, put, delete: del } = useApi()
  const voicemails = ref<Voicemail[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getVoicemails = async () => {
    loading.value = true
    try {
      const data = await get('/api/voicemail/')
      voicemails.value = data
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener buzones de voz'
    } finally {
      loading.value = false
    }
  }

  const createVoicemail = async (vm: Omit<Voicemail, 'id'>) => {
    try {
      const data = await post('/api/voicemail/', vm)
      voicemails.value.push(data)
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al crear buzón')
    }
  }

  const updateVoicemail = async (id: number, vm: Partial<Voicemail>) => {
    try {
      const data = await put(`/api/voicemail/${id}/`, vm)
      const index = voicemails.value.findIndex(v => v.id === id)
      if (index > -1) {
        voicemails.value[index] = data
      }
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al actualizar buzón')
    }
  }

  const deleteVoicemail = async (id: number) => {
    try {
      await del(`/api/voicemail/${id}/`)
      voicemails.value = voicemails.value.filter(v => v.id !== id)
    } catch (err: any) {
      throw new Error(err.message || 'Error al eliminar buzón')
    }
  }

  return {
    voicemails,
    loading,
    error,
    getVoicemails,
    createVoicemail,
    updateVoicemail,
    deleteVoicemail
  }
}
