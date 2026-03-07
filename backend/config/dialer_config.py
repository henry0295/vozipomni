"""
Configuración centralizada del Dialer Engine
"""
from decouple import config


# ============= CONFIGURACIÓN PREDICTIVA =============

DIALER_CONFIG = {
    # Ratio inicial para marcador predictivo
    'PREDICTIVE_INITIAL_RATIO': config('DIALER_PREDICTIVE_RATIO', default=1.5, cast=float),
    
    # Tasa de abandono objetivo (3%)
    'ABANDON_RATE_TARGET': config('DIALER_ABANDON_TARGET', default=0.03, cast=float),
    
    # Ratio máximo permitido
    'MAX_RATIO': config('DIALER_MAX_RATIO', default=3.0, cast=float),
    
    # Ratio mínimo permitido
    'MIN_RATIO': config('DIALER_MIN_RATIO', default=1.0, cast=float),
    
    # Ajuste de ratio por iteración
    'RATIO_ADJUSTMENT_STEP': config('DIALER_RATIO_STEP', default=0.1, cast=float),
    
    # Intervalo de procesamiento (segundos)
    'PROCESSING_INTERVAL': config('DIALER_PROCESSING_INTERVAL', default=10, cast=int),
}


# ============= CONFIGURACIÓN PROGRESIVA =============

PROGRESSIVE_CONFIG = {
    # Intervalo entre ciclos de discado (segundos)
    'CYCLE_INTERVAL': config('PROGRESSIVE_CYCLE_INTERVAL', default=2, cast=int),
    
    # Timeout para esperar agente disponible (segundos)
    'AGENT_WAIT_TIMEOUT': config('PROGRESSIVE_AGENT_TIMEOUT', default=30, cast=int),
}


# ============= CONFIGURACIÓN CALL BLASTING =============

CALL_BLASTING_CONFIG = {
    # Llamadas concurrentes máximas
    'MAX_CONCURRENT_CALLS': config('BLASTING_MAX_CONCURRENT', default=50, cast=int),
    
    # Delay entre lotes (segundos)
    'BATCH_DELAY': config('BLASTING_BATCH_DELAY', default=5, cast=int),
    
    # Timeout por llamada (segundos)
    'CALL_TIMEOUT': config('BLASTING_CALL_TIMEOUT', default=30, cast=int),
}


# ============= CONFIGURACIÓN GENERAL =============

GENERAL_CONFIG = {
    # Timeout de llamada default (segundos)
    'DEFAULT_CALL_TIMEOUT': config('DIALER_CALL_TIMEOUT', default=30, cast=int),
    
    # Reintentos máximos por contacto
    'MAX_RETRIES': config('DIALER_MAX_RETRIES', default=3, cast=int),
    
    # Delay entre reintentos (segundos)
    'RETRY_DELAY': config('DIALER_RETRY_DELAY', default=300, cast=int),
    
    # TTL de datos en Redis (segundos)
    'REDIS_TTL': config('DIALER_REDIS_TTL', default=3600, cast=int),
}


# ============= CONFIGURACIÓN DE LÍMITES =============

LIMITS_CONFIG = {
    # Llamadas máximas por agente
    'MAX_CALLS_PER_AGENT': config('DIALER_MAX_CALLS_PER_AGENT', default=5, cast=int),
    
    # Agentes mínimos para iniciar campaña predictiva
    'MIN_AGENTS_PREDICTIVE': config('DIALER_MIN_AGENTS_PREDICTIVE', default=3, cast=int),
    
    # Contactos mínimos para campaña
    'MIN_CONTACTS': config('DIALER_MIN_CONTACTS', default=1, cast=int),
}


def get_dialer_config():
    """Obtener configuración completa del dialer"""
    return {
        'predictive': DIALER_CONFIG,
        'progressive': PROGRESSIVE_CONFIG,
        'call_blasting': CALL_BLASTING_CONFIG,
        'general': GENERAL_CONFIG,
        'limits': LIMITS_CONFIG,
    }
