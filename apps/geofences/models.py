from django.db import models
from apps.tenants.models import Tenant

class Geofence(models.Model):
    SHAPE_CHOICES = [
        ('POLYGON', 'Polígono'),
        ('CIRCLE', 'Círculo'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='geofences')
    name = models.CharField(max_length=150)
    shape_type = models.CharField(max_length=10, choices=SHAPE_CHOICES, default='POLYGON')
    
    # Para polígonos: JSON array de [lat, lng] — ej. [[lat1,lng1],[lat2,lng2],...]
    coordinates = models.JSONField(default=list, blank=True, help_text="Lista de [lat, lng] para polígonos")
    
    # Para círculos
    center_lat = models.FloatField(null=True, blank=True)
    center_lng = models.FloatField(null=True, blank=True)
    radius_meters = models.FloatField(null=True, blank=True, help_text="Radio en metros (solo para círculos)")

    color = models.CharField(max_length=7, default='#3b82f6', help_text="Color hex para visualización")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_shape_type_display()}) - {self.tenant.name}"
