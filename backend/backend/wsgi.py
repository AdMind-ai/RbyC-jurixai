"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

settings_module = ''
if 'RUNNING_IN_PRODUCTION' in os.environ:
    settings_module = 'backend.azure-production'
elif 'WEBSITE_HOSTNAME' in os.environ:
    settings_module = 'backend.production'
else:
    settings_module = 'backend.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()
