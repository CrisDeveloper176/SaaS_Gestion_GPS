from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.tenants.models import Tenant

class User(AbstractUser):
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Admin'),
        ('ORG_ADMIN', 'Organization Admin'),
        ('MANAGER', 'Manager'),
        ('DRIVER', 'Driver'),
        ('VIEWER', 'Viewer'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='users')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='VIEWER')

    def __str__(self):
        return f"{self.email or self.username} ({self.role})"
