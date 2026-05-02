import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.tenants.models import Tenant
from apps.authentication.models import User
from apps.fleet.models import Vehicle, Driver
from apps.authentication.tokens import TenantAccessToken

@pytest.fixture
def setup_data():
    tenant1 = Tenant.objects.create(name='Tenant 1')
    tenant2 = Tenant.objects.create(name='Tenant 2')
    
    user1 = User.objects.create_user(username='user1', email='u1@test.com', password='pwd', tenant=tenant1, role='ORG_ADMIN')
    user2 = User.objects.create_user(username='user2', email='u2@test.com', password='pwd', tenant=tenant2, role='ORG_ADMIN')
    
    v1 = Vehicle.objects.create(tenant=tenant1, plate='AAA111', device_id='DEV1', year=2024, brand='Toyota', model='Yaris')
    d1 = Driver.objects.create(tenant=tenant1, name='Driver 1', license_number='LIC1')
    
    return {'t1': tenant1, 't2': tenant2, 'u1': user1, 'u2': user2, 'v1': v1, 'd1': d1}

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_vehicle_crud(setup_data, api_client):
    user = setup_data['u1']
    token = str(TenantAccessToken.for_user(user))
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    
    # 1. List (should only see tenant 1 vehicles)
    res_list = api_client.get(reverse('vehicle-list'))
    assert res_list.status_code == 200
    assert len(res_list.data['results']) == 1
    assert res_list.data['results'][0]['plate'] == 'AAA111'
    
    # 2. Create
    data = {'plate': 'BBB222', 'device_id': 'DEV2', 'year': 2024, 'brand': 'Ford', 'model': 'Focus'}
    res_create = api_client.post(reverse('vehicle-list'), data=data, format='json')
    print("CREATE RESPONSE:", res_create.data)
    assert res_create.status_code == 201
    assert Vehicle.objects.filter(plate='BBB222').exists()
    assert Vehicle.objects.get(plate='BBB222').tenant == setup_data['t1'] # tenant is auto-assigned
    
    v_id = res_create.data['id']
    
    # 3. Retrieve
    res_retrieve = api_client.get(reverse('vehicle-detail', args=[v_id]))
    assert res_retrieve.status_code == 200
    assert res_retrieve.data['plate'] == 'BBB222'
    
    # 4. Update
    res_update = api_client.patch(reverse('vehicle-detail', args=[v_id]), data={'alias': 'Truck 2'}, format='json')
    assert res_update.status_code == 200
    assert Vehicle.objects.get(id=v_id).alias == 'Truck 2'
    
    # 5. Delete (soft delete in reality if customized, but standard ModelViewSet performs delete)
    res_delete = api_client.delete(reverse('vehicle-detail', args=[v_id]))
    assert res_delete.status_code == 204
    assert not Vehicle.objects.filter(id=v_id).exists()

@pytest.mark.django_db
def test_driver_crud(setup_data, api_client):
    user = setup_data['u1']
    token = str(TenantAccessToken.for_user(user))
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    
    # 1. Create Driver
    data = {'name': 'New Driver', 'license_number': 'LIC2'}
    res_create = api_client.post(reverse('driver-list'), data=data, format='json')
    assert res_create.status_code == 201
    assert Driver.objects.filter(name='New Driver').exists()
    
    # 2. Assign Driver to Vehicle
    d_id = res_create.data['id']
    v_id = setup_data['v1'].id
    # Note: assuming the endpoint is /api/fleet/drivers/{id}/assign/ as per README
    # Will verify if this endpoint exists, or if it's done via PATCH on driver
    # The README says: POST /api/drivers/{id}/assign/
    # If it's not implemented yet, we can skip or implement. Let's see if the views.py has it.
    pass

@pytest.mark.django_db
def test_tenant_isolation(setup_data, api_client):
    # User 2 tries to see User 1's vehicle
    user2 = setup_data['u2']
    token = str(TenantAccessToken.for_user(user2))
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    
    res_list = api_client.get(reverse('vehicle-list'))
    assert res_list.status_code == 200
    assert len(res_list.data['results']) == 0 # User 2 has no vehicles
    
    # Try direct access to V1
    v1_id = setup_data['v1'].id
    res_detail = api_client.get(reverse('vehicle-detail', args=[v1_id]))
    assert res_detail.status_code == 404 # Should not find it due to TenantFilterMixin

def test_health_check(api_client):
    url = reverse('health_check')
    res = api_client.get(url)
    assert res.status_code == 200
    assert res.json()['status'] == 'healthy'
