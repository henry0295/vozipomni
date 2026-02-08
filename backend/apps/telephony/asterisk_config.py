"""
Generador de archivos de configuración de Asterisk
"""
import os
from pathlib import Path
from django.conf import settings
from .models import Extension, InboundRoute, OutboundRoute, Voicemail, MusicOnHold, TimeCondition


class AsteriskConfigGenerator:
    """
    Genera archivos de configuración de Asterisk a partir de los modelos Django
    """
    
    def __init__(self, config_dir='/etc/asterisk'):
        self.config_dir = Path(config_dir)
    
    def generate_sip_conf(self):
        """
        Genera sip.conf con todas las extensiones SIP
        """
        extensions = Extension.objects.filter(extension_type='SIP', is_active=True)
        
        config = [
            "; sip.conf - Generado automáticamente por VoziPOmni",
            "; NO EDITAR MANUALMENTE",
            "",
            "[general]",
            "context=default",
            "allowguest=no",
            "allowoverlap=no",
            "bindport=5060",
            "bindaddr=0.0.0.0",
            "srvlookup=yes",
            "disallow=all",
            "allow=ulaw",
            "allow=alaw",
            "allow=gsm",
            "alwaysauthreject=yes",
            "canreinvite=no",
            "nat=force_rport,comedia",
            "session-timers=refuse",
            "localnet=192.168.0.0/255.255.0.0",
            "localnet=10.0.0.0/255.0.0.0",
            "",
        ]
        
        for ext in extensions:
            config.extend([
                f"[{ext.extension}]",
                "type=friend",
                f"secret={ext.secret}",
                f"context={ext.context}",
                f"callerid=\"{ext.name}\" <{ext.extension}>",
                "host=dynamic",
                "qualify=yes",
                "nat=force_rport,comedia",
                "disallow=all",
                "allow=ulaw",
                "allow=alaw",
                "allow=gsm",
            ])
            
            if ext.voicemail_enabled:
                config.append(f"mailbox={ext.extension}@default")
            
            config.append("")
        
        return '\n'.join(config)
    
    def generate_pjsip_conf(self):
        """
        Genera pjsip.conf con todas las extensiones PJSIP
        """
        extensions = Extension.objects.filter(extension_type='PJSIP', is_active=True)
        
        config = [
            "; pjsip.conf - Generado automáticamente por VoziPOmni",
            "; NO EDITAR MANUALMENTE",
            "",
            "[transport-udp]",
            "type=transport",
            "protocol=udp",
            "bind=0.0.0.0:5060",
            "",
        ]
        
        for ext in extensions:
            # Endpoint
            config.extend([
                f"[{ext.extension}]",
                "type=endpoint",
                f"context={ext.context}",
                f"disallow=all",
                "allow=ulaw",
                "allow=alaw",
                f"auth={ext.extension}",
                f"aors={ext.extension}",
                f"callerid=\"{ext.name}\" <{ext.extension}>",
                "direct_media=no",
                "trust_id_inbound=yes",
                "device_state_busy_at=1",
                "",
            ])
            
            # Auth
            config.extend([
                f"[{ext.extension}]",
                "type=auth",
                "auth_type=userpass",
                f"username={ext.extension}",
                f"password={ext.secret}",
                "",
            ])
            
            # AOR
            config.extend([
                f"[{ext.extension}]",
                "type=aor",
                "max_contacts=1",
                "remove_existing=yes",
                "",
            ])
        
        return '\n'.join(config)
    
    def generate_extensions_conf(self):
        """
        Genera extensions.conf con el dialplan
        """
        config = [
            "; extensions.conf - Generado automáticamente por VoziPOmni",
            "; NO EDITAR MANUALMENTE",
            "",
            "[general]",
            "static=yes",
            "writeprotect=no",
            "",
            "[globals]",
            "",
            "; Contexto interno (extensiones)",
            "[from-internal]",
        ]
        
        # Agregar extensiones internas
        extensions = Extension.objects.filter(is_active=True).order_by('extension')
        for ext in extensions:
            config.extend([
                f"exten => {ext.extension},1,NoOp(Llamada a {ext.name})",
                f"same => n,Dial({ext.extension_type}/{ext.extension},30,tr)",
                f"same => n,Hangup()",
                "",
            ])
        
        # Rutas entrantes (DIDs)
        inbound_routes = InboundRoute.objects.filter(is_active=True)
        if inbound_routes.exists():
            config.extend([
                "",
                "; Contexto externo (DIDs)",
                "[from-external]",
            ])
            
            for route in inbound_routes:
                config.extend([
                    f"exten => {route.did},1,NoOp(DID: {route.description})",
                    f"same => n,Set(CALLERID(name)=${{CALLERID(num)}})",
                ])
                
                if route.destination_type == 'extension':
                    config.append(f"same => n,Dial(PJSIP/{route.destination},30,tr)")
                elif route.destination_type == 'ivr':
                    config.append(f"same => n,Goto(ivr-{route.destination},s,1)")
                elif route.destination_type == 'queue':
                    config.append(f"same => n,Queue({route.destination})")
                elif route.destination_type == 'voicemail':
                    config.append(f"same => n,VoiceMail({route.destination}@default)")
                
                config.extend([
                    "same => n,Hangup()",
                    "",
                ])
        
        # Rutas salientes
        outbound_routes = OutboundRoute.objects.filter(is_active=True).select_related('trunk')
        if outbound_routes.exists():
            config.extend([
                "",
                "; Rutas salientes",
            ])
            
            for route in outbound_routes:
                pattern = route.pattern.replace('X', '[0-9]').replace('N', '[2-9]').replace('Z', '[1-9]')
                config.extend([
                    f"exten => {pattern},1,NoOp(Saliente: {route.name})",
                ])
                
                if route.prepend:
                    config.append(f"same => n,Set(CALLERID(num)={route.prepend}${{CALLERID(num)}})")
                
                if route.prefix:
                    config.append(f"same => n,Set(dial_number={route.prefix}${{EXTEN}})")
                else:
                    config.append("same => n,Set(dial_number=${EXTEN})")
                
                config.extend([
                    f"same => n,Dial(PJSIP/${{dial_number}}@{route.trunk.name},60,tr)",
                    "same => n,Hangup()",
                    "",
                ])
        
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
            "",
            "[default]",
        ]
        
        for vm in voicemails:
            email_part = f",{vm.email}" if vm.email else ""
            config.append(f"{vm.mailbox} => {vm.password},{vm.name}{email_part}")
        
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
        ]
        
        for moh in moh_classes:
            config.extend([
                f"[{moh.name}]",
                f"mode={moh.mode}",
                f"directory={moh.directory}",
            ])
            
            if moh.application:
                config.append(f"application={moh.application}")
            
            if moh.sort:
                config.append(f"sort={moh.sort}")
            
            config.append("")
        
        return '\n'.join(config)
    
    def write_all_configs(self):
        """
        Escribe todos los archivos de configuración
        """
        configs = {
            'sip.conf': self.generate_sip_conf(),
            'pjsip.conf': self.generate_pjsip_conf(),
            'extensions.conf': self.generate_extensions_conf(),
            'voicemail.conf': self.generate_voicemail_conf(),
            'musiconhold.conf': self.generate_musiconhold_conf(),
        }
        
        for filename, content in configs.items():
            filepath = self.config_dir / filename
            try:
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"✓ {filename} generado exitosamente")
            except Exception as e:
                print(f"✗ Error generando {filename}: {e}")
        
        return configs
