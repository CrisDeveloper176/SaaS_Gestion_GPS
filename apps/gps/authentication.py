from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.hashers import check_password
from apps.fleet.models import Vehicle

class DeviceAPIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        api_key = request.headers.get('X-Device-API-Key')
        if not api_key:
            return None
            
        # Para DRF request.data procesa el JSON
        try:
            device_id = request.data.get('device_id')
        except Exception:
            device_id = None
            
        if not device_id:
            raise AuthenticationFailed('device_id no proporcionado en el payload para autenticar la API Key.')
            
        try:
            vehicle = Vehicle.objects.get(device_id=device_id)
        except Vehicle.DoesNotExist:
            raise AuthenticationFailed('Dispositivo no encontrado.')

        if not vehicle.tracker_api_key:
            raise AuthenticationFailed('El vehículo no tiene una API Key configurada.')

        if not check_password(api_key, vehicle.tracker_api_key):
            raise AuthenticationFailed('API Key inválida.')

        # En DRF `request.user` se utiliza para autorizar.
        # Al no tener un usuario real, enviamos una instancia dummy o un "DeviceUser".
        # Asignamos temporalmente el vehiculo a una propiedad
        request.vehicle = vehicle
        
        # Devolvemos un tuple (user, auth)
        return (None, api_key)
