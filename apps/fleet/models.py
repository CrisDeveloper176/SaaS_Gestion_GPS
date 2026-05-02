from django.db import models
from apps.tenants.models import Tenant
from django.conf import settings

class Driver(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=150)
    license_number = models.CharField(max_length=50, blank=True)
    license_expiry = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.license_number})"

class Vehicle(models.Model):
    FUEL_CHOICES = [
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    plate = models.CharField(max_length=20) # en specs "nicos por tenant", podemos validar en capa o meta unique_together
    alias = models.CharField(max_length=100, blank=True)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES, default='gasoline')
    odometer_base = models.FloatField(default=0)
    device_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    tracker_api_key = models.CharField(max_length=128, blank=True, null=True, help_text="Almacena el hash de la API Key")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    current_driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicles')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tenant', 'plate')

    def generate_api_key(self):
        import secrets, hashlib
        raw_key = secrets.token_hex(32)
        self.tracker_api_key = hashlib.sha256(raw_key.encode()).hexdigest()
        self.save(update_fields=["tracker_api_key"])
        return raw_key

    def __str__(self):
        return self.plate
