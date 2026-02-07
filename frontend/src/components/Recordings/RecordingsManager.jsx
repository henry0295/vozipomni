import React, { useState } from 'react'
import './RecordingsManager.css'

const RecordingsManager = () => {
  const [recordings, setRecordings] = useState([])
  const [filter, setFilter] = useState({
    date_from: '',
    date_to: '',
    agent: '',
    campaign: ''
  })

  return (
    <div className="recordings-container">
      <div className="page-header">
        <h1>🎙️ Grabaciones de Llamadas</h1>
        <button className="btn-secondary">📥 Exportar Reporte</button>
      </div>

      <div className="filter-panel">
        <div className="filter-row">
          <div className="filter-group">
            <label>Desde</label>
            <input
              type="date"
              value={filter.date_from}
              onChange={(e) => setFilter({...filter, date_from: e.target.value})}
            />
          </div>
          <div className="filter-group">
            <label>Hasta</label>
            <input
              type="date"
              value={filter.date_to}
              onChange={(e) => setFilter({...filter, date_to: e.target.value})}
            />
          </div>
          <div className="filter-group">
            <label>Agente</label>
            <select value={filter.agent} onChange={(e) => setFilter({...filter, agent: e.target.value})}>
              <option value="">Todos</option>
              <option value="1">Agente 1</option>
              <option value="2">Agente 2</option>
            </select>
          </div>
          <div className="filter-group">
            <label>Campaña</label>
            <select value={filter.campaign} onChange={(e) => setFilter({...filter, campaign: e.target.value})}>
              <option value="">Todas</option>
              <option value="1">Campaña 1</option>
              <option value="2">Campaña 2</option>
            </select>
          </div>
          <button className="btn-primary">🔍 Buscar</button>
        </div>
      </div>

      <div className="recordings-table">
        <table>
          <thead>
            <tr>
              <th>Fecha/Hora</th>
              <th>Agente</th>
              <th>Contacto</th>
              <th>Número</th>
              <th>Duración</th>
              <th>Campaña</th>
              <th>Calificación</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan="8" className="no-data">
                No hay grabaciones disponibles para los filtros seleccionados.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default RecordingsManager
