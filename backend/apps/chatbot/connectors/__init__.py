"""Registro de tipos de conector."""
from .base import ActionSpec, BaseConnector, ConnectorError, ConnectorResult  # noqa: F401
from .glpi import GlpiConnector
from .http import HttpConnector

REGISTRY = {
    'glpi': GlpiConnector,
    'http': HttpConnector,
}


def get_connector(connector) -> BaseConnector:
    cls = REGISTRY.get(connector.connector_type)
    if not cls:
        raise ConnectorError(f'Tipo de conector no soportado: {connector.connector_type}')
    return cls(connector)


def actions_for(connector) -> list:
    cls = REGISTRY.get(connector.connector_type)
    return [a.to_dict() for a in cls.actions(connector)] if cls else []
