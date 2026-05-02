import django_filters
from .models import Trip, GpsPoint

class TripFilter(django_filters.FilterSet):
    start_date = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='gte')
    end_date = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='lte')

    class Meta:
        model = Trip
        fields = ['vehicle_id', 'start_date', 'end_date']

class GpsPointHistoryFilter(django_filters.FilterSet):
    start_time = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    end_time = django_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')

    class Meta:
        model = GpsPoint
        fields = ['vehicle_id', 'start_time', 'end_time', 'trip_id']
