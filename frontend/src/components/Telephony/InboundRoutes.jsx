import React, { useState } from 'react'
import './InboundRoutes.css'

const InboundRoutes = () => {
  const [showModal, setShowModal] = useState(false)
  const [routes, setRoutes] = useState([
    { id: 1, did: '3001234567', description: 'Línea Principal', destination: 'IVR Principal', priority: 1, status: 'Activo' },
    { id: 2, did: '3007654321', description: 'Soporte Técnico', destination: 'Cola Soporte', priority: 2, status: 'Activo' },
    { id: 3, did: '3009876543', description: 'Ventas', destination: 'Cola Ventas', priority: 3, status: 'Inactivo' },
  ])

  const [formData, setFormData] = useState({
    did: '',
    description: '',
    destinationType: 'ivr',
    destination: '',
    priority: 1,
    timeCondition: '',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Creating inbound route:', formData)
    setShowModal(false)
    setFormData({
      did: '',
      description: '',
      destinationType: 'ivr',
      destination: '',
      priority: 1,
      timeCondition: '',
    })
  }

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta ruta?')) {
      setRoutes(routes.filter(r => r.id !== id))
    }
  }

  return (
    <div className="inbound-routes-container">
      <div className="page-header">
        <h1>Rutas Entrantes</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          + Nueva Ruta
        </button>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>DID / Número</th>
              <th>Descripción</th>
              <th>Destino</th>
              <th>Prioridad</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {routes.length === 0 ? (
              <tr>
                <td colSpan="6" className="no-data">No hay rutas entrantes configuradas</td>
              </tr>
            ) : (
              routes.map((route) => (
                <tr key={route.id}>
                  <td><strong>{route.did}</strong></td>
                  <td>{route.description}</td>
                  <td>{route.destination}</td>
                  <td>{route.priority}</td>
                  <td>
                    <span className={`status-badge ${route.status === 'Activo' ? 'active' : 'inactive'}`}>
                      {route.status}
                    </span>
                  </td>
                  <td>
                    <button className="btn-icon" title="Editar">✏️</button>
                    <button className="btn-icon" title="Eliminar" onClick={() => handleDelete(route.id)}>🗑️</button>
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
              <h2>Nueva Ruta Entrante</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-body">
              <div className="form-row">
                <div className="form-group">
                  <label>DID / Número Entrante *</label>
                  <input
                    type="text"
                    value={formData.did}
                    onChange={(e) => setFormData({ ...formData, did: e.target.value })}
                    placeholder="3001234567"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Descripción *</label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Línea Principal"
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Tipo de Destino</label>
                  <select
                    value={formData.destinationType}
                    onChange={(e) => setFormData({ ...formData, destinationType: e.target.value })}
                  >
                    <option value="ivr">IVR</option>
                    <option value="queue">Cola</option>
                    <option value="extension">Extensión</option>
                    <option value="voicemail">Buzón de Voz</option>
                    <option value="announcement">Anuncio</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Destino *</label>
                  <input
                    type="text"
                    value={formData.destination}
                    onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
                    placeholder="Seleccione o ingrese destino"
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Prioridad</label>
                  <input
                    type="number"
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                    min="1"
                    max="99"
                  />
                </div>
                <div className="form-group">
                  <label>Condición de Horario</label>
                  <select
                    value={formData.timeCondition}
                    onChange={(e) => setFormData({ ...formData, timeCondition: e.target.value })}
                  >
                    <option value="">Sin condición</option>
                    <option value="horario_oficina">Horario de Oficina</option>
                    <option value="fin_semana">Fin de Semana</option>
                    <option value="festivos">Festivos</option>
                  </select>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Crear Ruta
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default InboundRoutes
