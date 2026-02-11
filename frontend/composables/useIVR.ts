import { ref } from 'vue'
import { useApi } from './useApi'

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
  const { get, post, put, delete: del } = useApi()
  const ivrs = ref<IVR[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getIVRs = async () => {
    loading.value = true
    try {
      const data = await get('/api/ivr/')
      ivrs.value = data
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener IVRs'
    } finally {
      loading.value = false
    }
  }

  const createIVR = async (ivr: Omit<IVR, 'id'>) => {
    try {
      const data = await post('/api/ivr/', ivr)
      ivrs.value.push(data)
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al crear IVR')
    }
  }

  const updateIVR = async (id: number, ivr: Partial<IVR>) => {
    try {
      const data = await put(`/api/ivr/${id}/`, ivr)
      const index = ivrs.value.findIndex(i => i.id === id)
      if (index > -1) {
        ivrs.value[index] = data
      }
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al actualizar IVR')
    }
  }

  const deleteIVR = async (id: number) => {
    try {
      await del(`/api/ivr/${id}/`)
      ivrs.value = ivrs.value.filter(i => i.id !== id)
    } catch (err: any) {
      throw new Error(err.message || 'Error al eliminar IVR')
    }
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
