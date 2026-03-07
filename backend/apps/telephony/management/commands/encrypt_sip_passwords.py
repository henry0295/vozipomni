"""
Management command to encrypt existing SIP passwords
Run after applying migration 0009_encrypt_passwords
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.telephony.models import Extension, SIPTrunk


class Command(BaseCommand):
    help = 'Encrypt existing SIP passwords in database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be encrypted without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Encriptar contraseñas de extensiones
        extensions = Extension.objects.all()
        ext_count = 0
        
        self.stdout.write(f'Processing {extensions.count()} extensions...')
        
        with transaction.atomic():
            for ext in extensions:
                if ext.secret:
                    if dry_run:
                        self.stdout.write(f'  Would encrypt: Extension {ext.extension}')
                    else:
                        # El campo EncryptedCharField encriptará automáticamente al guardar
                        # Solo necesitamos forzar un save
                        ext.save(update_fields=['secret'])
                        self.stdout.write(f'  Encrypted: Extension {ext.extension}')
                    ext_count += 1
        
        # Encriptar contraseñas de troncales
        trunks = SIPTrunk.objects.all()
        trunk_count = 0
        
        self.stdout.write(f'\nProcessing {trunks.count()} SIP trunks...')
        
        with transaction.atomic():
            for trunk in trunks:
                fields_to_update = []
                
                if trunk.outbound_auth_password:
                    if dry_run:
                        self.stdout.write(f'  Would encrypt outbound password: Trunk {trunk.name}')
                    else:
                        fields_to_update.append('outbound_auth_password')
                
                if trunk.inbound_auth_password:
                    if dry_run:
                        self.stdout.write(f'  Would encrypt inbound password: Trunk {trunk.name}')
                    else:
                        fields_to_update.append('inbound_auth_password')
                
                if fields_to_update and not dry_run:
                    trunk.save(update_fields=fields_to_update)
                    self.stdout.write(f'  Encrypted: Trunk {trunk.name}')
                    trunk_count += 1
                elif fields_to_update:
                    trunk_count += 1
        
        # Resumen
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'DRY RUN: Would encrypt {ext_count} extensions and {trunk_count} trunks'
            ))
            self.stdout.write('Run without --dry-run to apply changes')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Successfully encrypted {ext_count} extensions and {trunk_count} trunks'
            ))
