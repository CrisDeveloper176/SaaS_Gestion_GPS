from django.contrib import admin
from .models import Vehicle, Driver
from apps.gps.models import Trip, GpsPoint

@admin.action(description='Eliminar historial (viajes y puntos GPS) de vehículos seleccionados')
def delete_vehicle_history(modeladmin, request, queryset):
    # Eliminar primero los puntos GPS para evitar la cascada costosa (SET_NULL) en Trip
    points_deleted, _ = GpsPoint.objects.filter(vehicle__in=queryset).delete()
    trips_deleted, _ = Trip.objects.filter(vehicle__in=queryset).delete()
    modeladmin.message_user(
        request,
        f"Se eliminaron {trips_deleted} viajes y {points_deleted} puntos GPS."
    )

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('plate', 'alias', 'tenant', 'status', 'device_id')
    search_fields = ('plate', 'alias', 'device_id')
    list_filter = ('status', 'tenant')
    actions = [delete_vehicle_history]

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'license_number', 'tenant', 'is_active')
    search_fields = ('name', 'license_number')
    list_filter = ('is_active', 'tenant')
