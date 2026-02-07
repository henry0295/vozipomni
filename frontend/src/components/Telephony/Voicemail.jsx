import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { voicemailService } from '../../services/telephonyService'
import './Voicemail.css'

const Voicemail = () => {
  const [showModal, setShowModal] = useState(false)
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState({
    mailbox: '',
    name: '',
    email: '',
    password: '',
    email_attach: true,
    email_delete: false,
    max_messages: 100,
  })

  const { data: voicemails = [], isLoading } = useQuery({
    queryKey: ['voicemail'],
    queryFn: async () => {
      const response = await voicemailService.getAll()
      const data = response.data?.results || response.data
      return Array.isArray(data) ? data : []
    },
  })

  const createMutation = useMutation({
    mutationFn: voicemailService.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['voicemail'])
      toast.success('Buzón creado exitosamente')
      setShowModal(false)
      setFormData({ mailbox: '', name: '', email: '', password: '', email_attach: true, email_delete: false, max_messages: 100 })
    },
    onError: () => toast.error('Error al crear buzón'),
  })

  const deleteMutation = useMutation({
    mutationFn: voicemailService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['voicemail'])
      toast.success('Buzón eliminado')
    },
    onError: () => toast.error('Error al eliminar buzón'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar este buzón de voz?')) {
      deleteMutation.mutate(id)
    }
  }

  if (isLoading) return <div className="voicemail-container"><p>Cargando...</p></div>

  return (
    <div className="voicemail-container">
      <div className="page-header">
        <h1>Buzones de Voz</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          + Nuevo Buzón
        </button>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Buzón</th>
              <th>Nombre</th>
              <th>Email</th>
              <th>Mensajes</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {voicemails.length === 0 ? (
              <tr>
                <td colSpan="6" className="no-data">No hay buzones de voz configurados</td>
              </tr>
            ) : (
              voicemails.map((vm) => (
                <tr key={vm.id}>
                  <td><strong>{vm.mailbox}</strong></td>
                  <td>{vm.name}</td>
                  <td>{vm.email}</td>
                  <td>
                    <span className={`message-badge ${vm.messages > 0 ? 'has-messages' : ''}`}>
                      {vm.messages || 0} mensaje{vm.messages !== 1 ? 's' : ''}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${vm.status === 'Activo' ? 'active' : 'inactive'}`}>
                      {vm.status}
                    </span>
                  </td>
                  <td>
                    <button className="btn-icon" title="Escuchar mensajes">📧</button>
                    <button className="btn-icon" title="Editar">✏️</button>
                    <button className="btn-icon" title="Eliminar" onClick={() => handleDelete(vm.id)}>🗑️</button>
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
              <h2>Nuevo Buzón de Voz</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-body">
              <div className="form-row">
                <div className="form-group">
                  <label>Número de Buzón *</label>
                  <input
                    type="text"
                    value={formData.mailbox}
                    onChange={(e) => setFormData({ ...formData, mailbox: e.target.value })}
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
                  <label>Email *</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="usuario@empresa.com"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Contraseña *</label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    placeholder="****"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Máximo de Mensajes</label>
                <input
                  type="number"
                  value={formData.max_messages}
                  onChange={(e) => setFormData({ ...formData, max_messages: e.target.value })}
                  min="1"
                  max="999"
                />
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.email_attach}
                    onChange={(e) => setFormData({ ...formData, email_attach: e.target.checked })}
                  />
                  <span>Adjuntar audio del mensaje al email</span>
                </label>
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.email_delete}
                    onChange={(e) => setFormData({ ...formData, email_delete: e.target.checked })}
                  />
                  <span>Eliminar mensaje después de enviarlo por email</span>
                </label>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creando...' : 'Crear Buzón'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Voicemail
