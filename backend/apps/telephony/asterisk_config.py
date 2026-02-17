"""
Generador de archivos de configuración de Asterisk
Compatible con la arquitectura OmniLeads:
- Extensiones PJSIP en pjsip_extensions.conf (incluido desde pjsip.conf)
- Troncales en pjsip_wizard.conf (manejado por PJSIPConfigGenerator)
- Dialplan con contextos from-pstn, from-pbx, from-internal
- Redis como backend para datos en tiempo real
"""
import os
import logging
from pathlib import Path
from django.conf import settings
from .models import Extension, InboundRoute, OutboundRoute, Voicemail, MusicOnHold, TimeCondition, IVR

logger = logging.getLogger(__name__)


class AsteriskConfigGenerator:
    """
    Genera archivos de configuración de Asterisk a partir de los modelos Django.
    
    IMPORTANTE: NO genera pjsip.conf principal (contiene transports, templates WebRTC).
    Las extensiones van en pjsip_extensions.conf que se incluye desde pjsip.conf.
    Las troncales van en pjsip_wizard.conf (manejado por PJSIPConfigGenerator).
    """
    
    def __init__(self, config_dir=None):
        from django.conf import settings
        # Usar directorio dinámico en volumen compartido con Asterisk
        self.config_dir = Path(config_dir or getattr(settings, 'ASTERISK_CONFIG_DIR', '/etc/asterisk/dynamic'))
    
    def generate_pjsip_extensions_conf(self):
        """
        Genera pjsip_extensions.conf con extensiones PJSIP de agentes.
        Este archivo se incluye desde pjsip.conf via #include.
        NO incluye transports ni templates (esos están en pjsip.conf estático).
        """
        extensions = Extension.objects.filter(extension_type='PJSIP', is_active=True)
        
        config = [
            "; ==========================================================================",
            "; VOZIPOMNI - PJSIP Extensions Configuration",
            "; Generado automáticamente desde Django",
            "; NO EDITAR MANUALMENTE - Los cambios se perderán",
            "; ==========================================================================",
            "",
        ]
        
        for ext in extensions:
            # Endpoint - heredando del template WebRTC o SIP según configuración
            config.extend([
                f"; Extension: {ext.extension} - {ext.name}",
                f"[{ext.extension}]",
                "type=endpoint",
                f"context={ext.context}",
                "disallow=all",
                "allow=opus,ulaw,alaw",
                f"auth={ext.extension}-auth",
                f"aors={ext.extension}-aor",
                f'callerid="{ext.name}" <{ext.extension}>',
                "direct_media=no",
                "rtp_symmetric=yes",
                "force_rport=yes",
                "rewrite_contact=yes",
                "trust_id_inbound=yes",
                "device_state_busy_at=1",
                "webrtc=yes",
                "dtls_auto_generate_cert=yes",
                "ice_support=yes",
                "media_encryption=dtls",
                "",
            ])
            
            # Auth
            config.extend([
                f"[{ext.extension}-auth]",
                "type=auth",
                "auth_type=userpass",
                f"username={ext.extension}",
                f"password={ext.secret}",
                "",
            ])
            
            # AOR
            config.extend([
                f"[{ext.extension}-aor]",
                "type=aor",
                "max_contacts=1",
                "remove_existing=yes",
                "qualify_frequency=30",
                "",
            ])
        
        return '\n'.join(config)
    
    def generate_extensions_conf(self):
        """
        Genera extensions_dynamic.conf con el dialplan dinámico.
        Complementa el extensions.conf estático que tiene los contextos base.
        """
        config = [
            "; ==========================================================================",
            "; VOZIPOMNI - Dynamic Extensions Configuration",
            "; Generado automáticamente desde Django",
            "; NO EDITAR MANUALMENTE - Los cambios se perderán",
            "; ==========================================================================",
            "",
            "; ====== EXTENSIONES INTERNAS DINÁMICAS ======",
            "[from-internal-dynamic]",
        ]
        
        # Agregar extensiones internas
        extensions = Extension.objects.filter(is_active=True).order_by('extension')
        for ext in extensions:
            config.extend([
                f"exten => {ext.extension},1,NoOp(Llamada a {ext.name})",
                f" same => n,Set(CALLERID(name)=${{CALLERID(name)}})",
                f" same => n,MixMonitor(${{STRFTIME(${{EPOCH}},,%Y%m%d-%H%M%S)}}_{ext.extension}.wav,ab)",
                f" same => n,Dial(PJSIP/{ext.extension},30,trg)",
            ])
            if ext.voicemail_enabled:
                config.append(f" same => n,VoiceMail({ext.extension}@default,u)")
            config.extend([
                " same => n,Hangup()",
                "",
            ])
        
        # Rutas entrantes (DIDs) para contexto from-pstn
        inbound_routes = InboundRoute.objects.filter(is_active=True).order_by('priority')
        if inbound_routes.exists():
            config.extend([
                "",
                "; ====== RUTAS ENTRANTES (DIDs) DINÁMICAS ======",
                "[from-pstn-dynamic]",
            ])
            
            for route in inbound_routes:
                config.extend([
                    f"exten => {route.did},1,NoOp(DID: {route.description})",
                    f" same => n,Set(CALLERID(name)=${{CALLERID(num)}})",
                    f" same => n,Set(__DID_NUMBER={route.did})",
                    f" same => n,MixMonitor(${{STRFTIME(${{EPOCH}},,%Y%m%d-%H%M%S)}}_{route.did}_${{CALLERID(num)}}.wav,ab)",
                ])
                
                if route.destination_type == 'extension':
                    config.append(f" same => n,Dial(PJSIP/{route.destination},30,trg)")
                    config.append(f" same => n,VoiceMail({route.destination}@default,u)")
                elif route.destination_type == 'ivr':
                    config.append(f" same => n,Goto(ivr-{route.destination},s,1)")
                elif route.destination_type == 'queue':
                    config.append(f" same => n,Queue({route.destination},tT,,,300)")
                elif route.destination_type == 'voicemail':
                    config.append(f" same => n,VoiceMail({route.destination}@default)")
                elif route.destination_type == 'announcement':
                    config.append(f" same => n,Playback({route.destination})")
                
                config.extend([
                    " same => n,Hangup()",
                    "",
                ])
        
        # Rutas salientes (ordenadas por prioridad)
        outbound_routes = OutboundRoute.objects.filter(is_active=True).select_related('trunk').order_by('priority', 'name')
        if outbound_routes.exists():
            config.extend([
                "",
                "; ====== RUTAS SALIENTES DINÁMICAS ======",
                "[from-internal-outbound]",
            ])
            
            for route in outbound_routes:
                # Usar pattern de Asterisk directamente (soporta _X., _NXXNXXXXXX, etc.)
                pattern = route.pattern
                ring_time = route.ring_time or 60
                dial_options = route.dial_options or 'trg'
                
                config.extend([
                    f"exten => {pattern},1,NoOp(Saliente: {route.name} via {route.trunk.name} [prioridad={route.priority}])",
                    f" same => n,Set(__TRUNK_NAME={route.trunk.name})",
                ])
                
                # Caller ID prefix
                if route.callerid_prefix:
                    config.append(f" same => n,Set(CALLERID(num)={route.callerid_prefix}${{CALLERID(num)}})")
                
                # Prepend digits
                if route.prepend:
                    config.append(f" same => n,Set(dial_number={route.prepend}${{EXTEN}})")
                elif route.prefix:
                    # Strip prefix digits from the beginning
                    prefix_len = len(route.prefix)
                    config.append(f" same => n,Set(dial_number=${{EXTEN:{prefix_len}}})")
                else:
                    config.append(" same => n,Set(dial_number=${EXTEN})")
                
                config.extend([
                    f" same => n,MixMonitor(${{STRFTIME(${{EPOCH}},,%Y%m%d-%H%M%S)}}_${{CALLERID(num)}}_${{dial_number}}.wav,ab)",
                    f" same => n,Dial(PJSIP/${{dial_number}}@{route.trunk.name},{ring_time},{dial_options})",
                    " same => n,Hangup()",
                    "",
                ])
        
        # IVRs dinámicos
        ivrs = IVR.objects.filter(is_active=True)
        for ivr_obj in ivrs:
            config.extend([
                "",
                f"; ====== IVR: {ivr_obj.name} ======",
                f"[ivr-{ivr_obj.extension}]",
                f"exten => s,1,NoOp(IVR: {ivr_obj.name})",
                " same => n,Answer()",
            ])
            
            if ivr_obj.welcome_message:
                config.append(f" same => n,Playback({ivr_obj.welcome_message})")
            
            config.extend([
                f" same => n,Set(TIMEOUT(response)={ivr_obj.timeout})",
                f" same => n,Set(ATTEMPTS=0)",
                " same => n(start),Background(main-menu)",
                f" same => n,WaitExten({ivr_obj.timeout})",
            ])
            
            # Opciones del menú
            if isinstance(ivr_obj.menu_options, dict):
                for digit, option in ivr_obj.menu_options.items():
                    dest_type = option.get('type', 'extension')
                    dest_value = option.get('destination', '')
                    if dest_type == 'queue':
                        config.append(f"exten => {digit},1,Queue({dest_value},tT,,,300)")
                    elif dest_type == 'extension':
                        config.append(f"exten => {digit},1,Dial(PJSIP/{dest_value},30,trg)")
                    elif dest_type == 'ivr':
                        config.append(f"exten => {digit},1,Goto(ivr-{dest_value},s,1)")
                    config.append(f" same => n,Hangup()")
            
            # Invalid option
            if ivr_obj.invalid_message:
                config.append(f"exten => i,1,Playback({ivr_obj.invalid_message})")
            else:
                config.append("exten => i,1,Playback(invalid)")
            config.extend([
                f" same => n,Set(ATTEMPTS=$[${{ATTEMPTS}}+1])",
                f" same => n,GotoIf($[${{ATTEMPTS}}<{ivr_obj.max_attempts}]?s,start)",
                " same => n,Hangup()",
            ])
            
            # Timeout
            if ivr_obj.timeout_message:
                config.append(f"exten => t,1,Playback({ivr_obj.timeout_message})")
            else:
                config.append("exten => t,1,Playback(vm-goodbye)")
            config.append(" same => n,Hangup()")
        
        return '\n'.join(config)
    
    def generate_voicemail_conf(self):
        """
        Genera voicemail.conf con buzones de voz
        """
        voicemails = Voicemail.objects.filter(is_active=True)
        
        config = [
            "; voicemail.conf - Generado automáticamente por VoziPOmni",
            "; NO EDITAR MANUALMENTE",
            "",
            "[general]",
            "format=wav49|gsm|wav",
            "serveremail=voicemail@vozipomni.com",
            "attach=yes",
            "maxmsg=100",
            "maxsecs=300",
            "minsecs=3",
            "maxsilence=10",
            "silencethreshold=128",
            "maxlogins=3",
            "emailsubject=Nuevo mensaje de voz de ${VM_CALLERID}",
            "emailbody=Hola ${VM_NAME},\\n\\nHas recibido un nuevo mensaje de voz de ${VM_CALLERID} con duración ${VM_DUR}.\\n\\nSaludos,\\nVozipOmni",
            "",
            "[default]",
        ]
        
        for vm in voicemails:
            email_part = f",{vm.email}" if vm.email else ""
            attach = "attach=yes" if vm.email_attach else "attach=no"
            delete = "delete=yes" if vm.email_delete else "delete=no"
            config.append(f"{vm.mailbox} => {vm.password},{vm.name}{email_part},,{attach}|{delete}|maxmsg={vm.max_messages}")
        
        return '\n'.join(config)
    
    def generate_musiconhold_conf(self):
        """
        Genera musiconhold.conf
        """
        moh_classes = MusicOnHold.objects.filter(is_active=True)
        
        config = [
            "; musiconhold.conf - Generado automáticamente por VoziPOmni",
            "; NO EDITAR MANUALMENTE",
            "",
            "[default]",
            "mode=files",
            "directory=/var/lib/asterisk/moh",
            "",
        ]
        
        for moh in moh_classes:
            config.extend([
                f"[{moh.name}]",
                f"mode={moh.mode}",
            ])
            if moh.directory:
                config.append(f"directory={moh.directory}")
            if moh.application:
                config.append(f"application={moh.application}")
            config.append("")
        
        return '\n'.join(config)
    
    def generate_queues_dynamic_conf(self):
        """
        Genera queues_dynamic.conf con colas dinámicas desde la base de datos
        """
        from apps.queues.models import Queue
        
        config = [
            "; queues_dynamic.conf - Generado automáticamente por VoziPOmni",
            "; NO EDITAR MANUALMENTE",
            "",
        ]
        
        try:
            queues = Queue.objects.filter(is_active=True)
            for queue in queues:
                strategy = getattr(queue, 'strategy', 'ringall')
                timeout = getattr(queue, 'timeout', 30)
                wrapup = getattr(queue, 'wrapup_time', 5)
                maxlen = getattr(queue, 'max_wait', 0)
                servicelevel = getattr(queue, 'service_level', 60)
                
                config.extend([
                    f"[{queue.name}]",
                    f"strategy = {strategy}",
                    f"timeout = {timeout}",
                    "retry = 5",
                    f"maxlen = {maxlen}",
                    f"wrapuptime = {wrapup}",
                    "announce-frequency = 30",
                    "announce-holdtime = yes",
                    "periodic-announce-frequency = 60",
                    "ringinuse = no",
                    f"servicelevel = {servicelevel}",
                    "weight = 0",
                    "monitor-type = MixMonitor",
                    "",
                ])
        except Exception as e:
            logger.warning(f"No se pudieron cargar colas dinámicas: {e}")
        
        return '\n'.join(config)
    
    def write_all_configs(self):
        """
        Escribe todos los archivos de configuración dinámicos.
        
        IMPORTANTE: NO sobrescribe pjsip.conf (contiene transports y templates WebRTC).
        Las extensiones PJSIP van en pjsip_extensions.conf (incluido desde pjsip.conf).
        Las troncales van en pjsip_wizard.conf (manejado por PJSIPConfigGenerator).
        """
        configs = {
            'pjsip_extensions.conf': self.generate_pjsip_extensions_conf(),
            'extensions_dynamic.conf': self.generate_extensions_conf(),
            'voicemail.conf': self.generate_voicemail_conf(),
            'musiconhold.conf': self.generate_musiconhold_conf(),
        }
        
        for filename, content in configs.items():
            filepath = self.config_dir / filename
            try:
                with open(filepath, 'w') as f:
                    f.write(content)
                logger.info(f"✓ {filename} generado exitosamente")
            except Exception as e:
                logger.error(f"✗ Error generando {filename}: {e}")
        
        return configs
