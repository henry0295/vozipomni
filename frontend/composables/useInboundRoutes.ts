import { ref } from 'vue'

interface InboundRoute {
  id: number
  did: string
  description: string
  destination_type: string
  destination: string
  priority: number
  time_condition?: string
  is_active: boolean
}

export const useInboundRoutes = () => {
  const { apiFetch } = useApi()
  const routes = ref<InboundRoute[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getInboundRoutes = async () => {
    loading.value = true
    try {
      const { data, error: fetchError } = await apiFetch<any>('/telephony/inbound-routes/')
      if (fetchError.value) throw new Error('Error al obtener rutas entrantes')
      const raw = data.value
      routes.value = Array.isArray(raw) ? raw : (raw?.results || [])
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener rutas entrantes'
    } finally {
      loading.value = false
    }
  }

  const createInboundRoute = async (route: Omit<InboundRoute, 'id'>) => {
    const { data, error: fetchError } = await apiFetch<any>('/telephony/inbound-routes/', {
      method: 'POST',
      body: route
    })
    if (fetchError.value) throw new Error('Error al crear ruta')
    const created = data.value
    routes.value.push(created)
    return created
  }

  const updateInboundRoute = async (id: number, route: Partial<InboundRoute>) => {
    const { data, error: fetchError } = await apiFetch<any>(`/telephony/inbound-routes/${id}/`, {
      method: 'PUT',
      body: route
    })
    if (fetchError.value) throw new Error('Error al actualizar ruta')
    const updated = data.value
    const index = routes.value.findIndex(r => r.id === id)
    if (index > -1) routes.value[index] = updated
    return updated
  }

  const deleteInboundRoute = async (id: number) => {
    const { error: fetchError } = await apiFetch(`/telephony/inbound-routes/${id}/`, {
      method: 'DELETE'
    })
    if (fetchError.value) throw new Error('Error al eliminar ruta')
    routes.value = routes.value.filter(r => r.id !== id)
  }

  return {
    routes,
    loading,
    error,
    getInboundRoutes,
    createInboundRoute,
    updateInboundRoute,
    deleteInboundRoute
  }
}
