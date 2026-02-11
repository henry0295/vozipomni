import { ref } from 'vue'
import { useApi } from './useApi'

interface TimeGroup {
  name: string
  days: string
  start_time: string
  end_time: string
}

interface TimeCondition {
  id: number
  name: string
  time_groups: TimeGroup[]
  true_destination_type: string
  true_destination: string
  false_destination_type: string
  false_destination: string
  is_active: boolean
}

export const useTimeConditions = () => {
  const { get, post, put, delete: del } = useApi()
  const conditions = ref<TimeCondition[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getTimeConditions = async () => {
    loading.value = true
    try {
      const data = await get('/api/time-conditions/')
      conditions.value = data
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener condiciones de horario'
    } finally {
      loading.value = false
    }
  }

  const createTimeCondition = async (condition: Omit<TimeCondition, 'id'>) => {
    try {
      const data = await post('/api/time-conditions/', condition)
      conditions.value.push(data)
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al crear condición')
    }
  }

  const updateTimeCondition = async (id: number, condition: Partial<TimeCondition>) => {
    try {
      const data = await put(`/api/time-conditions/${id}/`, condition)
      const index = conditions.value.findIndex(c => c.id === id)
      if (index > -1) {
        conditions.value[index] = data
      }
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al actualizar condición')
    }
  }

  const deleteTimeCondition = async (id: number) => {
    try {
      await del(`/api/time-conditions/${id}/`)
      conditions.value = conditions.value.filter(c => c.id !== id)
    } catch (err: any) {
      throw new Error(err.message || 'Error al eliminar condición')
    }
  }

  return {
    conditions,
    loading,
    error,
    getTimeConditions,
    createTimeCondition,
    updateTimeCondition,
    deleteTimeCondition
  }
}
