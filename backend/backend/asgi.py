"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

settings_module = ''
if 'RUNNING_IN_PRODUCTION' in os.environ:
    settings_module = 'backend.azure-production'
elif 'WEBSITE_HOSTNAME' in os.environ:
    settings_module = 'backend.production'
else:
    settings_module = 'backend.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_asgi_application()
