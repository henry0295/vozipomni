import React, { useState } from 'react'
import './Trunks.css'

const Trunks = () => {
  const [trunks, setTrunks] = useState([])
  const [showModal, setShowModal] = useState(false)
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

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Creating Trunk:', formData)
    setShowModal(false)
  }

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
            <tr>
              <td colSpan="8" className="no-data">
                No hay troncales SIP configuradas. Crea una nueva para comenzar.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Configurar Troncal SIP</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>✕</button>
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
                  <label>Contraseña *</label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                    required
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
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Guardar Troncal
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
