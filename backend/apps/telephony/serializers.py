from rest_framework import serializers
from .models import (
    Call, SIPTrunk, IVR, Extension, InboundRoute, 
    OutboundRoute, Voicemail, MusicOnHold, TimeCondition
)
from .asterisk_ami import AsteriskAMI


class CallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Call
        fields = '__all__'


class SIPTrunkSerializer(serializers.ModelSerializer):
    registration_status = serializers.SerializerMethodField()
    registration_detail = serializers.SerializerMethodField()
    
    # Campos de solo lectura calculados
    username = serializers.CharField(source='outbound_auth_username', read_only=True)
    password = serializers.CharField(source='outbound_auth_password', read_only=True, allow_blank=True)
    
    class Meta:
        model = SIPTrunk
        fields = '__all__'
        read_only_fields = [
            'is_registered', 
            'last_registration_time',
            'calls_total', 
            'calls_active', 
            'calls_successful',
            'calls_failed',
            'created_at', 
            'updated_at'
        ]
        extra_kwargs = {
            'outbound_auth_password': {'write_only': True, 'allow_blank': True},
            'inbound_auth_password': {'write_only': True, 'allow_blank': True}
        }
    
    def get_registration_status(self, obj):
        """Obtener estado de registro en tiempo real desde Asterisk"""
        try:
            ami = AsteriskAMI()
            if ami.connect():
                status = ami.get_trunk_registration_status(obj.name)
                ami.disconnect()
                return status
            return 'Disconnected'
        except Exception as e:
            return 'Error'
    
    def get_registration_detail(self, obj):
        """Obtener detalle legible del estado de registro"""
        status = self.get_registration_status(obj)
        
        status_map = {
            'Registered': {'text': 'Registrado', 'class': 'success', 'icon': '✓'},
            'Unregistered': {'text': 'No Registrado', 'class': 'warning', 'icon': '⚠'},
            'Failed': {'text': 'Fallo', 'class': 'error', 'icon': '✗'},
            'Not Configured': {'text': 'Sin Configurar', 'class': 'info', 'icon': 'ℹ'},
            'Disconnected': {'text': 'Asterisk Desconectado', 'class': 'error', 'icon': '✗'},
            'Error': {'text': 'Error', 'class': 'error', 'icon': '✗'},
            'Unknown': {'text': 'Desconocido', 'class': 'warning', 'icon': '?'}
        }
        
        return status_map.get(status, {'text': status, 'class': 'info', 'icon': '?'})
    
    def to_representation(self, instance):
        """Personalizar representación de salida"""
        data = super().to_representation(instance)
        
        # Ocultar contraseñas en respuesta
        if 'outbound_auth_password' in data and data['outbound_auth_password']:
            data['outbound_auth_password'] = '********'
        if 'inbound_auth_password' in data and data['inbound_auth_password']:
            data['inbound_auth_password'] = '********'
        
        # Agregar campos de compatibilidad
        data['username'] = instance.outbound_auth_username
        data['password'] = '********' if instance.outbound_auth_password else ''
        
        return data
    
    def validate(self, attrs):
        """Validar datos antes de guardar"""
        # Si es tipo custom, debe tener configuración personalizada
        if attrs.get('trunk_type') == 'custom' and not attrs.get('pjsip_config_custom'):
            raise serializers.ValidationError({
                'pjsip_config_custom': 'Debes proporcionar configuración PJSIP personalizada para tipo "Personalizado"'
            })
        
        # Si sends_registration está habilitado, validar URIs de registro
        if attrs.get('sends_registration'):
            if not attrs.get('registration_server_uri'):
                raise serializers.ValidationError({
                    'registration_server_uri': 'Debes proporcionar Server URI para habilitar registro'
                })
        
        # Si sends_auth está habilitado, debe haber credenciales
        if attrs.get('sends_auth'):
            if not attrs.get('outbound_auth_username'):
                raise serializers.ValidationError({
                    'outbound_auth_username': 'Debes proporcionar usuario para autenticación saliente'
                })
        
        # Si accepts_auth está habilitado, debe haber credenciales entrantes
        if attrs.get('accepts_auth'):
            if not attrs.get('inbound_auth_username'):
                raise serializers.ValidationError({
                    'inbound_auth_username': 'Debes proporcionar usuario para autenticación entrante'
                })
        
        return attrs


class IVRSerializer(serializers.ModelSerializer):
    class Meta:
        model = IVR
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ExtensionSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Extension
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'secret': {'write_only': True}
        }
    
    def get_status(self, obj):
        return 'Activo' if obj.is_active else 'Inactivo'
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ocultar contraseña en respuestas
        if 'secret' in data:
            data['secret'] = '********'
        return data


class InboundRouteSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = InboundRoute
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_status(self, obj):
        return 'Activo' if obj.is_active else 'Inactivo'


class OutboundRouteSerializer(serializers.ModelSerializer):
    trunk_name = serializers.CharField(source='trunk.name', read_only=True)
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = OutboundRoute
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_status(self, obj):
        return 'Activo' if obj.is_active else 'Inactivo'


class VoicemailSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    messages = serializers.SerializerMethodField()
    
    class Meta:
        model = Voicemail
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def get_status(self, obj):
        return 'Activo' if obj.is_active else 'Inactivo'
    
    def get_messages(self, obj):
        # TODO: Obtener cantidad real de mensajes desde Asterisk
        return 0
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ocultar contraseña en respuestas
        if 'password' in data:
            data['password'] = '****'
        return data


class MusicOnHoldSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()
    
    class Meta:
        model = MusicOnHold
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_status(self, obj):
        return 'Activo' if obj.is_active else 'Inactivo'
    
    def get_files(self, obj):
        # TODO: Contar archivos reales en el directorio
        return 0


class TimeConditionSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    times = serializers.SerializerMethodField()
    
    class Meta:
        model = TimeCondition
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_status(self, obj):
        return 'Activo' if obj.is_active else 'Inactivo'
    
    def get_times(self, obj):
        # Formatear los time_groups para mostrar
        if not obj.time_groups:
            return 'Sin horarios'
        
        # Ejemplo simple, se puede mejorar
        try:
            first_group = obj.time_groups[0]
            days = ', '.join(first_group.get('days', []))
            start = first_group.get('startTime', '')
            end = first_group.get('endTime', '')
            return f"{days} {start}-{end}"
        except (IndexError, KeyError):
            return 'Sin horarios'
