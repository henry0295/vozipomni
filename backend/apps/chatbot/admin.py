from django.contrib import admin

from .models import AIProvider, AIUsageLog, BotFlow, BotFlowVersion, BotSession, Connector, ConnectorLog


@admin.register(Connector)
class ConnectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'connector_type', 'base_url', 'is_active')
    exclude = ('secrets',)  # las credenciales se editan desde la aplicación


@admin.register(ConnectorLog)
class ConnectorLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'connector', 'action', 'status', 'duration_ms', 'source')
    list_filter = ('status', 'connector', 'source')


@admin.register(BotFlow)
class BotFlowAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'published_version', 'updated_at')


admin.site.register(BotFlowVersion)


@admin.register(BotSession)
class BotSessionAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'flow', 'status', 'current_node', 'last_activity_at')
    list_filter = ('status', 'flow')
    exclude = ('variables',)


@admin.register(AIProvider)
class AIProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'model', 'mask_personal_data', 'is_active')
    exclude = ('api_key',)


@admin.register(AIUsageLog)
class AIUsageLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'provider', 'purpose', 'status', 'result', 'prompt_tokens', 'completion_tokens')
    list_filter = ('status', 'purpose', 'provider')