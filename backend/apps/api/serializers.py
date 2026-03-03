from rest_framework import serializers
from apps.users.models import User
from apps.campaigns.models import Campaign, CampaignDisposition
from apps.agents.models import Agent
from apps.contacts.models import Contact, ContactList
from apps.queues.models import Queue
from apps.telephony.models import Call, SIPTrunk
from apps.recordings.models import Recording
from apps.reports.models import Report


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'name', 'role', 
                  'phone', 'department', 'is_active_agent', 'last_activity']
        read_only_fields = ['last_activity']
    
    def get_name(self, obj):
        """Retorna el nombre completo del usuario"""
        return obj.get_full_name() or obj.username


class CampaignDispositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignDisposition
        fields = ['id', 'code', 'name', 'description', 'is_success', 'requires_callback', 'order']


class CampaignSerializer(serializers.ModelSerializer):
    dispositions = CampaignDispositionSerializer(many=True, read_only=True)
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'total_contacts', 'contacted', 'successful']


class AgentSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    is_available = serializers.ReadOnlyField()
    
    # Campos para crear/actualizar usuario
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    first_name = serializers.CharField(write_only=True, required=False)
    last_name = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(write_only=True, required=False)
    sip_password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    
    class Meta:
        model = Agent
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'current_calls', 'last_call_time', 
                            'logged_in_at', 'calls_today', 'talk_time_today', 'status',
                            'available_time_today', 'break_time_today', 'oncall_time_today', 'wrapup_time_today']
        extra_kwargs = {
            'user': {'required': False}
        }
    
    def create(self, validated_data):
        # Extraer datos de usuario
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email', '')
        sip_password = validated_data.pop('sip_password', None)
        
        # Crear usuario si se proporcionó username
        if username:
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password or 'changeme123',
                role='agent',
                is_active_agent=True
            )
            validated_data['user'] = user
        elif 'user' not in validated_data:
            raise serializers.ValidationError({
                'username': 'Debe proporcionar un username o un user existente'
            })
        
        # Crear agente
        agent = Agent.objects.create(**validated_data)
        
        # Crear endpoint PJSIP en Asterisk si se habilitó WebRTC
        if agent.webrtc_enabled and sip_password:
            from apps.telephony.asterisk_config import AsteriskConfigGenerator
            generator = AsteriskConfigGenerator()
            try:
                generator.create_pjsip_endpoint(
                    extension=agent.sip_extension,
                    password=sip_password,
                    agent_name=agent.user.get_full_name() or agent.agent_id
                )
            except Exception as e:
                # Log error pero no fallar la creación
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creando endpoint PJSIP para {agent.sip_extension}: {e}")
        
        return agent
    
    def update(self, instance, validated_data):
        # Extraer datos de usuario
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)
        sip_password = validated_data.pop('sip_password', None)
        
        # Actualizar usuario si se proporcionaron datos
        if instance.user and any([username, password, first_name, last_name, email]):
            user = instance.user
            if username:
                user.username = username
            if password:
                user.set_password(password)
            if first_name is not None:
                user.first_name = first_name
            if last_name is not None:
                user.last_name = last_name
            if email:
                user.email = email
            user.save()
        
        # Actualizar extensión PJSIP si cambió
        old_extension = instance.sip_extension
        if 'sip_extension' in validated_data and validated_data['sip_extension'] != old_extension:
            from apps.telephony.asterisk_config import AsteriskConfigGenerator
            generator = AsteriskConfigGenerator()
            try:
                # Eliminar vieja extensión
                generator.delete_pjsip_endpoint(old_extension)
                # Crear nueva
                if sip_password:
                    generator.create_pjsip_endpoint(
                        extension=validated_data['sip_extension'],
                        password=sip_password,
                        agent_name=instance.user.get_full_name() or instance.agent_id
                    )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error actualizando endpoint PJSIP: {e}")
        
        # Actualizar agente
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'attempts', 'last_attempt']


class ContactListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactList
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'total_contacts']


class QueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Queue
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CallSerializer(serializers.ModelSerializer):
    duration = serializers.ReadOnlyField()
    agent_name = serializers.CharField(source='agent.user.get_full_name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = Call
        fields = '__all__'
        read_only_fields = ['start_time', 'answer_time', 'end_time', 'wait_time', 'talk_time', 'hold_time']


class RecordingSerializer(serializers.ModelSerializer):
    file_size_mb = serializers.ReadOnlyField()
    call_details = CallSerializer(source='call', read_only=True)
    
    class Meta:
        model = Recording
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'file_size', 'duration', 'access_count']


class ReportSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = ['created_at', 'completed_at', 'file_size', 'error_message']


class SIPTrunkSerializer(serializers.ModelSerializer):
    concurrent_calls = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = SIPTrunk
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_concurrent_calls(self, obj):
        """Obtener llamadas concurrentes actuales"""
        # Aquí conectaríamos con Asterisk para obtener datos reales
        return Call.objects.filter(
            status__in=['ringing', 'answered', 'initiated'],
            # Filtrar por troncal cuando tengamos esa relación
        ).count()
    
    def get_status(self, obj):
        """Determinar el estado del troncal"""
        if obj.is_active:
            # Aquí podríamos verificar con Asterisk AMI/ARI
            return 'Activo'
        return 'Inactivo'
