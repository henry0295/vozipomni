from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.users.models import User
from apps.campaigns.models import Campaign
from apps.agents.models import Agent
from apps.contacts.models import Contact, ContactList
from apps.queues.models import Queue
from apps.telephony.models import Call
from apps.recordings.models import Recording
from apps.reports.models import Report

from apps.api import serializers


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_active', 'is_active_agent']


class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = serializers.CampaignSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['campaign_type', 'status', 'dialer_type']
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Iniciar campaña"""
        campaign = self.get_object()
        campaign.status = 'active'
        campaign.save()
        return Response({'status': 'campaign started'})
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pausar campaña"""
        campaign = self.get_object()
        campaign.status = 'paused'
        campaign.save()
        return Response({'status': 'campaign paused'})
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Obtener estadísticas de campaña"""
        campaign = self.get_object()
        return Response({
            'total_contacts': campaign.total_contacts,
            'contacted': campaign.contacted,
            'successful': campaign.successful,
            'success_rate': campaign.success_rate
        })


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = serializers.AgentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['agent_id', 'sip_extension', 'user__username']
    filterset_fields = ['status', 'webrtc_enabled']
    
    @action(detail=True, methods=['post'])
    def login(self, request, pk=None):
        """Marcar agente como conectado"""
        agent = self.get_object()
        agent.login()
        return Response({'status': 'logged in'})
    
    @action(detail=True, methods=['post'])
    def logout(self, request, pk=None):
        """Marcar agente como desconectado"""
        agent = self.get_object()
        agent.logout()
        return Response({'status': 'logged out'})
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Cambiar estado del agente"""
        agent = self.get_object()
        new_status = request.data.get('status')
        if new_status in dict(Agent.STATUS_CHOICES):
            agent.status = new_status
            agent.save()
            return Response({'status': 'updated'})
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = serializers.ContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'phone', 'email', 'company']
    filterset_fields = ['contact_list', 'status']


class ContactListViewSet(viewsets.ModelViewSet):
    queryset = ContactList.objects.all()
    serializer_class = serializers.ContactListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'description']


class QueueViewSet(viewsets.ModelViewSet):
    queryset = Queue.objects.all()
    serializer_class = serializers.QueueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'extension']
    filterset_fields = ['is_active', 'strategy']


class CallViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Call.objects.all()
    serializer_class = serializers.CallSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['call_id', 'caller_id', 'called_number']
    filterset_fields = ['direction', 'status', 'agent', 'campaign']
    ordering_fields = ['start_time', 'talk_time']


class RecordingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Recording.objects.all()
    serializer_class = serializers.RecordingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['filename', 'call__call_id']
    filterset_fields = ['status', 'agent', 'campaign']


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = serializers.ReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name']
    filterset_fields = ['report_type', 'format', 'status']
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """Generar reporte"""
        report = self.get_object()
        from apps.reports.tasks import generate_report
        generate_report.delay(report.id)
        return Response({'status': 'generating report'})
