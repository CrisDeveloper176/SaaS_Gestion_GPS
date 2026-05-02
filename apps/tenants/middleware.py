from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken
import jwt

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.tenant = None
        
        # Primero intentamos resolver si el usuario ya est autenticado
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'tenant'):
                request.tenant = request.user.tenant
                return

        # Si no, intentamos leer el JWT del header de Authorization
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token_string = auth_header.split(' ')[1]
            try:
                # Decodificamos el token sin verificar la firma slo para extraer el tenant_id
                # El DRF ya se encargar de validar la firma despus.
                unverified_payload = jwt.decode(token_string, options={"verify_signature": False})
                tenant_id = unverified_payload.get('tenant_id')
                if tenant_id:
                    from apps.tenants.models import Tenant
                    try:
                        tenant = Tenant.objects.get(id=tenant_id)
                        request.tenant = tenant
                    except Tenant.DoesNotExist:
                        pass
            except Exception:
                pass
