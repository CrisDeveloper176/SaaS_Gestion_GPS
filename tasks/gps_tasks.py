from celery import shared_task
from apps.gps.models import GpsPoint
from apps.fleet.models import Vehicle
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

@shared_task
def process_gps_point(vehicle_id, data):
    # Retrieve vehicle
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
    except Vehicle.DoesNotExist:
        return {'status': 'error', 'message': 'Vehicle not found'}

    # Save to TimescaleDB
    point = GpsPoint.objects.create(
        vehicle=vehicle,
        lat=data['lat'],
        lng=data['lng'],
        speed=data['speed'],
        heading=data.get('heading', 0.0),
        altitude=data.get('altitude', 0.0),
        accuracy=data.get('accuracy', 0.0),
        timestamp=data['timestamp'],
        ignition=data.get('ignition', False),
        odometer=data.get('odometer', 0.0)
    )

    # Convert data for JSON serialization (datetime to string)
    broadcast_data = {
        'type': 'vehicle_update',
        'data': {
            'plate': vehicle.plate,
            'location': {
                'latitude': float(point.lat),
                'longitude': float(point.lng),
                'speed': float(point.speed),
                'heading': float(point.heading),
                'timestamp': point.timestamp.isoformat() if hasattr(point.timestamp, 'isoformat') else str(point.timestamp),
            },
            'status': vehicle.status
        }
    }

    # Update global cache
    cache_key = f"vehicle:last:{vehicle.id}"
    cache.set(cache_key, broadcast_data, timeout=30)

    # Enviar evento por WebSocket al grupo del Tenant
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            print(f"📡 Broadcasting to fleet_{vehicle.tenant.id}: {vehicle.plate} at {point.lat}, {point.lng}")
            async_to_sync(channel_layer.group_send)(
                f"fleet_{vehicle.tenant.id}",
                broadcast_data
            )
            # Group by vehicle (optional detail tracking)
            async_to_sync(channel_layer.group_send)(
                f"vehicle_{vehicle.id}",
                broadcast_data
            )
    except Exception as e:
        import logging
        logging.warning(f"No se pudo enviar mensaje por WebSocket (¿Redis está apagado?): {e}")

    # Disparar evaluate_alerts (síncrono para el test local sin Redis)
    from apps.alerts.tasks import evaluate_alerts
    try:
        evaluate_alerts(vehicle_id, data)
    except Exception as e:
        import logging
        logging.warning(f"Error evaluando alertas: {e}")
        
    # Trigger trip detection automatically (síncrono para entorno local)
    try:
        async_process_vehicle_trip(vehicle_id)
    except Exception as e:
        import logging
        logging.warning(f"Error disparando async_process_vehicle_trip: {e}")
    
    return {'status': 'processed', 'vehicle_id': vehicle_id}

@shared_task
def async_process_vehicle_trip(vehicle_id):
    from apps.gps.services import process_trip_detection
    try:
        res = process_trip_detection(vehicle_id)
        if res and res.get('processed', 0) > 0:
            return {'vehicle_id': vehicle_id, **res}
        return None
    except Exception as e:
        # En producción, registrar error en log
        return None

@shared_task
def run_trip_detection_for_all_vehicles():
    """
    Tarea periódica que ejecuta la detección de viajes para todos los vehículos activos.
    """
    from apps.fleet.models import Vehicle
    
    # Fetch only active vehicles to avoid unnecessary processing
    vehicle_ids = Vehicle.objects.filter(status='active').values_list('id', flat=True)
    
    for vehicle_id in vehicle_ids:
        async_process_vehicle_trip.delay(vehicle_id)
            
    return {'status': 'queued', 'vehicles_queued': len(vehicle_ids)}
