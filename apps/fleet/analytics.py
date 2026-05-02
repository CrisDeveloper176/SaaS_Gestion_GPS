from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Avg, Max, Sum, Q
from django.db.models.functions import TruncDate


class DashboardSummaryView(APIView):
    """
    Devuelve estadísticas generales del dashboard para el tenant actual.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = request.user.tenant
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        from apps.fleet.models import Vehicle, Driver
        from apps.alerts.models import Alert, AlertRule
        from apps.gps.models import Trip, GpsPoint
        from apps.geofences.models import Geofence

        # --- Vehículos ---
        vehicles = Vehicle.objects.filter(tenant=tenant)
        vehicles_total = vehicles.count()
        vehicles_active = vehicles.filter(status='active').count()

        # --- Conductores ---
        drivers_total = Driver.objects.filter(tenant=tenant).count()
        drivers_active = Driver.objects.filter(tenant=tenant, is_active=True).count()

        # --- Alertas ---
        alerts_qs = Alert.objects.filter(rule__tenant=tenant)
        alerts_24h = alerts_qs.filter(timestamp__gte=last_24h).count()
        alerts_unread = alerts_qs.filter(is_read=False).count()
        alerts_total = alerts_qs.count()

        # Alertas por tipo (últimos 7 días)
        alerts_by_type = list(
            alerts_qs
            .filter(timestamp__gte=last_7d)
            .values('rule__alert_type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Alertas por día (últimos 7 días)
        alerts_by_day = list(
            alerts_qs
            .filter(timestamp__gte=last_7d)
            .annotate(day=TruncDate('timestamp'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        # Formatear fechas
        for item in alerts_by_day:
            item['day'] = item['day'].strftime('%d/%m') if item['day'] else ''

        # --- Viajes ---
        trips_qs = Trip.objects.filter(vehicle__tenant=tenant)
        trips_7d = trips_qs.filter(start_time__gte=last_7d)
        trips_count_7d = trips_7d.count()
        trip_stats = trips_7d.aggregate(
            total_distance=Sum('distance_meters'),
            avg_speed=Avg('avg_speed'),
            max_speed=Max('max_speed'),
        )

        # Viajes por día (últimos 7 días)
        trips_by_day = list(
            trips_7d
            .annotate(day=TruncDate('start_time'))
            .values('day')
            .annotate(
                count=Count('id'),
                distance=Sum('distance_meters')
            )
            .order_by('day')
        )
        for item in trips_by_day:
            item['day'] = item['day'].strftime('%d/%m') if item['day'] else ''
            item['distance_km'] = round((item.get('distance') or 0) / 1000, 1)

        # --- Geocercas ---
        geofences_total = Geofence.objects.filter(tenant=tenant, is_active=True).count()

        # --- Top 5 vehículos por km recorridos (7 días) ---
        top_vehicles = list(
            trips_7d
            .values('vehicle__plate')
            .annotate(total_km=Sum('distance_meters'))
            .order_by('-total_km')[:5]
        )
        for v in top_vehicles:
            v['total_km'] = round((v.get('total_km') or 0) / 1000, 1)

        return Response({
            'vehicles': {
                'total': vehicles_total,
                'active': vehicles_active,
            },
            'drivers': {
                'total': drivers_total,
                'active': drivers_active,
            },
            'alerts': {
                'total': alerts_total,
                'last_24h': alerts_24h,
                'unread': alerts_unread,
                'by_type': alerts_by_type,
                'by_day': alerts_by_day,
            },
            'trips': {
                'count_7d': trips_count_7d,
                'total_distance_km': round((trip_stats['total_distance'] or 0) / 1000, 1),
                'avg_speed': round(trip_stats['avg_speed'] or 0, 1),
                'max_speed': round(trip_stats['max_speed'] or 0, 1),
                'by_day': trips_by_day,
            },
            'top_vehicles': top_vehicles,
            'geofences': {
                'active': geofences_total,
            },
        })
