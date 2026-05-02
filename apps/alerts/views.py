from rest_framework import viewsets, mixins, generics
from rest_framework.permissions import IsAuthenticated
from .models import Alert, AlertRule
from .serializers import AlertSerializer, AlertRuleSerializer

class AlertRuleViewSet(viewsets.ModelViewSet):
    """
    CRUD completo para reglas de alertas del tenant.
    """
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AlertRule.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


class AlertListView(generics.ListAPIView):
    """
    Listado histórico de alertas disparadas.
    """
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Alert.objects.filter(rule__tenant=self.request.user.tenant)
        
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read_bool)
            
        vehicle_id = self.request.query_params.get('vehicle_id')
        if vehicle_id:
            queryset = queryset.filter(vehicle_id=vehicle_id)
            
        return queryset

class AlertUpdateView(generics.UpdateAPIView):
    """
    Para marcar una alerta como leída (PATCH).
    """
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Alert.objects.filter(rule__tenant=self.request.user.tenant)
