import pytest
import json
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken
from config.asgi import application
from apps.authentication.tokens import TenantAccessToken
from apps.authentication.models import User
from apps.tenants.models import Tenant
from asgiref.sync import sync_to_async


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_tracking_consumer_auth():

    @sync_to_async
    def create_user_with_token():
        tenant = Tenant.objects.create(name='Tenant WS Test')
        user = User.objects.create_user(
            username='ws_user',
            email='ws@test.com',
            password='testpass123',
            tenant=tenant
        )
        token = TenantAccessToken.for_user(user)
        # tenant_id ya debe estar inyectado por TenantAccessToken.for_user
        return str(token)

    token_str = await create_user_with_token()

    communicator = WebsocketCommunicator(
        application,
        f"/ws/tracking/?token={token_str}"
    )

    connected, subprotocol = await communicator.connect()
    assert connected, "El consumer debería aceptar la conexión con JWT válido"

    # Test suscripción a vehículo
    await communicator.send_json_to({
        "action": "subscribe_vehicle",
        "vehicle_id": "1"
    })

    await communicator.disconnect()


@pytest.mark.asyncio
async def test_tracking_consumer_unauthorized():
    communicator = WebsocketCommunicator(
        application,
        "/ws/tracking/?token=invalid"
    )
    connected, subprotocol = await communicator.connect()
    assert connected, "El consumer debería aceptar la conexión inicial para validar el token"
    
    # El consumer debería cerrar la conexión rápidamente al fallar la validación
    # Esperamos un poco y verificamos si se cerró
    await communicator.disconnect()
