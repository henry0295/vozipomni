import React, { useState } from 'react'
import './TimeConditions.css'

const TimeConditions = () => {
  const [showModal, setShowModal] = useState(false)
  const [conditions, setConditions] = useState([
    { 
      id: 1, 
      name: 'Horario de Oficina', 
      times: 'Lun-Vie 08:00-18:00',
      trueDestination: 'IVR Principal',
      falseDestination: 'Buzón General',
      status: 'Activo' 
    },
    { 
      id: 2, 
      name: 'Fin de Semana', 
      times: 'Sáb-Dom 00:00-23:59',
      trueDestination: 'Anuncio Cerrado',
      falseDestination: 'IVR Principal',
      status: 'Activo' 
    },
    { 
      id: 3, 
      name: 'Festivos', 
      times: 'Días festivos',
      trueDestination: 'Anuncio Festivo',
      falseDestination: 'IVR Principal',
      status: 'Inactivo' 
    },
  ])

  const [formData, setFormData] = useState({
    name: '',
    timeGroups: [{ days: [], startTime: '09:00', endTime: '18:00' }],
    trueDestinationType: 'ivr',
    trueDestination: '',
    falseDestinationType: 'voicemail',
    falseDestination: '',
  })

  const addTimeGroup = () => {
    setFormData({
      ...formData,
      timeGroups: [...formData.timeGroups, { days: [], startTime: '09:00', endTime: '18:00' }]
    })
  }

  const removeTimeGroup = (index) => {
    const newGroups = formData.timeGroups.filter((_, i) => i !== index)
    setFormData({ ...formData, timeGroups: newGroups })
  }

  const updateTimeGroup = (index, field, value) => {
    const newGroups = [...formData.timeGroups]
    newGroups[index][field] = value
    setFormData({ ...formData, timeGroups: newGroups })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Creating time condition:', formData)
    setShowModal(false)
    setFormData({
      name: '',
      timeGroups: [{ days: [], startTime: '09:00', endTime: '18:00' }],
      trueDestinationType: 'ivr',
      trueDestination: '',
      falseDestinationType: 'voicemail',
      falseDestination: '',
    })
  }

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta condición de horario?')) {
      setConditions(conditions.filter(c => c.id !== id))
    }
  }

  return (
    <div className="time-conditions-container">
      <div className="page-header">
        <h1>Condiciones de Horario</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          + Nueva Condición
        </button>
      </div>

      <div className="info-box">
        <p><strong>Condiciones de Horario:</strong> Permite enrutar llamadas de manera diferente según la hora, día de la semana o fechas específicas.</p>
      </div>

      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Horario</th>
              <th>Si Cumple → Destino</th>
              <th>Si No Cumple → Destino</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {conditions.length === 0 ? (
              <tr>
                <td colSpan="6" className="no-data">No hay condiciones de horario configuradas</td>
              </tr>
            ) : (
              conditions.map((condition) => (
                <tr key={condition.id}>
                  <td><strong>{condition.name}</strong></td>
                  <td>{condition.times}</td>
                  <td>{condition.trueDestination}</td>
                  <td>{condition.falseDestination}</td>
                  <td>
                    <span className={`status-badge ${condition.status === 'Activo' ? 'active' : 'inactive'}`}>
                      {condition.status}
                    </span>
                  </td>
                  <td>
                    <button className="btn-icon" title="Editar">✏️</button>
                    <button className="btn-icon" title="Eliminar" onClick={() => handleDelete(condition.id)}>🗑️</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content large-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Nueva Condición de Horario</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-body">
              <div className="form-group">
                <label>Nombre de la Condición *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Horario de Oficina"
                  required
                />
              </div>

              <div className="time-groups-section">
                <div className="section-header">
                  <h3>Grupos de Horarios</h3>
                  <button type="button" className="btn-secondary btn-sm" onClick={addTimeGroup}>
                    + Agregar Horario
                  </button>
                </div>

                {formData.timeGroups.map((group, index) => (
                  <div key={index} className="time-group-card">
                    <div className="card-header">
                      <span>Horario {index + 1}</span>
                      {formData.timeGroups.length > 1 && (
                        <button 
                          type="button" 
                          className="btn-remove" 
                          onClick={() => removeTimeGroup(index)}
                        >
                          ×
                        </button>
                      )}
                    </div>
                    <div className="days-selector">
                      {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map((day, dayIndex) => (
                        <label key={dayIndex} className="day-checkbox">
                          <input
                            type="checkbox"
                            checked={group.days.includes(day)}
                            onChange={(e) => {
                              const newDays = e.target.checked
                                ? [...group.days, day]
                                : group.days.filter(d => d !== day)
                              updateTimeGroup(index, 'days', newDays)
                            }}
                          />
                          <span>{day}</span>
                        </label>
                      ))}
                    </div>
                    <div className="time-range">
                      <div className="form-group">
                        <label>Hora Inicio</label>
                        <input
                          type="time"
                          value={group.startTime}
                          onChange={(e) => updateTimeGroup(index, 'startTime', e.target.value)}
                        />
                      </div>
                      <span className="time-separator">→</span>
                      <div className="form-group">
                        <label>Hora Fin</label>
                        <input
                          type="time"
                          value={group.endTime}
                          onChange={(e) => updateTimeGroup(index, 'endTime', e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="destinations-section">
                <h3>Destinos</h3>
                
                <div className="destination-card success">
                  <h4>✓ Si cumple la condición</h4>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Tipo de Destino</label>
                      <select
                        value={formData.trueDestinationType}
                        onChange={(e) => setFormData({ ...formData, trueDestinationType: e.target.value })}
                      >
                        <option value="ivr">IVR</option>
                        <option value="queue">Cola</option>
                        <option value="extension">Extensión</option>
                        <option value="voicemail">Buzón de Voz</option>
                        <option value="announcement">Anuncio</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Destino</label>
                      <input
                        type="text"
                        value={formData.trueDestination}
                        onChange={(e) => setFormData({ ...formData, trueDestination: e.target.value })}
                        placeholder="Seleccione destino"
                      />
                    </div>
                  </div>
                </div>

                <div className="destination-card danger">
                  <h4>✗ Si NO cumple la condición</h4>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Tipo de Destino</label>
                      <select
                        value={formData.falseDestinationType}
                        onChange={(e) => setFormData({ ...formData, falseDestinationType: e.target.value })}
                      >
                        <option value="ivr">IVR</option>
                        <option value="queue">Cola</option>
                        <option value="extension">Extensión</option>
                        <option value="voicemail">Buzón de Voz</option>
                        <option value="announcement">Anuncio</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Destino</label>
                      <input
                        type="text"
                        value={formData.falseDestination}
                        onChange={(e) => setFormData({ ...formData, falseDestination: e.target.value })}
                        placeholder="Seleccione destino"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Crear Condición
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default TimeConditions
