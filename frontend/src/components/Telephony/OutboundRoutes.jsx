import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { outboundRoutesService, trunksService } from '../../services/telephonyService'
import './OutboundRoutes.css'

const OutboundRoutes = () => {
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState({
    name: '',
    pattern: '',
    trunk: '',
    prepend: '',
    prefix: '',
    callerid_prefix: '',
  })

  const { data: routes = [], isLoading } = useQuery({
    queryKey: ['outbound-routes'],
    queryFn: async () => {
      const response = await outboundRoutesService.getAll()
      const data = response.data?.results || response.data
      return Array.isArray(data) ? data : []
    },
  })

  const { data: trunks = [] } = useQuery({
    queryKey: ['trunks'],
    queryFn: async () => {
      const response = await trunksService.getAll()
      const data = response.data?.results || response.data
      return Array.isArray(data) ? data : []
    },
  })

  const createMutation = useMutation({
    mutationFn: outboundRoutesService.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['outbound-routes'])
      toast.success('Ruta creada exitosamente')
      resetForm()
    },
    onError: () => toast.error('Error al crear ruta'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => outboundRoutesService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['outbound-routes'])
      toast.success('Ruta actualizada exitosamente')
      resetForm()
    },
    onError: () => toast.error('Error al actualizar ruta'),
  })

  const deleteMutation = useMutation({
    mutationFn: outboundRoutesService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['outbound-routes'])
      toast.success('Ruta eliminada')
    },
    onError: () => toast.error('Error al eliminar ruta'),
  })

  const resetForm = () => {
    setShowModal(false)
    setEditingId(null)
    setFormData({ name: '', pattern: '', trunk: '', prepend: '', prefix: '', callerid_prefix: '' })
  }

  const handleEdit = (route) => {
    setEditingId(route.id)
    setFormData({
      name: route.name,
      pattern: route.pattern,
      trunk: route.trunk,
      prepend: route.prepend || '',
      prefix: route.prefix || '',
      callerid_prefix: route.callerid_prefix || '',
    })
    setShowModal(true)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta ruta?')) {
      deleteMutation.mutate(id)
    }
  }

  if (isLoading) return <div className="outbound-routes-container"><p>Cargando...</p></div>

  return (
    <div className="outbound-routes-container">
      <div className="page-header">
        <h1>Rutas Salientes</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          + Nueva Ruta
        </button>
      </div>

      <div className="info-box">
        <p><strong>Patrones de marcación:</strong></p>
        <ul>
          <li><code>X</code> - Cualquier dígito (0-9)</li>
          <li><code>N</code> - Dígito 2-9</li>
          <li><code>Z</code> - Dígito 1-9</li>
          <li><code>.</code> - Uno o más caracteres</li>
          <li><code>!</code> - Cero o más caracteres</li>
        </ul>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Patrón</th>
              <th>Troncal</th>
              <th>Prefijo</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {routes.length === 0 ? (
              <tr>
                <td colSpan="6" className="no-data">No hay rutas salientes configuradas</td>
              </tr>
            ) : (
              routes.map((route) => (
                <tr key={route.id}>
                  <td><strong>{route.name}</strong></td>
                  <td><code>{route.pattern}</code></td>
                  <td>{route.trunk_name}</td>
                  <td>{route.prepend || '-'}</td>
                  <td>
                    <span className={`status-badge ${route.status === 'Activo' ? 'active' : 'inactive'}`}>
                      {route.status}
                    </span>
                  </td>
                  <td>
                    <button className="btn-icon" title="Editar" onClick={() => handleEdit(route)}>✏️</button>
                    <button className="btn-icon" title="Eliminar" onClick={() => handleDelete(route.id)}>🗑️</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={resetForm}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingId ? 'Editar' : 'Nueva'} Ruta Saliente</h2>
              <button className="close-btn" onClick={resetForm}>×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-body">
              <div className="form-group">
                <label>Nombre de la Ruta *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Nacional, Internacional, Celular, etc."
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Patrón de Marcación *</label>
                  <input
                    type="text"
                    value={formData.pattern}
                    onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
                    placeholder="3XXXXXXXXX"
                    required
                  />
                  <small>Ej: 3XXXXXXXXX (celulares), 03XXXXXXXX (fijos)</small>
                </div>
                <div className="form-group">
                  <label>Troncal *</label>
                  <select
                    value={formData.trunk}
                    onChange={(e) => setFormData({ ...formData, trunk: e.target.value })}
                    required
                  >
                    <option value="">Seleccione una troncal</option>
                    {trunks.map(trunk => (
                      <option key={trunk.id} value={trunk.id}>{trunk.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Prefijo a Agregar</label>
                  <input
                    type="text"
                    value={formData.prepend}
                    onChange={(e) => setFormData({ ...formData, prepend: e.target.value })}
                    placeholder="03"
                  />
                  <small>Se agrega antes del número marcado</small>
                </div>
                <div className="form-group">
                  <label>Dígitos a Eliminar</label>
                  <input
                    type="text"
                    value={formData.prefix}
                    onChange={(e) => setFormData({ ...formData, prefix: e.target.value })}
                    placeholder="9"
                  />
                  <small>Cantidad de dígitos iniciales a eliminar</small>
                </div>
              </div>

              <div className="form-group">
                <label>Prefijo de Caller ID</label>
                <input
                  type="text"
                  value={formData.callerid_prefix}
                  onChange={(e) => setFormData({ ...formData, callerid_prefix: e.target.value })}
                  placeholder="3001234567"
                />
                <small>Número que se mostrará como identificador de llamadas salientes</small>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                  {editingId 
                    ? (updateMutation.isPending ? 'Actualizando...' : 'Actualizar Ruta')
                    : (createMutation.isPending ? 'Creando...' : 'Crear Ruta')
                  }
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default OutboundRoutes
