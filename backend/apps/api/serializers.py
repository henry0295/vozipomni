from rest_framework import serializers
from apps.users.models import User
from apps.campaigns.models import Campaign, CampaignDisposition
from apps.agents.models import Agent
from apps.contacts.models import Contact, ContactList
from apps.queues.models import Queue
from apps.telephony.models import Call
from apps.recordings.models import Recording
from apps.reports.models import Report


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 
                  'phone', 'department', 'is_active_agent', 'last_activity']
        read_only_fields = ['last_activity']


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
    
    class Meta:
        model = Agent
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'current_calls', 'last_call_time', 
                            'logged_in_at', 'calls_today', 'talk_time_today']


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
