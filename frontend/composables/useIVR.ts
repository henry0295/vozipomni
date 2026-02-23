import { ref } from 'vue'

interface IVR {
  id: number
  name: string
  extension: string
  welcome_message: string
  invalid_message: string
  timeout_message: string
  timeout: number
  max_attempts: number
  menu_options: Record<string, string>
  is_active: boolean
}

export const useIVR = () => {
  const { apiFetch } = useApi()
  const ivrs = ref<IVR[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getIVRs = async () => {
    loading.value = true
    try {
      const { data, error: fetchError } = await apiFetch<any>('/telephony/ivr/')
      if (fetchError.value) throw new Error('Error al obtener IVRs')
      const raw = data.value
      ivrs.value = Array.isArray(raw) ? raw : (raw?.results || [])
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener IVRs'
    } finally {
      loading.value = false
    }
  }

  const createIVR = async (ivr: Omit<IVR, 'id'>) => {
    const { data, error: fetchError } = await apiFetch<any>('/telephony/ivr/', {
      method: 'POST',
      body: ivr
    })
    if (fetchError.value) throw new Error('Error al crear IVR')
    const created = data.value
    ivrs.value.push(created)
    return created
  }

  const updateIVR = async (id: number, ivr: Partial<IVR>) => {
    const { data, error: fetchError } = await apiFetch<any>(`/telephony/ivr/${id}/`, {
      method: 'PUT',
      body: ivr
    })
    if (fetchError.value) throw new Error('Error al actualizar IVR')
    const updated = data.value
    const index = ivrs.value.findIndex(i => i.id === id)
    if (index > -1) ivrs.value[index] = updated
    return updated
  }

  const deleteIVR = async (id: number) => {
    const { error: fetchError } = await apiFetch(`/telephony/ivr/${id}/`, {
      method: 'DELETE'
    })
    if (fetchError.value) throw new Error('Error al eliminar IVR')
    ivrs.value = ivrs.value.filter(i => i.id !== id)
  }

  return {
    ivrs,
    loading,
    error,
    getIVRs,
    createIVR,
    updateIVR,
    deleteIVR
  }
}
