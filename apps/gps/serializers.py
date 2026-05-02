from rest_framework import serializers

class GpsIngestSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=100)
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    speed = serializers.FloatField()
    heading = serializers.FloatField(default=0.0)
    altitude = serializers.FloatField(default=0.0)
    accuracy = serializers.FloatField(default=0.0)
    timestamp = serializers.DateTimeField()
    ignition = serializers.BooleanField(default=False)
    odometer = serializers.FloatField(default=0.0)

from .models import GpsPoint, Trip

class GpsPointHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GpsPoint
        fields = ['id', 'lat', 'lng', 'speed', 'heading', 'timestamp', 'ignition']

class TripSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.CharField(source='vehicle.plate', read_only=True)

    class Meta:
        model = Trip
        fields = [
            'id', 'vehicle', 'vehicle_plate', 'start_time', 'end_time', 
            'start_lat', 'start_lng', 'end_lat', 'end_lng', 
            'max_speed', 'avg_speed', 'distance_meters', 'duration'
        ]
