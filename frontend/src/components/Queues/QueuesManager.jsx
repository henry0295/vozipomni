import React, { useState } from 'react'
import './QueuesManager.css'

const QueuesManager = () => {
  const [queues, setQueues] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    extension: '',
    strategy: 'ringall',
    timeout: 30,
    max_wait_time: 300,
    announce_position: true,
    announce_hold_time: true,
    music_on_hold: 'default',
    is_active: true
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Creating Queue:', formData)
    setShowModal(false)
  }

  return (
    <div className="queues-container">
      <div className="page-header">
        <h1>📋 Gestión de Colas</h1>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          ➕ Nueva Cola
        </button>
      </div>

      <div className="queues-table">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Extensión</th>
              <th>Estrategia</th>
              <th>Timeout</th>
              <th>Tiempo Máx. Espera</th>
              <th>Agentes</th>
              <th>Estado</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan="8" className="no-data">
                No hay colas configuradas. Crea una nueva para comenzar.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Configurar Cola</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit} className="queue-form">
             <div className="form-group">
                <label>Nombre de la Cola *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="Ej: Soporte Técnico"
                  required
                />
              </div>

              <div className="form-group">
                <label>Descripción</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  placeholder="Descripción de la cola"
                  rows="3"
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Extensión</label>
                  <input
                    type="text"
                    value={formData.extension}
                    onChange={(e) => setFormData({...formData, extension: e.target.value})}
                    placeholder="Ej: 8001"
                  />
                </div>
                <div className="form-group">
                  <label>Estrategia de Distribución</label>
                  <select
                    value={formData.strategy}
                    onChange={(e) => setFormData({...formData, strategy: e.target.value})}
                  >
                    <option value="ringall">Ring All (Todos)</option>
                    <option value="leastrecent">Menos Reciente</option>
                    <option value="fewestcalls">Menos Llamadas</option>
                    <option value="random">Aleatorio</option>
                    <option value="rrmemory">Round Robin</option>
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Timeout por Agente (segundos)</label>
                  <input
                    type="number"
                    value={formData.timeout}
                    onChange={(e) => setFormData({...formData, timeout: parseInt(e.target.value)})}
                    min="5"
                    max="180"
                  />
                </div>
                <div className="form-group">
                  <label>Tiempo Máximo de Espera (segundos)</label>
                  <input
                    type="number"
                    value={formData.max_wait_time}
                    onChange={(e) => setFormData({...formData, max_wait_time: parseInt(e.target.value)})}
                    min="30"
                    max="3600"
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Música en Espera</label>
                <select
                  value={formData.music_on_hold}
                  onChange={(e) => setFormData({...formData, music_on_hold: e.target.value})}
                >
                  <option value="default">Por Defecto</option>
                  <option value="custom1">Personalizada 1</option>
                  <option value="custom2">Personalizada 2</option>
                </select>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.announce_position}
                    onChange={(e) => setFormData({...formData, announce_position: e.target.checked})}
                  />
                  Anunciar Posición en Cola
                </label>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.announce_hold_time}
                    onChange={(e) => setFormData({...formData, announce_hold_time: e.target.checked})}
                  />
                  Anunciar Tiempo de Espera
                </label>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                  />
                  Cola Activa
                </label>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Guardar Cola
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default QueuesManager
