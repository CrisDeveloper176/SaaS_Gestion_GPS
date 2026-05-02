"""
URL configuration for fleet_backend project.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # OpenAPI Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Prometheus Metrics
    path('', include('django_prometheus.urls')),
    
    # API endpoints
    path('api/auth/', include('apps.authentication.urls')),
    path('api/fleet/', include('apps.fleet.urls')),
    path('api/gps/', include('apps.gps.urls')),
    path('api/alerts/', include('apps.alerts.urls')),
    path('api/geofences/', include('apps.geofences.urls')),
    path('api/analytics/summary/', __import__('apps.fleet.analytics', fromlist=['DashboardSummaryView']).DashboardSummaryView.as_view(), name='analytics-summary'),
    
    # Health check
    path('api/health/', lambda request: __import__('django').http.JsonResponse({"status": "healthy"}), name='health_check'),
]
