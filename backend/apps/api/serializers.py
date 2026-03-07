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
    
    def validate(self, attrs):
        """Validar datos de campaña"""
        # Validar fechas
        if attrs.get('end_date') and attrs.get('start_date'):
            if attrs['end_date'] <= attrs['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'La fecha de fin debe ser posterior a la fecha de inicio'
                })
        
        # Validar horarios
        if attrs.get('schedule_end_time') and attrs.get('schedule_start_time'):
            if attrs['schedule_end_time'] <= attrs['schedule_start_time']:
                raise serializers.ValidationError({
                    'schedule_end_time': 'La hora de fin debe ser posterior a la hora de inicio'
                })
        
        # Validar reintentos
        max_retries = attrs.get('max_retries', 0)
        if max_retries < 0:
            raise serializers.ValidationError({
                'max_retries': 'Los reintentos no pueden ser negativos'
            })
        if max_retries > 10:
            raise serializers.ValidationError({
                'max_retries': 'Máximo 10 reintentos permitidos'
            })
        
        # Validar timeout
        call_timeout = attrs.get('call_timeout', 30)
        if call_timeout < 10 or call_timeout > 300:
            raise serializers.ValidationError({
                'call_timeout': 'El timeout debe estar entre 10 y 300 segundos'
            })
        
        # Validar max_calls_per_agent
        max_calls = attrs.get('max_calls_per_agent', 1)
        if max_calls < 1 or max_calls > 5:
            raise serializers.ValidationError({
                'max_calls_per_agent': 'Debe estar entre 1 y 5 llamadas por agente'
            })
        
        # Validar que campaña saliente tenga lista de contactos
        if attrs.get('campaign_type') in ['outbound', 'preview']:
            if not attrs.get('contact_list') and not self.instance:
                raise serializers.ValidationError({
                    'contact_list': 'Las campañas salientes requieren una lista de contactos'
                })
        
        return attrs


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
        from django.db import IntegrityError
        
        # Extraer datos de usuario
        username = validated_data.pop('username', None)
        password = validated_data.pop('password', None)
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        email = validated_data.pop('email', '')
        sip_password = validated_data.pop('sip_password', None)
        
        try:
            # Crear usuario si se proporcionó username
            if username:
                # Verificar si el usuario ya existe
                if User.objects.filter(username=username).exists():
                    raise serializers.ValidationError({
                        'username': f'El nombre de usuario "{username}" ya está en uso'
                    })
                
                if email and User.objects.filter(email=email).exists():
                    raise serializers.ValidationError({
                        'email': f'El correo electrónico "{email}" ya está en uso'
                    })
                
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
            
            # Verificar duplicados de agent_id y sip_extension
            if Agent.objects.filter(agent_id=validated_data.get('agent_id')).exists():
                raise serializers.ValidationError({
                    'agent_id': f'El ID de agente "{validated_data.get("agent_id")}" ya está en uso'
                })
            
            if Agent.objects.filter(sip_extension=validated_data.get('sip_extension')).exists():
                raise serializers.ValidationError({
                    'sip_extension': f'La extensión SIP "{validated_data.get("sip_extension")}" ya está en uso'
                })
            
            # Crear agente
            agent = Agent.objects.create(**validated_data)
            
        except IntegrityError as e:
            error_msg = str(e)
            if 'username' in error_msg:
                raise serializers.ValidationError({
                    'username': 'El nombre de usuario ya está en uso'
                })
            elif 'email' in error_msg:
                raise serializers.ValidationError({
                    'email': 'El correo electrónico ya está en uso'
                })
            elif 'agent_id' in error_msg:
                raise serializers.ValidationError({
                    'agent_id': 'El ID de agente ya está en uso'
                })
            elif 'sip_extension' in error_msg:
                raise serializers.ValidationError({
                    'sip_extension': 'La extensión SIP ya está en uso'
                })
            else:
                raise serializers.ValidationError({
                    'detail': f'Error de integridad: {error_msg}'
                })
        
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
    
    def validate_phone(self, value):
        """Validar formato de número telefónico"""
        import re
        import phonenumbers
        
        if not value:
            raise serializers.ValidationError('El número de teléfono es requerido')
        
        # Limpiar el número
        cleaned = re.sub(r'[^\d+]', '', value)
        
        # Validar longitud mínima
        if len(cleaned) < 7:
            raise serializers.ValidationError('Número de teléfono demasiado corto')
        
        # Intentar validar con phonenumbers
        try:
            # Obtener país del contacto o usar default
            country = self.initial_data.get('country', 'CO')
            parsed = phonenumbers.parse(cleaned, country)
            
            if not phonenumbers.is_valid_number(parsed):
                raise serializers.ValidationError('Número de teléfono inválido')
            
            # Retornar en formato E164
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            # Si falla, validar formato básico
            if not re.match(r'^\+?[1-9]\d{6,14}$', cleaned):
                raise serializers.ValidationError(
                    'Formato de número inválido. Use formato internacional (+57...) o local'
                )
            return cleaned
    
    def validate_email(self, value):
        """Validar formato de email"""
        if value:
            import re
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, value):
                raise serializers.ValidationError('Formato de email inválido')
        return value
    
    def validate(self, attrs):
        """Validaciones adicionales"""
        # Validar que al menos un teléfono esté presente
        if not any([attrs.get('phone'), attrs.get('phone2'), attrs.get('phone3')]):
            raise serializers.ValidationError({
                'phone': 'Debe proporcionar al menos un número de teléfono'
            })
        
        # Validar prioridad
        priority = attrs.get('priority', 0)
        if priority < 0 or priority > 10:
            raise serializers.ValidationError({
                'priority': 'La prioridad debe estar entre 0 y 10'
            })
        
        return attrs


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
