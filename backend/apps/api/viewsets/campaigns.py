from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from django.utils import timezone
from datetime import timedelta

from apps.campaigns.models import Campaign
from apps.agents.models import Agent

from apps.api import serializers
from core.permissions import IsAdminOrSupervisorOrReadOnly


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.select_related(
        'queue', 'contact_list', 'created_by'
    ).prefetch_related(
        'dispositions', 'agents', 'calls'
    )
    serializer_class = serializers.CampaignSerializer
    # Admin y supervisor gestionan campañas; analyst y agent solo leen
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    # agents: permite filtrar campañas por agente asignado (usado por el panel de agente)
    # Ejemplo: /api/campaigns/?agents=5&status=active
    filterset_fields = ['campaign_type', 'status', 'dialer_type', 'agents']

    def get_permissions(self):
        # preview-decide lo usan los agentes: la propiedad se valida dentro de la acción
        if self.action == 'preview_decide':
            return [IsAuthenticated()]
        return super().get_permissions()
    
    @extend_schema(
        summary="Iniciar campaña",
        description="""
        Activa una campaña y comienza el proceso de discado automático.
        
        La campaña debe estar en estado 'draft' o 'paused' para poder iniciarla.
        Se validará que tenga contactos y configuración válida antes de iniciar.
        """,
        request=None,
        responses={
            200: OpenApiResponse(
                response={'type': 'object'},
                description='Campaña iniciada exitosamente',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={'success': True, 'campaign_id': 123, 'campaign_name': 'Test Campaign', 'status': 'active'},
                    )
                ]
            ),
            400: OpenApiResponse(
                description='Error al iniciar campaña',
                examples=[
                    OpenApiExample(
                        'Already Active',
                        value={'error': 'Campaign is already active'},
                    ),
                    OpenApiExample(
                        'No Contacts',
                        value={'error': 'Campaign has no contacts'},
                    )
                ]
            ),
        },
        tags=['campaigns']
    )
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Iniciar campaña usando capa de servicio"""
        from apps.campaigns.services import CampaignService
        from core.exceptions import (
            CampaignAlreadyActiveError,
            NoContactsError,
            CampaignNotFoundError
        )
        
        try:
            result = CampaignService.start_campaign(pk, request.user)
            return Response(result)
        except CampaignAlreadyActiveError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except NoContactsError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except CampaignNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pausar campaña usando capa de servicio"""
        from apps.campaigns.services import CampaignService
        from core.exceptions import InvalidCampaignStateError, CampaignNotFoundError
        
        try:
            result = CampaignService.pause_campaign(pk, request.user)
            return Response(result)
        except InvalidCampaignStateError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except CampaignNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Obtener estadísticas detalladas de campaña"""
        from apps.campaigns.services import CampaignService
        from core.exceptions import CampaignNotFoundError
        
        try:
            stats = CampaignService.get_campaign_statistics(pk)
            return Response(stats)
        except CampaignNotFoundError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def next_contact(self, request, pk=None):
        """Obtener siguiente contacto para marcación (dialer)"""
        campaign = self.get_object()
        if getattr(request.user, 'role', None) == 'agent' and not campaign.agents.filter(user=request.user).exists():
            return Response(
                {'error': 'El agente no está asignado a esta campaña'},
                status=status.HTTP_403_FORBIDDEN,
            )
        agent_id = request.query_params.get('agent_id')
        
        if not agent_id:
            return Response(
                {'error': 'agent_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # El agente solo puede pedir contactos para su propio agent_id
        if getattr(request.user, 'role', None) == 'agent' and not request.user.is_superuser:
            try:
                owns = Agent.objects.filter(id=agent_id, user=request.user).exists()
            except (ValueError, TypeError):
                owns = False
            if not owns:
                return Response(
                    {'error': 'No puede pedir contactos para otro agente'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        
        try:
            from apps.contacts.models import Contact
            from django.db.models import Q
            
            # Buscar contactos pendientes de la campaña
            contact = Contact.objects.filter(
                contact_list=campaign.contact_list,
                status__in=['pending', 'callback']
            ).exclude(
                # Excluir contactos llamados en las últimas 24h
                calls__start_time__gte=timezone.now() - timedelta(hours=24)
            ).order_by('priority', 'id').first()
            
            if not contact:
                return Response(
                    {'contact': None, 'message': 'No pending contacts'},
                    status=status.HTTP_200_OK
                )
            
            return Response({
                'contact': {
                    'id': contact.id,
                    'name': contact.full_name,
                    'phone': contact.phone,
                    'email': contact.email,
                    'company': contact.company,
                    'notes': list(contact.notes.order_by('-created_at').values(
                        'note', 'created_at', 'is_important'
                    )[:5]),
                    'custom_fields': contact.custom_fields,
                    'priority': contact.priority,
                    'call_history': [
                        {
                            'id': c.id,
                            'date': c.start_time.strftime('%Y-%m-%d %H:%M'),
                            'disposition': c.disposition.name if c.disposition else 'N/A',
                            'notes': c.notes
                        } for c in contact.calls.order_by('-start_time')[:5]
                    ]
                }
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """
        Clonar campaña (o plantilla) como una nueva campaña.
        Se puede especificar 'name' en el body para el nombre de la nueva campaña.
        Las relaciones M2M (agents, required_skills) se copian a la nueva campaña.
        """
        source = self.get_object()
        new_name = request.data.get('name', f'{source.name} (copia)')

        # Guardar relaciones M2M antes de mutar el objeto
        original_agents = list(source.agents.all())
        original_skills = list(source.required_skills.all())

        # Duplicar sin PK — Django hace INSERT cuando pk es None
        source.pk = None
        source.id = None
        source.name = new_name
        source.status = 'draft'
        source.is_template = False
        source.template_name = ''
        source.total_contacts = 0
        source.contacted = 0
        source.successful = 0
        source.created_by = request.user
        source.save()

        # Copiar relaciones M2M a la nueva campaña
        if original_agents:
            source.agents.set(original_agents)
        if original_skills:
            source.required_skills.set(original_skills)

        return Response(
            serializers.CampaignSerializer(source, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='preview-decide')
    def preview_decide(self, request, pk=None):
        """
        Registrar decisión de preview: el agente acepta o rechaza el contacto asignado.
        Body: {"agent_id": 1, "decision": "accept"|"reject"}
        El dialer lee estas claves de Redis para continuar/saltar.
        """
        import redis as _redis
        from django.conf import settings as _settings

        agent_id = request.data.get('agent_id')
        decision = request.data.get('decision')

        if not agent_id or decision not in ('accept', 'reject'):
            return Response(
                {'error': 'Se requiere agent_id y decision (accept/reject)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role = getattr(request.user, 'role', None)
        if not request.user.is_superuser and role not in ('admin', 'supervisor'):
            if role != 'agent':
                return Response(
                    {'error': 'Sin permisos para decidir contactos en preview'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            campaign = self.get_object()
            try:
                owns = Agent.objects.filter(id=agent_id, user=request.user, campaigns=campaign).exists()
            except (ValueError, TypeError):
                owns = False
            if not owns:
                return Response(
                    {'error': 'No puede decidir por otro agente ni en una campaña no asignada'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            redis_url = getattr(_settings, 'REDIS_URL', 'redis://localhost:6379/0')
            r = _redis.from_url(redis_url, decode_responses=True)
            campaign_id = pk
            base_key = f'campaign:{campaign_id}:preview:agent:{agent_id}'
            ttl = 120  # segundos

            if decision == 'accept':
                r.setex(f'{base_key}:accepted', ttl, '1')
            else:
                r.setex(f'{base_key}:rejected', ttl, '1')

            return Response({'status': 'ok', 'decision': decision})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='templates')
    def templates(self, request):
        """Listar todas las campañas marcadas como plantilla."""
        qs = Campaign.objects.filter(is_template=True).order_by('name')
        return Response(
            serializers.CampaignSerializer(qs, many=True, context={'request': request}).data
        )

    @action(detail=True, methods=['get', 'post'], url_path='dispositions')
    def dispositions(self, request, pk=None):
        """
        GET  → calificaciones de la campaña (usado por Auditoría y consola del agente)
        POST → crear calificación {code, name, is_success, requires_callback, order, form_id}
        """
        from apps.campaigns.models import CampaignDisposition
        campaign = self.get_object()

        if request.method == 'GET':
            qs = CampaignDisposition.objects.filter(campaign=campaign).select_related('form')
            return Response(serializers.CampaignDispositionSerializer(qs, many=True).data)

        if getattr(request.user, 'role', None) not in ('admin', 'supervisor') and not request.user.is_superuser:
            return Response({'error': 'Solo admin/supervisor pueden crear calificaciones'},
                            status=status.HTTP_403_FORBIDDEN)
        ser = serializers.CampaignDispositionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if CampaignDisposition.objects.filter(campaign=campaign, code=ser.validated_data['code']).exists():
            return Response({'code': ['Ya existe una calificación con ese código en la campaña.']},
                            status=status.HTTP_400_BAD_REQUEST)
        ser.save(campaign=campaign)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'dispositions/(?P<disposition_id>[0-9]+)')
    def disposition_detail(self, request, pk=None, disposition_id=None):
        """PATCH/DELETE de una calificación específica."""
        from apps.campaigns.models import CampaignDisposition
        if getattr(request.user, 'role', None) not in ('admin', 'supervisor') and not request.user.is_superuser:
            return Response({'error': 'Sin permisos'}, status=status.HTTP_403_FORBIDDEN)
        campaign = self.get_object()
        try:
            disp = CampaignDisposition.objects.get(pk=disposition_id, campaign=campaign)
        except CampaignDisposition.DoesNotExist:
            return Response({'error': 'Calificación no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            disp.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        ser = serializers.CampaignDispositionSerializer(disp, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class CampaignFormViewSet(viewsets.ModelViewSet):
    """CRUD para formularios de campaña."""
    from apps.campaigns.models import CampaignForm as _CampaignForm
    queryset = _CampaignForm.objects.all()
    serializer_class = serializers.CampaignFormSerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
