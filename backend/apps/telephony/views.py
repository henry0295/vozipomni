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
    
    def perform_create(self, serializer):
        """Crear troncal y regenerar configuración PJSIP"""
        trunk = serializer.save()
        self._regenerate_pjsip_config()
        return trunk
    
    def perform_update(self, serializer):
        """Actualizar troncal y regenerar configuración PJSIP"""
        trunk = serializer.save()
        self._regenerate_pjsip_config()
        return trunk
    
    def perform_destroy(self, instance):
        """Eliminar troncal y regenerar configuración PJSIP"""
        instance.delete()
        self._regenerate_pjsip_config()
    
    def _regenerate_pjsip_config(self):
        """Regenerar configuración PJSIP y recargar Asterisk"""
        try:
            from .pjsip_config_generator import PJSIPConfigGenerator
            
            generator = PJSIPConfigGenerator()
            success, message = generator.save_and_reload()
            
            if not success:
                # Log error pero no fallar la operación
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"No se pudo recargar PJSIP automáticamente: {message}")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error regenerando configuración PJSIP: {str(e)}")
    
    @action(detail=False, methods=['post'])
    def regenerate_config(self, request):
        """
        Regenerar configuración PJSIP de todas las troncales y recargar Asterisk
        
        POST /api/telephony/trunks/regenerate_config/
        """
        try:
            from .pjsip_config_generator import PJSIPConfigGenerator
            
            generator = PJSIPConfigGenerator()
            success, message = generator.save_and_reload()
            
            return Response({
                'success': success,
                'message': message
            }, status=status.HTTP_200_OK if success else status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def preview_config(self, request, pk=None):
        """
        Previsualizar la configuración PJSIP que se generará para esta troncal
        
        GET /api/telephony/trunks/{id}/preview_config/
        """
        trunk = self.get_object()
        try:
            from .pjsip_config_generator import PJSIPConfigGenerator
            
            generator = PJSIPConfigGenerator()
            config_text = generator.generate_trunk_config(trunk)
            
            return Response({
                'success': True,
                'trunk_name': trunk.name,
                'config': config_text
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error generando configuración: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """
        Probar conexión y obtener estado de la troncal
        
        POST /api/telephony/trunks/{id}/test_connection/
        
        - Si requiere registro: verifica estado de registro
        - Si NO requiere registro: verifica disponibilidad del endpoint
        """
        trunk = self.get_object()
        try:
            ami = AsteriskAMI()
            if not ami.connect():
                return Response({
                    'success': False,
                    'message': 'No se pudo conectar a Asterisk AMI',
                    'registered': False,
                    'available': False
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Si NO requiere registro, verificar disponibilidad del endpoint
            if not trunk.sends_registration:
                endpoints = ami.pjsip_show_endpoints()
                ami.disconnect()
                
                if trunk.name in endpoints:
                    endpoint = endpoints[trunk.name]
                    has_contacts = len(endpoint.get('contacts', [])) > 0
                    
                    return Response({
                        'success': True,
                        'trunk': trunk.name,
                        'registered': False,  # No aplica registro
                        'available': has_contacts,
                        'status': 'Disponible' if has_contacts else 'Sin Contacto',
                        'message': f'Endpoint {trunk.name}: {"✓ Disponible" if has_contacts else "⚠ Sin contacto activo"}',
                        'requires_registration': False
                    })
                else:
                    return Response({
                        'success': False,
                        'trunk': trunk.name,
                        'registered': False,
                        'available': False,
                        'status': 'No Encontrado',
                        'message': f'Endpoint {trunk.name} no encontrado en Asterisk',
                        'requires_registration': False
                    })
            
            # Si SÍ requiere registro, verificar estado de registro
            reg_status = ami.get_trunk_registration_status(trunk.name)
            ami.disconnect()
            
            is_registered = reg_status == 'Registered'
            
            return Response({
                'success': True,
                'trunk': trunk.name,
                'registered': is_registered,
                'available': is_registered,
                'status': reg_status,
                'message': f'Estado de registro: {reg_status}',
                'requires_registration': True
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}',
                'registered': False,
                'available': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def force_register(self, request, pk=None):
        """
        Forzar re-registro de la troncal en Asterisk
        
        POST /api/telephony/trunks/{id}/force_register/
        """
        trunk = self.get_object()
        
        if not trunk.needs_registration():
            return Response({
                'success': False,
                'message': 'Esta troncal no está configurada para registrarse'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Regenerar configuración y recargar
            from .pjsip_config_generator import PJSIPConfigGenerator
            generator = PJSIPConfigGenerator()
            success, message = generator.save_and_reload()
            
            if not success:
                return Response({
                    'success': False,
                    'message': message
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Esperar un momento y verificar estado
            import time
            time.sleep(2)
            
            # Verificar estado de registro
            ami = AsteriskAMI()
            if ami.connect():
                reg_status = ami.get_trunk_registration_status(trunk.name)
                ami.disconnect()
                
                return Response({
                    'success': True,
                    'message': 'Configuración recargada',
                    'status': reg_status,
                    'registered': reg_status == 'Registered'
                })
            
            return Response({
                'success': True,
                'message': 'Configuración recargada pero no se pudo verificar estado'
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                ami.reload_module('res_pjsip.so')
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
