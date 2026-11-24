/**
 * Tipos de bloque del designer de bots. Debe coincidir con backend/apps/chatbot/schema.py
 */
export interface BlockMeta {
  label: string
  icon: string
  color: string        // clases tailwind del borde/encabezado
  help: string
}

export const BLOCKS: Record<string, BlockMeta> = {
  message: { label: 'Mensaje', icon: 'i-heroicons-chat-bubble-left', color: 'sky', help: 'Envía un texto y continúa' },
  buttons: { label: 'Botones', icon: 'i-heroicons-squares-2x2', color: 'violet', help: 'Hasta 3 botones de respuesta' },
  list: { label: 'Lista / Menú', icon: 'i-heroicons-list-bullet', color: 'violet', help: 'Menú de hasta 10 opciones' },
  question: { label: 'Pregunta', icon: 'i-heroicons-question-mark-circle', color: 'amber', help: 'Guarda la respuesta en una variable' },
  condition: { label: 'Condición', icon: 'i-heroicons-arrows-right-left', color: 'orange', help: 'Separa el flujo según variables' },
  business_hours: { label: 'Horario', icon: 'i-heroicons-clock', color: 'orange', help: 'Dentro o fuera del horario de atención' },
  set_variable: { label: 'Asignar variable', icon: 'i-heroicons-variable', color: 'gray', help: 'Guarda un valor en una variable' },
  connector: { label: 'Conector', icon: 'i-heroicons-bolt', color: 'emerald', help: 'GLPI, API HTTP u otro sistema' },
  dynamic_list: { label: 'Lista dinámica', icon: 'i-heroicons-queue-list', color: 'emerald', help: 'Menú con los datos de un conector' },
  ai_intent: { label: 'Entender intención (IA)', icon: 'i-heroicons-sparkles', color: 'fuchsia', help: 'Entiende lo que escribe el cliente y extrae datos' },
  handoff: { label: 'Pasar a asesor', icon: 'i-heroicons-user', color: 'rose', help: 'Asigna la conversación a un agente' },
  end: { label: 'Fin', icon: 'i-heroicons-stop-circle', color: 'gray', help: 'Despide y cierra la conversación' },
}

export const PALETTE = [
  { group: 'Mensajes', items: ['message', 'buttons', 'list', 'question'] },
  { group: 'Lógica', items: ['condition', 'business_hours', 'set_variable'] },
  { group: 'Integraciones', items: ['connector', 'dynamic_list'] },
  { group: 'Inteligencia artificial', items: ['ai_intent'] },
  { group: 'Salida', items: ['handoff', 'end'] },
]

export const VALIDATIONS = [
  { label: 'Texto', value: 'text' }, { label: 'Número', value: 'number' },
  { label: 'Email', value: 'email' }, { label: 'Teléfono', value: 'phone' },
  { label: 'Documento', value: 'document' }, { label: 'Fecha (dd/mm/aaaa)', value: 'date' },
  { label: 'Expresión regular', value: 'regex' },
]

export const OPERATORS = [
  { label: 'es igual a', value: 'equals' }, { label: 'es distinto de', value: 'not_equals' },
  { label: 'contiene', value: 'contains' }, { label: 'está vacía', value: 'empty' },
  { label: 'tiene valor', value: 'not_empty' }, { label: 'es mayor que', value: 'gt' },
  { label: 'es menor que', value: 'lt' },
]

const FIXED_OUTPUTS: Record<string, { id: string, label: string }[]> = {
  message: [{ id: 'next', label: 'Siguiente' }],
  question: [{ id: 'next', label: 'Respuesta válida' }, { id: 'invalid', label: 'Intentos agotados' }],
  condition: [{ id: 'true', label: 'Se cumple' }, { id: 'false', label: 'No se cumple' }],
  business_hours: [{ id: 'open', label: 'En horario' }, { id: 'closed', label: 'Fuera de horario' }],
  set_variable: [{ id: 'next', label: 'Siguiente' }],
  connector: [{ id: 'success', label: 'Éxito' }, { id: 'empty', label: 'Sin resultados' }, { id: 'error', label: 'Error' }],
  dynamic_list: [{ id: 'next', label: 'Elemento elegido' }, { id: 'empty', label: 'Lista vacía' }],
  handoff: [],
  end: [],
}

export function blockOutputs(data: any) {
  if (data.kind === 'ai_intent') {
    return [
      ...(data.intents || []).map((i: any) => ({ id: `intent:${i.id}`, label: i.name || i.id })),
      { id: 'unknown', label: 'No entendí' },
      { id: 'error', label: 'Error de IA' },
    ]
  }
  if (data.kind === 'buttons' || data.kind === 'list') {
    return (data.options || []).map((o: any) => ({ id: `opt:${o.id}`, label: o.label || '(sin texto)' }))
  }
  return FIXED_OUTPUTS[data.kind] || []
}

export const uid = (p = 'n') => `${p}${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`

export function defaultData(kind: string): any {
  const title = BLOCKS[kind]?.label || kind
  switch (kind) {
    case 'message': return { title, text: '' }
    case 'buttons': return { title, text: '¿Qué deseas hacer?', options: [{ id: uid('o'), label: 'Opción 1' }, { id: uid('o'), label: 'Opción 2' }] }
    case 'list': return { title, text: 'Elige una opción:', button_label: 'Ver opciones', options: [{ id: uid('o'), label: 'Opción 1', description: '' }] }
    case 'question': return { title, text: '', variable: 'respuesta', validation: 'text', error_text: '', max_retries: 3 }
    case 'condition': return { title, match: 'all', rules: [{ variable: '', operator: 'equals', value: '' }] }
    case 'business_hours': return { title, time_condition_id: null }
    case 'set_variable': return { title, variable: 'variable', value: '' }
    case 'connector': return { title, text: '', connector_id: null, action: '', inputs: {}, output_variable: 'resultado', mock_result: {} }
    case 'dynamic_list': return { title, text: 'Elige una opción:', button_label: 'Ver opciones', source_variable: 'resultado', label_field: 'name', description_field: '', variable: 'seleccion' }
    case 'ai_intent': return {
      title, source: 'wait', text: 'Cuéntame en pocas palabras, ¿en qué te puedo ayudar?', source_variable: '',
      provider_id: null, min_confidence: 0.5, output_variable: 'ia',
      intents: [
        { id: 'soporte', name: 'Soporte técnico', description: 'Fallas, errores o algo que no funciona', examples: 'no tengo internet\nel teléfono no da tono' },
        { id: 'asesor', name: 'Hablar con un asesor', description: 'Pide atención humana', examples: 'quiero hablar con alguien' },
      ],
      fields: [],
    }
    case 'handoff': return { title, text: 'Te comunico con un asesor, un momento por favor.', campaign_id: null, note: '' }
    case 'end': return { title, text: '¡Gracias por escribirnos!' }
    default: return { title }
  }
}

/** Definición del backend → nodos/aristas de Vue Flow */
export function toFlow(def: any) {
  const nodes = (def?.nodes || []).map((n: any) => ({
    id: n.id, type: 'bot', position: n.position || { x: 0, y: 0 },
    data: { kind: n.type, ...(n.data || {}) },
  }))
  const edges = (def?.edges || []).map((e: any) => ({
    id: e.id || uid('e'), source: e.source, target: e.target, sourceHandle: e.sourceHandle || 'next',
  }))
  return { nodes, edges, start: def?.start || nodes[0]?.id || '' }
}

/** Vue Flow → definición del backend */
export function fromFlow(nodes: any[], edges: any[], start: string) {
  const ids = new Set(nodes.map(n => n.id))
  return {
    start,
    nodes: nodes.map((n) => {
      const { kind, ...data } = n.data || {}
      return { id: n.id, type: kind, data, position: { x: Math.round(n.position.x), y: Math.round(n.position.y) } }
    }),
    edges: edges.filter(e => ids.has(e.source) && ids.has(e.target)).map(e => ({
      id: e.id, source: e.source, sourceHandle: e.sourceHandle || 'next', target: e.target,
    })),
  }
}

/** Variables que el flujo define (para ayudar al escribir {{variable}}) */
export function flowVariables(nodes: any[]) {
  const vars = new Set(['contact.name', 'contact.phone', 'contact.email', 'channel.type'])
  for (const n of nodes) {
    const d = n.data || {}
    if (d.variable) vars.add(d.variable)
    if (d.output_variable) vars.add(d.output_variable)
    if (d.kind === 'ai_intent') {
      vars.add(`${d.output_variable || 'ia'}.intent`)
      for (const f of d.fields || []) if (f.name) vars.add(f.name)
    }
  }
  return [...vars]
}
