import React, { useState } from 'react'
import './OutboundRoutes.css'

const OutboundRoutes = () => {
  const [showModal, setShowModal] = useState(false)
  const [routes, setRoutes] = useState([
    { id: 1, name: 'Nacional', pattern: '03XXXXXXXX', trunk: 'Troncal Principal', prepend: '', status: 'Activo' },
    { id: 2, name: 'Celular', pattern: '3XXXXXXXXX', trunk: 'Troncal Celular', prepend: '03', status: 'Activo' },
    { id: 3, name: 'Internacional', pattern: '00XX.', trunk: 'Troncal Internacional', prepend: '', status: 'Inactivo' },
  ])

  const [formData, setFormData] = useState({
    name: '',
    pattern: '',
    trunk: '',
    prepend: '',
    prefix: '',
    calleridPrefix: '',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Creating outbound route:', formData)
    setShowModal(false)
    setFormData({
      name: '',
      pattern: '',
      trunk: '',
      prepend: '',
      prefix: '',
      calleridPrefix: '',
    })
  }

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta ruta?')) {
      setRoutes(routes.filter(r => r.id !== id))
    }
  }

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
                  <td>{route.trunk}</td>
                  <td>{route.prepend || '-'}</td>
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
              <h2>Nueva Ruta Saliente</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
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
                    <option value="trunk1">Troncal Principal</option>
                    <option value="trunk2">Troncal Celular</option>
                    <option value="trunk3">Troncal Internacional</option>
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
                  value={formData.calleridPrefix}
                  onChange={(e) => setFormData({ ...formData, calleridPrefix: e.target.value })}
                  placeholder="3001234567"
                />
                <small>Número que se mostrará como identificador de llamadas salientes</small>
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

export default OutboundRoutes
