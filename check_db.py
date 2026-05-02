import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute('SELECT version()')
    print('DB OK:', c.fetchone()[0][:60])
    c.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
    ext = c.fetchone()
    print('TimescaleDB extension:', ext[0] if ext else 'NOT FOUND in current DB')
print('Connection host:', connection.settings_dict['HOST'])
print('Connection port:', connection.settings_dict['PORT'])
print('Connection name:', connection.settings_dict['NAME'])
