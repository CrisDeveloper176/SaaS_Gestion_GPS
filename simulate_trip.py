"""
Simulador GPS realista — rutas por calles reales de Santiago
Modificado para probar TODAS las alertas y el cierre de viajes automático.
"""

import os
import django
import time
import math
import random
import datetime
import urllib.request
import urllib.error
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.fleet.models import Vehicle
from apps.alerts.models import AlertRule
from tasks.gps_tasks import process_gps_point

# Configuración
WAYPOINTS_SANTIAGO = [
    (-33.4372, -70.6506),  # Plaza Baquedano
    (-33.4420, -70.6480),  # Barrio Italia
    (-33.4489, -70.6493),  # Parque Bustamante
    (-33.4534, -70.6500),  # Barrio Lastarria
    (-33.4560, -70.6480),  # Centro Histórico
]
INTERPOLATION_STEPS = 5
SEND_INTERVAL = 0.5
BASE_SPEED_KMH = 45.0
OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"

def fetch_osrm_route(waypoints):
    coords_str = ";".join(f"{lon},{lat}" for lat, lon in waypoints)
    url = OSRM_URL.format(coords=coords_str)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FleetSimulator/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError:
        return [{"lat": lat, "lon": lon} for lat, lon in waypoints]
    if data.get("code") != "Ok":
        return [{"lat": lat, "lon": lon} for lat, lon in waypoints]
    coords = data["routes"][0]["geometry"]["coordinates"]
    return [{"lat": c[1], "lon": c[0]} for c in coords]

def bearing(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    x = math.sin(dlam) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def haversine(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def add_gps_noise(value, sigma=0.000012):
    return value + random.gauss(0, sigma)

def build_gps_points(osrm_coords):
    points = []
    prev_speed = 0.0
    for i in range(len(osrm_coords) - 1):
        p1 = osrm_coords[i]
        p2 = osrm_coords[i + 1]
        lat1, lon1 = p1["lat"], p1["lon"]
        lat2, lon2 = p2["lat"], p2["lon"]
        hdg = bearing(lat1, lon1, lat2, lon2)
        dist = haversine(lat1, lon1, lat2, lon2)
        
        for step in range(INTERPOLATION_STEPS):
            t = step / INTERPOLATION_STEPS
            t_ease = t * t * (3 - 2 * t)
            lat = add_gps_noise(lat1 + (lat2 - lat1) * t_ease)
            lon = add_gps_noise(lon1 + (lon2 - lon1) * t_ease)
            speed = max(0.0, prev_speed + random.gauss(0, 2.5)) if dist > 15 else BASE_SPEED_KMH * 0.25
            speed = min(speed, BASE_SPEED_KMH)
            prev_speed = speed
            points.append({"lat": round(lat, 7), "lng": round(lon, 7), "speed": speed, "heading": round(hdg, 1)})
    return points

def setup_alert_rules(vehicle):
    print("⚙️  Configurando Reglas de Alertas en Base de Datos...")
    AlertRule.objects.filter(vehicle=vehicle).delete() # Limpiar previas específicas
    AlertRule.objects.create(tenant=vehicle.tenant, vehicle=vehicle, alert_type='SPEEDING', threshold=100.0)
    AlertRule.objects.create(tenant=vehicle.tenant, vehicle=vehicle, alert_type='IDLE_TOO_LONG', threshold=15.0)
    AlertRule.objects.create(tenant=vehicle.tenant, vehicle=vehicle, alert_type='OFF_HOURS_USAGE', schedule_start=datetime.time(8, 0), schedule_end=datetime.time(20, 0))
    AlertRule.objects.create(tenant=vehicle.tenant, vehicle=vehicle, alert_type='GEOFENCE_EXIT')
    print("✅ Reglas configuradas.")
    
    # Limpiar base de datos para una simulación limpia
    from apps.gps.models import Trip, GpsPoint
    print("🧹 Limpiando historial previo del vehículo para prueba limpia...")
    Trip.objects.filter(vehicle=vehicle).delete()
    GpsPoint.objects.filter(vehicle=vehicle).delete()
    print("✅ Base de datos lista.")

def simulate_trip():
    try:
        vehicle = Vehicle.objects.get(plate='DEMO-02')
    except Vehicle.DoesNotExist:
        print("❌ Vehículo DEMO-02 no encontrado.")
        return

    setup_alert_rules(vehicle)
    osrm_coords = fetch_osrm_route(WAYPOINTS_SANTIAGO)
    route = build_gps_points(osrm_coords)
    total = len(route)

    print(f"\n🚗 Simulador de Pruebas: {vehicle.plate}")
    
    current_time = datetime.datetime.now(datetime.timezone.utc)

    for i, point in enumerate(route):
        data = {**point, "timestamp": current_time.isoformat(), "ignition": True}

        # Inyectar fases
        if i == 5:
            print("\n>> FASE 1: GEOFENCE EXIT (Saliendo de la geocerca simulada)")
            data["is_geofence_exit"] = True
            
        elif i == 15:
            print("\n>> FASE 2: SPEEDING (Exceso de Velocidad a 120 km/h)")
            data["speed"] = 120.0
            
        elif i == 25:
            print("\n>> FASE 3: OFF HOURS (Avanzando al día siguiente a las 03:00 AM)")
            current_time = current_time + datetime.timedelta(days=1)
            current_time = current_time.replace(hour=3, minute=0)
            data["timestamp"] = current_time.isoformat()
            
        print(f"  📍 [{i+1}/{total}] lat={data['lat']:.5f} lon={data['lng']:.5f} | vel={data['speed']:.1f} | {data['timestamp']}")
        
        try:
            process_gps_point(vehicle.id, data)
        except Exception as e:
            print(f"❌ Error: {e}")
            
        # Avanzar el tiempo simulado en 1 segundo por cada punto para evitar tiempos duplicados
        current_time += datetime.timedelta(seconds=1)
        time.sleep(SEND_INTERVAL)

    print("\n>> FASE 4: IDLE_TOO_LONG (Ralentí)")
    print("   Deteniendo vehículo y saltando 16 minutos en el tiempo...")
    last_point = route[-1]
    current_time += datetime.timedelta(minutes=16)
    data = {**last_point, "speed": 0.0, "heading": 0.0, "ignition": True, "timestamp": current_time.isoformat()}
    process_gps_point(vehicle.id, data)
    print("   Punto IDLE enviado.")
    
    time.sleep(2)
    
    print("\n>> FASE 5: TRIP COMPLETION (Fin de Viaje)")
    print("   Apagando motor y saltando 11 minutos adicionales...")
    current_time += datetime.timedelta(minutes=11)
    data = {**last_point, "speed": 0.0, "heading": 0.0, "ignition": False, "timestamp": current_time.isoformat()}
    process_gps_point(vehicle.id, data)
    print("   Punto de FIN DE VIAJE enviado. Revisa tu frontend.")

if __name__ == "__main__":
    simulate_trip()