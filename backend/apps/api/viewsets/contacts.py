from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.contacts.models import Contact, ContactList

from apps.api import serializers
from core.permissions import IsAdminOrSupervisorOrReadOnly


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ContactSerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['first_name', 'last_name', 'phone', 'email', 'company']
    filterset_fields = ['contact_list', 'status']

    def get_queryset(self):
        """
        Extiende el queryset para soportar filtro por campaña.
        El panel de agente filtra por ?campaign={id} para obtener los
        contactos asignados a la campaña (a través de contact_list).
        También soporta ?status__in=pending,callback como filtro múltiple.
        """
        qs = Contact.objects.select_related('contact_list').prefetch_related('notes')

        # Filtro por campaña: busca el contact_list de la campaña
        campaign_id = self.request.query_params.get('campaign')
        if campaign_id:
            from apps.campaigns.models import Campaign
            try:
                campaign = Campaign.objects.get(id=campaign_id)
                if campaign.contact_list_id:
                    qs = qs.filter(contact_list_id=campaign.contact_list_id)
                else:
                    qs = qs.none()
            except Campaign.DoesNotExist:
                qs = qs.none()

        # Filtro múltiple de status: ?status__in=pending,callback
        status_in = self.request.query_params.get('status__in')
        if status_in:
            statuses = [s.strip() for s in status_in.split(',') if s.strip()]
            if statuses:
                qs = qs.filter(status__in=statuses)

        return qs


class ContactListViewSet(viewsets.ModelViewSet):
    queryset = ContactList.objects.all()
    serializer_class = serializers.ContactListSerializer
    permission_classes = [IsAdminOrSupervisorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['name', 'description']
