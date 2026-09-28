"""
Views REST de mensajería multicanal.

Endpoints:
  GET  /api/messaging/channels/              — listar canales
  POST /api/messaging/channels/              — crear canal
  GET  /api/messaging/conversations/         — listar conversaciones (con filtros)
  POST /api/messaging/conversations/         — crear conversación
  GET  /api/messaging/conversations/{id}/    — detalle con mensajes
  POST /api/messaging/conversations/{id}/close/    — cerrar conversación
  POST /api/messaging/conversations/{id}/assign/   — asignar agente
  POST /api/messaging/conversations/{id}/messages/ — enviar mensaje
  GET  /api/messaging/conversations/{id}/messages/ — listar mensajes
  POST /api/messaging/conversations/{id}/messages/{msg_id}/read/ — marcar leído
"""
import logging

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminOrSupervisor, IsAdminOrSupervisorOrReadOnly
from .models import Channel, Conversation, Message
from .serializers import (
    ChannelSerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
)

logger = logging.getLogger(__name__)


class ChannelViewSet(viewsets.ModelViewSet):
    """CRUD de canales de comunicación."""

    queryset = Channel.objects.all()
    serializer_class = ChannelSerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['channel_type', 'is_active']
    search_fields = ['name', 'identifier']
    ordering = ['channel_type', 'name']


class ConversationViewSet(viewsets.ModelViewSet):
    """
    CRUD + acciones de conversaciones.
    Los agentes solo ven sus propias conversaciones o las sin asignar.
    Admin/supervisor ven todas.
    """

    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'channel', 'agent', 'campaign']
    search_fields = ['contact_identifier', 'contact__first_name', 'contact__last_name']
    ordering_fields = ['started_at', 'closed_at']
    ordering = ['-started_at']

    def get_queryset(self):
        qs = Conversation.objects.select_related(
            'channel', 'agent__user', 'contact', 'campaign'
        ).prefetch_related('messages')

        user = self.request.user
        role = getattr(user, 'role', None)
        if role not in ('admin', 'supervisor') and not user.is_superuser:
            # Agentes: solo sus conversaciones o las sin asignar
            try:
                from apps.agents.models import Agent
                agent = Agent.objects.get(user=user)
                qs = qs.filter(models.Q(agent=agent) | models.Q(agent__isnull=True))
            except Exception:
                qs = qs.none()

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer

    # ── Acciones ─────────────────────────────────────────────────────────────

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Cerrar una conversación."""
        conv = self.get_object()
        if conv.status == 'closed':
            return Response(
                {'error': 'La conversación ya está cerrada'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        conv.status = 'closed'
        conv.closed_at = timezone.now()
        conv.save(update_fields=['status', 'closed_at'])
        return Response({'status': 'closed', 'closed_at': conv.closed_at.isoformat()})

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Asignar la conversación a un agente."""
        from apps.agents.models import Agent

        conv = self.get_object()
        agent_id = request.data.get('agent_id')
        if not agent_id:
            return Response({'error': 'agent_id requerido'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            return Response({'error': 'Agente no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        conv.agent = agent
        if conv.status == 'waiting':
            conv.status = 'open'
        conv.save(update_fields=['agent', 'status'])

        return Response({
            'agent_id': agent.id,
            'agent_name': agent.user.get_full_name() or agent.user.username,
            'status': conv.status,
        })

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        """
        GET  → listar mensajes de la conversación
        POST → enviar un mensaje en la conversación
        """
        conv = self.get_object()

        if request.method == 'GET':
            msgs = conv.messages.order_by('sent_at')
            # Marcar mensajes inbound como leídos al consultar
            msgs.filter(direction='inbound', is_read=False).update(is_read=True)
            serializer = MessageSerializer(msgs, many=True)
            return Response(serializer.data)

        # POST — enviar mensaje outbound
        body = request.data.get('body', '').strip()
        media_url = request.data.get('media_url')
        if not body:
            return Response({'error': 'body es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        msg = Message.objects.create(
            conversation=conv,
            direction='outbound',
            body=body,
            media_url=media_url,
            is_read=True,
        )

        # Asegurarse de que la conversación esté abierta
        if conv.status != 'open':
            conv.status = 'open'
            conv.save(update_fields=['status'])

        # TODO: enviar el mensaje a la plataforma externa (WhatsApp/SMS/Email)
        # Despachar tarea Celery cuando exista la integración:
        # send_external_message.delay(msg.id)

        logger.info(
            f"[Messaging] Mensaje enviado en conv {conv.id} "
            f"(canal={conv.channel.channel_type})"
        )
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='messages/(?P<msg_id>[0-9]+)/read')
    def mark_read(self, request, pk=None, msg_id=None):
        """Marcar un mensaje específico como leído."""
        conv = self.get_object()
        try:
            msg = conv.messages.get(pk=msg_id)
        except Message.DoesNotExist:
            return Response({'error': 'Mensaje no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        msg.is_read = True
        msg.save(update_fields=['is_read'])
        return Response({'id': msg.id, 'is_read': True})


# Importar Q para el filtro de agente
from django.db import models
