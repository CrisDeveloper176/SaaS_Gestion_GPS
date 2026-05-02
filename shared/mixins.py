class TenantFilterMixin:
    """
    Mixin para ViewSets.
    Filtra automticamente el queryset en base al tenant_id del usuario autenticado.
    Asume que el modelo tiene un campo 'tenant'.
    """
    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return qs.filter(tenant=self.request.tenant)
        elif hasattr(self.request.user, 'tenant') and self.request.user.tenant:
            return qs.filter(tenant=self.request.user.tenant)
        return qs.none() # Fallback si no hay tenant
        
    def perform_create(self, serializer):
        # Asigna el tenant automticamente al crear un registro
        tenant = None
        if hasattr(self.request, 'tenant') and self.request.tenant:
            tenant = self.request.tenant
        elif hasattr(self.request.user, 'tenant') and self.request.user.tenant:
            tenant = self.request.user.tenant
        serializer.save(tenant=tenant)
