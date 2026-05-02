from rest_framework import permissions

class IsTenantMember(permissions.BasePermission):
    """
    Controla que el usuario pertenece a un tenant vido.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.tenant
        )

class IsOrgAdmin(permissions.BasePermission):
    """
    Permite acceso slo a usuarios con rol ORG_ADMIN.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.tenant and
            request.user.role in ['SUPER_ADMIN', 'ORG_ADMIN']
        )
