from rest_framework import serializers
from .models import Geofence

class GeofenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Geofence
        fields = [
            'id', 'tenant', 'name', 'shape_type',
            'coordinates', 'center_lat', 'center_lng', 'radius_meters',
            'color', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['tenant', 'created_at', 'updated_at']
