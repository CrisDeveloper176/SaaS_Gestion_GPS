import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from apps.tenants.models import Tenant
from apps.authentication.models import User
from apps.authentication.tokens import TenantAccessToken

@pytest.fixture
def setup_org():
    tenant = Tenant.objects.create(name='Test Org')
    admin_user = User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='pass',
        tenant=tenant,
        role='ORG_ADMIN'
    )
    viewer_user = User.objects.create_user(
        username='viewer',
        email='viewer@test.com',
        password='pass',
        tenant=tenant,
        role='VIEWER'
    )
    return tenant, admin_user, viewer_user

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_org_users_list(setup_org, api_client):
    tenant, admin_user, viewer_user = setup_org
    token = str(TenantAccessToken.for_user(admin_user))
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    
    url = reverse('org_users_list')
    res = api_client.get(url)
    
    assert res.status_code == 200
    assert len(res.data['results']) == 2

@pytest.mark.django_db
def test_user_invite_as_admin(setup_org, api_client):
    tenant, admin_user, viewer_user = setup_org
    token = str(TenantAccessToken.for_user(admin_user))
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    
    url = reverse('org_users_invite')
    payload = {'email': 'new_driver@test.com', 'role': 'DRIVER'}
    res = api_client.post(url, data=payload, format='json')
    
    assert res.status_code == 201
    assert User.objects.filter(email='new_driver@test.com').exists()

@pytest.mark.django_db
def test_user_invite_as_viewer_fails(setup_org, api_client):
    tenant, admin_user, viewer_user = setup_org
    token = str(TenantAccessToken.for_user(viewer_user))
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    
    url = reverse('org_users_invite')
    payload = {'email': 'hacker@test.com', 'role': 'ORG_ADMIN'}
    res = api_client.post(url, data=payload, format='json')
    
    assert res.status_code == 403

@pytest.mark.django_db
def test_user_role_update(setup_org, api_client):
    tenant, admin_user, viewer_user = setup_org
    token = str(TenantAccessToken.for_user(admin_user))
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
    
    url = reverse('org_users_role_update', kwargs={'pk': viewer_user.id})
    payload = {'role': 'MANAGER'}
    res = api_client.patch(url, data=payload, format='json')
    
    assert res.status_code == 200
    viewer_user.refresh_from_db()
    assert viewer_user.role == 'MANAGER'
