import api from './api'

const TELEPHONY_BASE = '/telephony'

// Extensiones
export const extensionsService = {
  getAll: () => api.get(`${TELEPHONY_BASE}/extensions/`),
  getOne: (id) => api.get(`${TELEPHONY_BASE}/extensions/${id}/`),
  create: (data) => api.post(`${TELEPHONY_BASE}/extensions/`, data),
  update: (id, data) => api.put(`${TELEPHONY_BASE}/extensions/${id}/`, data),
  patch: (id, data) => api.patch(`${TELEPHONY_BASE}/extensions/${id}/`, data),
  delete: (id) => api.delete(`${TELEPHONY_BASE}/extensions/${id}/`),
  reloadConfig: (id) => api.post(`${TELEPHONY_BASE}/extensions/${id}/reload_config/`),
}

// Troncales SIP
export const trunksService = {
  getAll: () => api.get(`${TELEPHONY_BASE}/trunks/`),
  getOne: (id) => api.get(`${TELEPHONY_BASE}/trunks/${id}/`),
  create: (data) => api.post(`${TELEPHONY_BASE}/trunks/`, data),
  update: (id, data) => api.put(`${TELEPHONY_BASE}/trunks/${id}/`, data),
  patch: (id, data) => api.patch(`${TELEPHONY_BASE}/trunks/${id}/`, data),
  delete: (id) => api.delete(`${TELEPHONY_BASE}/trunks/${id}/`),
  testConnection: (id) => api.post(`${TELEPHONY_BASE}/trunks/${id}/test_connection/`),
}

// IVR
export const ivrService = {
  getAll: () => api.get(`${TELEPHONY_BASE}/ivr/`),
  getOne: (id) => api.get(`${TELEPHONY_BASE}/ivr/${id}/`),
  create: (data) => api.post(`${TELEPHONY_BASE}/ivr/`, data),
  update: (id, data) => api.put(`${TELEPHONY_BASE}/ivr/${id}/`, data),
  patch: (id, data) => api.patch(`${TELEPHONY_BASE}/ivr/${id}/`, data),
  delete: (id) => api.delete(`${TELEPHONY_BASE}/ivr/${id}/`),
}

// Rutas Entrantes
export const inboundRoutesService = {
  getAll: () => api.get(`${TELEPHONY_BASE}/inbound-routes/`),
  getOne: (id) => api.get(`${TELEPHONY_BASE}/inbound-routes/${id}/`),
  create: (data) => api.post(`${TELEPHONY_BASE}/inbound-routes/`, data),
  update: (id, data) => api.put(`${TELEPHONY_BASE}/inbound-routes/${id}/`, data),
  patch: (id, data) => api.patch(`${TELEPHONY_BASE}/inbound-routes/${id}/`, data),
  delete: (id) => api.delete(`${TELEPHONY_BASE}/inbound-routes/${id}/`),
}

// Rutas Salientes
export const outboundRoutesService = {
  getAll: () => api.get(`${TELEPHONY_BASE}/outbound-routes/`),
  getOne: (id) => api.get(`${TELEPHONY_BASE}/outbound-routes/${id}/`),
  create: (data) => api.post(`${TELEPHONY_BASE}/outbound-routes/`, data),
  update: (id, data) => api.put(`${TELEPHONY_BASE}/outbound-routes/${id}/`, data),
  patch: (id, data) => api.patch(`${TELEPHONY_BASE}/outbound-routes/${id}/`, data),
  delete: (id) => api.delete(`${TELEPHONY_BASE}/outbound-routes/${id}/`),
}

// Buzones de Voz
export const voicemailService = {
  getAll: () => api.get(`${TELEPHONY_BASE}/voicemail/`),
  getOne: (id) => api.get(`${TELEPHONY_BASE}/voicemail/${id}/`),
  create: (data) => api.post(`${TELEPHONY_BASE}/voicemail/`, data),
  update: (id, data) => api.put(`${TELEPHONY_BASE}/voicemail/${id}/`, data),
  patch: (id, data) => api.patch(`${TELEPHONY_BASE}/voicemail/${id}/`, data),
  delete: (id) => api.delete(`${TELEPHONY_BASE}/voicemail/${id}/`),
  getMessages: (id) => api.get(`${TELEPHONY_BASE}/voicemail/${id}/messages/`),
}

// Música en Espera
export const musicOnHoldService = {
  getAll: () => api.get(`${TELEPHONY_BASE}/music-on-hold/`),
  getOne: (id) => api.get(`${TELEPHONY_BASE}/music-on-hold/${id}/`),
  create: (data) => api.post(`${TELEPHONY_BASE}/music-on-hold/`, data),
  update: (id, data) => api.put(`${TELEPHONY_BASE}/music-on-hold/${id}/`, data),
  patch: (id, data) => api.patch(`${TELEPHONY_BASE}/music-on-hold/${id}/`, data),
  delete: (id) => api.delete(`${TELEPHONY_BASE}/music-on-hold/${id}/`),
  getFiles: (id) => api.get(`${TELEPHONY_BASE}/music-on-hold/${id}/files/`),
}

// Condiciones de Horario
export const timeConditionsService = {
  getAll: () => api.get(`${TELEPHONY_BASE}/time-conditions/`),
  getOne: (id) => api.get(`${TELEPHONY_BASE}/time-conditions/${id}/`),
  create: (data) => api.post(`${TELEPHONY_BASE}/time-conditions/`, data),
  update: (id, data) => api.put(`${TELEPHONY_BASE}/time-conditions/${id}/`, data),
  patch: (id, data) => api.patch(`${TELEPHONY_BASE}/time-conditions/${id}/`, data),
  delete: (id) => api.delete(`${TELEPHONY_BASE}/time-conditions/${id}/`),
  evaluate: (id) => api.get(`${TELEPHONY_BASE}/time-conditions/${id}/evaluate/`),
}

export default {
  extensions: extensionsService,
  trunks: trunksService,
  ivr: ivrService,
  inboundRoutes: inboundRoutesService,
  outboundRoutes: outboundRoutesService,
  voicemail: voicemailService,
  musicOnHold: musicOnHoldService,
  timeConditions: timeConditionsService,
}
