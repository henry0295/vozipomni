import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { trunksService } from '../../services/telephonyService'
import './Trunks.css'

const Trunks = () => {
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState({
    name: '',
    host: '',
    port: 5060,
    username: '',
    password: '',
    protocol: 'udp',
    max_channels: 10,
    codec: 'ulaw,alaw,g729',
    is_active: true
  })

  const { data: trunks = [], isLoading } = useQuery({
    queryKey: ['trunks'],
    queryFn: async () => {
      const response = await trunksService.getAll()
      const data = response.data?.results || response.data
      return Array.isArray(data) ? data : []
    },
  })

  const createMutation = useMutation({
    mutationFn: trunksService.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['trunks'])
      toast.success('Troncal creada exitosamente')
      resetForm()
    },
    onError: () => toast.error('Error al crear troncal'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => trunksService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['trunks'])
      toast.success('Troncal actualizada exitosamente')
      resetForm()
    },
    onError: () => toast.error('Error al actualizar troncal'),
  })

  const deleteMutation = useMutation({
    mutationFn: trunksService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['trunks'])
      toast.success('Troncal eliminada')
    },
    onError: () => toast.error('Error al eliminar troncal'),
  })

  const resetForm = () => {
    setShowModal(false)
    setEditingId(null)
    setFormData({
      name: '',
      host: '',
      port: 5060,
      username: '',
      password: '',
      protocol: 'udp',
      max_channels: 10,
      codec: 'ulaw,alaw,g729',
      is_active: true
    })
  }

  const handleEdit = (trunk) => {
    setEditingId(trunk.id)
    setFormData({
      name: trunk.name,
      host: trunk.host,
      port: trunk.port,
      username: trunk.username,
      password: '',
      protocol: trunk.protocol,
      max_channels: trunk.max_channels,
      codec: trunk.codec,
      is_active: trunk.is_active
    })
    setShowModal(true)
  }

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta troncal?')) {
      deleteMutation.mutate(id)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (editingId) {
      const updateData = { ...formData }
      if (!updateData.password) {
        delete updateData.password
      }
      updateMutation.mutate({ id: editingId, data: updateData })
    } else {
      createMutation.mutate(formData)
    }
  }

  if (isLoading) return <div className="trunks-container"><p>Cargando...</p></div>

  if (isLoading) return <div className="trunks-container"><p>Cargando...</p></div>

  return (
    <div className="trunks-container">
      <div className="page-header">
        <h1>🌐 Troncales SIP</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          ➕ Nueva Troncal
        </button>
      </div>

      <div className="trunks-table">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Host</th>
              <th>Puerto</th>
              <th>Usuario</th>
              <th>Protocolo</th>
              <th>Canales Máx.</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {trunks.length === 0 ? (
              <tr>
                <td colSpan="8" className="no-data">
                  No hay troncales SIP configuradas. Crea una nueva para comenzar.
                </td>
              </tr>
            ) : (
              trunks.map((trunk) => (
                <tr key={trunk.id}>
                  <td><strong>{trunk.name}</strong></td>
                  <td>{trunk.host}</td>
                  <td>{trunk.port}</td>
                  <td>{trunk.username}</td>
                  <td>{trunk.protocol?.toUpperCase()}</td>
                  <td>{trunk.max_channels}</td>
                  <td>
                    <span className={`status-badge ${trunk.is_active ? 'active' : 'inactive'}`}>
                      {trunk.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td>
                    <button className="btn-icon" title="Editar" onClick={() => handleEdit(trunk)}>✏️</button>
                    <button className="btn-icon" title="Eliminar" onClick={() => handleDelete(trunk.id)}>🗑️</button>
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
              <h2>{editingId ? 'Editar' : 'Nueva'} Troncal SIP</h2>
              <button className="close-btn" onClick={resetForm}>✕</button>
            </div>
            <form onSubmit={handleSubmit} className="trunk-form">
              <div className="form-group">
                <label>Nombre de la Troncal *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="Ej: Proveedor Principal"
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Host/IP *</label>
                  <input
                    type="text"
                    value={formData.host}
                    onChange={(e) => setFormData({...formData, host: e.target.value})}
                    placeholder="sip.provider.com"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Puerto</label>
                  <input
                    type="number"
                    value={formData.port}
                    onChange={(e) => setFormData({...formData, port: parseInt(e.target.value)})}
                    min="1"
                    max="65535"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Usuario *</label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({...formData, username: e.target.value})}
                    placeholder="Usuario SIP"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Contraseña {!editingId && '*'}</label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    placeholder={editingId ? "Dejar vacío para mantener" : "********"}
                    required={!editingId}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Protocolo</label>
                  <select
                    value={formData.protocol}
                    onChange={(e) => setFormData({...formData, protocol: e.target.value})}
                  >
                    <option value="udp">UDP</option>
                    <option value="tcp">TCP</option>
                    <option value="tls">TLS</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Canales Máximo</label>
                  <input
                    type="number"
                    value={formData.max_channels}
                    onChange={(e) => setFormData({...formData, max_channels: parseInt(e.target.value)})}
                    min="1"
                    max="100"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Códecs (separados por coma)</label>
                <input
                  type="text"
                  value={formData.codec}
                  onChange={(e) => setFormData({...formData, codec: e.target.value})}
                  placeholder="ulaw,alaw,g729"
                />
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                  />
                  Troncal Activa
                </label>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                  {editingId 
                    ? (updateMutation.isPending ? 'Actualizando...' : 'Actualizar Troncal')
                    : (createMutation.isPending ? 'Creando...' : 'Guardar Troncal')
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

export default Trunks
