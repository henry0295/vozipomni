import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Layout.css'

const Layout = ({ children }) => {
  const location = useLocation()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [showTelephonySubmenu, setShowTelephonySubmenu] = useState(false)

  const handleLogout = () => {
    localStorage.removeItem('token')
    window.location.reload()
  }

  const isActive = (path) => location.pathname === path

  const menuItems = [
    { path: '/dashboard', icon: '📊', label: 'Dashboard' },
    { path: '/agent-console', icon: '🎧', label: 'Consola Agente' },
    { path: '/campaigns', icon: '📢', label: 'Campañas' },
    { path: '/contacts', icon: '👥', label: 'Contactos' },
    { path: '/queues', icon: '📋', label: 'Colas' },
    { path: '/recordings', icon: '🎙️', label: 'Grabaciones' },
    { path: '/users', icon: '👤', label: 'Usuarios' },
    { path: '/reports', icon: '📈', label: 'Reportes' },
  ]

  const telephonyItems = [
    { path: '/extensions', icon: '📞', label: 'Extensiones' },
    { path: '/trunks', icon: '🌐', label: 'Troncales' },
    { path: '/ivr', icon: '☎️', label: 'IVR' },
    { path: '/inbound-routes', icon: '📥', label: 'Rutas Entrantes' },
    { path: '/outbound-routes', icon: '📤', label: 'Rutas Salientes' },
    { path: '/voicemail', icon: '📧', label: 'Buzones de Voz' },
    { path: '/music-on-hold', icon: '🎵', label: 'Música en Espera' },
    { path: '/time-conditions', icon: '⏰', label: 'Horarios' },
  ]

  return (
    <div className="layout-container">
      {/* Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="logo">
            <span className="logo-icon">🎯</span>
            {isSidebarOpen && <h1>VozipCX</h1>}
          </div>
          <button 
            className="toggle-btn" 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          >
            {isSidebarOpen ? '◀' : '▶'}
          </button>
        </div>

        <nav className="sidebar-nav">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${isActive(item.path) ? 'active' : ''}`}
              title={!isSidebarOpen ? item.label : ''}
            >
              <span className="nav-icon">{item.icon}</span>
              {isSidebarOpen && <span className="nav-label">{item.label}</span>}
            </Link>
          ))}

          <div className="nav-group">
            <div
              className={`nav-item config-toggle ${showTelephonySubmenu || telephonyItems.some(i => isActive(i.path)) ? 'active' : ''}`}
              onClick={() => setShowTelephonySubmenu(!showTelephonySubmenu)}
            >
              <span className="nav-icon">📞</span>
              {isSidebarOpen && (
                <>
                  <span className="nav-label">Telefonía</span>
                  <span className="arrow">{showTelephonySubmenu ? '▼' : '▶'}</span>
                </>
              )}
            </div>
            {(showTelephonySubmenu || !isSidebarOpen) && (
              <div className="submenu">
                {telephonyItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`nav-item submenu-item ${isActive(item.path) ? 'active' : ''}`}
                    title={!isSidebarOpen ? item.label : ''}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    {isSidebarOpen && <span className="nav-label">{item.label}</span>}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="user-avatar">👤</div>
            {isSidebarOpen && (
              <div className="user-info">
                <span className="user-name">Admin</span>
                <span className="user-role">Administrador</span>
              </div>
            )}
          </div>
          <button className="logout-btn" onClick={handleLogout} title="Cerrar Sesión">
            <span className="nav-icon">🚪</span>
            {isSidebarOpen && <span>Salir</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className={`main-content ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <div className="content-wrapper">
          {children}
        </div>
      </main>
    </div>
  )
}

export default Layout
