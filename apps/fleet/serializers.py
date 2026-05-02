from rest_framework import serializers
from .models import Vehicle, Driver

class DriverSerializer(serializers.ModelSerializer):
    is_assigned = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']

    def get_is_assigned(self, obj):
        return obj.vehicles.exists()

class VehicleSerializer(serializers.ModelSerializer):
    last_location = serializers.SerializerMethodField()
    current_driver_name = serializers.CharField(source='current_driver.name', read_only=True)

    class Meta:
        model = Vehicle
        fields = '__all__'
        read_only_fields = ['tenant', 'created_at', 'updated_at']

    def get_last_location(self, obj):
        from apps.gps.models import GpsPoint
        last_point = GpsPoint.objects.filter(vehicle=obj).order_by('-timestamp').first()
        if last_point:
            return {
                'lat': float(last_point.lat),
                'lon': float(last_point.lng),
                'speed': float(last_point.speed),
                'timestamp': last_point.timestamp.isoformat()
            }
        return None
