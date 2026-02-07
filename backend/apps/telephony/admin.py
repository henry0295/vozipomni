from django.contrib import admin
from .models import Call, SIPTrunk, IVR


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ['call_id', 'direction', 'status', 'caller_id', 'called_number', 
                    'agent', 'campaign', 'start_time', 'talk_time', 'is_recorded']
    list_filter = ['direction', 'status', 'start_time', 'campaign', 'is_recorded']
    search_fields = ['call_id', 'caller_id', 'called_number', 'unique_id']
    readonly_fields = ['call_id', 'start_time', 'answer_time', 'end_time', 
                       'wait_time', 'talk_time', 'hold_time']
    
    fieldsets = (
        ('Información de Llamada', {
            'fields': ('call_id', 'channel', 'unique_id', 'direction', 'status')
        }),
        ('Números', {
            'fields': ('caller_id', 'called_number')
        }),
        ('Relaciones', {
            'fields': ('agent', 'campaign', 'contact', 'queue', 'disposition')
        }),
        ('Tiempos', {
            'fields': ('start_time', 'answer_time', 'end_time', 'wait_time', 'talk_time', 'hold_time')
        }),
        ('Grabación', {
            'fields': ('is_recorded', 'recording_file')
        }),
        ('Transferencia', {
            'fields': ('transferred', 'transfer_to'),
            'classes': ('collapse',)
        }),
        ('Adicional', {
            'fields': ('notes', 'metadata'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SIPTrunk)
class SIPTrunkAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'port', 'max_channels', 'is_active', 'is_registered', 
                    'calls_active', 'calls_total']
    list_filter = ['is_active', 'is_registered']
    search_fields = ['name', 'host', 'username']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'host', 'port', 'username', 'password')
        }),
        ('Configuración', {
            'fields': ('codec', 'max_channels', 'dtmf_mode')
        }),
        ('Estado', {
            'fields': ('is_active', 'is_registered', 'calls_active', 'calls_total')
        }),
    )


@admin.register(IVR)
class IVRAdmin(admin.ModelAdmin):
    list_display = ['name', 'extension', 'timeout', 'max_attempts', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'extension', 'description']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'extension', 'description', 'is_active')
        }),
        ('Mensajes', {
            'fields': ('welcome_message', 'invalid_message', 'timeout_message')
        }),
        ('Configuración', {
            'fields': ('timeout', 'max_attempts', 'menu_options')
        }),
    )
