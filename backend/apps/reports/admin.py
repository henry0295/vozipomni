from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'format', 'status', 'created_by', 'created_at', 'completed_at']
    list_filter = ['report_type', 'format', 'status', 'is_scheduled', 'created_at']
    search_fields = ['name', 'created_by__username']
    readonly_fields = ['file_size', 'created_at', 'completed_at', 'error_message']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'report_type', 'format', 'status')
        }),
        ('Período', {
            'fields': ('date_from', 'date_to')
        }),
        ('Filtros', {
            'fields': ('filters',),
            'classes': ('collapse',)
        }),
        ('Resultado', {
            'fields': ('file_path', 'file_size', 'error_message')
        }),
        ('Programación', {
            'fields': ('is_scheduled', 'schedule_frequency'),
            'classes': ('collapse',)
        }),
    )
