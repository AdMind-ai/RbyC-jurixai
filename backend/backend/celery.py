# celery.py

import os
from celery import Celery
from .settings_selector import get_settings_module

os.environ.setdefault('DJANGO_SETTINGS_MODULE', get_settings_module())


app = Celery("backend")

app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
