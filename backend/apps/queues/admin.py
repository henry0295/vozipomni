from django.contrib import admin
from .models import Queue, QueueMember, QueueStats


class QueueMemberInline(admin.TabularInline):
    model = QueueMember
    extra = 1
    fields = ['agent', 'penalty', 'paused', 'calls_taken']
    readonly_fields = ['calls_taken', 'last_call']


@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    list_display = ['name', 'extension', 'strategy', 'max_callers', 'is_active', 'created_at']
    list_filter = ['strategy', 'is_active', 'created_at']
    search_fields = ['name', 'extension', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [QueueMemberInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'extension', 'description', 'strategy', 'is_active')
        }),
        ('Configuración de Timers', {
            'fields': ('timeout', 'retry', 'max_wait_time', 'wrap_up_time')
        }),
        ('Anuncios', {
            'fields': ('announce_frequency', 'announce_holdtime', 'periodic_announce_frequency'),
            'classes': ('collapse',)
        }),
        ('Configuración Avanzada', {
            'fields': ('music_on_hold', 'max_callers', 'service_level'),
            'classes': ('collapse',)
        }),
    )


@admin.register(QueueMember)
class QueueMemberAdmin(admin.ModelAdmin):
    list_display = ['queue', 'agent', 'penalty', 'paused', 'calls_taken', 'last_call']
    list_filter = ['queue', 'paused']
    search_fields = ['queue__name', 'agent__user__username', 'agent__agent_id']


@admin.register(QueueStats)
class QueueStatsAdmin(admin.ModelAdmin):
    list_display = ['queue', 'calls_waiting', 'calls_completed', 'calls_abandoned', 
                    'agents_available', 'agents_busy', 'service_level_percentage']
    readonly_fields = ['queue', 'calls_waiting', 'calls_completed', 'calls_abandoned', 
                       'avg_wait_time', 'avg_talk_time', 'max_wait_time',
                       'agents_available', 'agents_busy', 'service_level_met', 
                       'service_level_percentage', 'updated_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
