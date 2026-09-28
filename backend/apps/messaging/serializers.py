"""
Serializers de la app de mensajería multicanal y WhatsApp Business.
"""
from django.conf import settings
from rest_framework import serializers

from .models import (
    Channel, Conversation, Message,
    WhatsAppLine, WhatsAppProvider, WhatsAppTemplate,
)


class ChannelSerializer(serializers.ModelSerializer):
    channel_type_display = serializers.CharField(source='get_channel_type_display', read_only=True)
    conversation_count = serializers.SerializerMethodField()
    whatsapp_line_id = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = [
            'id', 'name', 'channel_type', 'channel_type_display',
            'identifier', 'is_active', 'created_at', 'conversation_count', 'whatsapp_line_id',
        ]
        read_only_fields = ['created_at']

    def get_conversation_count(self, obj):
        return obj.conversations.filter(status__in=['open', 'waiting']).count()

    def get_whatsapp_line_id(self, obj):
        line = getattr(obj, 'whatsapp_line', None)
        return line.id if line else None


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    has_media = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'direction', 'message_type', 'body', 'media_url',
            'status', 'error_message', 'sender', 'sender_name', 'metadata', 'has_media',
            'is_read', 'sent_at', 'external_id',
        ]
        read_only_fields = fields

    def get_sender_name(self, obj):
        if obj.sender:
            return obj.sender.get_full_name() or obj.sender.username
        if obj.direction == 'outbound' and (obj.metadata or {}).get('system'):
            return 'Sistema'
        return None

    def get_has_media(self, obj):
        meta = obj.metadata or {}
        return bool(meta.get('local_path') or meta.get('media_id') or obj.media_url)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Nunca exponer rutas del servidor ni el payload crudo
        meta = dict(data.get('metadata') or {})
        meta.pop('local_path', None)
        data['metadata'] = meta
        return data


class ConversationSerializer(serializers.ModelSerializer):
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)
    agent_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    window_open = serializers.BooleanField(source='is_window_open', read_only=True)
    whatsapp_line_id = serializers.SerializerMethodField()
    campaign_name = serializers.CharField(source='campaign.name', read_only=True, default=None)

    class Meta:
        model = Conversation
        fields = [
            'id', 'channel', 'channel_name', 'channel_type', 'whatsapp_line_id',
            'agent', 'agent_name', 'contact', 'display_name', 'contact_name',
            'contact_identifier', 'status', 'status_display',
            'started_at', 'closed_at', 'last_message_at', 'last_inbound_at', 'window_open',
            'campaign', 'campaign_name', 'last_message', 'unread_count',
        ]
        read_only_fields = ['started_at', 'closed_at', 'last_message_at', 'last_inbound_at']

    def get_agent_name(self, obj):
        if obj.agent and obj.agent.user:
            return obj.agent.user.get_full_name() or obj.agent.user.username
        return None

    def get_display_name(self, obj):
        if obj.contact:
            return obj.contact.full_name
        return obj.contact_name or obj.contact_identifier

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-sent_at').first()
        if msg:
            return {
                'body': (msg.body or f'[{msg.get_message_type_display()}]')[:100],
                'direction': msg.direction,
                'message_type': msg.message_type,
                'status': msg.status,
                'sent_at': msg.sent_at.isoformat(),
            }
        return None

    def get_unread_count(self, obj):
        return obj.messages.filter(direction='inbound', is_read=False).count()

    def get_whatsapp_line_id(self, obj):
        line = getattr(obj.channel, 'whatsapp_line', None)
        return line.id if line else None


class ConversationDetailSerializer(ConversationSerializer):
    contact_details = serializers.SerializerMethodField()

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['contact_details']

    def get_contact_details(self, obj):
        c = obj.contact
        if not c:
            return None
        return {
            'id': c.id, 'full_name': c.full_name, 'phone': c.phone, 'email': c.email,
            'company': c.company, 'city': c.city, 'is_vip': c.is_vip,
            'custom_fields': c.custom_fields,
        }


# ══════════════════════════════════════════════════════════════════════════════
# WhatsApp Business (configuración)
# ══════════════════════════════════════════════════════════════════════════════

def build_webhook_url(request, app_id: str) -> str:
    path = f"/api/messaging/webhooks/meta/{app_id}/"
    base = getattr(settings, 'PUBLIC_BASE_URL', '').rstrip('/')
    if base:
        return base + path
    if request is not None:
        url = request.build_absolute_uri(path)
        # Meta solo acepta HTTPS
        return url.replace('http://', 'https://', 1)
    return path


class WhatsAppProviderSerializer(serializers.ModelSerializer):
    app_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)
    access_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_app_secret = serializers.SerializerMethodField()
    has_access_token = serializers.SerializerMethodField()
    access_token_hint = serializers.SerializerMethodField()
    webhook_url = serializers.SerializerMethodField()
    lines_count = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppProvider
        fields = [
            'id', 'name', 'app_id', 'app_secret', 'access_token', 'verify_token',
            'api_version', 'business_id', 'is_active',
            'has_app_secret', 'has_access_token', 'access_token_hint',
            'webhook_url', 'webhook_verified', 'webhook_verified_at', 'last_webhook_at',
            'last_error', 'lines_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['verify_token', 'webhook_verified', 'webhook_verified_at',
                            'last_webhook_at', 'last_error', 'created_at', 'updated_at']

    def get_has_app_secret(self, obj):
        return bool(obj.app_secret)

    def get_has_access_token(self, obj):
        return bool(obj.access_token)

    def get_access_token_hint(self, obj):
        t = obj.access_token or ''
        return f"…{t[-6:]}" if len(t) > 10 else ''

    def get_webhook_url(self, obj):
        return build_webhook_url(self.context.get('request'), obj.app_id)

    def get_lines_count(self, obj):
        return obj.lines.count()

    def validate_app_id(self, value):
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError('El App ID de Meta es numérico.')
        return value

    def validate(self, attrs):
        if not self.instance and not attrs.get('access_token'):
            raise serializers.ValidationError({'access_token': 'El token de acceso es obligatorio.'})
        return attrs

    def update(self, instance, validated_data):
        # Campos secretos vacíos = conservar el valor actual
        for secret in ('app_secret', 'access_token'):
            if secret in validated_data and not validated_data[secret]:
                validated_data.pop(secret)
        return super().update(instance, validated_data)


class WhatsAppLineSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    channel_id = serializers.IntegerField(source='channel.id', read_only=True)
    default_campaign_name = serializers.CharField(source='default_campaign.name', read_only=True, default=None)
    templates_count = serializers.SerializerMethodField()
    open_conversations = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppLine
        fields = [
            'id', 'provider', 'provider_name', 'channel_id', 'name', 'waba_id', 'phone_number_id',
            'display_phone_number', 'verified_name', 'quality_rating', 'messaging_limit',
            'status', 'status_detail', 'webhook_subscribed',
            'default_campaign', 'default_campaign_name', 'auto_assign', 'max_chats_per_agent',
            'welcome_message', 'is_active', 'last_sync_at',
            'templates_count', 'open_conversations', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'display_phone_number', 'verified_name', 'quality_rating', 'messaging_limit',
            'status', 'status_detail', 'webhook_subscribed', 'last_sync_at', 'created_at', 'updated_at',
        ]

    def get_templates_count(self, obj):
        return obj.templates.count()

    def get_open_conversations(self, obj):
        return obj.channel.conversations.exclude(status='closed').count()

    def validate_phone_number_id(self, value):
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError('El Phone Number ID es numérico (no es el número de teléfono).')
        return value

    def validate_waba_id(self, value):
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError('El WhatsApp Business Account ID es numérico.')
        return value

    def create(self, validated_data):
        channel = Channel.objects.create(
            name=f"WhatsApp · {validated_data['name']}",
            channel_type='whatsapp',
            identifier=validated_data['phone_number_id'],
            is_active=validated_data.get('is_active', True),
        )
        return WhatsAppLine.objects.create(channel=channel, **validated_data)

    def update(self, instance, validated_data):
        line = super().update(instance, validated_data)
        ch = line.channel
        ch.name = f"WhatsApp · {line.name}"
        ch.is_active = line.is_active
        ch.save(update_fields=['name', 'is_active'])
        return line


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    body_text = serializers.ReadOnlyField()
    header_text = serializers.ReadOnlyField()
    body_param_count = serializers.ReadOnlyField()
    header_param_count = serializers.ReadOnlyField()
    line_name = serializers.CharField(source='line.name', read_only=True)

    class Meta:
        model = WhatsAppTemplate
        fields = [
            'id', 'line', 'line_name', 'meta_id', 'name', 'language', 'category', 'status',
            'rejected_reason', 'components', 'body_text', 'header_text',
            'body_param_count', 'header_param_count', 'updated_at',
        ]
        read_only_fields = ['meta_id', 'status', 'rejected_reason', 'updated_at']
