import { ref } from 'vue'

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
  const { apiFetch } = useApi()
  const conditions = ref<TimeCondition[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getTimeConditions = async () => {
    loading.value = true
    try {
      const { data, error: fetchError } = await apiFetch<any>('/telephony/time-conditions/')
      if (fetchError.value) throw new Error('Error al obtener condiciones de horario')
      const raw = data.value
      conditions.value = Array.isArray(raw) ? raw : (raw?.results || [])
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener condiciones de horario'
    } finally {
      loading.value = false
    }
  }

  const createTimeCondition = async (condition: Omit<TimeCondition, 'id'>) => {
    const { data, error: fetchError } = await apiFetch<any>('/telephony/time-conditions/', {
      method: 'POST',
      body: condition
    })
    if (fetchError.value) throw new Error('Error al crear condición')
    const created = data.value
    conditions.value.push(created)
    return created
  }

  const updateTimeCondition = async (id: number, condition: Partial<TimeCondition>) => {
    const { data, error: fetchError } = await apiFetch<any>(`/telephony/time-conditions/${id}/`, {
      method: 'PUT',
      body: condition
    })
    if (fetchError.value) throw new Error('Error al actualizar condición')
    const updated = data.value
    const index = conditions.value.findIndex(c => c.id === id)
    if (index > -1) conditions.value[index] = updated
    return updated
  }

  const deleteTimeCondition = async (id: number) => {
    const { error: fetchError } = await apiFetch(`/telephony/time-conditions/${id}/`, {
      method: 'DELETE'
    })
    if (fetchError.value) throw new Error('Error al eliminar condición')
    conditions.value = conditions.value.filter(c => c.id !== id)
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
