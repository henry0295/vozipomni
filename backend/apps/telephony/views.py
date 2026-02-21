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
    
    @action(detail=False, methods=['get'])
    def statuses(self, request):
        """
        Obtener estado de registro de TODAS las troncales activas en una sola consulta AMI.
        Optimizado para el listado — una sola conexión AMI.
        
        GET /api/telephony/trunks/statuses/
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        trunks = SIPTrunk.objects.filter(is_active=True)
        result = {}
        
        try:
            ami = AsteriskAMI()
            if not ami.connect():
                # Asterisk no disponible
                for t in trunks:
                    result[str(t.id)] = {
                        'status': 'Desconectado',
                        'class': 'error',
                        'detail': 'No se pudo conectar a Asterisk AMI'
                    }
                return Response(result)
            
            # Obtener endpoints y registros en una sola sesión
            endpoints = ami.pjsip_show_endpoints() or {}
            registrations = ami.pjsip_show_registrations() or {}

            _logger.info(f"AMI endpoints encontrados: {list(endpoints.keys())}")
            _logger.info(f"AMI registrations encontradas: {list(registrations.keys())}")
            _logger.info(f"Troncales activas en BD: {[t.name for t in trunks]}")

            # Crear mapas case-insensitive para búsqueda flexible
            ep_lower_map = {k.lower(): v for k, v in endpoints.items()}
            reg_lower_map = {k.lower(): v for k, v in registrations.items()}

            def find_endpoint(name):
                """Buscar endpoint por nombre con variantes"""
                # 1. Búsqueda exacta
                if name in endpoints:
                    return endpoints[name]
                # 2. Case-insensitive
                if name.lower() in ep_lower_map:
                    return ep_lower_map[name.lower()]
                # 3. Reemplazar guiones por underscores y viceversa
                alt_name = name.replace('-', '_')
                if alt_name in endpoints:
                    return endpoints[alt_name]
                if alt_name.lower() in ep_lower_map:
                    return ep_lower_map[alt_name.lower()]
                alt_name2 = name.replace('_', '-')
                if alt_name2 in endpoints:
                    return endpoints[alt_name2]
                if alt_name2.lower() in ep_lower_map:
                    return ep_lower_map[alt_name2.lower()]
                return None

            def find_registration(name):
                """Buscar registration por nombre con variantes"""
                variants = [
                    name, f"{name}-reg",
                    name.replace('-', '_'), f"{name.replace('-', '_')}-reg",
                    name.replace('_', '-'), f"{name.replace('_', '-')}-reg",
                ]
                for v in variants:
                    if v in registrations:
                        return registrations[v]
                    if v.lower() in reg_lower_map:
                        return reg_lower_map[v.lower()]
                return None

            for t in trunks:
                ep = find_endpoint(t.name)
                ep_found = ep is not None
                contacts = ep.get('contacts', []) if ep else []
                has_avail_contact = any(c.get('available') for c in contacts) if contacts else False

                _logger.info(f"Troncal '{t.name}': ep_found={ep_found}, sends_reg={t.sends_registration}, contacts={len(contacts)}")

                if t.sends_registration:
                    # Troncales con registro: verificar estado de registro
                    reg = find_registration(t.name)
                    if reg:
                        reg_state = reg.get('status', 'Unknown')
                        _logger.info(f"  Registration '{t.name}': state={reg_state}")
                        if reg_state in ('Registered',):
                            result[str(t.id)] = {'status': 'Registrado', 'class': 'success'}
                        elif reg_state in ('Unregistered',):
                            result[str(t.id)] = {'status': 'No Registrado', 'class': 'warning'}
                        elif reg_state in ('Rejected', 'Failed'):
                            result[str(t.id)] = {'status': 'Rechazado', 'class': 'error'}
                        elif reg_state in ('Attempting',):
                            result[str(t.id)] = {'status': 'Conectando...', 'class': 'warning'}
                        else:
                            result[str(t.id)] = {'status': reg_state, 'class': 'warning'}
                    elif ep_found:
                        # Endpoint existe pero sin registro — posiblemente IP-based
                        if has_avail_contact:
                            result[str(t.id)] = {'status': 'Disponible', 'class': 'success'}
                        else:
                            result[str(t.id)] = {'status': 'Sin Registro', 'class': 'warning'}
                    else:
                        # Fallback: verificación individual
                        _logger.info(f"  Fallback individual para '{t.name}' (registration)")
                        reg_check = ami.pjsip_check_registration(t.name)
                        if reg_check:
                            reg_state = reg_check.get('status', 'Unknown')
                            if reg_state == 'Registered':
                                result[str(t.id)] = {'status': 'Registrado', 'class': 'success'}
                            elif reg_state == 'Attempting':
                                result[str(t.id)] = {'status': 'Conectando...', 'class': 'warning'}
                            elif reg_state in ('Rejected', 'Failed'):
                                result[str(t.id)] = {'status': 'Rechazado', 'class': 'error'}
                            else:
                                result[str(t.id)] = {'status': 'No Registrado', 'class': 'warning'}
                        else:
                            # Verificar si al menos el endpoint existe
                            ep_check = ami.pjsip_check_endpoint(t.name)
                            if ep_check:
                                result[str(t.id)] = {'status': 'EP sin Registro', 'class': 'warning',
                                                     'detail': 'Endpoint existe pero no hay registro activo'}
                            else:
                                result[str(t.id)] = {'status': 'No Configurado', 'class': 'gray',
                                                     'detail': 'Endpoint no encontrado en Asterisk. Regenere la configuración.'}
                else:
                    # Troncales sin registro: verificar endpoint y contactos
                    if ep_found:
                        if has_avail_contact:
                            result[str(t.id)] = {'status': 'Disponible', 'class': 'success'}
                        elif contacts:
                            result[str(t.id)] = {'status': 'Inalcanzable', 'class': 'warning'}
                        else:
                            result[str(t.id)] = {'status': 'Sin Contacto', 'class': 'warning'}
                    else:
                        # Fallback: verificación individual
                        _logger.info(f"  Fallback individual para '{t.name}' (endpoint)")
                        ep_check = ami.pjsip_check_endpoint(t.name)
                        if ep_check:
                            ep_contacts = ep_check.get('contacts', [])
                            if any(c.get('available') for c in ep_contacts):
                                result[str(t.id)] = {'status': 'Disponible', 'class': 'success'}
                            elif ep_contacts:
                                result[str(t.id)] = {'status': 'Inalcanzable', 'class': 'warning'}
                            else:
                                result[str(t.id)] = {'status': 'Sin Contacto', 'class': 'warning'}
                        else:
                            result[str(t.id)] = {'status': 'No Encontrado', 'class': 'gray',
                                                 'detail': 'Endpoint no encontrado en Asterisk. Regenere la configuración.'}
            
            ami.disconnect()

            # Auto-regenerar config si hay troncales sin endpoint (con cooldown de 120s)
            not_found_ids = [tid for tid, info in result.items() if info.get('status') in ('No Encontrado', 'No Configurado')]
            if not_found_ids:
                import time as _time
                _now = _time.time()
                _last_regen = getattr(SIPTrunkViewSet, '_last_auto_regen', 0)
                if _now - _last_regen > 120:  # Cooldown: máximo una vez cada 2 minutos
                    SIPTrunkViewSet._last_auto_regen = _now
                    _logger.info(f"Troncales sin endpoint ({len(not_found_ids)}), intentando auto-regenerar config PJSIP...")
                    try:
                        from .pjsip_config_generator import PJSIPConfigGenerator
                        gen = PJSIPConfigGenerator()
                        success, msg = gen.save_and_reload()
                        if success:
                            _logger.info(f"✓ Config PJSIP auto-regenerada: {msg}")
                            for tid in not_found_ids:
                                result[tid]['detail'] = 'Configuración regenerada. Actualice en unos segundos.'
                        else:
                            _logger.warning(f"✗ Error auto-regenerando config: {msg}")
                    except Exception as regen_err:
                        _logger.warning(f"Error en auto-regeneración: {regen_err}")
                else:
                    _logger.debug(f"Auto-regeneración omitida (cooldown, faltan {120 - (_now - _last_regen):.0f}s)")
        
        except Exception as e:
            _logger.error(f"Error general consultando estados AMI: {e}", exc_info=True)
            for t in trunks:
                if str(t.id) not in result:
                    result[str(t.id)] = {
                        'status': 'Error',
                        'class': 'error',
                        'detail': str(e)
                    }
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def regenerate_config(self, request):
        """
        Regenerar configuración PJSIP y recargar Asterisk
        
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
