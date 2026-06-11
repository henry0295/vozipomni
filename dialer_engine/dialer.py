"""
VozipOmni Dialer Engine
Motor de discado para campañas: Progresivas, Predictivas, Preview, Call Blasting y Manuales
Utiliza Asterisk AMI para originar llamadas
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
import redis.asyncio as aioredis
from panoramisk.manager import Manager as AMIManager
import os
import json
import pytz
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Custom exceptions
class DialerException(Exception):
    """Base exception for dialer errors"""
    pass

class AMIConnectionError(DialerException):
    """AMI connection failed"""
    pass

class CampaignNotFoundError(DialerException):
    """Campaign not found"""
    pass

class InvalidContactError(DialerException):
    """Invalid contact data"""
    pass

class CallOriginationError(DialerException):
    """Failed to originate call"""
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CampaignType(Enum):
    MANUAL = "manual"
    PROGRESSIVE = "progressive"
    PREDICTIVE = "predictive"
    PREVIEW = "preview"
    CALL_BLASTING = "call_blasting"

class CallStatus(Enum):
    QUEUED = "queued"
    DIALING = "dialing"
    RINGING = "ringing"
    ANSWERED = "answered"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    FAILED = "failed"
    COMPLETED = "completed"

class DialerEngine:
    def __init__(self):
        # Configuración desde variables de entorno
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.asterisk_host = os.getenv('ASTERISK_HOST', 'asterisk')
        self.asterisk_ami_port = int(os.getenv('ASTERISK_AMI_PORT', 5038))
        self.asterisk_ami_user = os.getenv('ASTERISK_AMI_USER', 'admin')
        self.asterisk_ami_password = os.getenv('ASTERISK_AMI_PASSWORD', '')
        
        self.redis_client = None
        self.ami_client = None
        
        # Estado del dialer
        self.active_campaigns = {}
        self.active_calls = {}
        self.agents_status = {}
        
        # Configuraciones predictivas
        self.predictive_ratio = 1.5  # Ratio de llamadas por agente
        self.abandon_rate_target = 0.03  # 3% de abandono objetivo
        
    async def initialize(self):
        """Inicializar conexiones"""
        try:
            # Redis
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Conectado a Redis")
        except Exception as e:
            logger.error(f"Error conectando a Redis: {e}")
            raise AMIConnectionError(f"Redis connection failed: {e}")
        
        try:
            # Asterisk AMI
            self.ami_client = AMIManager(
                host=self.asterisk_host,
                port=self.asterisk_ami_port,
                username=self.asterisk_ami_user,
                secret=self.asterisk_ami_password,
                ping_delay=10
            )
            
            await self.ami_client.connect()
            logger.info(f"Conectado a Asterisk AMI en {self.asterisk_host}")
        except Exception as e:
            logger.error(f"Error conectando a Asterisk AMI: {e}")
            raise AMIConnectionError(f"AMI connection failed: {e}")
        
        # Registrar event listeners
        self.ami_client.register_event('Newchannel', self.on_new_channel)
        self.ami_client.register_event('Hangup', self.on_hangup)
        self.ami_client.register_event('AgentConnect', self.on_agent_connect)
        self.ami_client.register_event('AgentComplete', self.on_agent_complete)
        
    async def start_campaign(self, campaign_id: int, campaign_type: str):
        """Iniciar una campaña de discado"""
        logger.info(f"Iniciando campaña {campaign_id} tipo: {campaign_type}")
        
        # Obtener configuración de campaña desde Redis
        campaign_config = await self.get_campaign_config(campaign_id)
        
        if not campaign_config:
            logger.error(f"Campaña {campaign_id} no encontrada")
            return
        
        self.active_campaigns[campaign_id] = {
            'type': campaign_type,
            'config': campaign_config,
            'started_at': datetime.now(),
            'calls_made': 0,
            'calls_answered': 0,
            'calls_abandoned': 0
        }
        
        # Iniciar loop de discado según el tipo
        if campaign_type == CampaignType.PROGRESSIVE.value:
            asyncio.create_task(self.progressive_dialer_loop(campaign_id))
        elif campaign_type == CampaignType.PREDICTIVE.value:
            asyncio.create_task(self.predictive_dialer_loop(campaign_id))
        elif campaign_type == CampaignType.PREVIEW.value:
            asyncio.create_task(self.preview_dialer_loop(campaign_id))
        elif campaign_type == CampaignType.CALL_BLASTING.value:
            asyncio.create_task(self.call_blasting_loop(campaign_id))
            
    async def stop_campaign(self, campaign_id: int):
        """Detener una campaña"""
        if campaign_id in self.active_campaigns:
            self.active_campaigns[campaign_id]['stopped'] = True
            logger.info(f"Campaña {campaign_id} marcada para detener")
            
    async def progressive_dialer_loop(self, campaign_id: int):
        """
        Campaña PROGRESIVA: Discado 1:1
        Una llamada por agente disponible
        """
        logger.info(f"Iniciando progressive dialer para campaña {campaign_id}")
        
        while campaign_id in self.active_campaigns:
            campaign = self.active_campaigns[campaign_id]
            
            if campaign.get('stopped'):
                break
            
            # Obtener agentes disponibles
            available_agents = await self.get_available_agents(campaign_id)
            
            for agent in available_agents:
                # Un contacto por agente
                contact = await self.get_next_contact(campaign_id)
                
                if contact:
                    await self.originate_call(
                        campaign_id=campaign_id,
                        contact=contact,
                        agent=agent
                    )
                    campaign['calls_made'] += 1
            
            # Esperar antes del siguiente ciclo
            await asyncio.sleep(2)
        
        logger.info(f"Progressive dialer detenido para campaña {campaign_id}")
        
    async def predictive_dialer_loop(self, campaign_id: int):
        """
        Campaña PREDICTIVA: Algoritmo inteligente
        Múltiples llamadas por agente basado en estadísticas
        """
        logger.info(f"Iniciando predictive dialer para campaña {campaign_id}")
        
        while campaign_id in self.active_campaigns:
            campaign = self.active_campaigns[campaign_id]
            
            if campaign.get('stopped'):
                break
            
            # Obtener agentes disponibles
            available_agents = await self.get_available_agents(campaign_id)
            num_agents = len(available_agents)
            
            if num_agents == 0:
                await asyncio.sleep(1)
                continue
            
            # Calcular ratio de discado predictivo
            current_ratio = await self.calculate_predictive_ratio(campaign_id)
            calls_to_make = int(num_agents * current_ratio)
            
            # Obtener contactos
            for _ in range(calls_to_make):
                contact = await self.get_next_contact(campaign_id)
                
                if contact:
                    await self.originate_call(
                        campaign_id=campaign_id,
                        contact=contact,
                        agent=None  # Se asigna cuando contesta
                    )
                    campaign['calls_made'] += 1
            
            # Esperar antes del siguiente ciclo
            await asyncio.sleep(1)
        
        logger.info(f"Predictive dialer detenido para campaña {campaign_id}")
        
    async def preview_dialer_loop(self, campaign_id: int):
        """
        Campaña PREVIEW: Agente revisa datos del contacto antes de que se origine la llamada.
        El backend publica contactos en 'campaign:{id}:preview:pending'. El agente acepta
        (lpush a ':preview:accepted') o rechaza (lpush a ':preview:rejected') con su agent_id.
        """
        logger.info(f"Iniciando preview dialer para campaña {campaign_id}")
        config = await self.get_campaign_config(campaign_id)
        timeout_secs = config.get('preview_timeout', 30) if config else 30

        while campaign_id in self.active_campaigns:
            campaign = self.active_campaigns[campaign_id]
            if campaign.get('stopped'):
                break

            available_agents = await self.get_available_agents(campaign_id)
            if not available_agents:
                await asyncio.sleep(2)
                continue

            for agent in available_agents:
                agent_id = str(agent['id'])
                # ¿Ya tiene un contacto en preview asignado?
                assigned_key = f'campaign:{campaign_id}:preview:agent:{agent_id}'
                already_assigned = await self.redis_client.get(assigned_key)
                if already_assigned:
                    # Revisar si el agente respondió
                    accepted = await self.redis_client.get(f'{assigned_key}:accepted')
                    rejected = await self.redis_client.get(f'{assigned_key}:rejected')
                    if accepted:
                        contact = json.loads(already_assigned)
                        await self.redis_client.delete(assigned_key, f'{assigned_key}:accepted')
                        try:
                            await self.originate_call(campaign_id=campaign_id, contact=contact, agent=agent)
                            campaign['calls_made'] += 1
                        except Exception as e:
                            logger.error(f"Preview originate failed: {e}")
                    elif rejected:
                        await self.redis_client.delete(assigned_key, f'{assigned_key}:rejected')
                        logger.info(f"Preview: agente {agent_id} rechazó contacto")
                    else:
                        # Verificar timeout del preview
                        assigned_ts = float(await self.redis_client.get(f'{assigned_key}:ts') or 0)
                        if assigned_ts and (datetime.now().timestamp() - assigned_ts) > timeout_secs:
                            logger.info(f"Preview timeout para agente {agent_id}")
                            await self.redis_client.delete(assigned_key, f'{assigned_key}:ts')
                    continue

                # Obtener siguiente contacto y asignarlo al agente
                contact = await self.get_next_contact(campaign_id)
                if not contact:
                    continue

                await self.redis_client.setex(assigned_key, timeout_secs + 60, json.dumps(contact))
                await self.redis_client.setex(f'{assigned_key}:ts', timeout_secs + 60,
                                               str(datetime.now().timestamp()))
                # Publicar evento para que el frontend muestre los datos
                await self.redis_client.publish('calls:events', json.dumps({
                    'type': 'preview_contact_assigned',
                    'campaign_id': campaign_id,
                    'agent_id': agent_id,
                    'contact': contact,
                    'timeout': timeout_secs,
                }))
                logger.info(f"Preview: contacto asignado a agente {agent_id}")

            await asyncio.sleep(1)

        logger.info(f"Preview dialer detenido para campaña {campaign_id}")

    async def call_blasting_loop(self, campaign_id: int):
        """
        CALL BLASTING: Discado masivo sin agentes
        Reproduce mensaje grabado
        """
        logger.info(f"Iniciando call blasting para campaña {campaign_id}")
        campaign = self.active_campaigns[campaign_id]
        config = campaign['config']
        
        # Obtener todos los contactos
        contacts = await self.get_all_contacts(campaign_id)
        
        # Configuración de concurrencia
        max_concurrent = config.get('max_concurrent_calls', 50)
        batch_delay = config.get('batch_delay', 5)  # segundos entre lotes
        
        # Dividir en lotes
        batches = [contacts[i:i + max_concurrent] for i in range(0, len(contacts), max_concurrent)]
        
        for batch in batches:
            if campaign.get('stopped'):
                break
            
            # Originar llamadas del lote
            tasks = []
            for contact in batch:
                task = self.originate_call_blasting(campaign_id, contact, config)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            campaign['calls_made'] += len(batch)
            
            # Esperar antes del siguiente lote
            await asyncio.sleep(batch_delay)
        
        logger.info(f"Call blasting completado para campaña {campaign_id}")
        
    async def originate_call(self, campaign_id: int, contact: Dict, agent: Optional[Dict] = None):
        """Originar llamada usando Asterisk AMI"""
        if not contact or 'phone_number' not in contact:
            raise InvalidContactError(f"Invalid contact data: {contact}")
        
        try:
            config = self.active_campaigns[campaign_id]['config']
            trunk = config.get('trunk', 'default_trunk')
            
            # Construir número de destino
            destination = contact['phone_number']
            caller_id = config.get('caller_id', '1000')
            
            # Variables de canal — se envían como headers separados via panoramisk
            variables = {
                'CAMPAIGN_ID': str(campaign_id),
                'CONTACT_ID': str(contact['id']),
                'CONTACT_NAME': contact.get('name', ''),
            }
            
            if agent:
                # Progresivo/Preview: el agente es el A-leg (quien llama primero).
                # Asterisk marca al agente; cuando contesta, origina la B-leg al contacto.
                variables['AGENT_ID'] = str(agent['id'])
                variables['QUEUE_NAME'] = config.get('queue_name', '')
                originate_action = {
                    'Action': 'Originate',
                    'Channel': f"PJSIP/{agent['extension']}",
                    'Context': config.get('context', 'from-internal'),
                    'Exten': destination,
                    'Priority': '1',
                    'CallerID': caller_id,
                    'Timeout': '30000',
                    'Async': 'true',
                }
            else:
                # Predictivo: llamar directamente al contacto y encolarlo.
                # El contexto outbound-queue conecta la llamada contestada a la cola.
                queue_name = config.get('queue_name', '')
                variables['QUEUE_NAME'] = queue_name
                originate_action = {
                    'Action': 'Originate',
                    'Channel': f'PJSIP/{trunk}/{destination}',
                    'Context': 'outbound-queue',
                    'Exten': 's',
                    'Priority': '1',
                    'CallerID': caller_id,
                    'Timeout': '30000',
                    'Async': 'true',
                }
            
            # Añadir variables al action — panoramisk acepta múltiples 'Variable' como lista
            # o como string concatenado. Usar lista garantiza headers separados en AMI.
            originate_action['Variable'] = [f'{k}={v}' for k, v in variables.items()]
            
            # Originar llamada vía AMI
            response = await self.ami_client.send_action(originate_action)
            
            # panoramisk Message: el header de respuesta es 'Response' (capitalizado)
            ami_response = getattr(response, 'Response', '') or ''
            if str(ami_response).lower() == 'success':
                call_id = getattr(response, 'ActionID', None) or str(datetime.now().timestamp())
                uniqueid = getattr(response, 'Uniqueid', call_id) or call_id
                
                self.active_calls[call_id] = {
                    'campaign_id': campaign_id,
                    'contact': contact,
                    'agent': agent,
                    'status': CallStatus.DIALING.value,
                    'started_at': datetime.now(),
                    'uniqueid': uniqueid
                }
                
                # Guardar en Redis con múltiples referencias para búsqueda
                await self.redis_client.setex(
                    f'call:{call_id}',
                    3600,
                    json.dumps(self.active_calls[call_id], default=str)
                )
                
                # Guardar referencias para mapeo en eventos
                channel_name = f'PJSIP/{trunk}/{destination}'
                await self.redis_client.setex(f'channel:{channel_name}:call_id', 3600, call_id)
                await self.redis_client.setex(f'uniqueid:{uniqueid}:call_id', 3600, call_id)
                
                logger.info(f"Llamada originada: {call_id} -> {destination} (uniqueid: {uniqueid})")
            else:
                error_msg = f"AMI originate failed: {response}"
                logger.error(error_msg)
                raise CallOriginationError(error_msg)
                
        except InvalidContactError:
            raise
        except CallOriginationError:
            raise
        except KeyError as e:
            error_msg = f"Missing campaign configuration: {e}"
            logger.error(error_msg)
            raise CampaignNotFoundError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error originating call: {e}"
            logger.exception(error_msg)
            raise CallOriginationError(error_msg)
            
    async def originate_call_blasting(self, campaign_id: int, contact: Dict, config: Dict):
        """Originar llamada para call blasting (sin agente)"""
        try:
            trunk = config.get('trunk', 'default_trunk')
            destination = contact['phone_number']
            caller_id = config.get('caller_id', '1000')
            audio_file = config.get('audio_file', 'welcome')
            
            # Originar y reproducir mensaje
            response = await self.ami_client.send_action({
                'Action': 'Originate',
                'Channel': f'PJSIP/{trunk}/{destination}',
                'Application': 'Playback',
                'Data': audio_file,
                'CallerID': caller_id,
                'Timeout': '30000',
                'Async': 'true',
                'Variable': f'CAMPAIGN_ID={campaign_id},CONTACT_ID={contact["id"]}'
            })
            
            ami_response = getattr(response, 'Response', '') or ''
            if str(ami_response).lower() == 'success':
                logger.info(f"Call blasting originado: {destination}")
            else:
                logger.error(f"Error en call blasting: {response}")
                
        except Exception as e:
            logger.error(f"Error en call blasting: {e}")
            
    async def calculate_predictive_ratio(self, campaign_id: int) -> float:
        """
        Calcular ratio de discado predictivo basado en estadísticas
        Objetivo: Maximizar contactos mientras se minimiza abandono
        """
        campaign = self.active_campaigns[campaign_id]
        
        calls_made = campaign['calls_made']
        calls_answered = campaign['calls_answered']
        calls_abandoned = campaign['calls_abandoned']
        
        if calls_made == 0:
            return 1.5  # Ratio inicial conservador
        
        # Calcular tasa de éxito
        answer_rate = calls_answered / calls_made if calls_made > 0 else 0.3
        
        # Calcular tasa de abandono
        abandon_rate = calls_abandoned / calls_answered if calls_answered > 0 else 0
        
        # Ajustar ratio basado en tasa de abandono
        current_ratio = self.predictive_ratio
        
        if abandon_rate > self.abandon_rate_target:
            # Demasiado abandono, reducir ratio
            current_ratio = max(1.0, current_ratio - 0.1)
        elif abandon_rate < self.abandon_rate_target * 0.5:
            # Abandono muy bajo, podemos aumentar
            current_ratio = min(3.0, current_ratio + 0.1)
        
        # Actualizar ratio
        self.predictive_ratio = current_ratio
        
        logger.debug(f"Predictive ratio: {current_ratio:.2f} (answer: {answer_rate:.2%}, abandon: {abandon_rate:.2%})")
        
        return current_ratio
        
    async def get_campaign_config(self, campaign_id: int) -> Optional[Dict]:
        """Obtener configuración de campaña desde Redis"""
        config = await self.redis_client.get(f'campaign:{campaign_id}:config')
        return json.loads(config) if config else None
        
    async def get_available_agents(self, campaign_id: int) -> List[Dict]:
        """Obtener agentes disponibles para la campaña"""
        agents_key = f'campaign:{campaign_id}:agents:available'
        agent_ids = await self.redis_client.smembers(agents_key)
        
        agents = []
        for agent_id in agent_ids:
            agent_data = await self.redis_client.get(f'agent:{agent_id}')
            if agent_data:
                agents.append(json.loads(agent_data))
        
        return agents
        
    async def get_next_contact(self, campaign_id: int) -> Optional[Dict]:
        """
        Obtener siguiente contacto de la campaña.
        Aplica filtros DNC, timezone y prioridad VIP antes de retornar.
        Soporta reintentos multi-número: intenta phone_number, luego phone_2, phone_3.
        """
        config = self.active_campaigns.get(campaign_id, {}).get('config', {})
        dnc_enabled = config.get('dnc_enabled', True)
        campaign_tz = config.get('timezone', 'America/Bogota')
        vip_boost = config.get('vip_priority_boost', 10)

        # Intentar hasta 10 contactos hasta encontrar uno válido
        for _ in range(10):
            contact_data = await self.redis_client.lpop(f'campaign:{campaign_id}:contacts:pending')
            if not contact_data:
                return None

            contact = json.loads(contact_data)

            # Determinar qué número usar (multi-number retry)
            phone_fields = ['phone_number', 'phone_2', 'phone_3']
            retry_index = contact.get('_retry_phone_index', 0)
            phone = None
            for idx in range(retry_index, len(phone_fields)):
                candidate = contact.get(phone_fields[idx], '').strip()
                if candidate:
                    phone = candidate
                    contact['phone_number'] = phone  # normalizar para originate_call
                    contact['_retry_phone_index'] = idx
                    break

            if not phone:
                logger.info(f"Contacto {contact.get('id')} sin números disponibles, descartando")
                continue

            # 1) Filtro DNC: verificar lista negra y opt-out
            if dnc_enabled and await self._is_dnc_blocked(phone):
                logger.info(f"DNC: saltando contacto {phone} (lista negra/opt-out)")
                await self._mark_contact_dnc(contact, campaign_id)
                continue

            # 2) Filtro Timezone: no marcar fuera del horario del contacto
            contact_tz = contact.get('timezone') or campaign_tz
            if not self._is_callable_now(contact_tz):
                logger.info(f"TZ: saltando {phone} — fuera de horario en {contact_tz}")
                # Re-encolar para el próximo ciclo
                await self.redis_client.rpush(
                    f'campaign:{campaign_id}:contacts:pending',
                    json.dumps(contact)
                )
                continue

            # 3) VIP boost: si es VIP, subir prioridad (ya se usa al cargar contactos)
            if contact.get('is_vip'):
                contact['priority'] = (contact.get('priority', 0) or 0) + vip_boost

            return contact

        return None

    async def _is_dnc_blocked(self, phone: str) -> bool:
        """
        Verifica si el número está en la lista negra (Redis cache de DNC).
        Cache TTL = 5 minutos para no golpear la DB en cada llamada.
        """
        if not phone:
            return False
        phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')
        cache_key = f'dnc:{phone_clean[-10:]}'
        cached = await self.redis_client.get(cache_key)
        if cached is not None:
            return cached == '1'

        # Verificar en la DB via HTTP al backend (evita importar Django en el dialer)
        try:
            import aiohttp
            backend_url = os.getenv('BACKEND_URL', 'http://backend:8000')
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f'{backend_url}/api/cc/dnc-check/',
                    json={'phone': phone},
                    headers={'Authorization': f"Bearer {os.getenv('DIALER_API_TOKEN', '')}"},
                    timeout=aiohttp.ClientTimeout(total=3),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        blocked = data.get('blocked', False)
                        await self.redis_client.setex(cache_key, 300, '1' if blocked else '0')
                        return blocked
        except Exception as e:
            logger.warning(f"DNC check failed for {phone}: {e}")
        # En caso de error, no bloquear
        await self.redis_client.setex(cache_key, 60, '0')
        return False

    async def _mark_contact_dnc(self, contact: Dict, campaign_id: int):
        """Publicar evento de contacto bloqueado por DNC."""
        await self.redis_client.publish('calls:events', json.dumps({
            'type': 'contact_skipped_dnc',
            'campaign_id': campaign_id,
            'contact_id': contact.get('id'),
            'phone': contact.get('phone'),
        }))

    def _is_callable_now(self, timezone_str: str) -> bool:
        """
        Verifica si es horario de llamada válido para la zona horaria dada.
        Horas permitidas: 8:00 AM – 8:00 PM de lunes a sábado.
        """
        try:
            tz = ZoneInfo(timezone_str) if timezone_str else ZoneInfo('America/Bogota')
        except (ZoneInfoNotFoundError, Exception):
            try:
                tz = pytz.timezone(timezone_str)
            except Exception:
                tz = pytz.timezone('America/Bogota')

        now_local = datetime.now(tz)
        hour = now_local.hour
        weekday = now_local.weekday()  # 0=Lunes, 6=Domingo

        # No llamar domingos (6) ni fuera de 8-20
        if weekday == 6:
            return False
        return 8 <= hour < 20
        
    async def get_all_contacts(self, campaign_id: int) -> List[Dict]:
        """Obtener todos los contactos de la campaña (para call blasting)"""
        contact_list = await self.redis_client.lrange(f'campaign:{campaign_id}:contacts:pending', 0, -1)
        return [json.loads(c) for c in contact_list]
        
    # Event Handlers
    async def on_new_channel(self, manager, event):
        """Manejar evento de nuevo canal"""
        logger.debug(f"Nuevo canal: {event.get('Channel')}")
        
    async def on_hangup(self, manager, event):
        """Manejar evento de cuelgue"""
        channel = event.get('Channel')
        uniqueid = event.get('Uniqueid')
        cause = event.get('Cause')
        cause_txt = event.get('Cause-txt', '')
        
        logger.info(f"Hangup: {channel} - Causa: {cause} ({cause_txt})")
        
        # Buscar call_id por uniqueid o channel
        call_id = await self.redis_client.get(f'channel:{channel}:call_id')
        if not call_id:
            call_id = await self.redis_client.get(f'uniqueid:{uniqueid}:call_id')
        
        if not call_id:
            logger.warning(f"No call_id found for channel {channel} or uniqueid {uniqueid}")
            return
        
        if call_id not in self.active_calls:
            logger.warning(f"Call {call_id} not in active_calls")
            return
        
        call_data = self.active_calls[call_id]
        campaign_id = call_data.get('campaign_id')
        
        if campaign_id not in self.active_campaigns:
            logger.warning(f"Campaign {campaign_id} not in active_campaigns")
            del self.active_calls[call_id]
            return
        
        campaign = self.active_campaigns[campaign_id]
        
        # Actualizar estadísticas según la causa del hangup
        # Causas normales: 16 (Normal Clearing), 17 (User busy)
        # Causas de no respuesta: 19 (No answer), 21 (Call rejected)
        if cause in ['16', '17']:  # Normal clearing o busy
            if call_data.get('status') == CallStatus.ANSWERED.value:
                campaign['calls_answered'] += 1
                logger.info(f"Call {call_id} answered and completed normally")
            else:
                campaign['calls_abandoned'] += 1
                logger.info(f"Call {call_id} abandoned (cause: {cause})")
        elif cause in ['19', '21']:  # No answer o rejected
            logger.info(f"Call {call_id} not answered (cause: {cause})")
        else:
            logger.info(f"Call {call_id} ended with cause: {cause}")
        
        # Guardar registro de llamada en Redis para procesamiento posterior
        call_record = {
            'call_id': call_id,
            'campaign_id': campaign_id,
            'contact': call_data.get('contact'),
            'agent': call_data.get('agent'),
            'status': call_data.get('status'),
            'started_at': str(call_data.get('started_at')),
            'ended_at': str(datetime.now()),
            'hangup_cause': cause,
            'hangup_cause_txt': cause_txt,
            'channel': channel,
            'uniqueid': uniqueid
        }
        
        # Guardar en cola de procesamiento
        await self.redis_client.rpush(
            'calls:completed',
            json.dumps(call_record, default=str)
        )
        
        # Actualizar estadísticas en Redis
        await self.redis_client.hset(
            f'campaign:{campaign_id}:stats',
            mapping={
                'calls_made': campaign['calls_made'],
                'calls_answered': campaign['calls_answered'],
                'calls_abandoned': campaign['calls_abandoned']
            }
        )
        
        # Limpiar referencias
        await self.redis_client.delete(f'channel:{channel}:call_id')
        await self.redis_client.delete(f'uniqueid:{uniqueid}:call_id')
        
        # Remover de llamadas activas
        del self.active_calls[call_id]
        
        logger.info(f"Call {call_id} processed and removed from active calls")
        
    async def on_agent_connect(self, manager, event):
        """Agente conectado a llamada"""
        agent = event.get('Agent')
        logger.info(f"Agente conectado: {agent}")
        
    async def on_agent_complete(self, manager, event):
        """Agente completó llamada"""
        agent = event.get('Agent')
        reason = event.get('Reason')
        logger.info(f"Agente {agent} completó - Razón: {reason}")

async def main():
    """Función principal con reconexión automática"""
    retry_delay = 5  # segundos entre reintentos
    max_retry_delay = 60
    attempt = 0

    while True:
        dialer = DialerEngine()
        try:
            await dialer.initialize()
            logger.info("Dialer Engine iniciado y listo")
            attempt = 0  # reiniciar contador de intentos al conectar exitosamente
            retry_delay = 5

            # Mantener el proceso corriendo, reiniciar si se cae la conexión
            while True:
                await asyncio.sleep(5)
                # Verificar que Redis sigue conectado
                try:
                    await dialer.redis_client.ping()
                except Exception:
                    logger.error("Redis ping falló — reconectando...")
                    break

        except KeyboardInterrupt:
            logger.info("Deteniendo Dialer Engine...")
            return
        except Exception as e:
            attempt += 1
            logger.error(f"Error en Dialer Engine (intento {attempt}): {e}")
            retry_delay = min(retry_delay * 2, max_retry_delay)
            logger.info(f"Reintentando en {retry_delay}s...")
            await asyncio.sleep(retry_delay)

if __name__ == '__main__':
    asyncio.run(main())
