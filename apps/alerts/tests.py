import pytest
from django.utils import timezone
from datetime import timedelta
from apps.fleet.models import Vehicle
from apps.tenants.models import Tenant
from apps.alerts.models import AlertRule, Alert
from apps.alerts.tasks import evaluate_alerts
from django.contrib.auth.hashers import make_password

@pytest.fixture
def setup_vehicle(db):
    tenant = Tenant.objects.create(name='Test Tenant')
    vehicle = Vehicle.objects.create(
        tenant=tenant,
        plate='ALRT12',
        brand='Toyota',
        model='Yaris',
        year=2023,
        device_id='TRACKER-ALT',
        tracker_api_key=make_password('secret')
    )
    return vehicle

@pytest.mark.django_db
def test_evaluate_alerts_speeding_cooldown(setup_vehicle, mocker):
    from unittest.mock import AsyncMock
    # Mockear channel layer para no requerir Redis en los tests unitarios
    mock_layer = mocker.patch('apps.alerts.tasks.get_channel_layer').return_value
    mock_layer.group_send = AsyncMock()

    # 1. Crear regla de velocidad (> 100) con cooldown de 5 min
    rule = AlertRule.objects.create(
        tenant=setup_vehicle.tenant,
        alert_type='SPEEDING',
        threshold=100.0,
        cooldown_minutes=5
    )

    # 2. Evaluar punto 1: Velocidad 120 (debería disparar alerta)
    data1 = {'speed': 120, 'timestamp': timezone.now().isoformat()}
    res1 = evaluate_alerts(setup_vehicle.id, data1)
    
    assert len(res1['alerts_created']) == 1
    assert Alert.objects.count() == 1
    
    rule.refresh_from_db()
    assert rule.last_triggered is not None

    # 3. Evaluar punto 2: Velocidad 130 un minuto después (NO debería disparar, en cooldown)
    data2 = {'speed': 130, 'timestamp': timezone.now().isoformat()}
    res2 = evaluate_alerts(setup_vehicle.id, data2)
    
    assert len(res2['alerts_created']) == 0
    assert Alert.objects.count() == 1 # Aún hay 1 sola alerta
    
    # 4. Modificar last_triggered para simular que pasaron 6 minutos
    rule.last_triggered = timezone.now() - timedelta(minutes=6)
    rule.save()

    # 5. Evaluar punto 3: Velocidad 110 (debería disparar otra alerta)
    data3 = {'speed': 110, 'timestamp': timezone.now().isoformat()}
    res3 = evaluate_alerts(setup_vehicle.id, data3)

    assert len(res3['alerts_created']) == 1
    assert Alert.objects.count() == 2 # Ahora hay 2 alertas

@pytest.mark.django_db
def test_evaluate_alerts_idle_too_long(setup_vehicle, mocker):
    from unittest.mock import AsyncMock
    mock_layer = mocker.patch('apps.alerts.tasks.get_channel_layer').return_value
    mock_layer.group_send = AsyncMock()

    rule = AlertRule.objects.create(
        tenant=setup_vehicle.tenant,
        alert_type='IDLE_TOO_LONG',
        threshold=10.0,
        cooldown_minutes=5
    )

    data_moving = {'speed': 50, 'ignition': True, 'timestamp': timezone.now().isoformat()}
    res_moving = evaluate_alerts(setup_vehicle.id, data_moving)
    assert len(res_moving['alerts_created']) == 0 # No debe disparar porque está en movimiento

    data_idle = {'speed': 0, 'ignition': True, 'timestamp': timezone.now().isoformat()}
    res_idle = evaluate_alerts(setup_vehicle.id, data_idle)
    assert len(res_idle['alerts_created']) == 1 # Debe disparar porque simulamos la condición inmediata
    assert Alert.objects.filter(rule=rule).count() == 1

@pytest.fixture
def setup_user_token_alerts(setup_vehicle):
    from apps.authentication.models import User
    from apps.authentication.tokens import TenantAccessToken
    user = User.objects.create_user(
        username='alert_tester',
        email='alerts@test.com',
        password='testpass123',
        tenant=setup_vehicle.tenant
    )
    token = TenantAccessToken.for_user(user)
    return str(token)

@pytest.mark.django_db
def test_alert_api_endpoints(setup_vehicle, setup_user_token_alerts):
    from rest_framework.test import APIClient
    from django.urls import reverse
    api_client = APIClient()
    headers = {'HTTP_AUTHORIZATION': f'Bearer {setup_user_token_alerts}'}

    # 1. Crear una regla vía API
    rule_data = {
        'alert_type': 'SPEEDING',
        'threshold': 120.0,
        'cooldown_minutes': 10
    }
    # La URL base del enrutador de reglas es "api/alerts/rules/"
    res_create = api_client.post('/api/alerts/rules/', data=rule_data, format='json', **headers)
    assert res_create.status_code == 201
    assert res_create.data['threshold'] == 120.0
    rule_id = res_create.data['id']

    # 2. Crear una alerta en la DB
    Alert.objects.create(
        rule_id=rule_id,
        vehicle=setup_vehicle,
        message="Test alert",
        timestamp=timezone.now(),
        is_read=False
    )

    # 3. Listar alertas
    res_list = api_client.get('/api/alerts/', **headers)
    assert res_list.status_code == 200
    assert len(res_list.data['results']) == 1
    alert_id = res_list.data['results'][0]['id']
    assert res_list.data['results'][0]['is_read'] == False

    # 4. Marcar alerta como leída (PATCH)
    res_patch = api_client.patch(f'/api/alerts/{alert_id}/', data={'is_read': True}, format='json', **headers)
    assert res_patch.status_code == 200
    assert res_patch.data['is_read'] == True
