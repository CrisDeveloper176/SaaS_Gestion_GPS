from rest_framework import serializers
from .models import Alert, AlertRule

class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = ['id', 'tenant', 'vehicle', 'alert_type', 'threshold', 'schedule_start', 'schedule_end', 'cooldown_minutes', 'last_triggered', 'is_active']
        read_only_fields = ['tenant', 'last_triggered']

class AlertSerializer(serializers.ModelSerializer):
    vehicle_plate = serializers.ReadOnlyField(source='vehicle.plate')
    alert_type = serializers.ReadOnlyField(source='rule.alert_type')

    class Meta:
        model = Alert
        fields = ['id', 'rule', 'vehicle', 'vehicle_plate', 'alert_type', 'gps_point', 'message', 'timestamp', 'is_read']
        read_only_fields = ['id', 'rule', 'vehicle', 'vehicle_plate', 'alert_type', 'gps_point', 'message', 'timestamp']
