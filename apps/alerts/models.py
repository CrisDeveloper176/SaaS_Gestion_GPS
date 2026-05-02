from django.db import models
from apps.tenants.models import Tenant
from apps.fleet.models import Vehicle
from apps.gps.models import GpsPoint

class AlertRule(models.Model):
    ALERT_TYPES = [
        ('SPEEDING', 'Exceso de Velocidad'),
        ('IDLE_TOO_LONG', 'Ralentí Excesivo'),
        ('GEOFENCE_EXIT', 'Salida de Geocerca'),
        ('OFF_HOURS_USAGE', 'Uso Fuera de Horario'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='alert_rules')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, null=True, blank=True, related_name='specific_alert_rules', help_text="Si es nulo, aplica a toda la flota")
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    threshold = models.FloatField(null=True, blank=True, help_text="Valor límite (ej. 100 km/h o 15 minutos)")
    schedule_start = models.TimeField(null=True, blank=True, help_text="Inicio de horario permitido")
    schedule_end = models.TimeField(null=True, blank=True, help_text="Fin de horario permitido")
    cooldown_minutes = models.IntegerField(default=5, help_text="Minutos a esperar antes de volver a disparar esta misma alerta")
    last_triggered = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        target = self.vehicle.plate if self.vehicle else "Toda la flota"
        return f"{self.get_alert_type_display()} > {self.threshold} ({target})"

class Alert(models.Model):
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='alerts')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='alerts')
    gps_point = models.ForeignKey(GpsPoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='alerts')
    message = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.vehicle.plate} - {self.message}"
