from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from shared.mixins import TenantFilterMixin
from .models import Vehicle, Driver
from .serializers import VehicleSerializer, DriverSerializer
from apps.authentication.permissions import IsTenantMember
from django_filters.rest_framework import DjangoFilterBackend

class VehicleViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsTenantMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'brand', 'fuel_type']
    search_fields = ['plate', 'alias']

    @action(detail=True, methods=["post"], url_path="generate-api-key")
    def generate_api_key(self, request, pk=None):
        vehicle = self.get_object()
        raw_key = vehicle.generate_api_key()
        return Response({"api_key": raw_key})

    @action(detail=True, methods=["post"], url_path="unassign-driver")
    def unassign_driver(self, request, pk=None):
        vehicle = self.get_object()
        if vehicle.current_driver:
            vehicle.current_driver = None
            vehicle.save(update_fields=['current_driver'])
            return Response({"status": "Conductor desvinculado"})
        return Response({"error": "No hay conductor asignado"}, status=400)

class DriverViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [IsTenantMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'license_number']
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        driver = self.get_object()
        vehicle_id = request.data.get("vehicle_id")
        
        if not vehicle_id:
            return Response({"error": "vehicle_id es requerido"}, status=400)
            
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id, tenant=request.tenant)
            
            # Asegurar que el conductor no esté en más de 1 vehículo a la vez
            # Lo desvinculamos de cualquier vehículo previo en este tenant
            Vehicle.objects.filter(current_driver=driver, tenant=request.tenant).update(current_driver=None)
            
            vehicle.current_driver = driver
            vehicle.save(update_fields=['current_driver'])
            return Response({"status": "asignado exitosamente"})
        except Vehicle.DoesNotExist:
            return Response({"error": "Vehículo no encontrado"}, status=404)
