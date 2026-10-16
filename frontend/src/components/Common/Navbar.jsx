import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Navbar.css'

const Navbar = () => {
  const location = useLocation()
  const [showDropdown, setShowDropdown] = useState(false)

  const handleLogout = () => {
    localStorage.removeItem('token')
    window.location.reload()
  }

  const isActive = (path) => location.pathname === path

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h2>VozipCX</h2>
      </div>
      <div className="navbar-menu">
        <Link 
          to="/dashboard" 
          className={`nav-link ${isActive('/dashboard') ? 'active' : ''}`}
        >
          📊 Dashboard
        </Link>
        <Link 
          to="/agent-console" 
          className={`nav-link ${isActive('/agent-console') ? 'active' : ''}`}
        >
          👤 Consola
        </Link>
        <Link 
          to="/campaigns" 
          className={`nav-link ${isActive('/campaigns') ? 'active' : ''}`}
        >
          📞 Campañas
        </Link>
        <Link 
          to="/contacts" 
          className={`nav-link ${isActive('/contacts') ? 'active' : ''}`}
        >
          📇 Contactos
        </Link>
        <Link 
          to="/queues" 
          className={`nav-link ${isActive('/queues') ? 'active' : ''}`}
        >
          📋 Colas
        </Link>
        <Link 
          to="/recordings" 
          className={`nav-link ${isActive('/recordings') ? 'active' : ''}`}
        >
          🎙️ Grabaciones
        </Link>
        <div 
          className="nav-dropdown"
          onMouseEnter={() => setShowDropdown(true)}
          onMouseLeave={() => setShowDropdown(false)}
        >
          <span className={`nav-link ${['/users', '/ivr', '/trunks'].includes(location.pathname) ? 'active' : ''}`}>
            ⚙️ Configuración ▼
          </span>
          {showDropdown && (
            <div className="dropdown-menu">
              <Link to="/users" className="dropdown-item">👥 Usuarios</Link>
              <Link to="/ivr" className="dropdown-item">📞 IVR</Link>
              <Link to="/trunks" className="dropdown-item">🌐 Troncales</Link>
            </div>
          )}
        </div>
        <Link 
          to="/reports" 
          className={`nav-link ${isActive('/reports') ? 'active' : ''}`}
        >
          📈 Reportes
        </Link>
      </div>
      <div className="navbar-actions">
        <span className="user-info">admin</span>
        <button onClick={handleLogout} className="logout-btn">
          🚪 Salir
        </button>
      </div>
    </nav>
  )
}

export default Navbar
