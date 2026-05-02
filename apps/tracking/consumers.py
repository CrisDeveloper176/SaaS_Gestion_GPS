import json
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.authentication.models import User
from apps.authentication.tokens import TenantAccessToken

@database_sync_to_async
def get_user_and_tenant_from_token(token_str):
    try:
        token = TenantAccessToken(token_str)
        user = User.objects.get(id=token['user_id'])
        return user, token.get('tenant_id')
    except Exception:
        return AnonymousUser(), None

class TrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        # No cerramos de inmediato si falta el token en URL, 
        # esperamos mensaje de 'auth' segun requiere el frontend.
        self.authenticated = False
        self.tenant_id = None

    async def disconnect(self, close_code):
        if hasattr(self, 'fleet_group_name'):
            await self.channel_layer.group_discard(
                self.fleet_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')
        token_str = data.get('token')

        # Manejar autenticación vía mensaje (requerido por WebSocketContext.jsx)
        if msg_type == 'auth' and token_str:
            user, tenant_id = await get_user_and_tenant_from_token(token_str)
            if not user.is_anonymous and tenant_id:
                self.scope['user'] = user
                self.scope['tenant_id'] = tenant_id
                self.tenant_id = tenant_id
                self.authenticated = True
                
                # Ahora sí nos unimos al grupo del tenant
                self.fleet_group_name = f"fleet_{tenant_id}"
                await self.channel_layer.group_add(
                    self.fleet_group_name,
                    self.channel_name
                )
                return
            else:
                await self.close(code=4003) # Forbidden
                return

        if not self.authenticated:
            return

        action = data.get('action')
        vehicle_id = data.get('vehicle_id')
        
        if action == 'subscribe_vehicle' and vehicle_id:
            await self.channel_layer.group_add(
                f"vehicle_{vehicle_id}",
                self.channel_name
            )
        elif action == 'unsubscribe_vehicle' and vehicle_id:
            await self.channel_layer.group_discard(
                f"vehicle_{vehicle_id}",
                self.channel_name
            )

    async def vehicle_update(self, event):
        # Envía el envento broadcast
        await self.send(text_data=json.dumps(event))

    async def vehicle_offline(self, event):
        await self.send(text_data=json.dumps(event))

    async def alert_triggered(self, event):
        await self.send(text_data=json.dumps(event))

    async def trip_completed(self, event):
        await self.send(text_data=json.dumps(event))
