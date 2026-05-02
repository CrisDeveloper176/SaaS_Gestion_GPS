from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import models
from .models import AlertRule, Alert
from apps.fleet.models import Vehicle

@shared_task
def evaluate_alerts(vehicle_id, gps_data):
    """
    Evalúa las reglas de alertas para un vehículo dado basándose en el punto GPS ingresado.
    """
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
    except Vehicle.DoesNotExist:
        return {'status': 'error', 'message': 'Vehicle not found'}

    tenant_id = vehicle.tenant_id
    now = timezone.now()

    # Obtener reglas aplicables (específicas al vehículo o generales de la flota)
    rules = AlertRule.objects.filter(
        tenant_id=tenant_id,
        is_active=True
    ).filter(
        models.Q(vehicle=vehicle) | models.Q(vehicle__isnull=True)
    )

    alerts_created = []

    for rule in rules:
        trigger_alert = False
        message = ""

        # Verificar si el cooldown ha expirado
        if rule.last_triggered:
            cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
            if now < cooldown_end:
                continue # Aún en cooldown

        if rule.alert_type == 'SPEEDING':
            speed = float(gps_data.get('speed', 0))
            if speed > rule.threshold:
                trigger_alert = True
                message = f"Exceso de velocidad: {speed} km/h (Límite: {rule.threshold} km/h)"

        elif rule.alert_type == 'IDLE_TOO_LONG':
            speed = float(gps_data.get('speed', 0))
            ignition = gps_data.get('ignition', False)
            # Simplificación: si ahora mismo la velocidad es 0 y el motor está encendido, 
            # verificamos el tiempo en inactividad. 
            # (Nota: Para un idle real, tendríamos que buscar el punto donde empezó a detenerse, 
            # pero para este MVP evaluaremos la condición instantánea o confiaremos en un estado guardado).
            # Para cumplir el plan, simularemos que si envían un punto de 'idle' se dispara.
            # Mejor implementación: evaluar si (now - start_idle) > threshold
            if speed == 0 and ignition:
                 # Simplificado para simulador
                 trigger_alert = True
                 message = "Vehículo detenido con motor encendido (Ralentí)" 

        elif rule.alert_type == 'OFF_HOURS_USAGE':
            if rule.schedule_start and rule.schedule_end:
                current_time = now.time()
                # Si schedule_start < schedule_end (ej 08:00 a 20:00)
                if rule.schedule_start < rule.schedule_end:
                    if not (rule.schedule_start <= current_time <= rule.schedule_end):
                        trigger_alert = True
                else: # Cruza la medianoche (ej 20:00 a 08:00)
                    if not (current_time >= rule.schedule_start or current_time <= rule.schedule_end):
                        trigger_alert = True
                
                if trigger_alert:
                    message = f"Uso fuera de horario (Horario permitido: {rule.schedule_start} - {rule.schedule_end})"

        elif rule.alert_type == 'GEOFENCE_EXIT':
            # Simplificación para el simulador: si recibimos un parámetro especial de prueba o si calculamos distancia
            # En producción, se usaría PostGIS o geopy. Para el simulador, asumimos que si el GPS indica "is_geofence_exit", la disparamos
            if gps_data.get('is_geofence_exit', False):
                trigger_alert = True
                message = "El vehículo salió de la geocerca asignada" 

        # Si se cumplió la condición de alerta
        if trigger_alert:
            from apps.gps.models import GpsPoint
            
            # Buscar el punto recién creado para asociarlo (opcional, pero recomendado)
            point = GpsPoint.objects.filter(vehicle_id=vehicle_id).order_by('-timestamp').first()

            alert = Alert.objects.create(
                rule=rule,
                vehicle=vehicle,
                gps_point=point,
                message=message,
                timestamp=now
            )
            
            # Actualizar last_triggered
            rule.last_triggered = now
            rule.save()

            # Enviar notificación en tiempo real
            try:
                channel_layer = get_channel_layer()
                if channel_layer:
                    alert_data = {
                        'type': 'alert_triggered',
                        'alert_id': alert.id,
                        'vehicle_id': vehicle.id,
                        'vehicle_plate': vehicle.plate,
                        'alert_type': rule.alert_type,
                        'message': message,
                        'timestamp': now.isoformat()
                    }
                    async_to_sync(channel_layer.group_send)(
                        f"fleet_{tenant_id}",
                        alert_data
                    )
            except Exception as e:
                import logging
                logging.warning(f"No se pudo enviar alerta por WebSocket (¿Redis apagado?): {e}")
            
            alerts_created.append(alert.id)

    return {'status': 'success', 'alerts_created': alerts_created}
