"""
Custom Django model fields
"""
from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
import base64
import os


class EncryptedCharField(models.CharField):
    """
    CharField que encripta automáticamente el valor antes de guardarlo en la base de datos
    y lo desencripta al leerlo.
    
    Usa Fernet (symmetric encryption) de cryptography.
    """
    
    description = "Encrypted CharField"
    
    def __init__(self, *args, **kwargs):
        # Obtener o generar clave de encriptación
        encryption_key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        
        if not encryption_key:
            # Generar clave si no existe (solo para desarrollo)
            # En producción debe estar en settings
            encryption_key = Fernet.generate_key().decode()
            if settings.DEBUG:
                import warnings
                warnings.warn(
                    "FIELD_ENCRYPTION_KEY not found in settings. "
                    "Using generated key (not suitable for production)."
                )
        
        # Asegurar que la clave es bytes
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.cipher = Fernet(encryption_key)
        
        # Aumentar max_length para acomodar el texto encriptado
        # El texto encriptado es más largo que el original
        if 'max_length' in kwargs:
            kwargs['max_length'] = kwargs['max_length'] * 2
        
        super().__init__(*args, **kwargs)
    
    def get_prep_value(self, value):
        """Encriptar antes de guardar en DB"""
        if value is None or value == '':
            return value
        
        if isinstance(value, str):
            # Encriptar y convertir a string
            encrypted = self.cipher.encrypt(value.encode())
            return encrypted.decode()
        
        return value
    
    def from_db_value(self, value, expression, connection):
        """Desencriptar al leer de DB"""
        if value is None or value == '':
            return value
        
        try:
            # Desencriptar
            decrypted = self.cipher.decrypt(value.encode())
            return decrypted.decode()
        except Exception as e:
            # Si falla la desencriptación, puede ser que el valor no esté encriptado
            # (migración de datos antiguos)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to decrypt value: {e}")
            return value
    
    def to_python(self, value):
        """Convertir a tipo Python"""
        if isinstance(value, str) or value is None:
            return value
        return str(value)
    
    def deconstruct(self):
        """Para migraciones"""
        name, path, args, kwargs = super().deconstruct()
        # Restaurar max_length original
        if 'max_length' in kwargs:
            kwargs['max_length'] = kwargs['max_length'] // 2
        return name, path, args, kwargs


class EncryptedTextField(models.TextField):
    """
    TextField que encripta automáticamente el valor.
    Similar a EncryptedCharField pero para textos largos.
    """
    
    description = "Encrypted TextField"
    
    def __init__(self, *args, **kwargs):
        encryption_key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        
        if not encryption_key:
            encryption_key = Fernet.generate_key().decode()
            if settings.DEBUG:
                import warnings
                warnings.warn(
                    "FIELD_ENCRYPTION_KEY not found in settings. "
                    "Using generated key (not suitable for production)."
                )
        
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        self.cipher = Fernet(encryption_key)
        super().__init__(*args, **kwargs)
    
    def get_prep_value(self, value):
        """Encriptar antes de guardar en DB"""
        if value is None or value == '':
            return value
        
        if isinstance(value, str):
            encrypted = self.cipher.encrypt(value.encode())
            return encrypted.decode()
        
        return value
    
    def from_db_value(self, value, expression, connection):
        """Desencriptar al leer de DB"""
        if value is None or value == '':
            return value
        
        try:
            decrypted = self.cipher.decrypt(value.encode())
            return decrypted.decode()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to decrypt value: {e}")
            return value
    
    def to_python(self, value):
        """Convertir a tipo Python"""
        if isinstance(value, str) or value is None:
            return value
        return str(value)
