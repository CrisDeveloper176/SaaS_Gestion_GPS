from django.db import models
from apps.fleet.models import Vehicle

class GpsPoint(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, db_index=True, related_name='gps_points')
    trip = models.ForeignKey('Trip', on_delete=models.SET_NULL, null=True, blank=True, related_name='points')
    lat = models.FloatField()
    lng = models.FloatField()
    speed = models.FloatField()
    heading = models.FloatField(default=0.0)
    altitude = models.FloatField(default=0.0)
    accuracy = models.FloatField(default=0.0)
    timestamp = models.DateTimeField()
    ignition = models.BooleanField(default=False)
    odometer = models.FloatField(default=0.0)

    class Meta:
        indexes = [
            models.Index(fields=['vehicle', '-timestamp']),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.vehicle.plate} - {self.lat}, {self.lng}"

class Trip(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, db_index=True, related_name='trips')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Ubicaciones de inicio y fin (separas en Lat/Lng para evitar dependencia de PostGIS)
    start_lat = models.FloatField(null=True, blank=True)
    start_lng = models.FloatField(null=True, blank=True)
    end_lat = models.FloatField(null=True, blank=True)
    end_lng = models.FloatField(null=True, blank=True)
    
    max_speed = models.FloatField(default=0.0)
    avg_speed = models.FloatField(default=0.0)
    distance_meters = models.FloatField(default=0.0)
    duration = models.DurationField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['vehicle', '-start_time'])
        ]
    
    def __str__(self):
        return f"Viaje {self.id} de {self.vehicle.plate} ({self.start_time})"
