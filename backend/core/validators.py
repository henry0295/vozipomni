"""
Validadores personalizados para VoziPOmni
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_phone_number(value):
    """
    Valida que el número de teléfono tenga un formato válido.
    
    Acepta:
    - Números internacionales: +573001234567
    - Números nacionales: 3001234567
    - Extensiones: 1001
    - Patrones de Asterisk: _X., _1XX, etc.
    """
    if not value:
        return
    
    # Permitir patrones de Asterisk (empiezan con _ o contienen X, N, Z)
    if value.startswith('_') or any(c in value for c in ['X', 'N', 'Z', '!']):
        return
    
    # Limpiar el número (quitar espacios, guiones, paréntesis)
    cleaned = re.sub(r'[\s\-\(\)]', '', value)
    
    # Validar formato básico: solo dígitos y opcionalmente + al inicio
    if not re.match(r'^\+?\d{3,15}$', cleaned):
        raise ValidationError(
            _('%(value)s no es un número de teléfono válido. '
              'Debe contener entre 3 y 15 dígitos, opcionalmente con + al inicio.'),
            params={'value': value},
        )


def validate_asterisk_pattern(value):
    """
    Valida que el patrón de Asterisk sea válido.
    
    Patrones válidos:
    - _X. (cualquier dígito seguido de cualquier cosa)
    - _1XX (1 seguido de dos dígitos)
    - _[2-9]XXXXXXXXX (patrones de rango)
    - _01800XXXXXXX (números toll-free)
    """
    if not value:
        return
    
    # Debe empezar con _ o ser un número directo
    if not value.startswith('_') and not value.isdigit():
        # Verificar caracteres especiales permitidos
        allowed_chars = set('0123456789XNZX![]-.+')
        if not all(c in allowed_chars for c in value):
            raise ValidationError(
                _('%(value)s no es un patrón válido de Asterisk. '
                  'Use _ para patrones o solo dígitos para números directos.'),
                params={'value': value},
            )
    
    # Si empieza con _, validar sintaxis de patrón
    if value.startswith('_'):
        pattern = value[1:]  # Quitar el _
        # Validar caracteres permitidos en patrones
        allowed_pattern_chars = set('0123456789XNZX![]-.+')
        if not all(c in allowed_pattern_chars for c in pattern):
            raise ValidationError(
                _('%(value)s contiene caracteres no permitidos en patrones de Asterisk. '
                  'Use: 0-9, X, N, Z, !, [, ], -, .'),
                params={'value': value},
            )


def validate_sip_codec(value):
    """
    Valida que el codec sea uno de los soportados por Asterisk.
    """
    VALID_CODECS = [
        'ulaw', 'alaw', 'gsm', 'g729', 'g722', 'g726', 'g723',
        'speex', 'ilbc', 'opus', 'vp8', 'vp9', 'h264', 'h265'
    ]
    
    if value and value.lower() not in VALID_CODECS:
        raise ValidationError(
            _('%(value)s no es un codec válido. '
              'Codecs soportados: %(codecs)s'),
            params={'value': value, 'codecs': ', '.join(VALID_CODECS)},
        )


def validate_ip_address(value):
    """
    Valida que sea una dirección IP o hostname válido.
    """
    if not value:
        return
    
    # Permitir localhost, hostnames y IPs
    if value in ['localhost', '127.0.0.1', '::1']:
        return
    
    # Validar formato IP (simple)
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    
    if not re.match(ip_pattern, value) and not re.match(hostname_pattern, value):
        raise ValidationError(
            _('%(value)s no es una dirección IP o hostname válido.'),
            params={'value': value},
        )
    
    # Si es IP, validar rangos
    if re.match(ip_pattern, value):
        octets = [int(x) for x in value.split('.')]
        if not all(0 <= octet <= 255 for octet in octets):
            raise ValidationError(
                _('%(value)s no es una dirección IP válida (octetos deben estar entre 0-255).'),
                params={'value': value},
            )


def validate_port_number(value):
    """
    Valida que el puerto esté en el rango válido (1-65535).
    """
    if value is None:
        return
    
    try:
        port = int(value)
        if not 1 <= port <= 65535:
            raise ValidationError(
                _('El puerto debe estar entre 1 y 65535. Valor recibido: %(value)s'),
                params={'value': value},
            )
    except (ValueError, TypeError):
        raise ValidationError(
            _('%(value)s no es un número de puerto válido.'),
            params={'value': value},
        )


def validate_trunk_channels(value):
    """
    Valida que el número de canales sea razonable.
    """
    if value is None:
        return
    
    try:
        channels = int(value)
        if channels < 0:
            raise ValidationError(
                _('El número de canales no puede ser negativo.'),
            )
        if channels > 1000:
            raise ValidationError(
                _('El número de canales parece demasiado alto (máximo recomendado: 1000).'),
            )
    except (ValueError, TypeError):
        raise ValidationError(
            _('%(value)s no es un número válido de canales.'),
            params={'value': value},
        )
