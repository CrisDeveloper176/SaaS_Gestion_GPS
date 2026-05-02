import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()
from apps.authentication.models import User
user = User.objects.get(username='admin')
print(f"User: {user.username}, Role: {user.role}, Tenant: {user.tenant}")
