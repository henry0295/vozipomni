"""
Tareas Celery para sincronización con Asterisk y Redis
"""
from celery import shared_task
from django.core.cache import cache
import logging
import json

logger = logging.getLogger(__name__)


# ============= TAREAS PARA SINCRONIZAR ASTERISK =============

@shared_task(bind=True, max_retries=3)
def sync_sip_trunk_to_asterisk(self, trunk_id):
    """
    Sincronizar configuración de troncal SIP con Asterisk
    - Regenera configuración PJSIP
    - Recarga módulo en Asterisk
    """
    try:
        from apps.telephony.models import SIPTrunk
        from apps.telephony.pjsip_config_generator import PJSIPConfigGenerator
        from apps.telephony.asterisk_ami import AsteriskAMI
        
        trunk = SIPTrunk.objects.get(id=trunk_id)
        logger.info(f"🔄 Sincronizando troncal SIP: {trunk.name}")
        
        # 1. Regenerar configuración PJSIP
        generator = PJSIPConfigGenerator()
        success, message = generator.save_and_reload()
        
        if success:
            logger.info(f"✓ Troncal {trunk.name} sincronizada con Asterisk")
            return {'success': True, 'message': message, 'trunk_id': trunk_id}
        else:
            logger.warning(f"⚠ Problema al sincronizar {trunk.name}: {message}")
            raise Exception(message)
            
    except Exception as e:
        logger.error(f"Error sincronizando troncal: {e}")
        # Reintentar en 30 segundos
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True)
def sync_inbound_route_to_asterisk(self, route_id):
    """
    Sincronizar ruta entrante (DID) con Asterisk
    - Guardar en Redis
    - Recargar dialplan
    """
    try:
        from apps.telephony.models import InboundRoute
        from apps.telephony.asterisk_ami import AsteriskAMI
        
        route = InboundRoute.objects.get(id=route_id)
        logger.info(f"🔄 Sincronizando ruta entrante: {route.did}")
        
        # 1. Guardar en Redis para lookups rápidos
        route_key = f"inbound_route:{route.did}"
        route_data = {
            'did': route.did,
            'destination_type': route.destination_type,
            'destination': route.destination,
            'priority': route.priority,
            'active': route.is_active
        }
        cache.set(route_key, json.dumps(route_data), timeout=None)
        
        # 2. Recargar dialplan en Asterisk
        ami = AsteriskAMI()
        if ami.connect():
            ami.reload_dialplan()
            ami.disconnect()
            logger.info(f"✓ Ruta entrante {route.did} sincronizada")
            return {'success': True, 'did': route.did}
        else:
            raise Exception("No se pudo conectar a Asterisk")
            
    except Exception as e:
        logger.error(f"Error sincronizando ruta entrante: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True)
def sync_outbound_route_to_asterisk(self, route_id):
    """
    Sincronizar ruta saliente con Asterisk
    - Guardar en Redis
    - Recargar dialplan
    """
    try:
        from apps.telephony.models import OutboundRoute
        from apps.telephony.asterisk_ami import AsteriskAMI
        
        route = OutboundRoute.objects.get(id=route_id)
        logger.info(f"🔄 Sincronizando ruta saliente: {route.name}")
        
        # 1. Guardar en Redis
        route_key = f"outbound_route:{route.id}"
        route_data = {
            'id': route.id,
            'name': route.name,
            'pattern': route.pattern,
            'trunk': route.trunk.name,
            'prepend': route.prepend,
            'prefix': route.prefix,
            'active': route.is_active
        }
        cache.set(route_key, json.dumps(route_data), timeout=None)
        
        # 2. Recargar dialplan
        ami = AsteriskAMI()
        if ami.connect():
            ami.reload_dialplan()
            ami.disconnect()
            logger.info(f"✓ Ruta saliente {route.name} sincronizada")
            return {'success': True, 'route_id': route_id}
        else:
            raise Exception("No se pudo conectar a Asterisk")
            
    except Exception as e:
        logger.error(f"Error sincronizando ruta saliente: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True)
def sync_extension_to_asterisk(self, extension_id):
    """
    Sincronizar extensión SIP con Asterisk
    - Guardar en Redis
    - Regenerar configuración PJSIP
    """
    try:
        from apps.telephony.models import Extension
        from apps.telephony.pjsip_config_generator import PJSIPConfigGenerator
        
        ext = Extension.objects.get(id=extension_id)
        logger.info(f"🔄 Sincronizando extensión: {ext.extension}")
        
        # 1. Guardar en Redis
        ext_key = f"extension:{ext.extension}"
        ext_data = {
            'extension': ext.extension,
            'name': ext.name,
            'type': ext.extension_type,
            'context': ext.context,
            'active': ext.is_active
        }
        cache.set(ext_key, json.dumps(ext_data), timeout=None)
        
        # 2. Regenerar PJSIP
        generator = PJSIPConfigGenerator()
        success, message = generator.save_and_reload()
        
        if success:
            logger.info(f"✓ Extensión {ext.extension} sincronizada")
            return {'success': True, 'extension': ext.extension}
        else:
            raise Exception(message)
            
    except Exception as e:
        logger.error(f"Error sincronizando extensión: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True)
def sync_ivr_to_asterisk(self, ivr_id):
    """
    Sincronizar menú IVR con Asterisk
    - Guardar en Redis
    - Recargar dialplan
    """
    try:
        from apps.telephony.models import IVR
        from apps.telephony.asterisk_ami import AsteriskAMI
        
        ivr = IVR.objects.get(id=ivr_id)
        logger.info(f"🔄 Sincronizando IVR: {ivr.name}")
        
        # 1. Guardar en Redis
        ivr_key = f"ivr:{ivr.extension}"
        ivr_data = {
            'name': ivr.name,
            'extension': ivr.extension,
            'welcome_message': ivr.welcome_message,
            'invalid_message': ivr.invalid_message,
            'timeout_message': ivr.timeout_message,
            'timeout': ivr.timeout,
            'max_attempts': ivr.max_attempts,
            'menu_options': ivr.menu_options,
            'active': ivr.is_active
        }
        cache.set(ivr_key, json.dumps(ivr_data), timeout=None)
        
        # 2. Recargar dialplan
        ami = AsteriskAMI()
        if ami.connect():
            ami.reload_dialplan()
            ami.disconnect()
            logger.info(f"✓ IVR {ivr.name} sincronizada")
            return {'success': True, 'ivr_id': ivr_id}
        else:
            raise Exception("No se pudo conectar a Asterisk")
            
    except Exception as e:
        logger.error(f"Error sincronizando IVR: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True)
def sync_voicemail_to_asterisk(self, voicemail_id):
    """
    Sincronizar buzón de voz con Asterisk
    - Guardar en Redis
    - Recargar configuración de voicemail
    """
    try:
        from apps.telephony.models import Voicemail
        from apps.telephony.asterisk_ami import AsteriskAMI
        
        vm = Voicemail.objects.get(id=voicemail_id)
        logger.info(f"🔄 Sincronizando buzón de voz: {vm.mailbox}")
        
        # 1. Guardar en Redis (sin contraseña por seguridad)
        vm_key = f"voicemail:{vm.mailbox}"
        vm_data = {
            'mailbox': vm.mailbox,
            'name': vm.name,
            'email': vm.email,
            'email_attach': vm.email_attach,
            'email_delete': vm.email_delete,
            'active': vm.is_active
        }
        cache.set(vm_key, json.dumps(vm_data), timeout=None)
        
        # 2. Recargar voicemail en Asterisk
        ami = AsteriskAMI()
        if ami.connect():
            ami.reload_module('res_voicemail')
            ami.disconnect()
            logger.info(f"✓ Buzón de voz {vm.mailbox} sincronizado")
            return {'success': True, 'mailbox': vm.mailbox}
        else:
            raise Exception("No se pudo conectar a Asterisk")
            
    except Exception as e:
        logger.error(f"Error sincronizando buzón de voz: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True)
def sync_time_condition_to_asterisk(self, condition_id):
    """
    Sincronizar condición de horario con Asterisk
    - Guardar en Redis
    - Recargar dialplan
    """
    try:
        from apps.telephony.models import TimeCondition
        from apps.telephony.asterisk_ami import AsteriskAMI
        
        condition = TimeCondition.objects.get(id=condition_id)
        logger.info(f"🔄 Sincronizando condición de horario: {condition.name}")
        
        # 1. Guardar en Redis
        cond_key = f"time_condition:{condition.id}"
        cond_data = {
            'name': condition.name,
            'time_groups': condition.time_groups,
            'true_destination_type': condition.true_destination_type,
            'true_destination': condition.true_destination,
            'false_destination_type': condition.false_destination_type,
            'false_destination': condition.false_destination,
            'active': condition.is_active
        }
        cache.set(cond_key, json.dumps(cond_data), timeout=None)
        
        # 2. Recargar dialplan
        ami = AsteriskAMI()
        if ami.connect():
            ami.reload_dialplan()
            ami.disconnect()
            logger.info(f"✓ Condición de horario {condition.name} sincronizada")
            return {'success': True, 'condition_id': condition_id}
        else:
            raise Exception("No se pudo conectar a Asterisk")
            
    except Exception as e:
        logger.error(f"Error sincronizando condición de horario: {e}")
        raise self.retry(exc=e, countdown=30)


# ============= TAREAS PARA LIMPIAR ASTERISK =============

@shared_task(bind=True)
def remove_sip_trunk_from_asterisk(self, trunk_name):
    """
    Eliminar troncal SIP de Asterisk
    - Limpiar configuración
    - Recargar PJSIP
    """
    try:
        from apps.telephony.pjsip_config_generator import PJSIPConfigGenerator
        from apps.telephony.asterisk_ami import AsteriskAMI
        
        logger.info(f"🗑️  Eliminando troncal SIP: {trunk_name}")
        
        # Limpiar Redis
        cache.delete(f"sip_trunk:{trunk_name}")
        
        # Regenerar PJSIP sin esta troncal
        generator = PJSIPConfigGenerator()
        success, message = generator.save_and_reload()
        
        if success:
            logger.info(f"✓ Troncal {trunk_name} eliminada")
            return {'success': True, 'trunk_name': trunk_name}
        else:
            raise Exception(message)
            
    except Exception as e:
        logger.error(f"Error eliminando troncal: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True)
def remove_inbound_route_from_asterisk(self, did):
    """
    Eliminar ruta entrante (DID) de Asterisk
    """
    try:
        from apps.telephony.asterisk_ami import AsteriskAMI
        
        logger.info(f"🗑️  Eliminando ruta entrante: {did}")
        
        # Limpiar Redis
        cache.delete(f"inbound_route:{did}")
        
        # Recargar dialplan
        ami = AsteriskAMI()
        if ami.connect():
            ami.reload_dialplan()
            ami.disconnect()
            logger.info(f"✓ Ruta entrante {did} eliminada")
            return {'success': True, 'did': did}
        else:
            raise Exception("No se pudo conectar a Asterisk")
            
    except Exception as e:
        logger.error(f"Error eliminando ruta entrante: {e}")
        raise self.retry(exc=e, countdown=30)


# ============= TAREAS PERIÓDICAS =============

@shared_task
def sync_all_telephony_config_to_redis():
    """
    Sincronizar TODA la configuración de telefonía a Redis
    - Ejecutar cada 5 minutos
    - Asegurar que Asterisk tenga acceso a datos actuales
    """
    try:
        from apps.telephony.models import (
            InboundRoute, OutboundRoute, Extension, IVR, 
            Voicemail, TimeCondition, SIPTrunk
        )
        
        count = 0
        
        # Sincronizar rutas entrantes
        for route in InboundRoute.objects.filter(is_active=True):
            sync_inbound_route_to_asterisk.apply_async(args=[route.id])
            count += 1
        
        # Sincronizar rutas salientes
        for route in OutboundRoute.objects.filter(is_active=True):
            sync_outbound_route_to_asterisk.apply_async(args=[route.id])
            count += 1
        
        # Sincronizar extensiones
        for ext in Extension.objects.filter(is_active=True):
            sync_extension_to_asterisk.apply_async(args=[ext.id])
            count += 1
        
        # Sincronizar IVRs
        for ivr in IVR.objects.filter(is_active=True):
            sync_ivr_to_asterisk.apply_async(args=[ivr.id])
            count += 1
        
        # Sincronizar buzones de voz
        for vm in Voicemail.objects.filter(is_active=True):
            sync_voicemail_to_asterisk.apply_async(args=[vm.id])
            count += 1
        
        # Sincronizar condiciones de horario
        for cond in TimeCondition.objects.filter(is_active=True):
            sync_time_condition_to_asterisk.apply_async(args=[cond.id])
            count += 1
        
        logger.info(f"✓ Sincronizadas {count} configuraciones de telefonía a Redis")
        return {'success': True, 'count': count}
        
    except Exception as e:
        logger.error(f"Error sincronizando configuración: {e}")
        return {'success': False, 'error': str(e)}


@shared_task
def check_asterisk_health():
    """
    Verificar salud de conexión con Asterisk
    - Ejecutar cada minuto
    """
    try:
        from apps.telephony.asterisk_ami import AsteriskAMI
        
        ami = AsteriskAMI()
        if ami.connect():
            ami.disconnect()
            logger.debug("✓ Asterisk AMI conectado")
            cache.set('asterisk_health', {'status': 'connected'}, timeout=120)
            return {'status': 'connected'}
        else:
            logger.warning("⚠ Asterisk AMI desconectado")
            cache.set('asterisk_health', {'status': 'disconnected'}, timeout=120)
            return {'status': 'disconnected'}
            
    except Exception as e:
        logger.error(f"Error verificando salud de Asterisk: {e}")
        return {'status': 'error', 'message': str(e)}
