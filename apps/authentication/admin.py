from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'tenant', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'groups')
    fieldsets = UserAdmin.fieldsets + (
        ('Fleet SaaS Data', {'fields': ('tenant', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Fleet SaaS Data', {'fields': ('tenant', 'role')}),
    )
