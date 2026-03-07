"""
VozipOmni Dialer Engine
Motor de discado para campañas: Progresivas, Predictivas, Call Blasting y Manuales
Utiliza Asterisk AMI para originar llamadas
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional
import redis.asyncio as aioredis
from panoramisk.manager import Manager as AMIManager
import os
import json

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
            
            # Variables de canal
            variables = {
                'CAMPAIGN_ID': str(campaign_id),
                'CONTACT_ID': str(contact['id']),
                'CONTACT_NAME': contact.get('name', ''),
            }
            
            if agent:
                # Progresivo: conectar directamente al agente
                channel = f"SIP/{agent['extension']}"
                context = config.get('context', 'from-internal')
                variables['AGENT_ID'] = str(agent['id'])
            else:
                # Predictivo: conectar a cola
                channel = config.get('queue_channel', 'Local/s@outbound-queue')
                context = 'outbound-queue'
            
            # Originar llamada vía AMI
            response = await self.ami_client.send_action({
                'Action': 'Originate',
                'Channel': f'SIP/{trunk}/{destination}',
                'Context': context,
                'Exten': 's',
                'Priority': '1',
                'CallerID': caller_id,
                'Timeout': '30000',
                'Async': 'true',
                'Variable': ','.join([f'{k}={v}' for k, v in variables.items()])
            })
            
            if response.success:
                call_id = response.headers.get('ActionID')
                uniqueid = response.headers.get('Uniqueid', call_id)
                
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
                channel = f'SIP/{trunk}/{destination}'
                await self.redis_client.setex(f'channel:{channel}:call_id', 3600, call_id)
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
                'Channel': f'SIP/{trunk}/{destination}',
                'Application': 'Playback',
                'Data': audio_file,
                'CallerID': caller_id,
                'Timeout': '30000',
                'Async': 'true',
                'Variable': f'CAMPAIGN_ID={campaign_id},CONTACT_ID={contact["id"]}'
            })
            
            if response.success:
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
        """Obtener siguiente contacto de la campaña"""
        contact_data = await self.redis_client.lpop(f'campaign:{campaign_id}:contacts:pending')
        return json.loads(contact_data) if contact_data else None
        
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
    """Función principal"""
    dialer = DialerEngine()
    await dialer.initialize()
    
    logger.info("Dialer Engine iniciado y listo")
    
    # Mantener el proceso corriendo
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo Dialer Engine...")

if __name__ == '__main__':
    asyncio.run(main())
