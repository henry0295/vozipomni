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
        # Directorio dinámico en volumen compartido con Asterisk
        # Para archivos parciales incluidos via #include desde pjsip.conf/extensions.conf
        self.config_dir = Path(config_dir or getattr(settings, 'ASTERISK_CONFIG_DIR', '/var/lib/asterisk/dynamic'))
        # Directorio estático de Asterisk para archivos de configuración completos
        # (voicemail.conf, musiconhold.conf) que Asterisk carga directamente
        self.static_config_dir = Path('/etc/asterisk')
    
    def generate_pjsip_extensions_conf(self):
        """
        Genera pjsip_extensions.conf con extensiones PJSIP de agentes.
        Este archivo se incluye desde pjsip.conf via #include.
        NO incluye transports ni templates (esos están en pjsip.conf estático).
        
        Soporta dos tipos:
        - PJSIP: Softphones SIP tradicionales (MicroSIP, Zoiper, etc.)
        - WEBRTC: Clientes WebRTC desde navegador
        """
        # Incluir tanto PJSIP como WEBRTC (ambos usan el driver chan_pjsip)
        extensions = Extension.objects.filter(
            extension_type__in=['PJSIP', 'WEBRTC', 'SIP'],
            is_active=True
        )
        
        config = [
            "; ==========================================================================",
            "; VOZIPOMNI - PJSIP Extensions Configuration",
            "; Generado automáticamente desde Django",
            "; NO EDITAR MANUALMENTE - Los cambios se perderán",
            "; ==========================================================================",
            "",
        ]
        
        for ext in extensions:
            is_webrtc = ext.extension_type == 'WEBRTC'
            transport = getattr(ext, 'transport', None) or ('transport-wss' if is_webrtc else 'transport-udp')
            callerid = ext.callerid if ext.callerid else f'"{ext.name}" <{ext.extension}>'
            # Si callerid no tiene formato correcto, formatearlo
            if callerid and '<' not in callerid:
                callerid = f'"{ext.name}" <{callerid}>'
            
            # Códecs según tipo
            if is_webrtc:
                codecs = 'opus,ulaw,alaw'
            else:
                codecs = getattr(ext, 'codecs', None) or 'ulaw,alaw,g722'
            
            max_contacts = getattr(ext, 'max_contacts', 1) or 1
            
            # ---- Endpoint ----
            config.extend([
                f"; Extension: {ext.extension} - {ext.name} ({ext.extension_type})",
                f"[{ext.extension}]",
                "type=endpoint",
                f"transport={transport}",
                f"context={ext.context}",
                "disallow=all",
                f"allow={codecs}",
                f"auth={ext.extension}",
                f"aors={ext.extension}",
                f"callerid={callerid}",
                "direct_media=no",
                "rtp_symmetric=yes",
                "force_rport=yes",
                "rewrite_contact=yes",
                "trust_id_inbound=yes",
                "device_state_busy_at=1",
                # Identificar por username de autenticación (crítico para match de INVITEs)
                "identify_by=username,auth_username",
            ])
            
            # Configuración específica WebRTC
            if is_webrtc:
                config.extend([
                    "webrtc=yes",
                    "dtls_auto_generate_cert=yes",
                    "dtls_verify=fingerprint",
                    "dtls_setup=actpass",
                    "ice_support=yes",
                    "media_encryption=dtls",
                ])
            
            config.append("")
            
            # ---- Auth ----
            config.extend([
                f"[{ext.extension}]",
                "type=auth",
                "auth_type=userpass",
                f"username={ext.extension}",
                f"password={ext.secret}",
                "",
            ])
            
            # ---- AOR ----
            config.extend([
                f"[{ext.extension}]",
                "type=aor",
                f"max_contacts={max_contacts}",
                "remove_existing=yes",
                "qualify_frequency=30",
                "",
            ])
            
            # ---- Identify ----
            # Permite identificar endpoint por auth_username
            config.extend([
                f"[{ext.extension}]",
                "type=identify",
                f"endpoint={ext.extension}",
                f"match_header=Authorization: Digest username=\"{ext.extension}\"",
                "",
            ])
        
        return '\n'.join(config)
    
    @staticmethod
    def _ensure_pattern_prefix(pattern):
        """
        Asegurar que los patrones de Asterisk tengan el prefijo '_'.
        En Asterisk 21, los patrones (X, Z, N, ., !) DEBEN empezar con '_'
        para ser tratados como patrones y no como extensiones literales.
        Ref: https://docs.asterisk.org/Asterisk_21_Documentation/
        """
        if not pattern:
            return pattern
        # Si ya tiene _, dejarlo
        if pattern.startswith('_'):
            return pattern
        # Si contiene caracteres de patrón Asterisk, agregar _
        pattern_chars = set('XZNxzn.![]')
        if any(c in pattern_chars for c in pattern):
            return f'_{pattern}'
        return pattern
    
    def generate_extensions_conf(self):
        """
        Genera extensions_dynamic.conf con el dialplan dinámico.
        
        IMPORTANTE: Usa [from-internal] como nombre de contexto para que
        Asterisk lo fusione (merge) con el [from-internal] del extensions.conf
        estático. Así las extensiones dinámicas y rutas salientes quedan
        accesibles desde el mismo contexto que usan los endpoints PJSIP.
        
        Ref: https://docs.asterisk.org/Asterisk_21_Documentation/
        "Contexts can be defined more than once; entries are merged."
        """
        config = [
            "; ==========================================================================",
            "; VOZIPOMNI - Dynamic Extensions Configuration",
            "; Generado automáticamente desde Django",
            "; NO EDITAR MANUALMENTE - Los cambios se perderán",
            "; ==========================================================================",
            "",
            "; ====== EXTENSIONES INTERNAS + RUTAS SALIENTES (merge con from-internal) ======",
            "[from-internal]",
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
        
        # Extensiones de colas (marcar extensión de la cola → Queue())
        try:
            from apps.queues.models import Queue
            queues = Queue.objects.filter(is_active=True)
            if queues.exists():
                config.extend([
                    "",
                    "; ====== EXTENSIONES DE COLAS ======",
                ])
                for queue in queues:
                    max_wait = queue.max_wait_time or 300
                    config.extend([
                        f"exten => {queue.extension},1,NoOp(Cola: {queue.name})",
                        f" same => n,Answer()",
                        f" same => n,MixMonitor(${{STRFTIME(${{EPOCH}},,%Y%m%d-%H%M%S)}}_{queue.extension}_${{CALLERID(num)}}.wav,ab)",
                        f" same => n,Queue({queue.name},tT,,,{max_wait})",
                        " same => n,Hangup()",
                        "",
                    ])
        except Exception as e:
            logger.warning(f"No se pudieron generar extensiones de colas: {e}")
        
        # Rutas entrantes (DIDs) - merge con [from-pstn] estático
        inbound_routes = InboundRoute.objects.filter(is_active=True).order_by('priority')
        if inbound_routes.exists():
            config.extend([
                "",
                "; ====== RUTAS ENTRANTES (DIDs) DINÁMICAS ======",
                "[from-pstn]",
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
        
        # Rutas salientes - RE-ABRIR contexto [from-internal]
        # Es necesario porque si hay rutas entrantes, el contexto activo es [from-pstn]
        outbound_routes = OutboundRoute.objects.filter(is_active=True).select_related('trunk').order_by('priority', 'name')
        if outbound_routes.exists():
            config.extend([
                "",
                "; ====== RUTAS SALIENTES DINÁMICAS ======",
                "; Re-abrir [from-internal] para que los endpoints las alcancen",
                "[from-internal]",
            ])
            
            for route in outbound_routes:
                # Asegurar prefijo _ en patrones (requerido por Asterisk)
                pattern = self._ensure_pattern_prefix(route.pattern)
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
                strategy = queue.strategy or 'ringall'
                timeout = queue.timeout or 30
                retry = queue.retry or 5
                wrapup = queue.wrap_up_time or 0
                maxlen = queue.max_callers or 0
                max_wait = queue.max_wait_time or 300
                servicelevel = queue.service_level or 60
                announce_freq = queue.announce_frequency or 30
                announce_hold = 'yes' if queue.announce_holdtime else 'no'
                periodic_freq = queue.periodic_announce_frequency or 60
                moh = queue.music_on_hold or 'default'
                
                config.extend([
                    f"[{queue.name}]",
                    f"strategy = {strategy}",
                    f"timeout = {timeout}",
                    f"retry = {retry}",
                    f"maxlen = {maxlen}",
                    f"wrapuptime = {wrapup}",
                    f"announce-frequency = {announce_freq}",
                    f"announce-holdtime = {announce_hold}",
                    f"periodic-announce-frequency = {periodic_freq}",
                    "ringinuse = no",
                    f"servicelevel = {servicelevel}",
                    f"musicclass = {moh}",
                    "weight = 0",
                    "monitor-type = MixMonitor",
                ])
                
                # Agregar miembros de la cola
                for member in queue.members.select_related('agent').filter(agent__is_active=True):
                    ext = getattr(member.agent, 'sip_extension', None)
                    if ext:
                        penalty = member.penalty or 0
                        config.append(f"member => PJSIP/{ext},{penalty}")
                
                config.append("")
        except Exception as e:
            logger.warning(f"No se pudieron cargar colas dinámicas: {e}")
        
        return '\n'.join(config)
    
    def write_all_configs(self):
        """
        Escribe todos los archivos de configuración dinámicos.
        
        IMPORTANTE: NO sobrescribe pjsip.conf (contiene transports y templates WebRTC).
        Las extensiones PJSIP van en pjsip_extensions.conf (incluido desde pjsip.conf).
        Las troncales van en pjsip_wizard.conf (manejado por PJSIPConfigGenerator).
        
        Archivos parciales (#include) → /var/lib/asterisk/dynamic/ (volumen compartido)
        Archivos completos (Asterisk los busca en /etc/asterisk/) → /etc/asterisk/
        """
        # TODOS los archivos van al directorio dinámico (volumen compartido)
        # /etc/asterisk/ es un bind mount de solo lectura desde el host
        # Los archivos estáticos (voicemail.conf, etc.) se incluyen via #include
        dynamic_configs = {
            'pjsip_extensions.conf': self.generate_pjsip_extensions_conf(),
            'extensions_dynamic.conf': self.generate_extensions_conf(),
            'queues_dynamic.conf': self.generate_queues_dynamic_conf(),
            'voicemail_dynamic.conf': self.generate_voicemail_conf(),
            'musiconhold_dynamic.conf': self.generate_musiconhold_conf(),
        }
        
        # Escribir todos los archivos al directorio dinámico
        for filename, content in dynamic_configs.items():
            filepath = self.config_dir / filename
            try:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, 'w') as f:
                    f.write(content)
                logger.info(f"✓ {filename} generado en {self.config_dir}")
            except Exception as e:
                logger.error(f"✗ Error generando {filename}: {e}")
        
        return dynamic_configs
