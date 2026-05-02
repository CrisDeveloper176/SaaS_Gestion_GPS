from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Geofence
from .serializers import GeofenceSerializer

class GeofenceViewSet(viewsets.ModelViewSet):
    serializer_class = GeofenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Geofence.objects.filter(tenant=self.request.user.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)
