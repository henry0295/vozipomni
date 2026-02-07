from django.contrib import admin
from .models import ContactList, Contact, ContactNote, Blacklist


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    can_delete = False
    fields = ['first_name', 'last_name', 'phone', 'email', 'status']
    readonly_fields = ['first_name', 'last_name', 'phone', 'email', 'status']


@admin.register(ContactList)
class ContactListAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_contacts', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['total_contacts', 'created_at', 'updated_at']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'email', 'contact_list', 'status', 'attempts', 'last_attempt']
    list_filter = ['status', 'contact_list', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone', 'email', 'company']
    readonly_fields = ['created_at', 'updated_at', 'attempts', 'last_attempt']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('contact_list', 'first_name', 'last_name', 'email')
        }),
        ('Teléfonos', {
            'fields': ('phone', 'phone2', 'phone3')
        }),
        ('Información Adicional', {
            'fields': ('company', 'position', 'address', 'city', 'country'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('status', 'priority', 'attempts', 'last_attempt', 'next_attempt')
        }),
        ('Datos Personalizados', {
            'fields': ('custom_fields',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ContactNote)
class ContactNoteAdmin(admin.ModelAdmin):
    list_display = ['contact', 'note', 'created_by', 'created_at', 'is_important']
    list_filter = ['is_important', 'created_at']
    search_fields = ['contact__first_name', 'contact__last_name', 'note']
    readonly_fields = ['created_at']


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display = ['phone', 'reason', 'added_by', 'added_at', 'is_active']
    list_filter = ['is_active', 'added_at']
    search_fields = ['phone', 'reason']
    readonly_fields = ['added_at']
