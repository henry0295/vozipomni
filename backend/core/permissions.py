"""
VozipOmni — RBAC Permissions
Sistema de permisos basado en roles: admin, supervisor, agent, analyst

Jerarquía de roles:
  admin       → acceso total (lectura + escritura + administración)
  supervisor  → lectura total + escritura limitada (sin gestión de usuarios)
  analyst     → solo lectura sobre reportes y llamadas
  agent       → solo sus propios datos y acciones de agente
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminUser(BasePermission):
    """Solo administradores."""
    message = 'Se requiere rol de administrador para esta acción.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'admin'
        )


class IsAdminOrSupervisor(BasePermission):
    """Administradores o supervisores."""
    message = 'Se requiere rol de administrador o supervisor para esta acción.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) in ('admin', 'supervisor')
        )


class IsAdminOrSupervisorOrReadOnly(BasePermission):
    """
    Lectura para cualquier usuario autenticado.
    Escritura solo para admin/supervisor.
    """
    message = 'Se requiere rol de administrador o supervisor para modificar.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(request.user, 'role', None) in ('admin', 'supervisor')


class IsAdminSupervisorOrAnalyst(BasePermission):
    """Lectura para admin, supervisor y analyst. Sin escritura para analyst."""
    message = 'Se requiere rol de administrador, supervisor o analista.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(request.user, 'role', None)
        if role in ('admin', 'supervisor'):
            return True
        # Analyst solo puede leer
        if role == 'analyst' and request.method in SAFE_METHODS:
            return True
        return False


class IsAgentUser(BasePermission):
    """Solo agentes autenticados."""
    message = 'Se requiere perfil de agente para esta acción.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) == 'agent'
        )


class IsOwnerAgentOrAdminSupervisor(BasePermission):
    """
    Un agente solo puede operar sobre su propio perfil/llamada.
    Admin y supervisor pueden operar sobre cualquiera.
    """
    message = 'Solo puedes acceder a tus propios datos como agente.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, 'role', None)
        if role in ('admin', 'supervisor'):
            return True
        # El agente solo puede ver/modificar su propio objeto
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'agent') and hasattr(obj.agent, 'user'):
            return obj.agent.user == request.user
        return False
