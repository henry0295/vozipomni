from django.contrib import admin
from .models import Recording, RecordingNote, RecordingEvaluation


class RecordingNoteInline(admin.TabularInline):
    model = RecordingNote
    extra = 0
    fields = ['timestamp', 'note', 'created_by']
    readonly_fields = ['created_at']


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ['filename', 'call', 'status', 'duration', 'file_size_mb', 'agent', 
                    'campaign', 'access_count', 'created_at']
    list_filter = ['status', 'format', 'created_at', 'campaign']
    search_fields = ['filename', 'call__call_id', 'agent__user__username']
    readonly_fields = ['file_size', 'duration', 'created_at', 'updated_at', 'access_count']
    inlines = [RecordingNoteInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('call', 'filename', 'file_path', 'status')
        }),
        ('Detalles', {
            'fields': ('format', 'codec', 'duration', 'file_size')
        }),
        ('Relaciones', {
            'fields': ('agent', 'campaign')
        }),
        ('Transcripción', {
            'fields': ('transcription', 'transcription_status'),
            'classes': ('collapse',)
        }),
        ('Control de Acceso', {
            'fields': ('is_public', 'access_count')
        }),
    )


@admin.register(RecordingNote)
class RecordingNoteAdmin(admin.ModelAdmin):
    list_display = ['recording', 'timestamp', 'note', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['recording__filename', 'note']


@admin.register(RecordingEvaluation)
class RecordingEvaluationAdmin(admin.ModelAdmin):
    list_display = ['recording', 'evaluator', 'total_score', 'greeting', 'clarity', 
                    'professionalism', 'resolution', 'closing', 'feedback_sent']
    list_filter = ['feedback_sent', 'created_at']
    search_fields = ['recording__filename', 'evaluator__username', 'comments']
    readonly_fields = ['total_score', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información', {
            'fields': ('recording', 'evaluator')
        }),
        ('Criterios de Evaluación (1-5)', {
            'fields': ('greeting', 'clarity', 'professionalism', 'resolution', 'closing', 'total_score')
        }),
        ('Comentarios', {
            'fields': ('comments', 'feedback_sent')
        }),
    )
