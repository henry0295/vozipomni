"""
PJSIP Configuration Generator
Genera archivos de configuración PJSIP Wizard automáticamente desde el modelo SIPTrunk
"""
import os
import logging
from pathlib import Path
from django.conf import settings
from .models import SIPTrunk

logger = logging.getLogger(__name__)


class PJSIPConfigGenerator:
    """
    Generador de configuración PJSIP Wizard para Asterisk
    Crea archivos de configuración basados en los datos del modelo SIPTrunk
    """
    
    def __init__(self):
        # Ruta del archivo de configuración PJSIP (volumen compartido con Asterisk)
        self.config_path = getattr(
            settings, 
            'PJSIP_CONFIG_PATH',
            '/var/lib/asterisk/dynamic/pjsip_wizard.conf'
        )
        
    def generate_trunk_config(self, trunk):
        """
        Genera la configuración PJSIP Wizard para una troncal específica
        
        Args:
            trunk: Instancia del modelo SIPTrunk
            
        Returns:
            str: Configuración PJSIP Wizard para la troncal
        """
        if trunk.trunk_type == 'custom' and trunk.pjsip_config_custom:
            # Si es personalizado y tiene configuración raw, usarla directamente
            return f"; Troncal: {trunk.name} (Configuración Personalizada)\n" + trunk.pjsip_config_custom
        
        # Generar configuración según el tipo de troncal
        if trunk.trunk_type == 'nat_provider':
            return self._generate_nat_provider_config(trunk)
        elif trunk.trunk_type == 'no_nat_provider':
            return self._generate_no_nat_provider_config(trunk)
        elif trunk.trunk_type == 'pbx_lan':
            return self._generate_pbx_lan_config(trunk)
        elif trunk.trunk_type == 'corporate':
            return self._generate_corporate_config(trunk)
        else:
            # Configuración genérica
            return self._generate_generic_config(trunk)
    
    def _generate_nat_provider_config(self, trunk):
        """
        Configuración para proveedor con NAT (ej: VoIP provider desde cloud/NAT)
        Usa trunk-nat-transport (puerto 5162)
        """
        config_lines = [
            f"; {'='*70}",
            f"; Troncal: {trunk.name}",
            f"; Tipo: Proveedor con NAT",
            f"; Host: {trunk.host}:{trunk.port}",
            f"; {'='*70}",
            "",
            f"[{trunk.name}]",
            "type=wizard",
            "transport=trunk-nat-transport",
            f"accepts_registrations={'yes' if trunk.accepts_registrations else 'no'}",
            f"accepts_auth={'yes' if trunk.accepts_auth else 'no'}",
            f"sends_registrations={'yes' if trunk.sends_registration else 'no'}",
            f"sends_auth={'yes' if trunk.sends_auth else 'no'}",
            f"endpoint/rtp_symmetric={'yes' if trunk.rtp_symmetric else 'no'}",
            f"endpoint/force_rport={'yes' if trunk.force_rport else 'no'}",
            f"endpoint/rewrite_contact={'yes' if trunk.rewrite_contact else 'no'}",
            f"endpoint/timers={'yes' if trunk.timers else 'no'}",
        ]
        
        # Timers avanzados
        if trunk.timers:
            config_lines.append(f"endpoint/timers_min_se={trunk.timers_min_se}")
            config_lines.append(f"endpoint/timers_sess_expires={trunk.timers_sess_expires}")
        
        # Direct media
        config_lines.append(f"endpoint/direct_media={'yes' if trunk.direct_media else 'no'}")
        
        # Qualify
        if trunk.qualify_enabled:
            config_lines.append(f"aor/qualify_frequency={trunk.qualify_frequency}")
            if trunk.qualify_timeout:
                config_lines.append(f"aor/qualify_timeout={trunk.qualify_timeout}")
        
        # Códecs y DTMF - !all limpia codecs por defecto antes de agregar los deseados
        if trunk.codec:
            codecs = trunk.codec.replace(' ', '')
            config_lines.append(f"endpoint/allow=!all,{codecs}")
        config_lines.append(f"endpoint/dtmf_mode={trunk.dtmf_mode}")
        
        # Context
        context_value = trunk.get_context_value()
        config_lines.append(f"endpoint/context={context_value}")
        
        # Idioma
        if trunk.language:
            config_lines.append(f"endpoint/language={trunk.language}")
        
        # Remote host
        remote_host = f"{trunk.host}:{trunk.port}" if trunk.port != 5060 else trunk.host
        config_lines.append(f"remote_hosts={remote_host}")
        
        # Autenticación saliente
        if trunk.outbound_auth_username:
            config_lines.append(f"outbound_auth/username={trunk.outbound_auth_username}")
        if trunk.outbound_auth_password:
            config_lines.append(f"outbound_auth/password={trunk.outbound_auth_password}")
        
        # Autenticación entrante
        if trunk.accepts_auth and trunk.inbound_auth_username:
            config_lines.append(f"inbound_auth/username={trunk.inbound_auth_username}")
        if trunk.accepts_auth and trunk.inbound_auth_password:
            config_lines.append(f"inbound_auth/password={trunk.inbound_auth_password}")
        
        # From User/Domain
        if trunk.from_user:
            config_lines.append(f"endpoint/from_user={trunk.from_user}")
        if trunk.from_domain:
            config_lines.append(f"endpoint/from_domain={trunk.from_domain}")
        
        # Caller ID
        if trunk.caller_id:
            config_lines.append(f"endpoint/callerid={trunk.caller_id}")
        
        # Identidad y caller ID avanzado
        if trunk.trust_id_inbound:
            config_lines.append("endpoint/trust_id_inbound=yes")
        if trunk.trust_id_outbound:
            config_lines.append("endpoint/trust_id_outbound=yes")
        if trunk.send_pai:
            config_lines.append("endpoint/send_pai=yes")
        if trunk.send_rpid:
            config_lines.append("endpoint/send_rpid=yes")
        
        # Registro (si está habilitado)
        if trunk.sends_registration and trunk.registration_server_uri:
            config_lines.extend([
                "",
                f"; Configuración de Registro para {trunk.name}",
                f"registration/server_uri={trunk.registration_server_uri}",
            ])
            if trunk.registration_client_uri:
                config_lines.append(f"registration/client_uri={trunk.registration_client_uri}")
            config_lines.extend([
                f"registration/retry_interval={trunk.registration_retry_interval}",
                f"registration/expiration={trunk.registration_expiration}",
            ])
        
        config_lines.append("")
        return "\n".join(config_lines)
    
    def _generate_no_nat_provider_config(self, trunk):
        """
        Configuración para proveedor sin NAT (ej: VPS con IP pública)
        Usa trunk-transport (puerto 5060)
        """
        config_lines = [
            f"; {'='*70}",
            f"; Troncal: {trunk.name}",
            f"; Tipo: Proveedor sin NAT",
            f"; Host: {trunk.host}:{trunk.port}",
            f"; {'='*70}",
            "",
            f"[{trunk.name}]",
            "type=wizard",
            "transport=trunk-transport",  # Puerto 5060, sin NAT
            f"accepts_registrations={'yes' if trunk.accepts_registrations else 'no'}",
            f"accepts_auth={'yes' if trunk.accepts_auth else 'no'}",
            f"sends_registrations={'yes' if trunk.sends_registration else 'no'}",
            f"sends_auth={'yes' if trunk.sends_auth else 'no'}",
            f"endpoint/rtp_symmetric={'yes' if trunk.rtp_symmetric else 'no'}",
            f"endpoint/force_rport={'yes' if trunk.force_rport else 'no'}",
            f"endpoint/rewrite_contact={'yes' if trunk.rewrite_contact else 'no'}",
            f"endpoint/timers={'yes' if trunk.timers else 'no'}",
        ]
        
        # Timers avanzados
        if trunk.timers:
            config_lines.append(f"endpoint/timers_min_se={trunk.timers_min_se}")
            config_lines.append(f"endpoint/timers_sess_expires={trunk.timers_sess_expires}")
        
        # Direct media
        config_lines.append(f"endpoint/direct_media={'yes' if trunk.direct_media else 'no'}")
        
        # Qualify
        if trunk.qualify_enabled:
            config_lines.append(f"aor/qualify_frequency={trunk.qualify_frequency}")
        
        # Códecs - !all limpia codecs por defecto
        if trunk.codec:
            config_lines.append(f"endpoint/allow=!all,{trunk.codec.replace(' ', '')}")
        config_lines.append(f"endpoint/dtmf_mode={trunk.dtmf_mode}")
        config_lines.append(f"endpoint/context={trunk.get_context_value()}")
        
        if trunk.language:
            config_lines.append(f"endpoint/language={trunk.language}")
        
        # Remote host
        remote_host = f"{trunk.host}:{trunk.port}" if trunk.port != 5060 else trunk.host
        config_lines.append(f"remote_hosts={remote_host}")
        
        # Autenticación
        if trunk.outbound_auth_username:
            config_lines.append(f"outbound_auth/username={trunk.outbound_auth_username}")
            config_lines.append(f"outbound_auth/password={trunk.outbound_auth_password}")
        
        if trunk.accepts_auth and trunk.inbound_auth_username:
            config_lines.append(f"inbound_auth/username={trunk.inbound_auth_username}")
            config_lines.append(f"inbound_auth/password={trunk.inbound_auth_password}")
        
        if trunk.from_user:
            config_lines.append(f"endpoint/from_user={trunk.from_user}")
        if trunk.from_domain:
            config_lines.append(f"endpoint/from_domain={trunk.from_domain}")
        
        # Caller ID
        if trunk.caller_id:
            config_lines.append(f"endpoint/callerid={trunk.caller_id}")
        
        # Identidad avanzada
        if trunk.trust_id_inbound:
            config_lines.append("endpoint/trust_id_inbound=yes")
        if trunk.trust_id_outbound:
            config_lines.append("endpoint/trust_id_outbound=yes")
        if trunk.send_pai:
            config_lines.append("endpoint/send_pai=yes")
        if trunk.send_rpid:
            config_lines.append("endpoint/send_rpid=yes")
        
        # Registro
        if trunk.sends_registration and trunk.registration_server_uri:
            config_lines.extend([
                "",
                f"; Registro",
                f"registration/server_uri={trunk.registration_server_uri}",
            ])
            if trunk.registration_client_uri:
                config_lines.append(f"registration/client_uri={trunk.registration_client_uri}")
            config_lines.extend([
                f"registration/retry_interval={trunk.registration_retry_interval}",
                f"registration/expiration={trunk.registration_expiration}",
            ])
        
        config_lines.append("")
        return "\n".join(config_lines)
    
    def _generate_pbx_lan_config(self, trunk):
        """
        Configuración para PBX en LAN (comunicación bidireccional con PBX local)
        """
        config_lines = [
            f"; {'='*70}",
            f"; Troncal: {trunk.name}",
            f"; Tipo: PBX en LAN",
            f"; Host: {trunk.host}:{trunk.port}",
            f"; {'='*70}",
            "",
            f"[{trunk.name}]",
            "type=wizard",
            "transport=trunk-transport",
            f"accepts_registrations={'yes' if trunk.accepts_registrations else 'no'}",
            f"sends_auth={'yes' if trunk.sends_auth else 'no'}",
            f"sends_registrations={'yes' if trunk.sends_registration else 'no'}",
            f"accepts_auth={'yes' if trunk.accepts_auth else 'no'}",
            "endpoint/rtp_symmetric=no",  # No necesario en LAN
            "endpoint/force_rport=no",
            "endpoint/rewrite_contact=no",
            f"endpoint/timers={'yes' if trunk.timers else 'no'}",
        ]
        
        # Timers avanzados
        if trunk.timers:
            config_lines.append(f"endpoint/timers_min_se={trunk.timers_min_se}")
            config_lines.append(f"endpoint/timers_sess_expires={trunk.timers_sess_expires}")
        
        # Direct media (siempre no en LAN para grabación)
        config_lines.append(f"endpoint/direct_media={'yes' if trunk.direct_media else 'no'}")
        
        # Qualify
        if trunk.qualify_enabled:
            config_lines.append(f"aor/qualify_frequency={trunk.qualify_frequency}")
        
        # Códecs - !all limpia codecs por defecto
        if trunk.codec:
            config_lines.append(f"endpoint/allow=!all,{trunk.codec.replace(' ', '')}")
        config_lines.append(f"endpoint/dtmf_mode={trunk.dtmf_mode}")
        config_lines.append(f"endpoint/context={trunk.get_context_value()}")
        config_lines.append(f"endpoint/language={trunk.language}")
        
        # Remote host
        remote_host = f"{trunk.host}:{trunk.port}" if trunk.port != 5060 else trunk.host
        config_lines.append(f"remote_hosts={remote_host}")
        
        # Autenticación bidireccional (típico con PBX)
        if trunk.inbound_auth_username:
            config_lines.append(f"inbound_auth/username={trunk.inbound_auth_username}")
            config_lines.append(f"inbound_auth/password={trunk.inbound_auth_password}")
        
        if trunk.outbound_auth_username:
            config_lines.append(f"outbound_auth/username={trunk.outbound_auth_username}")
            config_lines.append(f"outbound_auth/password={trunk.outbound_auth_password}")
            config_lines.append(f"endpoint/from_user={trunk.outbound_auth_username}")
        
        # Caller ID
        if trunk.caller_id:
            config_lines.append(f"endpoint/callerid={trunk.caller_id}")
        
        # Identidad avanzada
        if trunk.trust_id_inbound:
            config_lines.append("endpoint/trust_id_inbound=yes")
        if trunk.trust_id_outbound:
            config_lines.append("endpoint/trust_id_outbound=yes")
        if trunk.send_pai:
            config_lines.append("endpoint/send_pai=yes")
        if trunk.send_rpid:
            config_lines.append("endpoint/send_rpid=yes")
        
        config_lines.append("")
        return "\n".join(config_lines)
    
    def _generate_corporate_config(self, trunk):
        """
        Configuración para troncal corporativa (backbone privado, sin auth/registro)
        """
        config_lines = [
            f"; {'='*70}",
            f"; Troncal: {trunk.name}",
            f"; Tipo: Troncal Corporativa",
            f"; Host: {trunk.host}:{trunk.port}",
            f"; {'='*70}",
            "",
            f"[{trunk.name}]",
            "type=wizard",
            "transport=trunk-transport",
            "accepts_registrations=no",
            "accepts_auth=no",
            "sends_registrations=no",
            "sends_auth=no",
            "endpoint/rtp_symmetric=no",
            "endpoint/force_rport=no",
            "endpoint/rewrite_contact=no",
            f"endpoint/timers={'yes' if trunk.timers else 'no'}",
        ]
        
        # Timers avanzados
        if trunk.timers:
            config_lines.append(f"endpoint/timers_min_se={trunk.timers_min_se}")
            config_lines.append(f"endpoint/timers_sess_expires={trunk.timers_sess_expires}")
        
        # Direct media
        config_lines.append(f"endpoint/direct_media={'yes' if trunk.direct_media else 'no'}")
        
        # Qualify
        if trunk.qualify_enabled:
            config_lines.append(f"aor/qualify_frequency={trunk.qualify_frequency}")
        
        # Códecs - !all limpia codecs por defecto
        if trunk.codec:
            config_lines.append(f"endpoint/allow=!all,{trunk.codec.replace(' ', '')}")
        config_lines.append(f"endpoint/dtmf_mode={trunk.dtmf_mode}")
        config_lines.append(f"endpoint/language={trunk.language}")
        config_lines.append(f"endpoint/context={trunk.get_context_value()}")
        
        # Remote host
        remote_host = f"{trunk.host}:{trunk.port}" if trunk.port != 5060 else trunk.host
        config_lines.append(f"remote_hosts={remote_host}")
        
        config_lines.append("")
        return "\n".join(config_lines)
    
    def _generate_generic_config(self, trunk):
        """
        Configuración genérica basada en los campos del modelo
        """
        config_lines = [
            f"; {'='*70}",
            f"; Troncal: {trunk.name}",
            f"; Tipo: Genérico/Personalizado",
            f"; {'='*70}",
            "",
            f"[{trunk.name}]",
            "type=wizard",
            f"transport=trunk-{'nat-' if trunk.force_rport else ''}transport",
            f"accepts_registrations={'yes' if trunk.accepts_registrations else 'no'}",
            f"accepts_auth={'yes' if trunk.accepts_auth else 'no'}",
            f"sends_registrations={'yes' if trunk.sends_registration else 'no'}",
            f"sends_auth={'yes' if trunk.sends_auth else 'no'}",
            f"endpoint/rtp_symmetric={'yes' if trunk.rtp_symmetric else 'no'}",
            f"endpoint/force_rport={'yes' if trunk.force_rport else 'no'}",
            f"endpoint/rewrite_contact={'yes' if trunk.rewrite_contact else 'no'}",
            f"endpoint/timers={'yes' if trunk.timers else 'no'}",
        ]
        
        # Timers avanzados
        if trunk.timers:
            config_lines.append(f"endpoint/timers_min_se={trunk.timers_min_se}")
            config_lines.append(f"endpoint/timers_sess_expires={trunk.timers_sess_expires}")
        
        # Direct media
        config_lines.append(f"endpoint/direct_media={'yes' if trunk.direct_media else 'no'}")
        
        if trunk.qualify_enabled:
            config_lines.append(f"aor/qualify_frequency={trunk.qualify_frequency}")
        
        # Códecs - !all limpia codecs por defecto
        if trunk.codec:
            config_lines.append(f"endpoint/allow=!all,{trunk.codec.replace(' ', '')}")
        config_lines.append(f"endpoint/dtmf_mode={trunk.dtmf_mode}")
        config_lines.append(f"endpoint/context={trunk.get_context_value()}")
        
        if trunk.language:
            config_lines.append(f"endpoint/language={trunk.language}")
        
        remote_host = f"{trunk.host}:{trunk.port}" if trunk.port != 5060 else trunk.host
        config_lines.append(f"remote_hosts={remote_host}")
        
        if trunk.outbound_auth_username:
            config_lines.append(f"outbound_auth/username={trunk.outbound_auth_username}")
            config_lines.append(f"outbound_auth/password={trunk.outbound_auth_password}")
        
        if trunk.from_user:
            config_lines.append(f"endpoint/from_user={trunk.from_user}")
        if trunk.from_domain:
            config_lines.append(f"endpoint/from_domain={trunk.from_domain}")
        
        # Caller ID
        if trunk.caller_id:
            config_lines.append(f"endpoint/callerid={trunk.caller_id}")
        
        # Identidad avanzada
        if trunk.trust_id_inbound:
            config_lines.append("endpoint/trust_id_inbound=yes")
        if trunk.trust_id_outbound:
            config_lines.append("endpoint/trust_id_outbound=yes")
        if trunk.send_pai:
            config_lines.append("endpoint/send_pai=yes")
        if trunk.send_rpid:
            config_lines.append("endpoint/send_rpid=yes")
        
        if trunk.sends_registration and trunk.registration_server_uri:
            config_lines.append(f"registration/server_uri={trunk.registration_server_uri}")
            if trunk.registration_client_uri:
                config_lines.append(f"registration/client_uri={trunk.registration_client_uri}")
            config_lines.extend([
                f"registration/retry_interval={trunk.registration_retry_interval}",
                f"registration/expiration={trunk.registration_expiration}",
            ])
        
        config_lines.append("")
        return "\n".join(config_lines)
    
    def generate_all_trunks_config(self):
        """
        Genera la configuración completa de todas las troncales activas
        
        Returns:
            str: Configuración PJSIP completa
        """
        active_trunks = SIPTrunk.objects.filter(is_active=True).order_by('name')
        
        config_parts = [
            "; " + "="*78,
            "; VOZIPOMNI - PJSIP WIZARD CONFIGURATION",
            "; Generado automáticamente desde Django",
            "; NO EDITAR MANUALMENTE - Los cambios se perderán",
            "; " + "="*78,
            "",
            "; Este archivo contiene la configuración de todas las troncales SIP",
            "; configuradas en VoziPOmni usando PJSIP Wizard de Asterisk",
            "",
            ""
        ]
        
        for trunk in active_trunks:
            trunk_config = self.generate_trunk_config(trunk)
            config_parts.append(trunk_config)
        
        return "\n".join(config_parts)
    
    def write_config_file(self, config_content=None):
        """
        Escribe el archivo de configuración PJSIP
        
        Args:
            config_content: Contenido a escribir. Si es None, genera automáticamente.
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if config_content is None:
                config_content = self.generate_all_trunks_config()
            
            # Crear directorio si no existe
            config_dir = os.path.dirname(self.config_path)
            Path(config_dir).mkdir(parents=True, exist_ok=True)
            
            # Escribir archivo
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            logger.info(f"✓ Configuración PJSIP escrita en: {self.config_path}")
            return True, f"Configuración guardada en {self.config_path}"
            
        except PermissionError:
            error_msg = f"No hay permisos para escribir en {self.config_path}"
            logger.error(f"✗ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Error escribiendo configuración: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return False, error_msg
    
    def reload_pjsip(self):
        """
        Recarga la configuración PJSIP en Asterisk via AMI
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            from .asterisk_ami import AsteriskAMI
            
            ami = AsteriskAMI()
            if not ami.connect():
                return False, "No se pudo conectar a Asterisk AMI"
            
            # Recargar módulo PJSIP
            success = ami.reload_module('res_pjsip.so')
            ami.disconnect()
            
            if success:
                logger.info("✓ PJSIP recargado exitosamente")
                return True, "PJSIP recargado exitosamente"
            else:
                return False, "Error recargando PJSIP"
                
        except Exception as e:
            error_msg = f"Error recargando PJSIP: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return False, error_msg
    
    def save_and_reload(self):
        """
        Guarda la configuración y recarga Asterisk
        
        Returns:
            tuple: (success: bool, message: str)
        """
        # Escribir archivo
        write_success, write_msg = self.write_config_file()
        if not write_success:
            return False, write_msg
        
        # Recargar Asterisk
        reload_success, reload_msg = self.reload_pjsip()
        if not reload_success:
            return False, f"Archivo guardado pero error al recargar: {reload_msg}"
        
        return True, "Configuración guardada y Asterisk recargado exitosamente"
