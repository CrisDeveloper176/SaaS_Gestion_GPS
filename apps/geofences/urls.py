from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GeofenceViewSet

router = DefaultRouter()
router.register(r'', GeofenceViewSet, basename='geofence')

urlpatterns = [
    path('', include(router.urls)),
]
