import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

app = Celery('fleet_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'detect-trips-every-5-minutes': {
        'task': 'tasks.gps_tasks.run_trip_detection_for_all_vehicles',
        'schedule': crontab(minute='*/5'),
    },
}
