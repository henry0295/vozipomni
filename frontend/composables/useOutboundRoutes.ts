import { ref } from 'vue'

interface OutboundRoute {
  id: number
  name: string
  pattern: string
  trunk: string
  prepend: string
  prefix: string
  callerid_prefix: string
  is_active: boolean
}

export const useOutboundRoutes = () => {
  const { apiFetch } = useApi()
  const routes = ref<OutboundRoute[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getOutboundRoutes = async () => {
    loading.value = true
    try {
      const { data, error: fetchError } = await apiFetch<any>('/telephony/outbound-routes/')
      if (fetchError.value) throw new Error('Error al obtener rutas salientes')
      const raw = data.value
      routes.value = Array.isArray(raw) ? raw : (raw?.results || [])
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener rutas salientes'
    } finally {
      loading.value = false
    }
  }

  const createOutboundRoute = async (route: Omit<OutboundRoute, 'id'>) => {
    const { data, error: fetchError } = await apiFetch<any>('/telephony/outbound-routes/', {
      method: 'POST',
      body: route
    })
    if (fetchError.value) throw new Error('Error al crear ruta')
    const created = data.value
    routes.value.push(created)
    return created
  }

  const updateOutboundRoute = async (id: number, route: Partial<OutboundRoute>) => {
    const { data, error: fetchError } = await apiFetch<any>(`/telephony/outbound-routes/${id}/`, {
      method: 'PUT',
      body: route
    })
    if (fetchError.value) throw new Error('Error al actualizar ruta')
    const updated = data.value
    const index = routes.value.findIndex(r => r.id === id)
    if (index > -1) routes.value[index] = updated
    return updated
  }

  const deleteOutboundRoute = async (id: number) => {
    const { error: fetchError } = await apiFetch(`/telephony/outbound-routes/${id}/`, {
      method: 'DELETE'
    })
    if (fetchError.value) throw new Error('Error al eliminar ruta')
    routes.value = routes.value.filter(r => r.id !== id)
  }

  return {
    routes,
    loading,
    error,
    getOutboundRoutes,
    createOutboundRoute,
    updateOutboundRoute,
    deleteOutboundRoute
  }
}
