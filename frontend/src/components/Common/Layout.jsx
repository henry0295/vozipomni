import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Layout.css'

const Layout = ({ children }) => {
  const location = useLocation()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [showConfigSubmenu, setShowConfigSubmenu] = useState(false)

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
    { path: '/reports', icon: '📊', label: 'Reportes' },
  ]

  const configItems = [
    { path: '/users', icon: '👤', label: 'Usuarios' },
    { path: '/ivr', icon: '☎️', label: 'IVR' },
    { path: '/trunks', icon: '🌐', label: 'Troncales' },
  ]

  return (
    <div className="layout-container">
      {/* Sidebar */}
      <aside className={`sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <div className="logo">
            <span className="logo-icon">🎯</span>
            {isSidebarOpen && <h1>VoziPOmni</h1>}
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
              className={`nav-item config-toggle ${showConfigSubmenu || configItems.some(i => isActive(i.path)) ? 'active' : ''}`}
              onClick={() => setShowConfigSubmenu(!showConfigSubmenu)}
            >
              <span className="nav-icon">⚙️</span>
              {isSidebarOpen && (
                <>
                  <span className="nav-label">Configuración</span>
                  <span className="arrow">{showConfigSubmenu ? '▼' : '▶'}</span>
                </>
              )}
            </div>
            {(showConfigSubmenu || !isSidebarOpen) && (
              <div className="submenu">
                {configItems.map((item) => (
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
