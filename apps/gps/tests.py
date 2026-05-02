import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.hashers import make_password
from apps.fleet.models import Vehicle
from apps.tenants.models import Tenant

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def setup_vehicle(db):
    tenant = Tenant.objects.create(name='Test Tenant')
    vehicle = Vehicle.objects.create(
        tenant=tenant,
        plate='XX1234',
        brand='Toyota',
        model='Yaris',
        year=2023,
        device_id='TRACKER-001',
        tracker_api_key=make_password('secret-key-123')
    )
    return vehicle

@pytest.mark.django_db
def test_gps_ingest_success(api_client, setup_vehicle, mocker):
    mocker.patch('apps.gps.views.process_gps_point.delay', return_value=None)

    payload = {
        "device_id": "TRACKER-001",
        "lat": -37.4734,
        "lng": -72.3441,
        "speed": 65.5,
        "heading": 180.0,
        "timestamp": "2026-04-17T14:30:00Z"
    }

    response = api_client.post(
        reverse('gps-ingest'),
        data=payload,
        format='json',
        HTTP_X_DEVICE_API_KEY='secret-key-123'
    )

    assert response.status_code == 202
    assert response.data['status'] == 'queued'

@pytest.mark.django_db
def test_gps_ingest_invalid_api_key(api_client, setup_vehicle):
    payload = {
        "device_id": "TRACKER-001",
        "lat": -37.4734,
        "lng": -72.3441,
        "speed": 65.5,
        "timestamp": "2026-04-17T14:30:00Z"
    }

    response = api_client.post(
        reverse('gps-ingest'),
        data=payload,
        format='json',
        HTTP_X_DEVICE_API_KEY='wrong-key'
    )

    assert response.status_code == 403

from datetime import datetime, timedelta
from django.utils import timezone
from apps.gps.models import GpsPoint, Trip
from apps.gps.services import process_trip_detection
from apps.authentication.models import User

@pytest.fixture
def setup_user_token(setup_vehicle):
    user = User.objects.create_user(
        username='test_api_user',
        email='user@test.com',
        password='testpass123',
        tenant=setup_vehicle.tenant
    )
    from apps.authentication.tokens import TenantAccessToken
    token = TenantAccessToken.for_user(user)
    return str(token)

@pytest.mark.django_db
def test_trip_detection_logic(setup_vehicle):
    base_time = timezone.now() - timedelta(hours=2)
    
    # 1. Crear puntos en movimiento (inicio del viaje)
    p1 = GpsPoint.objects.create(vehicle=setup_vehicle, lat=-33.0, lng=-70.0, speed=50, ignition=True, timestamp=base_time)
    p2 = GpsPoint.objects.create(vehicle=setup_vehicle, lat=-33.1, lng=-70.1, speed=60, ignition=True, timestamp=base_time + timedelta(minutes=5))

    
    res1 = process_trip_detection(setup_vehicle.id)
    assert res1['opened'] is not None, "Debería abrir un viaje al detectar movimiento"
    assert res1['closed'] is None
    
    trip = Trip.objects.get(vehicle=setup_vehicle)
    assert trip.end_time is None, "El viaje debe estar activo"
    
    # Verificar que los puntos fueron asignados al viaje
    p1.refresh_from_db()
    assert p1.trip_id == trip.id
    
    # 2. Simular detención prolongada (> 15 min) para cerrar el viaje
    p3 = GpsPoint.objects.create(vehicle=setup_vehicle, lat=-33.1, lng=-70.1, speed=0, timestamp=base_time + timedelta(minutes=10))
    p4 = GpsPoint.objects.create(vehicle=setup_vehicle, lat=-33.1, lng=-70.1, speed=0, timestamp=base_time + timedelta(minutes=30))
    
    res2 = process_trip_detection(setup_vehicle.id)
    assert res2['closed'] is not None, "Debería cerrar el viaje al detectar parada larga"
    
    trip.refresh_from_db()
    assert trip.end_time == p3.timestamp, "El fin del viaje debe coincidir con el inicio de la detención"
    assert trip.distance_meters > 0, "Debe haber calculado la distancia"
    assert trip.avg_speed > 0
    assert trip.duration == (p3.timestamp - trip.start_time)

@pytest.mark.django_db
def test_trip_and_history_endpoints(api_client, setup_vehicle, setup_user_token):
    # Setup data (1 cerrado, 1 punto)
    base_time = timezone.now()
    trip = Trip.objects.create(
        vehicle=setup_vehicle, 
        start_time=base_time - timedelta(hours=1),
        end_time=base_time,
        distance_meters=15000,
        max_speed=80,
        avg_speed=50
    )
    point = GpsPoint.objects.create(
        vehicle=setup_vehicle, trip=trip, lat=-33.0, lng=-70.0, speed=50, timestamp=base_time - timedelta(minutes=30)
    )
    
    headers = {'HTTP_AUTHORIZATION': f'Bearer {setup_user_token}'}
    
    # Test Trips List
    res_trips = api_client.get(reverse('trip-list'), **headers)
    assert res_trips.status_code == 200
    assert len(res_trips.data['results']) == 1
    assert res_trips.data['results'][0]['distance_meters'] == 15000.0
    
    # Test History List
    res_hist = api_client.get(f"{reverse('gps-history')}?trip_id={trip.id}", **headers)
    assert res_hist.status_code == 200
    assert len(res_hist.data['results']) == 1
    assert res_hist.data['results'][0]['id'] == point.id
