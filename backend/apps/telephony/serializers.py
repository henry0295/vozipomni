from rest_framework import serializers
from .models import (
    Call, SIPTrunk, IVR, Extension, InboundRoute, 
    OutboundRoute, Voicemail, MusicOnHold, TimeCondition
)


class CallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Call
        fields = '__all__'


class SIPTrunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SIPTrunk
        fields = '__all__'
        read_only_fields = ['is_registered', 'calls_total', 'calls_active', 'created_at', 'updated_at']


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
