import os
import secrets

from .settings import *
from .settings import BASE_DIR


ALLOWED_HOSTS = ['.azurecontainerapps.io', 'localhost']
CSRF_TRUSTED_ORIGINS = ['https://*.azurecontainerapps.io']

CORS_ALLOWED_ORIGINS = [
    "https://agreeable-stone-0bd82ae10.1.azurestaticapps.net",
]
CORS_ALLOW_CREDENTIALS = True

DEBUG = False
DEBUG_PROPAGATE_EXCEPTIONS = True
SECRET_KEY = os.getenv('AZURE_SECRET_KEY') or secrets.token_hex()

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

CONNECTION = os.environ['AZURE_POSTGRESQL_CONNECTIONSTRING']
CONNECTION_STR = {pair.split('=')[0]: pair.split('=')[1]
                  for pair in CONNECTION.split(' ')}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": CONNECTION_STR['dbname'],
        "HOST": CONNECTION_STR['host'],
        "USER": CONNECTION_STR['user'],
        "PASSWORD": CONNECTION_STR['password'],
    }
}

STORAGES["staticfiles"] = {
    "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
}
