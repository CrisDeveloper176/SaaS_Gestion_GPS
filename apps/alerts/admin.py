from django.contrib import admin
from .models import AlertRule, Alert

@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'vehicle', 'alert_type', 'threshold', 'is_active')
    list_filter = ('alert_type', 'is_active', 'tenant')
    search_fields = ('tenant__name', 'vehicle__plate')

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'rule', 'timestamp', 'is_read')
    list_filter = ('is_read', 'rule__alert_type')
    search_fields = ('vehicle__plate',)
