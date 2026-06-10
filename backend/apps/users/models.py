from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class VozipOmniUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Superusuarios siempre tienen rol 'admin', sin importar el valor por defecto
        extra_fields['role'] = 'admin'
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Usuario extendido para VoziPOmni
    """
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('supervisor', 'Supervisor'),
        ('agent', 'Agente'),
        ('analyst', 'Analista'),
    ]
    
    objects = VozipOmniUserManager()

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_active_agent = models.BooleanField(default=False)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"
