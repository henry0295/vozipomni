"""Serializers de etiquetas, respuestas rápidas, envíos masivos y canales email / chat web / Meta."""
from django.conf import settings
from rest_framework import serializers

from .models import (
    Channel, ConversationTag, EmailAccount, MetaPage, QuickReply,
    WebChatWidget, WhatsAppBroadcast,
)

ROUTING_FIELDS = [
    'default_campaign', 'default_campaign_name', 'auto_assign', 'max_chats_per_agent',
    'welcome_message', 'time_condition', 'time_condition_name', 'after_hours_message', 'is_active',
]


class ConversationTagSerializer(serializers.ModelSerializer):
    usage = serializers.SerializerMethodField()

    class Meta:
        model = ConversationTag
        fields = ['id', 'name', 'color', 'is_active', 'usage', 'created_at']
        read_only_fields = ['created_at']

    def get_usage(self, obj):
        return obj.conversations.count()


class QuickReplySerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(source='campaign.name', read_only=True, default=None)

    class Meta:
        model = QuickReply
        fields = ['id', 'title', 'shortcut', 'body', 'campaign', 'campaign_name', 'channel_type',
                  'order', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_shortcut(self, value):
        value = (value or '').strip()
        if value and not value.startswith('/'):
            value = '/' + value
        return value.replace(' ', '')


class WhatsAppBroadcastSerializer(serializers.ModelSerializer):
    line_name = serializers.CharField(source='line.name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_language = serializers.CharField(source='template.language', read_only=True)
    template_body = serializers.CharField(source='template.body_text', read_only=True)
    body_param_count = serializers.IntegerField(source='template.body_param_count', read_only=True)
    header_param_count = serializers.IntegerField(source='template.header_param_count', read_only=True)
    contact_list_name = serializers.CharField(source='contact_list.name', read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppBroadcast
        fields = [
            'id', 'name', 'line', 'line_name', 'template', 'template_name', 'template_language',
            'template_body', 'body_param_count', 'header_param_count',
            'contact_list', 'contact_list_name', 'body_params', 'header_params', 'require_opt_in',
            'rate_per_minute', 'status', 'scheduled_at', 'started_at', 'finished_at',
            'total_recipients', 'skipped_count', 'last_error', 'created_by_name', 'created_at', 'stats',
        ]
        read_only_fields = ['status', 'started_at', 'finished_at', 'total_recipients',
                            'skipped_count', 'last_error', 'created_at']

    def get_created_by_name(self, obj):
        u = obj.created_by
        return (u.get_full_name() or u.username) if u else None

    def get_stats(self, obj):
        from .broadcasts import stats
        return stats(obj)

    def validate_rate_per_minute(self, value):
        if not 1 <= value <= 1000:
            raise serializers.ValidationError('Entre 1 y 1000 mensajes por minuto.')
        return value

    def validate(self, attrs):
        line = attrs.get('line') or getattr(self.instance, 'line', None)
        tpl = attrs.get('template') or getattr(self.instance, 'template', None)
        if line and tpl and tpl.line_id != line.id:
            raise serializers.ValidationError({'template': 'La plantilla no pertenece a esa línea.'})
        if tpl:
            bp = attrs.get('body_params', getattr(self.instance, 'body_params', []) or [])
            hp = attrs.get('header_params', getattr(self.instance, 'header_params', []) or [])
            if len(bp) < tpl.body_param_count or len(hp) < tpl.header_param_count:
                raise serializers.ValidationError(
                    {'body_params': f'La plantilla requiere {tpl.body_param_count} variable(s) en el cuerpo '
                                    f'y {tpl.header_param_count} en el encabezado.'})
        if self.instance and self.instance.status not in ('draft', 'scheduled', 'paused'):
            raise serializers.ValidationError('Solo se pueden editar envíos en borrador, programados o pausados.')
        return attrs


class _RoutingMixin(serializers.Serializer):
    default_campaign_name = serializers.CharField(source='default_campaign.name', read_only=True, default=None)
    time_condition_name = serializers.CharField(source='time_condition.name', read_only=True, default=None)
    channel_id = serializers.IntegerField(source='channel.id', read_only=True)
    open_conversations = serializers.SerializerMethodField()

    def get_open_conversations(self, obj):
        return obj.channel.conversations.exclude(status='closed').count()

    def _sync_channel(self, obj, ctype, identifier):
        ch = obj.channel
        ch.name = f"{dict(Channel.CHANNEL_TYPES).get(ctype, ctype)} · {obj.name}"
        ch.identifier = identifier
        ch.is_active = obj.is_active
        ch.save(update_fields=['name', 'identifier', 'is_active'])


class EmailAccountSerializer(_RoutingMixin, serializers.ModelSerializer):
    imap_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    smtp_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_imap_password = serializers.SerializerMethodField()
    has_smtp_password = serializers.SerializerMethodField()

    class Meta:
        model = EmailAccount
        fields = [
            'id', 'channel_id', 'name', 'email_address', 'from_name', 'signature',
            'imap_host', 'imap_port', 'imap_ssl', 'imap_username', 'imap_password', 'imap_folder',
            'smtp_host', 'smtp_port', 'smtp_starttls', 'smtp_ssl', 'smtp_username', 'smtp_password',
            'has_imap_password', 'has_smtp_password', 'last_polled_at', 'last_error', 'open_conversations',
            *ROUTING_FIELDS, 'created_at', 'updated_at',
        ]
        read_only_fields = ['last_polled_at', 'last_error', 'created_at', 'updated_at']

    def get_has_imap_password(self, obj):
        return bool(obj.imap_password)

    def get_has_smtp_password(self, obj):
        return bool(obj.smtp_password)

    def create(self, validated_data):
        channel = Channel.objects.create(name=f"Email · {validated_data['name']}", channel_type='email',
                                         identifier=validated_data['email_address'],
                                         is_active=validated_data.get('is_active', True))
        return EmailAccount.objects.create(channel=channel, **validated_data)

    def update(self, instance, validated_data):
        for secret in ('imap_password', 'smtp_password'):
            if secret in validated_data and not validated_data[secret]:
                validated_data.pop(secret)
        obj = super().update(instance, validated_data)
        self._sync_channel(obj, 'email', obj.email_address)
        return obj


class WebChatWidgetSerializer(_RoutingMixin, serializers.ModelSerializer):
    embed_code = serializers.SerializerMethodField()

    class Meta:
        model = WebChatWidget
        fields = [
            'id', 'channel_id', 'name', 'widget_key', 'allowed_origins', 'title', 'subtitle',
            'primary_color', 'position', 'require_name', 'require_email', 'intro_text',
            'embed_code', 'open_conversations', *ROUTING_FIELDS, 'created_at', 'updated_at',
        ]
        read_only_fields = ['widget_key', 'created_at', 'updated_at']

    def get_embed_code(self, obj):
        base = getattr(settings, 'PUBLIC_BASE_URL', '').rstrip('/')
        request = self.context.get('request')
        if not base and request is not None:
            base = request.build_absolute_uri('/').rstrip('/')
        return (f'<script src="{base}/webchat/widget.js" data-key="{obj.widget_key}" '
                f'data-api="{base}/api/messaging/webchat/public" async></script>')

    def validate_primary_color(self, value):
        import re
        if not re.fullmatch(r'#[0-9a-fA-F]{3,8}', value or ''):
            raise serializers.ValidationError('Color hexadecimal, ej: #16a34a')
        return value

    def create(self, validated_data):
        channel = Channel.objects.create(name=f"Chat web · {validated_data['name']}", channel_type='webchat',
                                         identifier=validated_data['name'],
                                         is_active=validated_data.get('is_active', True))
        return WebChatWidget.objects.create(channel=channel, **validated_data)

    def update(self, instance, validated_data):
        obj = super().update(instance, validated_data)
        self._sync_channel(obj, 'webchat', obj.name)
        return obj


class MetaPageSerializer(_RoutingMixin, serializers.ModelSerializer):
    page_access_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_token = serializers.SerializerMethodField()
    provider_name = serializers.CharField(source='provider.name', read_only=True)

    class Meta:
        model = MetaPage
        fields = [
            'id', 'channel_id', 'provider', 'provider_name', 'platform', 'name', 'page_id',
            'instagram_account_id', 'page_access_token', 'has_token', 'subscribed', 'last_error',
            'open_conversations', *ROUTING_FIELDS, 'created_at', 'updated_at',
        ]
        read_only_fields = ['subscribed', 'last_error', 'created_at', 'updated_at']

    def get_has_token(self, obj):
        return bool(obj.page_access_token)

    def validate(self, attrs):
        platform = attrs.get('platform', getattr(self.instance, 'platform', None))
        ig = attrs.get('instagram_account_id', getattr(self.instance, 'instagram_account_id', ''))
        if platform == 'instagram' and not ig:
            raise serializers.ValidationError({'instagram_account_id': 'Requerido para Instagram.'})
        if not self.instance and not attrs.get('page_access_token'):
            raise serializers.ValidationError({'page_access_token': 'El token de la página es obligatorio.'})
        return attrs

    def create(self, validated_data):
        platform = validated_data['platform']
        channel = Channel.objects.create(
            name=f"{dict(Channel.CHANNEL_TYPES)[platform]} · {validated_data['name']}",
            channel_type=platform, identifier=validated_data['page_id'],
            is_active=validated_data.get('is_active', True),
        )
        return MetaPage.objects.create(channel=channel, **validated_data)

    def update(self, instance, validated_data):
        if 'page_access_token' in validated_data and not validated_data['page_access_token']:
            validated_data.pop('page_access_token')
        validated_data.pop('platform', None)  # la plataforma no cambia (define el tipo de canal)
        obj = super().update(instance, validated_data)
        self._sync_channel(obj, obj.platform, obj.page_id)
        return obj
