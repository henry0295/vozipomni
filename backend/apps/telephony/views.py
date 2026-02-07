from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import (
    Call, SIPTrunk, IVR, Extension, InboundRoute,
    OutboundRoute, Voicemail, MusicOnHold, TimeCondition
)
from .serializers import (
    CallSerializer, SIPTrunkSerializer, IVRSerializer,
    ExtensionSerializer, InboundRouteSerializer, OutboundRouteSerializer,
    VoicemailSerializer, MusicOnHoldSerializer, TimeConditionSerializer
)
from .asterisk_config import AsteriskConfigGenerator
from .asterisk_ami import AsteriskAMI


class CallViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de llamadas
    """
    queryset = Call.objects.all()
    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['direction', 'status', 'agent', 'campaign']
    search_fields = ['caller_id', 'called_number', 'call_id']
    ordering_fields = ['start_time', 'duration']


class SIPTrunkViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de troncales SIP
    """
    queryset = SIPTrunk.objects.all()
    serializer_class = SIPTrunkSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """
        Probar conexión con la troncal
        """
        trunk = self.get_object()
        # TODO: Implementar prueba de conexión real con Asterisk
        return Response({
            'success': True,
            'message': f'Prueba de conexión para {trunk.name}',
            'registered': trunk.is_registered
        })


class IVRViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de IVRs
    """
    queryset = IVR.objects.all()
    serializer_class = IVRSerializer
    permission_classes = [IsAuthenticated]


class ExtensionViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de extensiones
    """
    queryset = Extension.objects.all()
    serializer_class = ExtensionSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['extension', 'name']
    filterset_fields = ['extension_type', 'is_active']
    ordering = ['extension']
    
    def perform_create(self, serializer):
        """Crear extensión y regenerar configuración de Asterisk"""
        extension = serializer.save()
        self._reload_asterisk_config()
        return extension
    
    def perform_update(self, serializer):
        """Actualizar extensión y regenerar configuración de Asterisk"""
        extension = serializer.save()
        self._reload_asterisk_config()
        return extension
    
    def perform_destroy(self, instance):
        """Eliminar extensión y regenerar configuración de Asterisk"""
        instance.delete()
        self._reload_asterisk_config()
    
    def _reload_asterisk_config(self):
        """Regenerar archivos de configuración y recargar Asterisk"""
        try:
            # Generar archivos de configuración
            generator = AsteriskConfigGenerator()
            generator.write_all_configs()
            
            # Recargar Asterisk vía AMI
            ami = AsteriskAMI()
            if ami.connect():
                ami.reload_module('chan_sip.so')
                ami.reload_module('chan_pjsip.so')
                ami.reload_dialplan()
                ami.disconnect()
        except Exception as e:
            print(f"Error recargando configuración de Asterisk: {e}")
    
    @action(detail=True, methods=['post'])
    def reload_config(self, request, pk=None):
        """
        Recargar configuración de la extensión en Asterisk
        """
        extension = self.get_object()
        try:
            self._reload_asterisk_config()
            return Response({
                'success': True,
                'message': f'Configuración de extensión {extension.extension} recargada'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InboundRouteViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de rutas entrantes
    """
    queryset = InboundRoute.objects.all()
    serializer_class = InboundRouteSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['did', 'description']
    filterset_fields = ['destination_type', 'is_active']
    ordering = ['priority', 'did']    
    def perform_create(self, serializer):
        serializer.save()
        self._reload_asterisk_config()
    
    def perform_update(self, serializer):
        serializer.save()
        self._reload_asterisk_config()
    
    def perform_destroy(self, instance):
        instance.delete()
        self._reload_asterisk_config()
    
    def _reload_asterisk_config(self):
        try:
            generator = AsteriskConfigGenerator()
            generator.write_all_configs()
            ami = AsteriskAMI()
            if ami.connect():
                ami.reload_dialplan()
                ami.disconnect()
        except Exception as e:
            print(f"Error recargando configuración: {e}")

class OutboundRouteViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de rutas salientes
    """
    queryset = OutboundRoute.objects.all()
    serializer_class = OutboundRouteSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'pattern']
    filterset_fields = ['trunk', 'is_active']
    
    def perform_create(self, serializer):
        serializer.save()
        self._reload_asterisk_config()
    
    def perform_update(self, serializer):
        serializer.save()
        self._reload_asterisk_config()
    
    def perform_destroy(self, instance):
        instance.delete()
        self._reload_asterisk_config()
    
    def _reload_asterisk_config(self):
        try:
            generator = AsteriskConfigGenerator()
            generator.write_all_configs()
            ami = AsteriskAMI()
            if ami.connect():
                ami.reload_dialplan()
                ami.disconnect()
        except Exception as e:
            print(f"Error recargando configuración: {e}")


class VoicemailViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de buzones de voz
    """
    queryset = Voicemail.objects.all()
    serializer_class = VoicemailSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['mailbox', 'name', 'email']
    filterset_fields = ['is_active']
    ordering = ['mailbox']    
    def perform_create(self, serializer):
        serializer.save()
        self._reload_asterisk_config()
    
    def perform_update(self, serializer):
        serializer.save()
        self._reload_asterisk_config()
    
    def perform_destroy(self, instance):
        instance.delete()
        self._reload_asterisk_config()
    
    def _reload_asterisk_config(self):
        try:
            generator = AsteriskConfigGenerator()
            generator.write_all_configs()
            ami = AsteriskAMI()
            if ami.connect():
                ami.reload_module('app_voicemail.so')
                ami.disconnect()
        except Exception as e:
            print(f"Error recargando configuración: {e}")    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Obtener mensajes del buzón
        """
        voicemail = self.get_object()
        # TODO: Obtener mensajes reales desde Asterisk
        return Response({
            'mailbox': voicemail.mailbox,
            'messages': [],
            'count': 0
        })


class MusicOnHoldViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de música en espera
    """
    queryset = MusicOnHold.objects.all()
    serializer_class = MusicOnHoldSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'description']
    filterset_fields = ['mode', 'is_active']
    
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """
        Listar archivos de audio de la clase MOH
        """
        moh = self.get_object()
        # TODO: Listar archivos reales del directorio
        return Response({
            'name': moh.name,
            'directory': moh.directory,
            'files': []
        })


class TimeConditionViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de condiciones de horario
    """
    queryset = TimeCondition.objects.all()
    serializer_class = TimeConditionSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name']
    filterset_fields = ['is_active']
    
    @action(detail=True, methods=['get'])
    def evaluate(self, request, pk=None):
        """
        Evaluar si la condición se cumple en el momento actual
        """
        condition = self.get_object()
        # TODO: Implementar lógica de evaluación real
        return Response({
            'name': condition.name,
            'matches': False,
            'current_destination': condition.false_destination
        })
