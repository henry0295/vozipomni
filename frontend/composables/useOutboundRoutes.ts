import { ref } from 'vue'
import { useApi } from './useApi'

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
  const { get, post, put, delete: del } = useApi()
  const routes = ref<OutboundRoute[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const getOutboundRoutes = async () => {
    loading.value = true
    try {
      const data = await get('/api/outbound-routes/')
      routes.value = data
      error.value = null
    } catch (err: any) {
      error.value = err.message || 'Error al obtener rutas salientes'
    } finally {
      loading.value = false
    }
  }

  const createOutboundRoute = async (route: Omit<OutboundRoute, 'id'>) => {
    try {
      const data = await post('/api/outbound-routes/', route)
      routes.value.push(data)
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al crear ruta')
    }
  }

  const updateOutboundRoute = async (id: number, route: Partial<OutboundRoute>) => {
    try {
      const data = await put(`/api/outbound-routes/${id}/`, route)
      const index = routes.value.findIndex(r => r.id === id)
      if (index > -1) {
        routes.value[index] = data
      }
      return data
    } catch (err: any) {
      throw new Error(err.message || 'Error al actualizar ruta')
    }
  }

  const deleteOutboundRoute = async (id: number) => {
    try {
      await del(`/api/outbound-routes/${id}/`)
      routes.value = routes.value.filter(r => r.id !== id)
    } catch (err: any) {
      throw new Error(err.message || 'Error al eliminar ruta')
    }
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
