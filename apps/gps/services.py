from django.utils import timezone
from datetime import timedelta
import math

from .models import GpsPoint, Trip


def haversine_meters(lat1, lon1, lat2, lon2):
    """Distancia en metros entre dos coordenadas."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

STOP_THRESHOLD = timedelta(minutes=10)
STOP_DRIFT_METERS = 50.0


def _is_stopped(point):
    """Punto detenido si velocidad es 0 o ignición apagada."""
    return point.speed == 0 or not getattr(point, "ignition", True)


def _calc_trip_stats(points):
    """
    Calcula distancia (metros), velocidad media y máxima (km/h)
    a partir de una lista ordenada de GpsPoints.
    """
    total_meters = 0.0
    for i in range(1, len(points)):
        p1, p2 = points[i - 1], points[i]
        total_meters += haversine_meters(p1.lat, p1.lng, p2.lat, p2.lng)

    speeds = [p.speed for p in points if p.speed is not None]
    avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
    max_speed = max(speeds) if speeds else 0.0

    return round(total_meters, 2), round(avg_speed, 2), round(max_speed, 2)


def process_trip_detection(vehicle_id):
    """
    Detecta inicio y cierre de viajes a partir de puntos GPS sin asignar.

    Reglas:
    - Vehículo parado > 15 min y luego se mueve  →  abre un Trip nuevo.
    - Vehículo se detiene (vel=0 o ignición OFF) > 15 min  →  cierra el Trip activo
      y persiste: distance_meters, avg_speed, max_speed, duration,
      start_lat/lng, end_lat/lng.

    Returns:
        dict:
            'opened'   : Trip recién abierto (o None)
            'closed'   : Trip recién cerrado (o None)
            'processed': cantidad de puntos evaluados
    """
    result = {"opened": None, "closed": None, "processed": 0}

    # 1. Puntos sin viaje, ordenados cronológicamente
    unassigned = list(
        GpsPoint.objects
        .filter(vehicle_id=vehicle_id, trip__isnull=True)
        .order_by("timestamp")
    )
    if not unassigned:
        return result

    result["processed"] = len(unassigned)

    # 2. Viaje activo (sin end_time)
    active_trip = (
        Trip.objects
        .filter(vehicle_id=vehicle_id, end_time__isnull=True)
        .order_by("-start_time")
        .first()
    )

    # Si hay un viaje activo, filtramos los puntos no asignados para ignorar basura muy antigua
    if active_trip:
        valid_unassigned = [p for p in unassigned if p.timestamp >= active_trip.start_time]
        # Limpiar basura antigua de la BD asignandola al viaje activo para que no estorbe
        old_ids = [p.pk for p in unassigned if p.timestamp < active_trip.start_time]
        if old_ids:
            GpsPoint.objects.filter(pk__in=old_ids).update(trip=active_trip)
        unassigned = valid_unassigned

    if not unassigned:
        return result

    def close_active_trip(trip, end_point, all_points):
        trip.end_time = end_point.timestamp
        trip.duration = trip.end_time - trip.start_time
        trip.end_lat = end_point.lat
        trip.end_lng = end_point.lng

        if len(all_points) >= 2:
            trip.distance_meters, trip.avg_speed, trip.max_speed = _calc_trip_stats(all_points)
        else:
            trip.distance_meters, trip.avg_speed, trip.max_speed = 0.0, 0.0, 0.0

        trip.save()

        # Broadcast event
        try:
            from apps.fleet.models import Vehicle
            vehicle = Vehicle.objects.get(id=trip.vehicle_id)
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"fleet_{vehicle.tenant_id}",
                    {
                        "type": "trip_completed",
                        "data": {
                            "trip_id": trip.id,
                            "vehicle_plate": vehicle.plate,
                            "distance_meters": trip.distance_meters,
                            "duration": str(trip.duration)
                        }
                    }
                )
        except Exception as e:
            import logging
            logging.error(f"Error enviando WebSocket trip_completed: {e}")

    # ── 3. Lógica simplificada ────────────────────────────────────────────────
    
    if active_trip is None:
        # Buscar el primer punto que se mueve
        first_moving = next((p for p in unassigned if not _is_stopped(p)), None)
        if first_moving:
            active_trip = Trip.objects.create(
                vehicle_id=vehicle_id,
                start_time=first_moving.timestamp,
                start_lat=first_moving.lat,
                start_lng=first_moving.lng,
            )
            result["opened"] = active_trip
            
            # Asignar todos los puntos móviles al viaje
            moving_ids = [p.pk for p in unassigned if p.timestamp >= first_moving.timestamp and not _is_stopped(p)]
            if moving_ids:
                GpsPoint.objects.filter(pk__in=moving_ids).update(trip=active_trip)
    else:
        # Tenemos viaje activo. Veamos si hay que cerrarlo.
        
        moving_points = [p for p in unassigned if not _is_stopped(p)]
        if moving_points:
            # Si hubo puntos que se movieron, significa que cualquier punto detenido
            # anterior a ellos fue sólo una pausa temporal (semáforo).
            # Asignamos TODOS los puntos hasta el último punto móvil al viaje activo.
            last_moving = moving_points[-1]
            to_assign = [p for p in unassigned if p.timestamp <= last_moving.timestamp]
            if to_assign:
                GpsPoint.objects.filter(pk__in=[p.pk for p in to_assign]).update(trip=active_trip)
            
            # Nos quedamos solo con los puntos detenidos posteriores al último movimiento
            unassigned = [p for p in unassigned if p.timestamp > last_moving.timestamp]
            
        stopped_points = unassigned
        
        if stopped_points:
            first_stopped = stopped_points[0]
            last_stopped = stopped_points[-1]
            duration = last_stopped.timestamp - first_stopped.timestamp
            
            # Validar drift (deriva GPS)
            dist = haversine_meters(first_stopped.lat, first_stopped.lng, last_stopped.lat, last_stopped.lng)
            
            if duration >= STOP_THRESHOLD and dist <= STOP_DRIFT_METERS:
                # CERRAR VIAJE
                persisted_points = list(GpsPoint.objects.filter(trip=active_trip).order_by("timestamp"))
                all_points = persisted_points + stopped_points
                close_active_trip(active_trip, first_stopped, all_points)
                result["closed"] = active_trip
                
                # Asignar los puntos detenidos al viaje que acabamos de cerrar
                GpsPoint.objects.filter(pk__in=[p.pk for p in stopped_points]).update(trip=active_trip)

    return result