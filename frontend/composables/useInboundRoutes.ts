import { ref } from 'vue'
import { useApi } from './useApi'

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
  const { get, post, put, delete: del } = useApi()
  const routes = ref<InboundRoute[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getInboundRoutes = async () => {
    loading.value = true
    try {
      const data = await get('/api/inbound-routes/')
      routes.value = data
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener rutas entrantes'
    } finally {
      loading.value = false
    }
  }

  const createInboundRoute = async (route: Omit<InboundRoute, 'id'>) => {
    try {
      const data = await post('/api/inbound-routes/', route)
      routes.value.push(data)
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al crear ruta')
    }
  }

  const updateInboundRoute = async (id: number, route: Partial<InboundRoute>) => {
    try {
      const data = await put(`/api/inbound-routes/${id}/`, route)
      const index = routes.value.findIndex(r => r.id === id)
      if (index > -1) {
        routes.value[index] = data
      }
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al actualizar ruta')
    }
  }

  const deleteInboundRoute = async (id: number) => {
    try {
      await del(`/api/inbound-routes/${id}/`)
      routes.value = routes.value.filter(r => r.id !== id)
    } catch (err: any) {
      throw new Error(err.message || 'Error al eliminar ruta')
    }
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
