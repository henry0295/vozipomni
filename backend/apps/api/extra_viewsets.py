"""
ViewSets para:
  - Auditoría de gestiones (CallDispositionAudit)
  - Grupos de agentes (AgentGroup)
  - Razones de descanso (AgentBreakReason)
"""
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from core.permissions import IsAdminOrSupervisor, IsAdminUser, IsAdminOrSupervisorOrReadOnly


# ─────────────────────────────────────────────────────────────────────────────
# Serializers inline (livianos, sin archivo extra para no sobre-ingeniería)
# ─────────────────────────────────────────────────────────────────────────────

class AgentBreakReasonSerializer(drf_serializers.ModelSerializer):
    class Meta:
        from apps.agents.models import AgentBreakReason
        model = AgentBreakReason
        fields = ['id', 'name', 'code', 'is_paid', 'max_duration', 'order', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class AgentGroupSerializer(drf_serializers.ModelSerializer):
    agent_count = drf_serializers.ReadOnlyField()

    class Meta:
        from apps.agents.models import AgentGroup
        model = AgentGroup
        fields = ['id', 'name', 'description', 'agents', 'agent_count', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'agent_count']


class AuditSerializer(drf_serializers.ModelSerializer):
    call_id = drf_serializers.CharField(source='call.call_id', read_only=True)
    agent_name = drf_serializers.SerializerMethodField()
    audited_by_name = drf_serializers.SerializerMethodField()
    original_disposition_name = drf_serializers.CharField(
        source='original_disposition.name', read_only=True
    )
    corrected_disposition_name = drf_serializers.CharField(
        source='corrected_disposition.name', read_only=True
    )

    class Meta:
        from apps.audit.models import CallDispositionAudit
        model = CallDispositionAudit
        fields = [
            'id', 'call', 'call_id', 'agent', 'agent_name', 'campaign',
            'original_disposition', 'original_disposition_name',
            'agent_notes', 'status', 'audited_by', 'audited_by_name',
            'corrected_disposition', 'corrected_disposition_name',
            'supervisor_notes', 'quality_score',
            'created_at', 'audited_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'audited_at', 'audited_by']

    def get_agent_name(self, obj):
        if obj.agent:
            return obj.agent.user.get_full_name() or obj.agent.user.username
        return None

    def get_audited_by_name(self, obj):
        if obj.audited_by:
            return obj.audited_by.get_full_name() or obj.audited_by.username
        return None


# ─────────────────────────────────────────────────────────────────────────────
# ViewSets
# ─────────────────────────────────────────────────────────────────────────────

class AgentBreakReasonViewSet(viewsets.ModelViewSet):
    """Gestión de razones de descanso configurables."""
    from apps.agents.models import AgentBreakReason
    queryset = AgentBreakReason.objects.all()
    serializer_class = AgentBreakReasonSerializer
    # Solo admin crea/borra razones; supervisor puede listar
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_paid']
    search_fields = ['name', 'code']
    ordering_fields = ['order', 'name']
    ordering = ['order']


class AgentGroupViewSet(viewsets.ModelViewSet):
    """Gestión de grupos de agentes."""
    from apps.agents.models import AgentGroup
    queryset = AgentGroup.objects.prefetch_related('agents__user').all()
    serializer_class = AgentGroupSerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='add_agent')
    def add_agent(self, request, pk=None):
        """Agregar un agente al grupo."""
        from apps.agents.models import Agent, AgentGroup
        group = self.get_object()
        agent_id = request.data.get('agent_id')
        try:
            agent = Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            return Response({'error': 'Agente no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        group.agents.add(agent)
        return Response({'success': True, 'message': f'Agente {agent.agent_id} agregado al grupo {group.name}'})

    @action(detail=True, methods=['post'], url_path='remove_agent')
    def remove_agent(self, request, pk=None):
        """Retirar un agente del grupo."""
        from apps.agents.models import Agent
        group = self.get_object()
        agent_id = request.data.get('agent_id')
        try:
            agent = Agent.objects.get(pk=agent_id)
        except Agent.DoesNotExist:
            return Response({'error': 'Agente no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        group.agents.remove(agent)
        return Response({'success': True, 'message': f'Agente {agent.agent_id} retirado del grupo {group.name}'})


class AuditViewSet(viewsets.ModelViewSet):
    """Auditoría de gestiones de agentes."""
    from apps.audit.models import CallDispositionAudit
    queryset = CallDispositionAudit.objects.select_related(
        'call', 'agent__user', 'campaign',
        'original_disposition', 'corrected_disposition', 'audited_by'
    ).all()
    serializer_class = AuditSerializer
    permission_classes = [IsAdminOrSupervisor]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'agent', 'campaign']
    search_fields = ['call__call_id', 'agent__agent_id', 'agent__user__username']
    ordering_fields = ['created_at', 'audited_at', 'quality_score']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        """Aprobar la gestión del agente."""
        audit = self.get_object()
        notes = request.data.get('notes', '')
        audit.approve(supervisor=request.user, notes=notes)
        return Response({'success': True, 'status': 'approved'})

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """Rechazar la gestión del agente."""
        audit = self.get_object()
        notes = request.data.get('notes', '')
        if not notes:
            return Response({'error': 'Se requiere una nota de rechazo'}, status=status.HTTP_400_BAD_REQUEST)
        audit.reject(supervisor=request.user, notes=notes)
        return Response({'success': True, 'status': 'rejected'})

    @action(detail=True, methods=['post'], url_path='correct')
    def correct(self, request, pk=None):
        """Corregir la calificación del agente."""
        from apps.campaigns.models import CampaignDisposition
        audit = self.get_object()
        notes = request.data.get('notes', '')
        score = request.data.get('quality_score')
        disposition_id = request.data.get('corrected_disposition_id')

        if not disposition_id:
            return Response({'error': 'corrected_disposition_id requerido'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            new_disposition = CampaignDisposition.objects.get(pk=disposition_id)
        except CampaignDisposition.DoesNotExist:
            return Response({'error': 'Calificación no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        audit.correct(supervisor=request.user, new_disposition=new_disposition, notes=notes, score=score)
        return Response({'success': True, 'status': 'corrected'})

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Resumen estadístico de auditorías por período."""
        from apps.audit.models import CallDispositionAudit
        from django.db.models import Count, Avg

        qs = self.get_queryset()
        total = qs.count()
        by_status = qs.values('status').annotate(count=Count('id'))
        avg_score = qs.filter(quality_score__isnull=False).aggregate(avg=Avg('quality_score'))['avg']

        return Response({
            'total': total,
            'by_status': {item['status']: item['count'] for item in by_status},
            'avg_quality_score': round(avg_score, 2) if avg_score else None,
            'pending': qs.filter(status='pending').count(),
        })
