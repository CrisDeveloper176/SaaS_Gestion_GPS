from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_datetime
from .authentication import DeviceAPIKeyAuthentication
from .serializers import GpsIngestSerializer
from tasks.gps_tasks import process_gps_point

class GpsIngestView(APIView):
    authentication_classes = [DeviceAPIKeyAuthentication]
    permission_classes = [] # Allow any device with valid auth

    def post(self, request, *args, **kwargs):
        serializer = GpsIngestSerializer(data=request.data)
        if serializer.is_valid():
            vehicle = request.vehicle
            # Disparar tarea en Celery
            # We must pass basic types, request.data is just dict.
            data = serializer.validated_data
            # Convert datetime to ISO string for celery JSON serialization
            data['timestamp'] = data['timestamp'].isoformat()
            
            process_gps_point.delay(vehicle.id, data)
            
            return Response({'status': 'queued'}, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Trip, GpsPoint
from .serializers import TripSerializer, GpsPointHistorySerializer
from .filters import TripFilter, GpsPointHistoryFilter

class TripListView(generics.ListAPIView):
    queryset = Trip.objects.all().order_by('-start_time')
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TripFilter

class TripDetailView(generics.RetrieveAPIView):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

class HistoryView(generics.ListAPIView):
    queryset = GpsPoint.objects.all().order_by('timestamp')
    serializer_class = GpsPointHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = GpsPointHistoryFilter
    pagination_class = None
