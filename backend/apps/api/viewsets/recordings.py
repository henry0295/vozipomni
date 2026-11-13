from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from apps.recordings.models import Recording

from apps.api import serializers
from core.permissions import IsAdminSupervisorOrAnalyst


class RecordingViewSet(viewsets.ModelViewSet):
    queryset = Recording.objects.all()
    serializer_class = serializers.RecordingSerializer
    # Grabaciones: admin y supervisor; analyst puede leer también
    permission_classes = [IsAdminSupervisorOrAnalyst]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['filename', 'call__call_id']
    filterset_fields = ['status', 'agent', 'campaign']
    http_method_names = ['get', 'delete', 'head', 'options']  # Solo lectura + borrado

    def get_queryset(self):
        qs = super().get_queryset().select_related('call', 'agent__user')
        p = self.request.query_params
        if p.get('date_from'):
            qs = qs.filter(created_at__date__gte=p['date_from'])
        if p.get('date_to'):
            qs = qs.filter(created_at__date__lte=p['date_to'])
        return qs

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Audio de la grabación (autenticado). ?inline=1 para reproducir en el navegador."""
        import mimetypes
        import os
        from django.http import FileResponse
        from apps.recordings.tasks import RECORDING_DIRS

        recording = self.get_object()
        path = os.path.realpath(recording.file_path or '')
        # Solo servir archivos dentro de los directorios de grabaciones (el path viene de la BD)
        allowed = [os.path.realpath(d) for d in RECORDING_DIRS]
        if not path or not any(path.startswith(d + os.sep) for d in allowed) or not os.path.isfile(path):
            return Response({'error': 'El archivo de la grabación no está disponible'},
                            status=status.HTTP_404_NOT_FOUND)

        Recording.objects.filter(pk=recording.pk).update(access_count=recording.access_count + 1)
        content_type = mimetypes.guess_type(path)[0] or 'audio/wav'
        return FileResponse(open(path, 'rb'), content_type=content_type,
                            as_attachment=request.query_params.get('inline') != '1',
                            filename=recording.filename or os.path.basename(path))

    def perform_destroy(self, instance):
        import os
        if instance.file_path and os.path.exists(instance.file_path):
            try:
                os.remove(instance.file_path)
            except OSError:
                pass
        instance.delete()
