from rest_framework_simplejwt.tokens import AccessToken

class TenantAccessToken(AccessToken):
    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)

        # Inyectar tenant_id y role
        if hasattr(user, 'tenant') and user.tenant:
            token['tenant_id'] = user.tenant.id
        token['role'] = user.role

        return token
