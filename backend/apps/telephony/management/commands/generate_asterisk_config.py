"""
Management command para regenerar configuración de Asterisk
Uso: python manage.py generate_asterisk_config
"""
from django.core.management.base import BaseCommand
from apps.telephony.asterisk_config import AsteriskConfigGenerator
from apps.telephony.pjsip_config_generator import PJSIPConfigGenerator
from apps.telephony.asterisk_ami import AsteriskAMI
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Regenera archivos de configuración de Asterisk (extensiones, troncales, dialplan, etc.) y recarga'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-reload',
            action='store_true',
            help='Generar archivos sin recargar Asterisk',
        )
        parser.add_argument(
            '--only-extensions',
            action='store_true',
            help='Solo regenerar extensiones y dialplan',
        )
        parser.add_argument(
            '--only-trunks',
            action='store_true',
            help='Solo regenerar troncales PJSIP',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write(self.style.HTTP_INFO('Regenerando Configuración de Asterisk'))
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        self.stdout.write('')

        success = True

        # Regenerar troncales PJSIP
        if not options['only_extensions']:
            self.stdout.write('📡 Regenerando troncales PJSIP (pjsip_wizard.conf)...')
            try:
                pjsip_gen = PJSIPConfigGenerator()
                
                if options['no_reload']:
                    # Solo guardar sin recargar
                    pjsip_gen.save_config()
                    self.stdout.write(self.style.SUCCESS('  ✓ pjsip_wizard.conf generado (sin reload)'))
                else:
                    # Guardar y recargar
                    trunk_success, trunk_msg = pjsip_gen.save_and_reload()
                    if trunk_success:
                        self.stdout.write(self.style.SUCCESS(f'  ✓ {trunk_msg}'))
                    else:
                        self.stdout.write(self.style.ERROR(f'  ✗ {trunk_msg}'))
                        success = False
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                success = False
            self.stdout.write('')

        # Regenerar extensiones y dialplan
        if not options['only_trunks']:
            self.stdout.write('📞 Regenerando extensiones y dialplan...')
            try:
                config_gen = AsteriskConfigGenerator()
                configs = config_gen.write_all_configs()
                
                for filename in configs.keys():
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {filename}'))
                
                self.stdout.write('')
                
                # Recargar módulos de Asterisk
                if not options['no_reload']:
                    self.stdout.write('🔄 Recargando módulos de Asterisk...')
                    ami = AsteriskAMI()
                    if ami.connect():
                        # Recargar módulos relevantes
                        modules = [
                            ('res_pjsip.so', 'PJSIP'),
                            ('chan_pjsip.so', 'Canal PJSIP'),
                        ]
                        
                        for module, desc in modules:
                            if ami.reload_module(module):
                                self.stdout.write(self.style.SUCCESS(f'  ✓ {desc} recargado'))
                            else:
                                self.stdout.write(self.style.WARNING(f'  ⚠ No se pudo recargar {desc}'))
                        
                        # Recargar dialplan
                        if ami.reload_dialplan():
                            self.stdout.write(self.style.SUCCESS('  ✓ Dialplan recargado'))
                        else:
                            self.stdout.write(self.style.WARNING('  ⚠ No se pudo recargar dialplan'))
                        
                        # Recargar voicemail y queues
                        ami.reload_module('app_voicemail.so')
                        ami.reload_module('app_queue.so')
                        self.stdout.write(self.style.SUCCESS('  ✓ Voicemail y Queues recargados'))
                        
                        ami.disconnect()
                        self.stdout.write('')
                    else:
                        self.stdout.write(self.style.ERROR('  ✗ No se pudo conectar a AMI'))
                        success = False
                        self.stdout.write('')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                success = False
                self.stdout.write('')

        # Resumen
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
        if success:
            self.stdout.write(self.style.SUCCESS('✅ Configuración regenerada exitosamente'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Configuración regenerada con advertencias'))
        self.stdout.write(self.style.HTTP_INFO('=' * 70))
