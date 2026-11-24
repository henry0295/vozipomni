"""Flujos de ejemplo que se pueden crear desde el designer ("Nuevo desde plantilla")."""


class _B:
    """Ayudante para armar definiciones con posiciones en una grilla."""

    def __init__(self):
        self.nodes, self.edges, self._e = [], [], 0

    def node(self, nid, ntype, col, row, **data):
        self.nodes.append({'id': nid, 'type': ntype, 'data': data,
                           'position': {'x': col * 300, 'y': row * 170}})
        return nid

    def link(self, src, target, handle='next'):
        self._e += 1
        self.edges.append({'id': f'e{self._e}', 'source': src, 'sourceHandle': handle, 'target': target})

    def build(self, start):
        return {'start': start, 'nodes': self.nodes, 'edges': self.edges}


def basic_menu(params):
    b = _B()
    b.node('menu', 'list', 0, 0, title='Menú principal',
           text='Hola {{contact.name}} 👋 Soy el asistente virtual. ¿En qué te ayudo?',
           button_label='Ver opciones', variable='opcion', options=[
               {'id': 'info', 'label': 'Información', 'description': 'Horarios y canales'},
               {'id': 'asesor', 'label': 'Hablar con un asesor'},
           ])
    b.node('info', 'message', 1, 0, title='Información',
           text='Atendemos de lunes a viernes de 8:00 a. m. a 6:00 p. m.')
    b.node('fin', 'end', 2, 0, title='Fin', text='¡Gracias por escribirnos!')
    b.node('horario', 'business_hours', 1, 1, title='¿Horario de atención?')
    b.node('asesor', 'handoff', 2, 1, title='Pasar a asesor', text='Te comunico con un asesor, un momento por favor.')
    b.node('cerrado', 'end', 2, 2, title='Fuera de horario',
           text='En este momento no hay asesores disponibles. Escríbenos en horario de atención.')
    b.link('menu', 'info', 'opt:info')
    b.link('menu', 'horario', 'opt:asesor')
    b.link('info', 'fin')
    b.link('horario', 'asesor', 'open')
    b.link('horario', 'cerrado', 'closed')
    return b.build('menu')


def glpi_support(params):
    cid = int(params.get('connector_id') or 0) or None
    b = _B()
    b.node('buscar', 'connector', 0, 0, title='Identificar cliente en GLPI',
           connector_id=cid, action='find_requester', inputs={'phone': '{{contact.phone}}'},
           output_variable='solicitante')
    b.node('pedir_email', 'question', 0, 1, title='Pedir email',
           text='Hola 👋 No encontré tu número registrado. ¿Cuál es tu correo electrónico?',
           variable='email', validation='email', error_text='Escribe un correo válido, por ejemplo nombre@empresa.com')
    b.node('buscar_email', 'connector', 0, 2, title='Buscar por email',
           connector_id=cid, action='find_requester', inputs={'email': '{{email}}'},
           output_variable='solicitante')
    b.node('menu', 'list', 1, 0, title='Menú de soporte',
           text='Hola {{solicitante.name}} 👋 Soy el asistente de soporte. ¿Qué necesitas?',
           button_label='Ver opciones', options=[
               {'id': 'crear', 'label': 'Reportar una falla', 'description': 'Crear un ticket de soporte'},
               {'id': 'estado', 'label': 'Estado de mi ticket'},
               {'id': 'asesor', 'label': 'Hablar con un asesor'},
           ])
    # Crear ticket
    b.node('categoria', 'list', 2, 0, title='Categoría', text='¿Sobre qué es tu solicitud?',
           button_label='Categorías', variable='categoria', options=[
               {'id': 'internet', 'label': 'Internet'},
               {'id': 'telefonia', 'label': 'Telefonía / PBX'},
               {'id': 'facturacion', 'label': 'Facturación'},
               {'id': 'otro', 'label': 'Otro'},
           ])
    b.node('descripcion', 'question', 3, 0, title='Descripción',
           text='Describe el problema con el mayor detalle posible (qué pasa, desde cuándo, a quién afecta).',
           variable='descripcion', validation='text')
    b.node('urgencia', 'buttons', 4, 0, title='Urgencia', text='¿Qué tan urgente es?', variable='urgencia',
           options=[{'id': 'baja', 'label': 'Baja'}, {'id': 'media', 'label': 'Media'}, {'id': 'alta', 'label': 'Alta'}])
    b.node('crear_ticket', 'connector', 5, 0, title='Crear ticket en GLPI',
           text='Un momento, estoy creando tu ticket…', connector_id=cid, action='create_ticket',
           inputs={'title': 'WhatsApp — {{categoria}}',
                   'description': '{{descripcion}}\n\nCliente: {{contact.name}} ({{contact.phone}})\nCanal: WhatsApp',
                   'requester_id': '{{solicitante.id}}', 'urgency': '{{urgencia}}'},
           output_variable='ticket')
    b.node('creado', 'buttons', 6, 0, title='Ticket creado',
           text='✅ Creamos el ticket #{{ticket.id}}. Un técnico te contactará pronto.\n¿Quieres hablar ya con un asesor?',
           options=[{'id': 'si', 'label': 'Sí, por favor'}, {'id': 'no', 'label': 'No, gracias'}])
    b.node('gracias', 'end', 7, 0, title='Fin', text='¡Gracias! Puedes consultar el estado escribiéndonos de nuevo.')
    # Estado
    b.node('tiene_solicitante', 'condition', 2, 2, title='¿Cliente identificado?',
           rules=[{'variable': 'solicitante.id', 'operator': 'not_empty', 'value': ''}], match='all')
    b.node('mis_tickets', 'connector', 3, 2, title='Tickets abiertos', connector_id=cid, action='my_tickets',
           inputs={'requester_id': '{{solicitante.id}}'}, output_variable='tickets')
    b.node('elegir_ticket', 'dynamic_list', 4, 2, title='Elegir ticket', text='Estos son tus tickets abiertos:',
           button_label='Ver tickets', source_variable='tickets', label_field='#{{id}} {{title}}',
           description_field='{{status}}', variable='seleccion')
    b.node('consultar', 'connector', 5, 2, title='Consultar ticket', connector_id=cid, action='get_ticket',
           inputs={'ticket_id': '{{seleccion.id}}'}, output_variable='t')
    b.node('pedir_numero', 'question', 4, 3, title='Pedir número de ticket',
           text='Escribe el número de tu ticket.', variable='numero', validation='number',
           error_text='Escribe solo el número, por ejemplo 1234')
    b.node('consultar_numero', 'connector', 5, 3, title='Consultar por número', connector_id=cid,
           action='get_ticket', inputs={'ticket_id': '{{numero}}'}, output_variable='t')
    b.node('mostrar', 'buttons', 6, 2, title='Mostrar estado',
           text='🎫 Ticket #{{t.id}} — {{t.title}}\nEstado: {{t.status}}\nÚltimo seguimiento: {{t.last_followup}}',
           options=[{'id': 'menu', 'label': 'Volver al menú'}, {'id': 'asesor', 'label': 'Hablar con asesor'}])
    b.node('no_existe', 'message', 6, 3, title='No encontrado', text='No encontré ese ticket.')
    # Asesor
    b.node('horario', 'business_hours', 2, 4, title='¿Horario de atención?')
    b.node('asesor', 'handoff', 3, 4, title='Pasar a asesor', text='Te comunico con un asesor de soporte 👩‍💻',
           note='Ticket: {{ticket.id}} · Categoría: {{categoria}}')
    b.node('cerrado', 'end', 3, 5, title='Fuera de horario',
           text='Nuestros asesores atienden de lunes a viernes de 8:00 a. m. a 6:00 p. m. '
                'Puedes crear un ticket y te contactaremos.')
    b.node('error', 'handoff', 6, 1, title='Error de GLPI',
           text='No pude registrar la información en este momento. Te comunico con un asesor.')

    b.link('buscar', 'menu', 'success')
    b.link('buscar', 'pedir_email', 'empty')
    b.link('buscar', 'menu', 'error')
    b.link('pedir_email', 'buscar_email')
    b.link('buscar_email', 'menu', 'success')
    b.link('buscar_email', 'menu', 'empty')
    b.link('buscar_email', 'menu', 'error')
    b.link('menu', 'categoria', 'opt:crear')
    b.link('menu', 'tiene_solicitante', 'opt:estado')
    b.link('menu', 'horario', 'opt:asesor')
    for opt in ('internet', 'telefonia', 'facturacion', 'otro'):
        b.link('categoria', 'descripcion', f'opt:{opt}')
    b.link('descripcion', 'urgencia')
    for opt in ('baja', 'media', 'alta'):
        b.link('urgencia', 'crear_ticket', f'opt:{opt}')
    b.link('crear_ticket', 'creado', 'success')
    b.link('crear_ticket', 'error', 'error')
    b.link('creado', 'horario', 'opt:si')
    b.link('creado', 'gracias', 'opt:no')
    b.link('tiene_solicitante', 'mis_tickets', 'true')
    b.link('tiene_solicitante', 'pedir_numero', 'false')
    b.link('mis_tickets', 'elegir_ticket', 'success')
    b.link('mis_tickets', 'pedir_numero', 'empty')
    b.link('mis_tickets', 'pedir_numero', 'error')
    b.link('elegir_ticket', 'consultar')
    b.link('elegir_ticket', 'pedir_numero', 'empty')
    b.link('consultar', 'mostrar', 'success')
    b.link('consultar', 'no_existe', 'empty')
    b.link('consultar', 'error', 'error')
    b.link('pedir_numero', 'consultar_numero')
    b.link('consultar_numero', 'mostrar', 'success')
    b.link('consultar_numero', 'no_existe', 'empty')
    b.link('consultar_numero', 'error', 'error')
    b.link('no_existe', 'menu')
    b.link('mostrar', 'menu', 'opt:menu')
    b.link('mostrar', 'horario', 'opt:asesor')
    b.link('horario', 'asesor', 'open')
    b.link('horario', 'cerrado', 'closed')
    return b.build('buscar')


FLOW_TEMPLATES = {
    'basic': {'name': 'Menú básico', 'description': 'Menú, información, horario y paso a asesor',
              'definition': basic_menu},
    'glpi_support': {'name': 'Soporte con GLPI',
                     'description': 'Identifica al cliente, crea tickets y consulta su estado en GLPI',
                     'definition': glpi_support},
}
