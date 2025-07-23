# celery.py

import os
from celery import Celery

settings_module = ''
if 'RUNNING_IN_PRODUCTION' in os.environ:
    settings_module = 'backend.azure-production'
elif 'WEBSITE_HOSTNAME' in os.environ:
    settings_module = 'backend.production'
else:
    settings_module = 'backend.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)


app = Celery("backend")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
