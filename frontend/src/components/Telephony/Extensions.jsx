import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { extensionsService } from '../../services/telephonyService'
import './Extensions.css'

const Extensions = () => {
  const [showModal, setShowModal] = useState(false)
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState({
    extension: '',
    name: '',
    extension_type: 'SIP',
    secret: '',
    context: 'from-internal',
    callerid: '',
    email: '',
    voicemail_enabled: false,
  })

  // Query para obtener extensiones
  const { data: extensions = [], isLoading, error } = useQuery({
    queryKey: ['extensions'],
    queryFn: async () => {
      const response = await extensionsService.getAll()
      return response.data
    },
  })

  // Mutation para crear extensión
  const createMutation = useMutation({
    mutationFn: extensionsService.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['extensions'])
      toast.success('Extensión creada exitosamente')
      setShowModal(false)
      setFormData({
        extension: '',
        name: '',
        extension_type: 'SIP',
        secret: '',
        context: 'from-internal',
        callerid: '',
        email: '',
        voicemail_enabled: false,
      })
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Error al crear extensión')
    },
  })

  // Mutation para eliminar extensión
  const deleteMutation = useMutation({
    mutationFn: extensionsService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['extensions'])
      toast.success('Extensión eliminada')
    },
    onError: () => {
      toast.error('Error al eliminar extensión')
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta extensión?')) {
      deleteMutation.mutate(id)
    }
  }

  if (isLoading) return <div className="extensions-container"><p>Cargando...</p></div>
  if (error) return <div className="extensions-container"><p>Error al cargar extensiones</p></div>

  return (
    <div className="extensions-container">
      <div className="page-header">
        <h1>Extensiones</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          + Nueva Extensión
        </button>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Extensión</th>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Contexto</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {extensions.length === 0 ? (
              <tr>
                <td colSpan="6" className="no-data">No hay extensiones configuradas</td>
              </tr>
            ) : (
              extensions.map((ext) => (
                <tr key={ext.id}>
                  <td><strong>{ext.extension}</strong></td>
                  <td>{ext.name}</td>
                  <td>{ext.extension_type}</td>
                  <td>{ext.context}</td>
                  <td>
                    <span className={`status-badge ${ext.status === 'Activo' ? 'active' : 'inactive'}`}>
                      {ext.status}
                    </span>
                  </td>
                  <td>
                    <button className="btn-icon" title="Editar">✏️</button>
                    <button className="btn-icon" title="Eliminar" onClick={() => handleDelete(ext.id)}>🗑️</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Nueva Extensión</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-body">
              <div className="form-row">
                <div className="form-group">
                  <label>Extensión *</label>
                  <input
                    type="text"
                    value={formData.extension}
                    onChange={(e) => setFormData({ ...formData, extension: e.target.value })}
                    placeholder="1001"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Nombre *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Juan Pérez"
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Tipo</label>
                  <select
                    value={formData.extension_type}
                    onChange={(e) => setFormData({ ...formData, extension_type: e.target.value })}
                  >
                    <option value="SIP">SIP</option>
                    <option value="IAX2">IAX2</option>
                    <option value="PJSIP">PJSIP</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Contraseña *</label>
                  <input
                    type="password"
                    value={formData.secret}
                    onChange={(e) => setFormData({ ...formData, secret: e.target.value })}
                    placeholder="********"
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Contexto</label>
                  <select
                    value={formData.context}
                    onChange={(e) => setFormData({ ...formData, context: e.target.value })}
                  >
                    <option value="from-internal">from-internal</option>
                    <option value="from-external">from-external</option>
                    <option value="custom">custom</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Caller ID</label>
                  <input
                    type="text"
                    value={formData.callerid}
                    onChange={(e) => setFormData({ ...formData, callerid: e.target.value })}
                    placeholder='"Juan Pérez" <1001>'
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Email (para notificaciones de buzón)</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="usuario@ejemplo.com"
                />
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.voicemail_enabled}
                    onChange={(e) => setFormData({ ...formData, voicemail_enabled: e.target.checked })}
                  />
                  <span>Habilitar buzón de voz</span>
                </label>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creando...' : 'Crear Extensión'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Extensions
