"""
Serializers de la app de mensajería multicanal.
"""
from rest_framework import serializers
from .models import Channel, Conversation, Message


class ChannelSerializer(serializers.ModelSerializer):
    channel_type_display = serializers.CharField(
        source='get_channel_type_display', read_only=True
    )
    conversation_count = serializers.SerializerMethodField()

    class Meta:
        model = Channel
        fields = [
            'id', 'name', 'channel_type', 'channel_type_display',
            'identifier', 'is_active', 'created_at', 'conversation_count',
        ]
        read_only_fields = ['created_at']

    def get_conversation_count(self, obj):
        return obj.conversations.filter(status__in=['open', 'waiting']).count()


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'direction', 'body', 'media_url',
            'is_read', 'sent_at', 'external_id',
        ]
        read_only_fields = ['sent_at']

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('El mensaje no puede estar vacío.')
        return value.strip()


class ConversationSerializer(serializers.ModelSerializer):
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    channel_type = serializers.CharField(source='channel.channel_type', read_only=True)
    agent_name = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id', 'channel', 'channel_name', 'channel_type',
            'agent', 'agent_name', 'contact', 'contact_name',
            'contact_identifier', 'status', 'status_display',
            'started_at', 'closed_at', 'campaign',
            'last_message', 'unread_count',
        ]
        read_only_fields = ['started_at', 'closed_at']

    def get_agent_name(self, obj):
        if obj.agent and obj.agent.user:
            return obj.agent.user.get_full_name() or obj.agent.user.username
        return None

    def get_contact_name(self, obj):
        if obj.contact:
            return obj.contact.full_name
        return obj.contact_identifier

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-sent_at').first()
        if msg:
            return {
                'body': msg.body[:100],
                'direction': msg.direction,
                'sent_at': msg.sent_at.isoformat(),
                'is_read': msg.is_read,
            }
        return None

    def get_unread_count(self, obj):
        return obj.messages.filter(direction='inbound', is_read=False).count()


class ConversationDetailSerializer(ConversationSerializer):
    """Serializer detallado con mensajes incluidos."""
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages']
