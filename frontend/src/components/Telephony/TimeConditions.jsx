import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { timeConditionsService } from '../../services/telephonyService'
import './TimeConditions.css'

const TimeConditions = () => {
  const [showModal, setShowModal] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const queryClient = useQueryClient()

  const [formData, setFormData] = useState({
    name: '',
    time_groups: [{ days: [], startTime: '09:00', endTime: '18:00' }],
    true_destination_type: 'ivr',
    true_destination: '',
    false_destination_type: 'voicemail',
    false_destination: '',
  })

  const { data: conditions = [], isLoading } = useQuery({
    queryKey: ['time-conditions'],
    queryFn: async () => {
      const response = await timeConditionsService.getAll()
      const data = response.data?.results || response.data
      return Array.isArray(data) ? data : []
    },
  })

  const createMutation = useMutation({
    mutationFn: timeConditionsService.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['time-conditions'])
      toast.success('Condición creada exitosamente')
      resetForm()
    },
    onError: () => toast.error('Error al crear condición'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => timeConditionsService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['time-conditions'])
      toast.success('Condición actualizada exitosamente')
      resetForm()
    },
    onError: () => toast.error('Error al actualizar condición'),
  })

  const deleteMutation = useMutation({
    mutationFn: timeConditionsService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['time-conditions'])
      toast.success('Condición eliminada')
    },
    onError: () => toast.error('Error al eliminar condición'),
  })

  const resetForm = () => {
    setShowModal(false)
    setEditingId(null)
    setFormData({
      name: '',
      time_groups: [{ days: [], startTime: '09:00', endTime: '18:00' }],
      true_destination_type: 'ivr',
      true_destination: '',
      false_destination_type: 'voicemail',
      false_destination: '',
    })
  }

  const handleEdit = (condition) => {
    setEditingId(condition.id)
    setFormData({
      name: condition.name,
      time_groups: condition.time_groups || [{ days: [], startTime: '09:00', endTime: '18:00' }],
      true_destination_type: condition.true_destination_type,
      true_destination: condition.true_destination,
      false_destination_type: condition.false_destination_type,
      false_destination: condition.false_destination,
    })
    setShowModal(true)
  }

  const addTimeGroup = () => {
    setFormData({
      ...formData,
      time_groups: [...formData.time_groups, { days: [], startTime: '09:00', endTime: '18:00' }]
    })
  }

  const removeTimeGroup = (index) => {
    const newGroups = formData.time_groups.filter((_, i) => i !== index)
    setFormData({ ...formData, time_groups: newGroups })
  }

  const updateTimeGroup = (index, field, value) => {
    const newGroups = [...formData.time_groups]
    newGroups[index][field] = value
    setFormData({ ...formData, time_groups: newGroups })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta condición de horario?')) {
      deleteMutation.mutate(id)
    }
  }

  if (isLoading) return <div className="time-conditions-container"><p>Cargando...</p></div>

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
                    <button className="btn-icon" title="Editar" onClick={() => handleEdit(condition)}>✏️</button>
                    <button className="btn-icon" title="Eliminar" onClick={() => handleDelete(condition.id)}>🗑️</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={resetForm}>
          <div className="modal-content large-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingId ? 'Editar' : 'Nueva'} Condición de Horario</h2>
              <button className="close-btn" onClick={resetForm}>×</button>
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

                {formData.time_groups.map((group, index) => (
                  <div key={index} className="time-group-card">
                    <div className="card-header">
                      <span>Horario {index + 1}</span>
                      {formData.time_groups.length > 1 && (
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
                        value={formData.true_destination_type}
                        onChange={(e) => setFormData({ ...formData, true_destination_type: e.target.value })}
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
                        value={formData.true_destination}
                        onChange={(e) => setFormData({ ...formData, true_destination: e.target.value })}
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
                        value={formData.false_destination_type}
                        onChange={(e) => setFormData({ ...formData, false_destination_type: e.target.value })}
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
                        value={formData.false_destination}
                        onChange={(e) => setFormData({ ...formData, false_destination: e.target.value })}
                        placeholder="Seleccione destino"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={resetForm}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={createMutation.isPending || updateMutation.isPending}>
                  {editingId 
                    ? (updateMutation.isPending ? 'Actualizando...' : 'Actualizar Condición')
                    : (createMutation.isPending ? 'Creando...' : 'Crear Condición')
                  }
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
