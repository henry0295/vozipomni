from django.db import models
from django.conf import settings
import phonenumbers


class ContactList(models.Model):
    """
    Lista de contactos para campañas
    """
    name = models.CharField(max_length=200, unique=True, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripción')
    total_contacts = models.IntegerField(default=0, verbose_name='Total contactos')
    is_active = models.BooleanField(default=True, verbose_name='Activa')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'contact_lists'
        verbose_name = 'Lista de Contactos'
        verbose_name_plural = 'Listas de Contactos'
    
    def __str__(self):
        return f"{self.name} ({self.total_contacts} contactos)"


class Contact(models.Model):
    """
    Contacto individual
    """
    STATUS_CHOICES = [
        ('new', 'Nuevo'),
        ('pending', 'Pendiente'),
        ('contacted', 'Contactado'),
        ('success', 'Exitoso'),
        ('failed', 'Fallido'),
        ('blacklisted', 'Lista Negra'),
    ]
    
    # Información básica
    contact_list = models.ForeignKey(ContactList, on_delete=models.CASCADE, related_name='contacts')
    first_name = models.CharField(max_length=100, verbose_name='Nombre')
    last_name = models.CharField(max_length=100, blank=True, verbose_name='Apellido')
    email = models.EmailField(blank=True, verbose_name='Email')
    phone = models.CharField(max_length=20, verbose_name='Teléfono')
    phone2 = models.CharField(max_length=20, blank=True, verbose_name='Teléfono 2')
    phone3 = models.CharField(max_length=20, blank=True, verbose_name='Teléfono 3')
    
    # Información adicional
    company = models.CharField(max_length=200, blank=True, verbose_name='Empresa')
    position = models.CharField(max_length=100, blank=True, verbose_name='Cargo')
    address = models.TextField(blank=True, verbose_name='Dirección')
    city = models.CharField(max_length=100, blank=True, verbose_name='Ciudad')
    country = models.CharField(max_length=2, blank=True, verbose_name='País')
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Estado')
    priority = models.IntegerField(default=0, verbose_name='Prioridad')
    
    # Intentos de llamada
    attempts = models.IntegerField(default=0, verbose_name='Intentos')
    last_attempt = models.DateTimeField(null=True, blank=True, verbose_name='Último intento')
    next_attempt = models.DateTimeField(null=True, blank=True, verbose_name='Próximo intento')
    
    # Datos personalizados (JSON)
    custom_fields = models.JSONField(default=dict, blank=True, verbose_name='Campos personalizados')
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contacts'
        ordering = ['-priority', 'last_name', 'first_name']
        verbose_name = 'Contacto'
        verbose_name_plural = 'Contactos'
        indexes = [
            models.Index(fields=['contact_list', 'status']),
            models.Index(fields=['phone']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.phone}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def validate_phone(self, phone_number):
        """Validar formato de teléfono"""
        try:
            parsed = phonenumbers.parse(phone_number, self.country or 'CO')
            return phonenumbers.is_valid_number(parsed)
        except:
            return False


class ContactNote(models.Model):
    """
    Notas sobre contactos
    """
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField(verbose_name='Nota')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_important = models.BooleanField(default=False, verbose_name='Importante')
    
    class Meta:
        db_table = 'contact_notes'
        ordering = ['-created_at']
        verbose_name = 'Nota de Contacto'
        verbose_name_plural = 'Notas de Contactos'
    
    def __str__(self):
        return f"Nota de {self.contact.full_name} - {self.created_at}"


class Blacklist(models.Model):
    """
    Lista negra de números
    """
    phone = models.CharField(max_length=20, unique=True, verbose_name='Teléfono')
    reason = models.CharField(max_length=200, blank=True, verbose_name='Razón')
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    
    class Meta:
        db_table = 'blacklist'
        verbose_name = 'Lista Negra'
        verbose_name_plural = 'Listas Negras'
    
    def __str__(self):
        return self.phone
