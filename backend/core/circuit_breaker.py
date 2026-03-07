"""
Circuit Breaker implementation for external services
"""
import time
import logging
from functools import wraps
from enum import Enum
from typing import Callable, Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Estados del circuit breaker"""
    CLOSED = "closed"  # Funcionando normalmente
    OPEN = "open"  # Circuito abierto, rechazando llamadas
    HALF_OPEN = "half_open"  # Probando si el servicio se recuperó


class CircuitBreakerError(Exception):
    """Excepción cuando el circuit breaker está abierto"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation
    
    Protege contra fallos en cascada al detectar servicios caídos
    y evitar llamadas innecesarias.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "circuit_breaker"
    ):
        """
        Args:
            failure_threshold: Número de fallos antes de abrir el circuito
            recovery_timeout: Segundos antes de intentar recuperación
            expected_exception: Tipo de excepción que cuenta como fallo
            name: Nombre del circuit breaker para logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecutar función protegida por circuit breaker
        
        Args:
            func: Función a ejecutar
            *args, **kwargs: Argumentos para la función
            
        Returns:
            Resultado de la función
            
        Raises:
            CircuitBreakerError: Si el circuito está abierto
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service unavailable. Retry after {self.recovery_timeout}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Verificar si es tiempo de intentar recuperación"""
        if self.last_failure_time is None:
            return True
        
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """Manejar llamada exitosa"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}' recovered, closing circuit")
            self.state = CircuitState.CLOSED
        
        self.failure_count = 0
    
    def _on_failure(self):
        """Manejar llamada fallida"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(
                    f"Circuit breaker '{self.name}' threshold reached "
                    f"({self.failure_count} failures), opening circuit"
                )
                self.state = CircuitState.OPEN
        else:
            logger.warning(
                f"Circuit breaker '{self.name}' failure {self.failure_count}/"
                f"{self.failure_threshold}"
            )
    
    def reset(self):
        """Resetear manualmente el circuit breaker"""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def __call__(self, func: Callable) -> Callable:
        """Usar como decorador"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper


# Circuit breakers globales para servicios comunes
ami_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    name="asterisk_ami"
)

redis_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    name="redis"
)

database_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    name="database"
)
