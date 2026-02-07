from django.contrib import admin
from .models import Agent, AgentStatusHistory, AgentBreakReason


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['agent_id', 'user', 'sip_extension', 'status', 'current_calls', 'calls_today', 'logged_in_at']
    list_filter = ['status', 'webrtc_enabled', 'logged_in_at']
    search_fields = ['agent_id', 'sip_extension', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['current_calls', 'last_call_time', 'logged_in_at', 'last_status_change', 'created_at', 'updated_at']
    filter_horizontal = ['campaigns']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('user', 'agent_id', 'sip_extension', 'status')
        }),
        ('Configuración', {
            'fields': ('webrtc_enabled', 'max_concurrent_calls', 'auto_answer', 'recording_enabled')
        }),
        ('Estado Actual', {
            'fields': ('current_calls', 'last_call_time', 'logged_in_at', 'last_status_change')
        }),
        ('Métricas del Día', {
            'fields': ('calls_today', 'talk_time_today', 'available_time_today', 'break_time_today'),
            'classes': ('collapse',)
        }),
        ('Campañas', {
            'fields': ('campaigns', 'current_campaign'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AgentStatusHistory)
class AgentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['agent', 'status', 'started_at', 'ended_at', 'duration', 'campaign']
    list_filter = ['status', 'started_at', 'campaign']
    search_fields = ['agent__user__username', 'agent__agent_id']
    readonly_fields = ['started_at']


@admin.register(AgentBreakReason)
class AgentBreakReasonAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_paid', 'max_duration', 'is_active']
    list_filter = ['is_paid', 'is_active']
    search_fields = ['code', 'name']
