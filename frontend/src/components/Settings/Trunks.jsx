import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { trunksService } from '../../services/telephonyService'
import './Trunks.css'

const Trunks = () => {
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [activeTab, setActiveTab] = useState('basic')
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState({
    // Básico
    name: '',
    description: '',
    trunk_type: 'nat_provider',
    host: '',
    port: 5060,
    protocol: 'udp',
    max_channels: 10,
    is_active: true,
    
    // Autenticación Saliente
    outbound_auth_username: '',
    outbound_auth_password: '',
    from_user: '',
    from_domain: '',
    
    // Autenticación Entrante
    inbound_auth_username: '',
    inbound_auth_password: '',
    
    // Registro
    sends_registration: true,
    registration_server_uri: '',
    registration_client_uri: '',
    registration_retry_interval: 60,
    registration_expiration: 3600,
    
    // Comportamiento SIP
    sends_auth: true,
    accepts_auth: false,
    accepts_registrations: false,
    
    // RTP/Media
    rtp_symmetric: true,
    force_rport: true,
    rewrite_contact: true,
    direct_media: false,
    
    // Códecs y DTMF
    codec: 'ulaw,alaw,g729',
    dtmf_mode: 'rfc4733',
    
    // Context
    context: 'from-pstn',
    custom_context: '',
    
    // Timers
    timers: true,
    timers_min_se: 90,
    timers_sess_expires: 1800,
    
    // Qualify
    qualify_enabled: true,
    qualify_frequency: 60,
    qualify_timeout: 3.0,
    
    // Caller ID
    caller_id: '',
    caller_id_name: '',
    
    // NAT
    local_net: '',
    external_media_address: '',
    external_signaling_address: '',
    
    // Avanzado
    language: 'es',
    trust_id_inbound: false,
    trust_id_outbound: false,
    send_pai: false,
    send_rpid: false,
    
    // Custom
    pjsip_config_custom: ''
  })

  // Queries y Mutations
  const { data: trunks = [], isLoading, refetch } = useQuery({
    queryKey: ['trunks'],
    queryFn: async () => {
      const response = await trunksService.getAll()
      const data = response.data?.results || response.data
      return Array.isArray(data) ? data : []
    }
  })

  const createMutation = useMutation({
    mutationFn: trunksService.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['trunks'])
      toast.success('Troncal creada y configuración regenerada')
      resetForm()
    },
    onError: (error) => {
      const msg = error.response?.data?.message || 'Error al crear troncal'
      toast.error(msg)
    }
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => trunksService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['trunks'])
      toast.success('Troncal actualizada y configuración regenerada')
      resetForm()
    },
    onError: (error) => {
      const msg = error.response?.data?.message || 'Error al actualizar troncal'
      toast.error(msg)
    }
  })

  const deleteMutation = useMutation({
    mutationFn: trunksService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['trunks'])
      toast.success('Troncal eliminada y configuración regenerada')
    },
    onError: () => toast.error('Error al eliminar troncal')
  })

  // Event Handlers
  const handleSubmit = (e) => {
    e.preventDefault()
    
    const dataToSend = { ...formData }
    
    // Si no es tipo custom, limpiar pjsip_config_custom
    if (dataToSend.trunk_type !== 'custom') {
      dataToSend.pjsip_config_custom = ''
    }
    
    // Si context no es custom, limpiar custom_context
    if (dataToSend.context !== 'custom') {
      dataToSend.custom_context = ''
    }
    
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: dataToSend })
    } else {
      createMutation.mutate(dataToSend)
    }
  }

  const handleEdit = (trunk) => {
    setFormData({
      ...trunk,
      outbound_auth_password: '', // No cargar password por seguridad
      inbound_auth_password: ''
    })
    setEditingId(trunk.id)
    setShowModal(true)
    setActiveTab('basic')
  }

  const handleDelete = async (id) => {
    if (window.confirm('¿Estás seguro de eliminar esta troncal?')) {
      deleteMutation.mutate(id)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      trunk_type: 'nat_provider',
      host: '',
      port: 5060,
      protocol: 'udp',
      max_channels: 10,
      is_active: true,
      outbound_auth_username: '',
      outbound_auth_password: '',
      from_user: '',
      from_domain: '',
      inbound_auth_username: '',
      inbound_auth_password: '',
      sends_registration: true,
      registration_server_uri: '',
      registration_client_uri: '',
      registration_retry_interval: 60,
      registration_expiration: 3600,
      sends_auth: true,
      accepts_auth: false,
      accepts_registrations: false,
      rtp_symmetric: true,
      force_rport: true,
      rewrite_contact: true,
      direct_media: false,
      codec: 'ulaw,alaw,g729',
      dtmf_mode: 'rfc4733',
      context: 'from-pstn',
      custom_context: '',
      timers: true,
      timers_min_se: 90,
      timers_sess_expires: 1800,
      qualify_enabled: true,
      qualify_frequency: 60,
      qualify_timeout: 3.0,
      caller_id: '',
      caller_id_name: '',
      local_net: '',
      external_media_address: '',
      external_signaling_address: '',
      language: 'es',
      trust_id_inbound: false,
      trust_id_outbound: false,
      send_pai: false,
      send_rpid: false,
      pjsip_config_custom: ''
    })
    setEditingId(null)
    setShowModal(false)
    setActiveTab('basic')
  }

  const handleTestConnection = async (trunkId) => {
    try {
      toast.loading('Probando conexión...', { id: `test-${trunkId}` })
      const response = await trunksService.testConnection(trunkId)
      
      // Verificar si requiere registro o solo disponibilidad
      if (response.data.requires_registration === false) {
        // Troncal sin registro (corporate, etc)
        if (response.data.available) {
          toast.success(`✓ ${response.data.message}`, { id: `test-${trunkId}` })
        } else {
          toast.warning(`⚠ ${response.data.message}`, { id: `test-${trunkId}` })
        }
      } else {
        // Troncal con registro (NAT provider, etc)
        if (response.data.registered) {
          toast.success(`✓ Registrado: ${response.data.status}`, { id: `test-${trunkId}` })
        } else {
          toast.error(`✗ No registrado: ${response.data.status}`, { id: `test-${trunkId}` })
        }
      }
      
      refetch()
    } catch (error) {
      const errorMsg = error.response?.data?.message || 'Error probando conexión'
      toast.error(`✗ ${errorMsg}`, { id: `test-${trunkId}` })
    }
  }

  // Auto-completar campos según tipo de troncal
  const handleTrunkTypeChange = (type) => {
    setFormData(prev => {
      const updates = { trunk_type: type }
      
      switch (type) {
        case 'nat_provider':
          updates.sends_registration = true
          updates.sends_auth = true
          updates.accepts_auth = false
          updates.accepts_registrations = false
          updates.rtp_symmetric = true
          updates.force_rport = true
          updates.rewrite_contact = true
          updates.context = 'from-pstn'
          break
        
        case 'no_nat_provider':
          updates.sends_registration = true
          updates.sends_auth = true
          updates.accepts_auth = false
          updates.accepts_registrations = false
          updates.rtp_symmetric = true
          updates.force_rport = true
          updates.rewrite_contact = true
          updates.context = 'from-pstn'
          break
        
        case 'pbx_lan':
          updates.sends_registration = false
          updates.sends_auth = true
          updates.accepts_auth = true
          updates.accepts_registrations = false
          updates.rtp_symmetric = false
          updates.force_rport = false
          updates.rewrite_contact = false
          updates.context = 'from-pbx'
          break
        
        case 'corporate':
          updates.sends_registration = false
          updates.sends_auth = false
          updates.accepts_auth = false
          updates.accepts_registrations = false
          updates.rtp_symmetric = false
          updates.force_rport = false
          updates.rewrite_contact = false
          updates.context = 'from-pstn'
          break
        
        default:
          break
      }
      
      return { ...prev, ...updates }
    })
  }

  if (isLoading) return <div className="loading">Cargando troncales...</div>

  return (
    <div className="trunks-container">
      <div className="trunks-header">
        <div className="header-left">
          <h1>🌐 Troncales SIP</h1>
          <p>Gestiona las conexiones con proveedores&#x20;VoIP y PBX</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          + Nueva Troncal
        </button>
      </div>

      <div className="table-container">
        <table className="trunks-table">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Host</th>
              <th>Puerto</th>
              <th>Usuario</th>
              <th>Protocolo</th>
              <th>Canales Máx.</th>
              <th>Estado</th>
              <th>Registro</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {trunks.length === 0 ? (
              <tr>
                <td colSpan="10" className="no-data">
                  No hay troncales SIP configuradas. Crea una nueva para comenzar.
                </td>
              </tr>
            ) : (
              trunks.map((trunk) => (
                <tr key={trunk.id}>
                  <td><strong>{trunk.name}</strong></td>
                  <td>
                    <span className="trunk-type-badge">
                      {trunk.trunk_type === 'nat_provider' && '☁️ NAT'}
                      {trunk.trunk_type === 'no_nat_provider' && '🌐 Sin NAT'}
                      {trunk.trunk_type === 'pbx_lan' && '📞 PBX LAN'}
                      {trunk.trunk_type === 'corporate' && '🏢 Corporativo'}
                      {trunk.trunk_type === 'custom' && '⚙️ Custom'}
                    </span>
                  </td>
                  <td>{trunk.host}</td>
                  <td>{trunk.port}</td>
                  <td>{trunk.outbound_auth_username || trunk.username || '-'}</td>
                  <td>{trunk.protocol?.toUpperCase()}</td>
                  <td>{trunk.max_channels}</td>
                  <td>
                    <span className={`status-badge ${trunk.is_active ? 'active' : 'inactive'}`}>
                      {trunk.is_active ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${
                      trunk.registration_detail?.class === 'success' ? 'registered' :
                      trunk.registration_detail?.class === 'error' ? 'error' :
                      trunk.registration_detail?.class === 'warning' ? 'warning' : 'info'
                    }`}>
                      {trunk.registration_detail?.icon} {trunk.registration_detail?.text || 'Verificando...'}
                    </span>
                  </td>
                  <td>
                    <button className="btn-icon" title="Probar Conexión" onClick={() => handleTestConnection(trunk.id)}>🔍</button>
                    <button className="btn-icon" title="Editar" onClick={() => handleEdit(trunk)}>✏️</button>
                    <button className="btn-icon" title="Eliminar" onClick={() => handleDelete(trunk.id)}>🗑️</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* MODAL CON FORMULARIO POR PESTAÑAS */}
      {showModal && (
        <div className="modal-overlay" onClick={resetForm}>
          <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingId ? '✏️ Editar' : '➕ Nueva'} Troncal SIP</h2>
              <button className="close-btn" onClick={resetForm}>✕</button>
            </div>

            {/* PESTAÑAS */}
            <div className="tabs-container">
              <div className="tabs">
                <button
                  className={`tab ${activeTab === 'basic' ? 'active' : ''}`}
                  onClick={() => setActiveTab('basic')}
                >
                  📋 Básico
                </button>
                <button
                  className={`tab ${activeTab === 'auth' ? 'active' : ''}`}
                  onClick={() => setActiveTab('auth')}
                >
                  🔐 Autenticación
                </button>
                <button
                  className={`tab ${activeTab === 'registration' ? 'active' : ''}`}
                  onClick={() => setActiveTab('registration')}
                >
                  📡 Registro
                </button>
                <button
                  className={`tab ${activeTab === 'media' ? 'active' : ''}`}
                  onClick={() => setActiveTab('media')}
                >
                  🎵 RTP/Media
                </button>
                <button
                  className={`tab ${activeTab === 'advanced' ? 'active' : ''}`}
                  onClick={() => setActiveTab('advanced')}
                >
                  ⚙️ Avanzado
                </button>
                {formData.trunk_type === 'custom' && (
                  <button
                    className={`tab ${activeTab === 'custom' ? 'active' : ''}`}
                    onClick={() => setActiveTab('custom')}
                  >
                    💻 Config Custom
                  </button>
                )}
              </div>
            </div>

            <form onSubmit={handleSubmit} className="trunk-form">
              
              {/* PESTAÑA: BÁSICO */}
              {activeTab === 'basic' && (
                <div className="tab-content">
                  <h3>Configuración Básica</h3>
                  
                  <div className="form-group">
                    <label>Nombre de la Troncal *</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      placeholder="Ej: proveedor_principal"
                      required
                    />
                    <small>Identificador único (alfanumérico, sin espacios)</small>
                  </div>

                  <div className="form-group">
                    <label>Descripción</label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData({...formData, description: e.target.value})}
                      placeholder="Descripción opcional de la troncal"
                      rows="2"
                    />
                  </div>

                  <div className="form-group">
                    <label>Tipo de Troncal *</label>
                    <select
                      value={formData.trunk_type}
                      onChange={(e) => handleTrunkTypeChange(e.target.value)}
                    >
                      <option value="nat_provider">☁️ Proveedor con NAT (Cloud/VPS detrás de NAT)</option>
                      <option value="no_nat_provider">🌐 Proveedor sin NAT (VPS con IP pública)</option>
                      <option value="pbx_lan">📞 PBX en LAN (Asterisk/FreePBX/Issabel local)</option>
                      <option value="corporate">🏢 Troncal Corporativa (sin auth/registro)</option>
                      <option value="custom">⚙️ Personalizado (configuración manual)</option>
                    </select>
                    <small>
                      {formData.trunk_type === 'nat_provider' && 'Para proveedores SIP cuando VoziPOmni está detrás de NAT'}
                      {formData.trunk_type === 'no_nat_provider' && 'Para proveedores SIP con IP pública directa'}
                      {formData.trunk_type === 'pbx_lan' && 'Para conectar con PBX/Asterisk en red local'}
                      {formData.trunk_type === 'corporate' && 'Para vínculos corporativos sin autenticación'}
                      {formData.trunk_type === 'custom' && 'Configuración PJSIP Wizard manual completa'}
                    </small>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Host/IP o FQDN *</label>
                      <input
                        type="text"
                        value={formData.host}
                        onChange={(e) => setFormData({...formData, host: e.target.value})}
                        placeholder="sip.provider.com o 192.168.1.100"
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
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Códecs (separados por coma)</label>
                      <input
                        type="text"
                        value={formData.codec}
                        onChange={(e) => setFormData({...formData, codec: e.target.value})}
                        placeholder="ulaw,alaw,g729"
                      />
                    </div>
                    <div className="form-group">
                      <label>Modo DTMF</label>
                      <select
                        value={formData.dtmf_mode}
                        onChange={(e) => setFormData({...formData, dtmf_mode: e.target.value})}
                      >
                        <option value="rfc4733">RFC4733 (Recomendado)</option>
                        <option value="rfc2833">RFC2833</option>
                        <option value="inband">Inband</option>
                        <option value="info">SIP INFO</option>
                        <option value="auto">Auto</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Canales Máximos</label>
                      <input
                        type="number"
                        value={formData.max_channels}
                        onChange={(e) => setFormData({...formData, max_channels: parseInt(e.target.value)})}
                        min="1"
                        max="100"
                      />
                    </div>
                    <div className="form-group">
                      <label>Contexto Dialplan</label>
                      <select
                        value={formData.context}
                        onChange={(e) => setFormData({...formData, context: e.target.value})}
                      >
                        <option value="from-pstn">from-pstn (Llamadas desde PSTN)</option>
                        <option value="from-pbx">from-pbx (Llamadas desde PBX)</option>
                        <option value="from-trunk">from-trunk (Desde Troncal)</option>
                        <option value="custom">Personalizado</option>
                      </select>
                    </div>
                    {formData.context === 'custom' && (
                      <div className="form-group">
                        <label>Contexto Personalizado</label>
                        <input
                          type="text"
                          value={formData.custom_context}
                          onChange={(e) => setFormData({...formData, custom_context: e.target.value})}
                          placeholder="mi-contexto-custom"
                        />
                      </div>
                    )}
                  </div>

                  <div className="form-group checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                      />
                      <strong>Troncal Activa</strong>
                    </label>
                  </div>
                </div>
              )}

              {/* PESTAÑA: AUTENTICACIÓN */}
              {activeTab === 'auth' && (
                <div className="tab-content">
                  <h3>🔐 Autenticación y Credenciales</h3>
                  
                  <div className="form-section">
                    <h4>Autenticación Saliente (Outbound)</h4>
                    <p className="help-text">Credenciales para registrarse con el proveedor y hacer llamadas salientes</p>
                    
                    <div className="form-row">
                      <div className="form-group">
                        <label>Usuario SIP</label>
                        <input
                          type="text"
                          value={formData.outbound_auth_username}
                          onChange={(e) => setFormData({...formData, outbound_auth_username: e.target.value})}
                          placeholder="Usuario SIP"
                        />
                      </div>
                      <div className="form-group">
                        <label>Contraseña</label>
                        <input
                          type="password"
                          value={formData.outbound_auth_password}
                          onChange={(e) => setFormData({...formData, outbound_auth_password: e.target.value})}
                          placeholder="••••••••"
                        />
                      </div>
                    </div>

                    <div className="form-row">
                      <div className="form-group">
                        <label>From User</label>
                        <input
                          type="text"
                          value={formData.from_user}
                          onChange={(e) => setFormData({...formData, from_user: e.target.value})}
                          placeholder="username (opcional)"
                        />
                        <small>Usuario en header From (si es diferente al auth)</small>
                      </div>
                      <div className="form-group">
                        <label>From Domain</label>
                        <input
                          type="text"
                          value={formData.from_domain}
                          onChange={(e) => setFormData({...formData, from_domain: e.target.value})}
                          placeholder="sip.provider.com (opcional)"
                        />
                        <small>Dominio en header From</small>
                      </div>
                    </div>
                  </div>

                  <div className="form-section">
                    <h4>Autenticación Entrante (Inbound)</h4>
                    <p className="help-text">Credenciales que el proveedor debe usar para llamadas entrantes</p>
                    
                    <div className="form-row">
                      <div className="form-group">
                        <label>Usuario Entrante</label>
                        <input
                          type="text"
                          value={formData.inbound_auth_username}
                          onChange={(e) => setFormData({...formData, inbound_auth_username: e.target.value})}
                          placeholder="Usuario entrante (opcional)"
                        />
                      </div>
                      <div className="form-group">
                        <label>Contraseña Entrante</label>
                        <input
                          type="password"
                          value={formData.inbound_auth_password}
                          onChange={(e) => setFormData({...formData, inbound_auth_password: e.target.value})}
                          placeholder="••••••••"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="form-section">
                    <h4>Comportamiento de Autenticación SIP</h4>
                    
                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.sends_auth}
                          onChange={(e) => setFormData({...formData, sends_auth: e.target.checked})}
                        />
                        <strong>Enviar Autenticación</strong>
                        <small>El sistema enviará credenciales al proveedor</small>
                      </label>
                    </div>

                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.accepts_auth}
                          onChange={(e) => setFormData({...formData, accepts_auth: e.target.checked})}
                        />
                        <strong>Aceptar Autenticación</strong>
                        <small>El sistema solicitará autenticación al proveedor</small>
                      </label>
                    </div>

                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.accepts_registrations}
                          onChange={(e) => setFormData({...formData, accepts_registrations: e.target.checked})}
                        />
                        <strong>Aceptar Registros del Proveedor</strong>
                        <small>Permitir que el proveedor se registre en este sistema</small>
                      </label>
                    </div>
                  </div>

                  <div className="form-section">
                    <h4>Caller ID</h4>
                    <div className="form-row">
                      <div className="form-group">
                        <label>Caller ID</label>
                        <input
                          type="text"
                          value={formData.caller_id}
                          onChange={(e) => setFormData({...formData, caller_id: e.target.value})}
                          placeholder="+573001234567"
                        />
                      </div>
                      <div className="form-group">
                        <label>Nombre Caller ID</label>
                        <input
                          type="text"
                          value={formData.caller_id_name}
                          onChange={(e) => setFormData({...formData, caller_id_name: e.target.value})}
                          placeholder="Mi Empresa"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* PESTAÑA: REGISTRO */}
              {activeTab === 'registration' && (
                <div className="tab-content">
                  <h3>📡 Configuración de Registro SIP</h3>
                  
                  <div className="checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={formData.sends_registration}
                        onChange={(e) => setFormData({...formData, sends_registration: e.target.checked})}
                      />
                      <strong>Enviar Registro al Proveedor</strong>
                      <small>Activar si el proveedor requiere que nos registremos</small>
                    </label>
                  </div>

                  {formData.sends_registration && (
                    <>
                      <div className="form-group">
                        <label>Server URI *</label>
                        <input
                          type="text"
                          value={formData.registration_server_uri}
                          onChange={(e) => setFormData({...formData, registration_server_uri: e.target.value})}
                          placeholder="sip:sip.provider.com:5060"
                          required={formData.sends_registration}
                        />
                        <small>URI del servidor de registro (ej: sip:proveedor.com o sip:proveedor.com:5060)</small>
                      </div>

                      <div className="form-group">
                        <label>Client URI</label>
                        <input
                          type="text"
                          value={formData.registration_client_uri}
                          onChange={(e) => setFormData({...formData, registration_client_uri: e.target.value})}
                          placeholder="sip:usuario@proveedor.com"
                        />
                        <small>URI del cliente (ej: sip:usuario@proveedor.com). Si se omite, se genera automáticamente.</small>
                      </div>

                      <div className="form-row">
                        <div className="form-group">
                          <label>Intervalo de Reintento (segundos)</label>
                          <input
                            type="number"
                            value={formData.registration_retry_interval}
                            onChange={(e) => setFormData({...formData, registration_retry_interval: parseInt(e.target.value)})}
                            min="10"
                            max="600"
                          />
                          <small>Tiempo entre reintentos si falla el registro</small>
                        </div>
                        <div className="form-group">
                          <label>Expiración (segundos)</label>
                          <input
                            type="number"
                            value={formData.registration_expiration}
                            onChange={(e) => setFormData({...formData, registration_expiration: parseInt(e.target.value)})}
                            min="60"
                            max="7200"
                          />
                          <small>Tiempo de validez del registro</small>
                        </div>
                      </div>
                    </>
                  )}

                  <div className="form-section">
                    <h4>Session Timers</h4>
                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.timers}
                          onChange={(e) => setFormData({...formData, timers: e.target.checked})}
                        />
                        <strong>Habilitar Session Timers</strong>
                        <small>Mantener sesiones vivas con re-INVITE periódicos</small>
                      </label>
                    </div>

                    {formData.timers && (
                      <div className="form-row">
                        <div className="form-group">
                          <label>Mínimo SE (segundos)</label>
                          <input
                            type="number"
                            value={formData.timers_min_se}
                            onChange={(e) => setFormData({...formData, timers_min_se: parseInt(e.target.value)})}
                            min="90"
                          />
                        </div>
                        <div className="form-group">
                          <label>Session Expires (segundos)</label>
                          <input
                            type="number"
                            value={formData.timers_sess_expires}
                            onChange={(e) => setFormData({...formData, timers_sess_expires: parseInt(e.target.value)})}
                            min="90"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="form-section">
                    <h4>Qualify (Monitoreo de Disponibilidad)</h4>
                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.qualify_enabled}
                          onChange={(e) => setFormData({...formData, qualify_enabled: e.target.checked})}
                        />
                        <strong>Habilitar Qualify</strong>
                        <small>Enviar OPTIONS periódicos para verificar disponibilidad</small>
                      </label>
                    </div>

                    {formData.qualify_enabled && (
                      <div className="form-row">
                        <div className="form-group">
                          <label>Frecuencia (segundos)</label>
                          <input
                            type="number"
                            value={formData.qualify_frequency}
                            onChange={(e) => setFormData({...formData, qualify_frequency: parseInt(e.target.value)})}
                            min="10"
                          />
                        </div>
                        <div className="form-group">
                          <label>Timeout (segundos)</label>
                          <input
                            type="number"
                            step="0.1"
                            value={formData.qualify_timeout}
                            onChange={(e) => setFormData({...formData, qualify_timeout: parseFloat(e.target.value)})}
                            min="0.5"
                            max="10"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* PESTAÑA: RTP/MEDIA */}
              {activeTab === 'media' && (
                <div className="tab-content">
                  <h3>🎵 Configuración RTP y Media</h3>
                  
                  <div className="form-section">
                    <h4>Configuración RTP</h4>
                    
                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.rtp_symmetric}
                          onChange={(e) => setFormData({...formData, rtp_symmetric: e.target.checked})}
                        />
                        <strong>RTP Simétrico</strong>
                        <small>Enviar RTP a la dirección desde donde se recibió (importante para NAT)</small>
                      </label>
                    </div>

                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.force_rport}
                          onChange={(e) => setFormData({...formData, force_rport: e.target.checked})}
                        />
                        <strong>Force RPORT</strong>
                        <small>Forzar uso del puerto remoto para NAT traversal</small>
                      </label>
                    </div>

                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.rewrite_contact}
                          onChange={(e) => setFormData({...formData, rewrite_contact: e.target.checked})}
                        />
                        <strong>Rewrite Contact</strong>
                        <small>Reescribir header Contact con IP/puerto real (para NAT)</small>
                      </label>
                    </div>

                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.direct_media}
                          onChange={(e) => setFormData({...formData, direct_media: e.target.checked})}
                        />
                        <strong>Direct Media (reinvite)</strong>
                        <small>Permitir audio directo entre endpoints (no recomendado para NAT)</small>
                      </label>
                    </div>
                  </div>

                  <div className="form-section">
                    <h4>Configuración NAT</h4>
                    <p className="help-text">Configurar solo si VoziPOmni está detrás de NAT/Firewall</p>
                    
                    <div className="form-group">
                      <label>Redes Locales</label>
                      <input
                        type="text"
                        value={formData.local_net}
                        onChange={(e) => setFormData({...formData, local_net: e.target.value})}
                        placeholder="192.168.0.0/16, 10.0.0.0/8"
                      />
                      <small>Redes locales separadas por coma (ej: 192.168.0.0/16, 10.0.0.0/8)</small>
                    </div>

                    <div className="form-row">
                      <div className="form-group">
                        <label>IP Externa para Media</label>
                        <input
                          type="text"
                          value={formData.external_media_address}
                          onChange={(e) => setFormData({...formData, external_media_address: e.target.value})}
                          placeholder="200.100.50.25"
                        />
                        <small>IP pública para RTP</small>
                      </div>
                      <div className="form-group">
                        <label>IP Externa para Señalización</label>
                        <input
                          type="text"
                          value={formData.external_signaling_address}
                          onChange={(e) => setFormData({...formData, external_signaling_address: e.target.value})}
                          placeholder="200.100.50.25"
                        />
                        <small>IP pública para SIP</small>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* PESTAÑA: AVANZADO */}
              {activeTab === 'advanced' && (
                <div className="tab-content">
                  <h3>⚙️ Opciones Avanzadas</h3>
                  
                  <div className="form-section">
                    <h4>Configuración Regional</h4>
                    <div className="form-group">
                      <label>Idioma</label>
                      <select
                        value={formData.language}
                        onChange={(e) => setFormData({...formData, language: e.target.value})}
                      >
                        <option value="es">Español</option>
                        <option value="en">English</option>
                        <option value="pt">Português</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-section">
                    <h4>Manejo de Identidad</h4>
                    
                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.trust_id_inbound}
                          onChange={(e) => setFormData({...formData, trust_id_inbound: e.target.checked})}
                        />
                        <strong>Confiar en ID Entrante</strong>
                        <small>Confiar en Caller ID de llamadas entrantes</small>
                      </label>
                    </div>

                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.trust_id_outbound}
                          onChange={(e) => setFormData({...formData, trust_id_outbound: e.target.checked})}
                        />
                        <strong>Confiar en ID Saliente</strong>
                        <small>Confiar en Caller ID de llamadas salientes</small>
                      </label>
                    </div>

                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.send_pai}
                          onChange={(e) => setFormData({...formData, send_pai: e.target.checked})}
                        />
                        <strong>Enviar P-Asserted-Identity</strong>
                        <small>Incluir header PAI en llamadas</small>
                      </label>
                    </div>

                    <div className="checkbox-group">
                      <label>
                        <input
                          type="checkbox"
                          checked={formData.send_rpid}
                          onChange={(e) => setFormData({...formData, send_rpid: e.target.checked})}
                        />
                        <strong>Enviar Remote-Party-ID</strong>
                        <small>Incluir header RPID en llamadas</small>
                      </label>
                    </div>
                  </div>
                </div>
              )}

              {/* PESTAÑA: CUSTOM (solo si trunk_type es custom) */}
              {activeTab === 'custom' && formData.trunk_type === 'custom' && (
                <div className="tab-content">
                  <h3>💻 Configuración PJSIP Wizard Personalizada</h3>
                  
                  <div className="alert alert-warning">
                    <strong>⚠️ Modo Avanzado</strong>
                    <p>Esta configuración se insertará directamente en pjsip_wizard.conf. Asegúrate de usar sintaxis válida de PJSIP Wizard.</p>
                  </div>

                  <div className="form-group">
                    <label>Configuración PJSIP Wizard Raw</label>
                    <textarea
                      value={formData.pjsip_config_custom}
                      onChange={(e) => setFormData({...formData, pjsip_config_custom: e.target.value})}
                      placeholder={`Ejemplo:\ntype = wizard\ntransport = trunk-transport\nendpoint/context = from-pstn\nendpoint/allow = !all,ulaw,alaw\n...`}
                      rows="15"
                      style={{ fontFamily: 'monospace', fontSize: '13px' }}
                    />
                    <small>Configuración PJSIP Wizard completa. Consulta la documentación de Asterisk PJSIP Wizard.</small>
                  </div>
                </div>
              )}

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary">
                  {editingId ? 'Actualizar' : 'Crear'} Troncal
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
