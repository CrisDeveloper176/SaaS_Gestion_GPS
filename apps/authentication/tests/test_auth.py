import pytest
from rest_framework.test import APIClient
from apps.tenants.models import Tenant
from apps.authentication.models import User
from django.urls import reverse

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
def test_user_registration(api_client):
    url = reverse('auth_register')
    data = {
        'username': 'admin_user',
        'email': 'admin@test.com',
        'password': 'testpassword123!',
        'tenant_name': 'My Company'
    }
    response = api_client.post(url, data)
    
    assert response.status_code == 201
    assert 'user' in response.data
    assert response.data['user']['username'] == 'admin_user'
    
    # Check if Tenant was created
    tenant = Tenant.objects.get(name='My Company')
    assert tenant is not None
    
    # Check if user has ORG_ADMIN role and is assigned to tenant
    user = User.objects.get(username='admin_user')
    assert user.role == 'ORG_ADMIN'
    assert user.tenant == tenant

@pytest.mark.django_db
def test_user_login(api_client):
    # Setup
    tenant = Tenant.objects.create(name='Login Company')
    user = User.objects.create_user(
        username='login_user',
        email='login@test.com',
        password='testpassword123!',
        tenant=tenant,
        role='DRIVER'
    )
    
    url = reverse('token_obtain_pair')
    data = {
        'username': 'login_user',
        'password': 'testpassword123!'
    }
    
    response = api_client.post(url, data)
    
    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data
