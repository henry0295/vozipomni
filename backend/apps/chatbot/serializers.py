from rest_framework import serializers

from apps.messaging.models import Channel

from .connectors import actions_for
from .models import BotFlow, BotFlowVersion, BotSession, Connector, ConnectorLog
from .schema import validate_definition

SECRET_MASK = '••••••'


class ConnectorSerializer(serializers.ModelSerializer):
    # Credenciales: solo escritura. Se devuelve qué claves están configuradas, nunca su valor.
    secrets = serializers.DictField(child=serializers.CharField(allow_blank=True), write_only=True, required=False)
    secret_keys = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = Connector
        fields = ['id', 'name', 'connector_type', 'base_url', 'config', 'secrets', 'secret_keys',
                  'timeout_seconds', 'verify_ssl', 'is_active', 'actions', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_secret_keys(self, obj):
        return sorted(k for k, v in obj.secret_values.items() if v)

    def get_actions(self, obj):
        return actions_for(obj)

    def validate_base_url(self, v):
        if not v.lower().startswith(('http://', 'https://')):
            raise serializers.ValidationError('Debe empezar por http:// o https://')
        return v.rstrip('/')

    def validate_config(self, v):
        if not isinstance(v, dict):
            raise serializers.ValidationError('Debe ser un objeto JSON')
        for a in v.get('actions') or []:
            if not isinstance(a, dict) or not a.get('name'):
                raise serializers.ValidationError('Cada acción necesita un "name"')
        return v

    def _apply_secrets(self, instance, secrets):
        if secrets is None:
            return
        current = instance.secret_values
        for k, val in secrets.items():
            if val == SECRET_MASK:
                continue          # sin cambios
            if val == '':
                current.pop(k, None)
            else:
                current[k] = val
        instance.set_secret_values(current)

    def create(self, validated):
        secrets = validated.pop('secrets', None)
        instance = Connector(**validated)
        self._apply_secrets(instance, secrets or {})
        instance.save()
        return instance

    def update(self, instance, validated):
        secrets = validated.pop('secrets', None)
        for k, v in validated.items():
            setattr(instance, k, v)
        self._apply_secrets(instance, secrets)
        instance.save()
        return instance


class ConnectorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectorLog
        fields = ['id', 'action', 'status', 'duration_ms', 'error', 'conversation_id', 'source', 'created_at']


class BotFlowVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = BotFlowVersion
        fields = ['id', 'number', 'notes', 'created_at', 'created_by_name']

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username if obj.created_by else ''


class BotFlowSerializer(serializers.ModelSerializer):
    channels = serializers.PrimaryKeyRelatedField(queryset=Channel.objects.all(), many=True, required=False)
    channel_names = serializers.SerializerMethodField()
    published_number = serializers.IntegerField(source='published_version.number', read_only=True, default=None)
    has_unpublished_changes = serializers.SerializerMethodField()
    active_sessions = serializers.SerializerMethodField()

    class Meta:
        model = BotFlow
        fields = ['id', 'name', 'description', 'is_active', 'channels', 'channel_names', 'draft',
                  'published_number', 'has_unpublished_changes', 'session_timeout_minutes',
                  'active_sessions', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_channel_names(self, obj):
        return [f'{c.get_channel_type_display()} — {c.name}' for c in obj.channels.all()]

    def get_has_unpublished_changes(self, obj):
        return bool(obj.draft) and (not obj.published_version or obj.published_version.definition != obj.draft)

    def get_active_sessions(self, obj):
        return obj.sessions.filter(status__in=['active', 'busy']).count()

    def validate_session_timeout_minutes(self, v):
        if not 1 <= v <= 1440:
            raise serializers.ValidationError('Entre 1 y 1440 minutos')
        return v

    def validate(self, attrs):
        # Un canal solo puede tener un bot activo
        is_active = attrs.get('is_active', getattr(self.instance, 'is_active', False))
        channels = attrs.get('channels')
        if channels is None and self.instance:
            channels = list(self.instance.channels.all())
        if is_active:
            if not self.instance or not self.instance.published_version_id:
                raise serializers.ValidationError({'is_active': 'Publique el flujo antes de activarlo'})
            for ch in channels or []:
                clash = BotFlow.objects.filter(is_active=True, channels=ch).exclude(
                    pk=getattr(self.instance, 'pk', None)).first()
                if clash:
                    raise serializers.ValidationError(
                        {'channels': f'El canal "{ch.name}" ya tiene activo el bot "{clash.name}"'})
        if attrs.get('draft'):
            ids = set(Connector.objects.filter(is_active=True).values_list('id', flat=True))
            # En el borrador solo se valida la forma básica; la validación completa es al publicar
            if not isinstance(attrs['draft'], dict):
                raise serializers.ValidationError({'draft': 'Formato inválido'})
            attrs['_draft_warnings'] = validate_definition(attrs['draft'], connectors_ids=ids)
        return attrs

    def create(self, validated):
        validated.pop('_draft_warnings', None)
        return super().create(validated)

    def update(self, instance, validated):
        validated.pop('_draft_warnings', None)
        return super().update(instance, validated)


class BotSessionSerializer(serializers.ModelSerializer):
    contact = serializers.CharField(source='conversation.contact_name', read_only=True)
    channel = serializers.CharField(source='conversation.channel.name', read_only=True)
    version_number = serializers.IntegerField(source='version.number', read_only=True, default=None)

    class Meta:
        model = BotSession
        fields = ['id', 'conversation', 'contact', 'channel', 'flow', 'version_number', 'current_node',
                  'status', 'path', 'started_at', 'last_activity_at']
