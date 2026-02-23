import { ref } from 'vue'

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
  const { apiFetch } = useApi()
  const voicemails = ref<Voicemail[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getVoicemails = async () => {
    loading.value = true
    try {
      const { data, error: fetchError } = await apiFetch<any>('/telephony/voicemail/')
      if (fetchError.value) throw new Error('Error al obtener buzones de voz')
      const raw = data.value
      voicemails.value = Array.isArray(raw) ? raw : (raw?.results || [])
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener buzones de voz'
    } finally {
      loading.value = false
    }
  }

  const createVoicemail = async (vm: Omit<Voicemail, 'id'>) => {
    const { data, error: fetchError } = await apiFetch<any>('/telephony/voicemail/', {
      method: 'POST',
      body: vm
    })
    if (fetchError.value) throw new Error('Error al crear buzón')
    const created = data.value
    voicemails.value.push(created)
    return created
  }

  const updateVoicemail = async (id: number, vm: Partial<Voicemail>) => {
    const { data, error: fetchError } = await apiFetch<any>(`/telephony/voicemail/${id}/`, {
      method: 'PUT',
      body: vm
    })
    if (fetchError.value) throw new Error('Error al actualizar buzón')
    const updated = data.value
    const index = voicemails.value.findIndex(v => v.id === id)
    if (index > -1) voicemails.value[index] = updated
    return updated
  }

  const deleteVoicemail = async (id: number) => {
    const { error: fetchError } = await apiFetch(`/telephony/voicemail/${id}/`, {
      method: 'DELETE'
    })
    if (fetchError.value) throw new Error('Error al eliminar buzón')
    voicemails.value = voicemails.value.filter(v => v.id !== id)
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
