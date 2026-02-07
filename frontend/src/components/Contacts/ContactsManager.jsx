import React, { useState } from 'react'
import './ContactsManager.css'

const ContactsManager = () => {
  const [contacts, setContacts] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    company: '',
    position: '',
    notes: '',
    tags: ''
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Creating Contact:', formData)
    setShowModal(false)
  }

  return (
    <div className="contacts-container">
      <div className="page-header">
        <h1>📇 Gestión de Contactos</h1>
        <div className="header-actions">
          <button className="btn-secondary">📥 Importar CSV</button>
          <button className="btn-primary" onClick={() => setShowModal(true)}>
            ➕ Nuevo Contacto
          </button>
        </div>
      </div>

      <div className="search-bar">
        <input type="text" placeholder="🔍 Buscar contactos por nombre, teléfono o email..." />
      </div>

      <div className="contacts-table">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Teléfono</th>
              <th>Email</th>
              <th>Empresa</th>
              <th>Cargo</th>
              <th>Etiquetas</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan="7" className="no-data">
                No hay contactos registrados. Crea uno nuevo o importa desde CSV.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Nuevo Contacto</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit} className="contact-form">
              <div className="form-row">
                <div className="form-group">
                  <label>Nombre *</label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Apellido *</label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                    required
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Teléfono *</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                    placeholder="+57 300 123 4567"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    placeholder="contacto@empresa.com"
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Empresa</label>
                  <input
                    type="text"
                    value={formData.company}
                    onChange={(e) => setFormData({...formData, company: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label>Cargo</label>
                  <input
                    type="text"
                    value={formData.position}
                    onChange={(e) => setFormData({...formData, position: e.target.value})}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Etiquetas (separadas por coma)</label>
                <input
                  type="text"
                  value={formData.tags}
                  onChange={(e) => setFormData({...formData, tags: e.target.value})}
                  placeholder="cliente, vip, soporte"
                />
              </div>

              <div className="form-group">
                <label>Notas</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({...formData, notes: e.target.value})}
                  rows="4"
                  placeholder="Notas adicionales sobre el contacto..."
                />
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  Guardar Contacto
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default ContactsManager
