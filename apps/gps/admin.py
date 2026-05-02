from django.contrib import admin
from .models import GpsPoint, Trip

@admin.register(GpsPoint)
class GpsPointAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'timestamp', 'lat', 'lng', 'speed', 'ignition')
    list_filter = ('ignition',)
    search_fields = ('vehicle__plate',)

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'start_time', 'end_time', 'distance_meters', 'duration')
    list_filter = ('vehicle__tenant',)
    search_fields = ('vehicle__plate',)
