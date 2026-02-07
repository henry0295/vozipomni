from django.contrib import admin
from .models import Campaign, CampaignDisposition


class CampaignDispositionInline(admin.TabularInline):
    model = CampaignDisposition
    extra = 1
    fields = ['code', 'name', 'is_success', 'requires_callback', 'order']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'campaign_type', 'status', 'total_contacts', 'contacted', 'successful', 'success_rate', 'created_at']
    list_filter = ['campaign_type', 'status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'total_contacts', 'contacted', 'successful']
    inlines = [CampaignDispositionInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'campaign_type', 'dialer_type', 'status')
        }),
        ('Configuración', {
            'fields': ('max_calls_per_agent', 'max_retries', 'retry_delay', 'call_timeout')
        }),
        ('Horarios', {
            'fields': ('start_date', 'end_date', 'schedule_start_time', 'schedule_end_time')
        }),
        ('Relaciones', {
            'fields': ('queue', 'contact_list')
        }),
        ('Script y Formulario', {
            'fields': ('script_template', 'form_fields'),
            'classes': ('collapse',)
        }),
        ('Métricas', {
            'fields': ('total_contacts', 'contacted', 'successful'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CampaignDisposition)
class CampaignDispositionAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'code', 'name', 'is_success', 'requires_callback', 'order']
    list_filter = ['campaign', 'is_success', 'requires_callback']
    search_fields = ['code', 'name', 'campaign__name']
