import React from 'react'
import './Dashboard.css'

const Dashboard = () => {
  return (
    <div className="dashboard-container">
      <h1>Dashboard VoziPOmni</h1>
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Llamadas Activas</h3>
          <div className="stat-value">0</div>
        </div>
        <div className="stat-card">
          <h3>Agentes Disponibles</h3>
          <div className="stat-value">0</div>
        </div>
        <div className="stat-card">
          <h3>Campañas Activas</h3>
          <div className="stat-value">0</div>
        </div>
        <div className="stat-card">
          <h3>Llamadas Hoy</h3>
          <div className="stat-value">0</div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
