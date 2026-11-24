"""Base común de los conectores."""
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConnectorResult:
    status: str                 # success | empty | error
    data: Any = None
    error: str = ''
    duration_ms: int = 0


@dataclass
class ActionSpec:
    name: str
    label: str
    inputs: list = field(default_factory=list)   # [{"name","label","required","help"}]
    outputs: str = ''                            # descripción del resultado
    returns_list: bool = False                   # útil para "Lista dinámica"

    def to_dict(self):
        return {'name': self.name, 'label': self.label, 'inputs': self.inputs,
                'outputs': self.outputs, 'returns_list': self.returns_list}


class ConnectorError(Exception):
    pass


class BaseConnector:
    """Subclases: definen `actions()` y `run(action, params)`."""

    def __init__(self, connector):
        self.connector = connector
        self.config = connector.config or {}
        self.secrets = connector.secret_values
        self.base_url = (connector.base_url or '').rstrip('/')
        self.timeout = max(3, min(int(connector.timeout_seconds or 15), 60))
        self.verify = bool(connector.verify_ssl)

    @classmethod
    def actions(cls, connector=None) -> list:
        return []

    def run(self, action: str, params: dict) -> ConnectorResult:  # pragma: no cover
        raise NotImplementedError

    def test(self) -> ConnectorResult:
        return ConnectorResult('success', {'message': 'Sin prueba específica'})

    def execute(self, action: str, params: dict, *, conversation_id=None, source='bot') -> ConnectorResult:
        """Ejecuta una acción, mide el tiempo y deja registro (sin parámetros ni datos sensibles)."""
        from apps.chatbot.models import ConnectorLog
        t0 = time.monotonic()
        try:
            if action == '__test__':
                result = self.test()
            else:
                valid = {a.name for a in self.actions(self.connector)}
                if action not in valid:
                    raise ConnectorError(f'Acción desconocida: {action}')
                result = self.run(action, params or {})
        except ConnectorError as e:
            result = ConnectorResult('error', error=str(e)[:500])
        except Exception as e:  # red, JSON, etc.
            logger.warning(f"[Conector {self.connector.name}] {action}: {e}")
            result = ConnectorResult('error', error=f'{type(e).__name__}: {str(e)[:400]}')
        result.duration_ms = int((time.monotonic() - t0) * 1000)
        try:
            ConnectorLog.objects.create(
                connector=self.connector, action=action, status=result.status,
                duration_ms=result.duration_ms, error=result.error[:1000],
                conversation_id=conversation_id, source=source,
            )
        except Exception:
            logger.exception('[Conector] No se pudo guardar el log')
        return result


def dig(data, path: str):
    """Extrae data['a']['b'][0]... con una ruta 'a.b.0'. Ruta vacía = todo."""
    if not path:
        return data
    cur = data
    for part in path.split('.'):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
        if cur is None:
            return None
    return cur


def is_empty(value) -> bool:
    return value is None or value == '' or value == [] or value == {}
