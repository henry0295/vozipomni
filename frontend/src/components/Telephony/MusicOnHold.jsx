import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { musicOnHoldService } from '../../services/telephonyService'
import './MusicOnHold.css'

const MusicOnHold = () => {
  const [showModal, setShowModal] = useState(false)
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    mode: 'files',
    directory: '',
    application: '',
  })

  const { data: mohClasses = [], isLoading } = useQuery({
    queryKey: ['music-on-hold'],
    queryFn: async () => {
      const response = await musicOnHoldService.getAll()
      return Array.isArray(response.data) ? response.data : []
    },
  })

  const createMutation = useMutation({
    mutationFn: musicOnHoldService.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['music-on-hold'])
      toast.success('Clase MOH creada exitosamente')
      setShowModal(false)
      setFormData({ name: '', description: '', mode: 'files', directory: '', application: '' })
    },
    onError: () => toast.error('Error al crear clase MOH'),
  })

  const deleteMutation = useMutation({
    mutationFn: musicOnHoldService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['music-on-hold'])
      toast.success('Clase MOH eliminada')
    },
    onError: () => toast.error('Error al eliminar clase MOH'),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta clase de música en espera?')) {
      deleteMutation.mutate(id)
    }
  }

  if (isLoading) return <div className="moh-container"><p>Cargando...</p></div>

  return (
    <div className="moh-container">
      <div className="page-header">
        <h1>Música en Espera</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          + Nueva Clase MOH
        </button>
      </div>

      <div className="info-box">
        <p><strong>Información:</strong> La música en espera (MOH) se reproduce cuando una llamada está en espera o en una cola.</p>
        <p>Los archivos de audio deben estar en formato WAV (8kHz, 16-bit, mono) para mejor rendimiento.</p>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Descripción</th>
              <th>Modo</th>
              <th>Archivos</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {mohClasses.length === 0 ? (
              <tr>
                <td colSpan="6" className="no-data">No hay clases de música configuradas</td>
              </tr>
            ) : (
              mohClasses.map((moh) => (
                <tr key={moh.id}>
                  <td><strong>{moh.name}</strong></td>
                  <td>{moh.description}</td>
                  <td>
                    <span className="mode-badge">{moh.mode}</span>
                  </td>
                  <td>{moh.files || 0} archivo{moh.files !== 1 ? 's' : ''}</td>
                  <td>
                    <span className={`status-badge ${moh.status === 'Activo' ? 'active' : 'inactive'}`}>
                      {moh.status}
                    </span>
                  </td>
                  <td>
                    <button className="btn-icon" title="Gestionar archivos">📁</button>
                    <button className="btn-icon" title="Reproducir">▶️</button>
                    <button className="btn-icon" title="Editar">✏️</button>
                    <button className="btn-icon" title="Eliminar" onClick={() => handleDelete(moh.id)}>🗑️</button>
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
              <h2>Nueva Clase de Música en Espera</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-body">
              <div className="form-row">
                <div className="form-group">
                  <label>Nombre de la Clase *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="default"
                    required
                  />
                  <small>Sin espacios, solo letras, números y guiones</small>
                </div>
                <div className="form-group">
                  <label>Descripción *</label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Música Por Defecto"
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Modo</label>
                <select
                  value={formData.mode}
                  onChange={(e) => setFormData({ ...formData, mode: e.target.value })}
                >
                  <option value="files">Archivos (files)</option>
                  <option value="quietmp3">MP3 Silencioso (quietmp3)</option>
                  <option value="custom">Aplicación Personalizada (custom)</option>
                </select>
              </div>

              {formData.mode === 'files' && (
                <div className="form-group">
                  <label>Directorio de Archivos *</label>
                  <input
                    type="text"
                    value={formData.directory}
                    onChange={(e) => setFormData({ ...formData, directory: e.target.value })}
                    placeholder="/var/lib/asterisk/moh/default"
                    required={formData.mode === 'files'}
                  />
                  <small>Ruta absoluta al directorio con los archivos de audio</small>
                </div>
              )}

              {formData.mode === 'custom' && (
                <div className="form-group">
                  <label>Aplicación *</label>
                  <input
                    type="text"
                    value={formData.application}
                    onChange={(e) => setFormData({ ...formData, application: e.target.value })}
                    placeholder="/usr/bin/mpg123 -q -r 8000 -f 8192 --mono -s"
                    required={formData.mode === 'custom'}
                  />
                  <small>Comando de la aplicación que generará el audio</small>
                </div>
              )}

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creando...' : 'Crear Clase MOH'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default MusicOnHold
