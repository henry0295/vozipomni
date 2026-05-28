from django.contrib import admin
from apps.audit.models import CallDispositionAudit


@admin.register(CallDispositionAudit)
class CallDispositionAuditAdmin(admin.ModelAdmin):
    list_display = ['id', 'call', 'agent', 'campaign', 'status', 'audited_by', 'quality_score', 'created_at']
    list_filter = ['status', 'campaign', 'created_at']
    search_fields = ['call__call_id', 'agent__agent_id', 'agent__user__username']
    readonly_fields = ['created_at', 'updated_at', 'audited_at']
    raw_id_fields = ['call', 'agent', 'campaign', 'original_disposition', 'corrected_disposition', 'audited_by']
