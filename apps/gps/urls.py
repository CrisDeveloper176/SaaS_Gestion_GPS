from django.urls import path
from .views import GpsIngestView, TripListView, TripDetailView, HistoryView

urlpatterns = [
    path('ingest/', GpsIngestView.as_view(), name='gps-ingest'),
    path('trips/', TripListView.as_view(), name='trip-list'),
    path('trips/<int:pk>/', TripDetailView.as_view(), name='trip-detail'),
    path('history/', HistoryView.as_view(), name='gps-history'),
]
