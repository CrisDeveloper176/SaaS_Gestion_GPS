from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlertRuleViewSet, AlertListView, AlertUpdateView

router = DefaultRouter()
router.register(r'rules', AlertRuleViewSet, basename='alertrule')

urlpatterns = [
    path('', AlertListView.as_view(), name='alert-list'),
    path('<int:pk>/', AlertUpdateView.as_view(), name='alert-update'),
    path('', include(router.urls)),
]
