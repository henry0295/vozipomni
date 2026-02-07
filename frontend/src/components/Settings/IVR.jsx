import React, { useState } from 'react'
import './IVR.css'

const IVR = () => {
  const [ivrs, setIvrs] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    welcome_message: '',
    timeout: 10,
    max_retries: 3,
    is_active: true,
    options: [
      { digit: '1', action: 'queue', value: '' },
    ]
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Creating IVR:', formData)
    setShowModal(false)
  }

  const addOption = () => {
    setFormData(prev => ({
      ...prev,
      options: [...prev.options, { digit: '', action: 'queue', value: '' }]
    }))
  }

  const removeOption = (index) => {
    setFormData(prev => ({
      ...prev,
      options: prev.options.filter((_, i) => i !== index)
    }))
  }

  const handleOptionChange = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      options: prev.options.map((opt, i) => 
        i === index ? { ...opt, [field]: value } : opt
      )
    }))
  }

  return (
    <div className="ivr-container">
      <div className="page-header">
        <h1>📞 Configuración de IVR</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          ➕ Nuevo IVR
        </button>
      </div>

      <div className="ivr-table">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Descripción</th>
              <th>Mensaje de Bienvenida</th>
              <th>Timeout</th>
              <th>Opciones</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan="7" className="no-data">
                No hay IVRs configurados. Crea uno nuevo para comenzar.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Configurar IVR</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit} className="ivr-form">
              <div className="form-group">
                <label>Nombre del IVR *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="Ej: IVR Principal"
                  required
                />
              </div>

              <div className="form-group">
                <label>Descripción</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  placeholder="Descripción del IVR"
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>Mensaje de Bienvenida *</label>
                <textarea
                  value={formData.welcome_message}
                  onChange={(e) => setFormData({...formData, welcome_message: e.target.value})}
                  placeholder="Ej: Bienvenido a VoziPOmni. Presione 1 para ventas, 2 para soporte..."
                  rows="3"
                  required
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Timeout (segundos)</label>
                  <input
                    type="number"
                    value={formData.timeout}
                    onChange={(e) => setFormData({...formData, timeout: parseInt(e.target.value)})}
                    min="1"
                    max="60"
                  />
                </div>
                <div className="form-group">
                  <label>Máximo Reintentos</label>
                  <input
                    type="number"
                    value={formData.max_retries}
                    onChange={(e) => setFormData({...formData, max_retries: parseInt(e.target.value)})}
                    min="1"
                    max="10"
                  />
                </div>
              </div>

              <div className="options-section">
                <div className="options-header">
                  <h3>Opciones del IVR</h3>
                  <button type="button" className="btn-secondary" onClick={addOption}>
                    ➕ Agregar Opción
                  </button>
                </div>

                {formData.options.map((option, index) => (
                  <div key={index} className="option-row">
                    <div className="form-group">
                      <label>Dígito</label>
                      <input
                        type="text"
                        value={option.digit}
                        onChange={(e) => handleOptionChange(index, 'digit', e.target.value)}
                        maxLength="1"
                        placeholder="1-9"
                      />
                    </div>
                    <div className="form-group">
                      <label>Acción</label>
                      <select
                        value={option.action}
                        onChange={(e) => handleOptionChange(index, 'action', e.target.value)}
                      >
                        <option value="queue">Cola</option>
                        <option value="extension">Extensión</option>
                        <option value="voicemail">Buzón de Voz</option>
                        <option value="hangup">Colgar</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Valor</label>
                      <input
                        type="text"
                        value={option.value}
                        onChange={(e) => handleOptionChange(index, 'value', e.target.value)}
                        placeholder="Nombre de cola o extensión"
                      />
                    </div>
                    <button
                      type="button"
                      className="btn-remove"
                      onClick={() => removeOption(index)}
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Guardar IVR
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default IVR
